#!/usr/bin/env python3
"""TACHYON RETROBOUND R1 paired validation (synthetic, opt-in).

All arms receive the SAME b per trial. The forward control creates its full
history BEFORE pseudo-random b is drawn, then two offline conditional solvers
receive b. This does NOT create physical late entropy or a real pre-frozen log.
"""
from __future__ import annotations

from hashlib import sha256
import argparse
import json
import math
import random

from tools import tachyon_retrobound_r1 as retro

SCHEMA = "janus.demihead.tachyon.retrobound_r1.paired_validation.v1"
ARMS = ("two_boundary", "causal_null", "postselection")


def seeded(seed: int, role: str) -> random.Random:
    raw = sha256(("RETROBOUND-PAIRED-v1|" + str(seed) + "|" + role).encode()).digest()
    return random.Random(int.from_bytes(raw, "big"))


def paired_validation(
    *, steps: int = 8, rho: float = 0.85, eta: float = 0.9,
    trials: int = 40000, seed: int = 20261123
) -> dict:
    retro.validate(steps, rho, eta)
    if type(trials) is not int or not 1000 <= trials <= 2000000:
        raise ValueError("trials must be integer 1000..2000000")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be nonnegative integer")

    rng_choice = seeded(seed, "late_choice")
    rng_null = seeded(seed, "causal_null")
    rng_bridge = seeded(seed, "two_boundary")
    rng_post = seeded(seed, "postselection")
    messages = {b: retro.transfer_messages(steps, rho, eta, b) for b in retro.SPINS}

    b_hash = sha256()
    null_record_hash = sha256()
    totals = {a: {"n": 0, "choice_n": {-1: 0, 1: 0},
                  "visible_plus": {-1: 0, 1: 0},
                  "hidden_xb": 0, "last_xb": 0, "draws": 0}
              for a in ARMS}
    paired_difference_sum = paired_difference_square_sum = 0

    for _ in range(trials):
        # Synthetic null path is fixed BEFORE this loop's b is sampled.
        null_path = retro.sample_forward(rng_null, steps, rho)
        public_null = retro.accessible_record(null_path)
        null_record_hash.update(bytes(0 if y == -1 else 1 for y in public_null))
        b = 1 if rng_choice.getrandbits(1) else -1
        b_hash.update(b"+" if b == 1 else b"-")

        bridge_path = retro.sample_bridge(rng_bridge, *messages[b], rho)
        post_path, post_draws = retro.sample_postselection(rng_post, steps, rho, eta, b)
        paths = {
            "two_boundary": (bridge_path, 1),
            "causal_null": (null_path, 1),
            "postselection": (post_path, post_draws),
        }
        for arm, (path, draws) in paths.items():
            row = totals[arm]
            row["n"] += 1
            row["choice_n"][b] += 1
            row["visible_plus"][b] += int(retro.accessible_record(path)[0] == 1)
            row["hidden_xb"] += b * path[0]
            row["last_xb"] += b * path[-1]
            row["draws"] += draws

        difference = b * (bridge_path[0] - post_path[0])
        paired_difference_sum += difference
        paired_difference_square_sum += difference * difference

    theory = eta * rho ** steps
    p_visible = (1 + rho) / 2
    summary = {}
    for arm in ARMS:
        row = totals[arm]
        c = row["choice_n"]
        if min(c.values()) == 0:
            raise ValueError("both late-choice values required")
        hidden_corr = row["hidden_xb"] / trials
        endpoint_corr = row["last_xb"] / trials
        expected_corr = theory if arm != "causal_null" else 0.0
        expected_endpoint = eta if arm != "causal_null" else 0.0
        se_hidden = math.sqrt((1 - expected_corr ** 2) / trials)
        se_endpoint = math.sqrt((1 - expected_endpoint ** 2) / trials)
        delta = row["visible_plus"][1] / c[1] - row["visible_plus"][-1] / c[-1]
        visible_se = math.sqrt(p_visible * (1 - p_visible) * (1 / c[1] + 1 / c[-1]))
        summary[arm] = {
            "n": trials,
            "choice_n": {str(k): v for k, v in c.items()},
            "common_late_choice_schedule_sha256": b_hash.hexdigest(),
            "hidden_early_boundary_correlation": hidden_corr,
            "expected_hidden_correlation": expected_corr,
            "hidden_correlation_z": (hidden_corr - expected_corr) / se_hidden,
            "terminal_boundary_correlation": endpoint_corr,
            "expected_terminal_correlation": expected_endpoint,
            "terminal_correlation_z": (endpoint_corr - expected_endpoint) / se_endpoint,
            "early_public_parity_difference": delta,
            "early_public_parity_difference_se": visible_se,
            "early_public_parity_z": delta / visible_se,
            "total_forward_draws": row["draws"],
            "draws_per_accepted_history": row["draws"] / trials,
        }

    # Since the models use separate trajectory RNGs under the SAME b_i,
    # calculate paired uncertainty from the trialwise hidden differences.
    mean_difference = paired_difference_sum / trials
    variance_d = max(
        0.0,
        (paired_difference_square_sum - trials * mean_difference ** 2) / (trials - 1),
    )
    se_difference = math.sqrt(variance_d / trials)
    pair_z = mean_difference / se_difference if se_difference > 0 else 0.0

    max_enum_steps = min(steps, 12)
    exact_public_tv = retro.exact_tv(
        max_enum_steps, rho, eta, retro.accessible_record
    )
    exact_hidden_tv = retro.exact_tv(
        max_enum_steps, rho, eta, lambda path: path[0]
    )

    checks = {
        "all_arms_shared_identical_future_choice_schedule": (
            len({row["common_late_choice_schedule_sha256"] for row in summary.values()}) == 1
            and all(row["n"] == trials for row in summary.values())
        ),
        "boundary_transfer_exact": math.isclose(
            retro.hidden_mean(steps, rho, eta, 1, 0), theory, abs_tol=1e-11
        ),
        "full_public_parity_exact_tv_zero": exact_public_tv < 1e-10,
        "private_hidden_spin_nonzero_matches_model": (
            abs(exact_hidden_tv - eta * rho ** max_enum_steps) < 1e-10
        ),
        "two_boundary_theory_within_5sigma": abs(summary["two_boundary"]["hidden_correlation_z"]) < 5,
        "causal_null_hidden_zero_within_5sigma": abs(summary["causal_null"]["hidden_correlation_z"]) < 5,
        "postselection_theory_within_5sigma": abs(summary["postselection"]["hidden_correlation_z"]) < 5,
        "two_boundary_postselection_paired_agreement_within_5sigma": abs(pair_z) < 5,
        "all_public_early_parity_no_signal_within_5sigma": all(
            abs(row["early_public_parity_z"]) < 5 for row in summary.values()
        ),
        "all_terminal_correlations_match_theory_within_5sigma": all(
            abs(row["terminal_correlation_z"]) < 5 for row in summary.values()
        ),
        "postselection_forward_cost_is_accounted": (
            summary["postselection"]["total_forward_draws"] >= trials
        ),
    }

    return {
        "schema": SCHEMA,
        "status": "PAIRED_SYNTHETIC_VALIDATION_ONLY__PHYSICS_HOLD",
        "config": {"steps": steps, "rho": rho, "eta": eta,
                   "trials_per_arm": trials, "seed": seed},
        "source": {
            "port_module": "tools/tachyon_retrobound_r1.py",
            "original_r1_sha256": retro.SOURCE_SHA256,
            "all_arms_common_future_choice_schedule_sha256": b_hash.hexdigest(),
            "causal_null_prechoice_public_record_sha256": null_record_hash.hexdigest(),
            "hashes_are_deterministic_simulation_receipts_not_external_timestamps": True,
        },
        "theory": {
            "expected_hidden_correlation_if_conditioned": theory,
            "public_full_parity_exact_tv": exact_public_tv,
            "hidden_spin_exact_tv": exact_hidden_tv,
            "forward_postselection_acceptance_rate": 1 / (1 + eta),
            "forward_postselection_expected_draws_per_accepted": 1 + eta,
            "two_boundary_equals_postselection_in_exact_path_distribution": True,
        },
        "arms": summary,
        "paired_two_boundary_minus_postselection_hidden": {
            "difference": mean_difference,
            "standard_error": se_difference,
            "z": pair_z,
        },
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "scientific_boundary": {
            "future_choice_is_independent_physical_late_entropy": False,
            "early_record_was_immutable_and_external_before_late_choice": False,
            "no_signalling_of_public_parity_is_by_construction": True,
            "physical_retrocausal_effect_measured": False,
            "future_prediction_established": False,
            "external_reproduction_established": False,
            "postselection_excluded": False,
            "production_models_changed": False,
            "next_gate": "INDEPENDENT_LATE_CHOICE_AFTER_EXTERNAL_EARLY_FREEZE__FULL_TRIAL_LEDGER__PREDECLARED_STRONG_FORWARD_NULL",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", type=int, default=8)
    ap.add_argument("--rho", type=float, default=0.85)
    ap.add_argument("--eta", type=float, default=0.9)
    ap.add_argument("--trials", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=20261123)
    args = ap.parse_args()
    result = paired_validation(steps=args.steps, rho=args.rho, eta=args.eta,
                               trials=args.trials, seed=args.seed)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if not result["all_checks_passed"]:
        raise SystemExit("RETROBOUND_R1_PAIRED_VALIDATION_FAIL")


if __name__ == "__main__":
    main()
