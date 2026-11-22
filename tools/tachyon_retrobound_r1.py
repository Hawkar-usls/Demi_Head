#!/usr/bin/env python3
"""JANUS TACHYON / RETROBOUND R1, isolated offline two-boundary experiment.

Port of JANUS_RETROBOUND_R1/retrobound.py; source SHA256:
690e6d8fd4ca21f0b2a3cc1784ae1d265ce08c6817624efc9cbbab1a7157c3b8

A future boundary is supplied to an OFFLINE solver. This never gives a
pre-existing observer access to an independently generated future choice.
Neither conditional histories nor postselection demonstrate retrocausality.
No model weights, R5F graph semantics, physical clocks or production routes
are modified.
"""
from __future__ import annotations

from collections import defaultdict
from hashlib import sha256
from itertools import product
import argparse
import json
import math
import random

SPINS = (-1, 1)
SCHEMA = "janus.demihead.tachyon.retrobound.r1.simulation.v1"
SOURCE_SHA256 = "690e6d8fd4ca21f0b2a3cc1784ae1d265ce08c6817624efc9cbbab1a7157c3b8"


def validate(steps: int, rho: float, eta: float) -> None:
    if type(steps) is not int or not 1 <= steps <= 32:
        raise ValueError("steps must be integer in [1, 32]")
    if type(rho) not in (int, float) or not math.isfinite(rho) or not 0 <= rho < 1:
        raise ValueError("rho must be finite in [0, 1)")
    if type(eta) not in (int, float) or not math.isfinite(eta) or not 0 <= eta < 1:
        raise ValueError("eta must be finite in [0, 1)")


def transition(x: int, y: int, rho: float) -> float:
    return (1.0 + rho * x * y) / 2.0


def boundary_likelihood(last: int, b: int, eta: float) -> float:
    return 1.0 + eta * b * last


def path_probability(path: tuple[int, ...], b: int, rho: float, eta: float) -> float:
    """Exactly normalized path probability in the b-conditioned ensemble."""
    p = 0.5 * boundary_likelihood(path[-1], b, eta)
    for x, y in zip(path, path[1:]):
        p *= transition(x, y, rho)
    return p


def transfer_messages(steps: int, rho: float, eta: float, b: int):
    validate(steps, rho, eta)
    if b not in SPINS:
        raise ValueError("future boundary must be +/-1")
    alpha = [{x: 0.5 for x in SPINS}]
    for t in range(steps):
        alpha.append({
            y: sum(alpha[t][x] * transition(x, y, rho) for x in SPINS)
            for y in SPINS
        })
    beta = [None] * (steps + 1)
    beta[-1] = {x: boundary_likelihood(x, b, eta) for x in SPINS}
    for t in range(steps - 1, -1, -1):
        beta[t] = {
            x: sum(transition(x, y, rho) * beta[t + 1][y] for y in SPINS)
            for x in SPINS
        }
    z = sum(alpha[0][x] * beta[0][x] for x in SPINS)
    if not math.isclose(z, 1.0, abs_tol=1e-11, rel_tol=0):
        raise ArithmeticError("bridge normalization failed")
    return alpha, beta, z


def hidden_mean(steps: int, rho: float, eta: float, b: int, t: int) -> float:
    if type(t) is not int or not 0 <= t <= steps:
        raise ValueError("time index outside path")
    alpha, beta, z = transfer_messages(steps, rho, eta, b)
    return sum(x * alpha[t][x] * beta[t][x] for x in SPINS) / z


def _choose(weights: dict[int, float], rng: random.Random) -> int:
    total = weights[-1] + weights[1]
    if total <= 0 or not math.isfinite(total):
        raise ArithmeticError("invalid transition weights")
    return 1 if rng.random() < weights[1] / total else -1


def sample_bridge(
    rng: random.Random, alpha, beta, z: float, rho: float
) -> tuple[int, ...]:
    """Sample globally after the future boundary is ALREADY KNOWN."""
    path = [_choose({x: alpha[0][x] * beta[0][x] / z for x in SPINS}, rng)]
    for t in range(len(alpha) - 1):
        x = path[-1]
        path.append(_choose({
            y: transition(x, y, rho) * beta[t + 1][y] for y in SPINS
        }, rng))
    return tuple(path)


def sample_forward(rng: random.Random, steps: int, rho: float) -> tuple[int, ...]:
    """Causal null creates the full history before drawing future b."""
    path = [1 if rng.getrandbits(1) else -1]
    for _ in range(steps):
        path.append(path[-1] if rng.random() < (1 + rho) / 2 else -path[-1])
    return tuple(path)


def sample_postselection(
    rng: random.Random, steps: int, rho: float, eta: float, b: int
) -> tuple[tuple[int, ...], int]:
    """Forward-only rejection sampling with EXACT bridge law on accepted paths."""
    draws = 0
    while True:
        draws += 1
        path = sample_forward(rng, steps, rho)
        if rng.random() < boundary_likelihood(path[-1], b, eta) / (1 + eta):
            return path, draws


def accessible_record(path: tuple[int, ...]) -> tuple[int, ...]:
    """Only public early record admitted in R1: transitions, not hidden spins."""
    return tuple(x * y for x, y in zip(path, path[1:]))


def exact_tv(steps: int, rho: float, eta: float, observable) -> float:
    """Enumerated TV of b=+1 vs b=-1. Exponential, capped at 12 steps."""
    validate(steps, rho, eta)
    if steps > 12:
        raise ValueError("exact enumeration capped at 12 steps")
    distributions = {}
    for b in SPINS:
        dist = defaultdict(float)
        for path in product(SPINS, repeat=steps + 1):
            dist[observable(path)] += path_probability(path, b, rho, eta)
        distributions[b] = dist
    keys = distributions[-1].keys() | distributions[1].keys()
    return 0.5 * sum(abs(distributions[-1][x] - distributions[1][x]) for x in keys)


def _rng(seed: int, arm: str) -> random.Random:
    h = sha256(("JANUS-RETROBOUND-R1|" + str(seed) + "|" + arm).encode()).digest()
    return random.Random(int.from_bytes(h, "big"))


def _arm(
    name: str, rng: random.Random, trials: int, steps: int, rho: float, eta: float
) -> dict:
    bridge = {b: transfer_messages(steps, rho, eta, b) for b in SPINS} if name == "two_boundary" else {}
    choices = {-1: 0, 1: 0}
    visible_positive = {-1: 0, 1: 0}
    hidden_sum = endpoint_sum = draws_sum = 0
    for _ in range(trials):
        if name == "causal_null":
            path = sample_forward(rng, steps, rho)
            b = 1 if rng.getrandbits(1) else -1   # after complete path
            draws = 1
        else:
            b = 1 if rng.getrandbits(1) else -1   # known to offline solver
            if name == "two_boundary":
                path = sample_bridge(rng, *bridge[b], rho)
                draws = 1
            elif name == "postselection":
                path, draws = sample_postselection(rng, steps, rho, eta, b)
            else:
                raise ValueError("unknown arm")
        choices[b] += 1
        visible_positive[b] += int(accessible_record(path)[0] == 1)
        hidden_sum += b * path[0]
        endpoint_sum += b * path[-1]
        draws_sum += draws
    if not min(choices.values()):
        raise ArithmeticError("insufficient randomized future-choice coverage")
    delta = visible_positive[1] / choices[1] - visible_positive[-1] / choices[-1]
    baseline = (1 + rho) / 2
    se = math.sqrt(baseline * (1 - baseline) *
                   (1 / choices[1] + 1 / choices[-1]))
    expected = 0 if name == "causal_null" else eta * rho ** steps
    hidden_se = math.sqrt((1 - expected ** 2) / trials)
    return {
        "arm": name,
        "trials": trials,
        "hidden_past_future_correlation": hidden_sum / trials,
        "hidden_past_future_correlation_exact": expected,
        "hidden_correlation_z": (hidden_sum / trials - expected) / hidden_se,
        "future_endpoint_correlation": endpoint_sum / trials,
        "visible_early_parity_difference_by_b": delta,
        "visible_difference_z": delta / se if se else None,
        "forward_draws_per_accepted_path": draws_sum / trials,
        "physical_future_entropy_source": False,
    }


def run_experiment(
    steps: int = 8, rho: float = 0.85, eta: float = 0.9,
    trials: int = 40000, seed: int = 20261123
) -> dict:
    validate(steps, rho, eta)
    if type(trials) is not int or not 100 <= trials <= 2000000:
        raise ValueError("trials must be integer in [100, 2000000]")
    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be nonnegative integer")
    arms = {
        name: _arm(name, _rng(seed, name), trials, steps, rho, eta)
        for name in ("two_boundary", "causal_null", "postselection")
    }
    enum_steps = min(steps, 12)
    public_tv = exact_tv(enum_steps, rho, eta, accessible_record)
    private_tv = exact_tv(enum_steps, rho, eta, lambda path: path[0])
    theoretical_private_tv = eta * rho ** enum_steps
    checks = {
        "analytic_hidden_boundary_dependence": math.isclose(
            hidden_mean(steps, rho, eta, 1, 0), eta * rho ** steps, abs_tol=1e-11
        ),
        "exact_public_parity_record_no_signalling": public_tv < 1e-10,
        "exact_hidden_spin_tv": abs(private_tv - theoretical_private_tv) < 1e-10,
        "two_boundary_mc_5se": abs(arms["two_boundary"]["hidden_correlation_z"]) < 5,
        "causal_null_mc_5se": abs(arms["causal_null"]["hidden_correlation_z"]) < 5,
        "postselection_mc_5se": abs(arms["postselection"]["hidden_correlation_z"]) < 5,
        "two_boundary_public_no_signal_5se": abs(arms["two_boundary"]["visible_difference_z"]) < 5,
        "causal_null_public_no_signal_5se": abs(arms["causal_null"]["visible_difference_z"]) < 5,
        "postselection_public_no_signal_5se": abs(arms["postselection"]["visible_difference_z"]) < 5,
    }
    report = {
        "schema": SCHEMA,
        "algorithm": "TACHYON_RETROBOUND_R1_TWO_BOUNDARY_TRANSFER",
        "classification": "SYNTHETIC_OFFLINE_MODEL_ONLY",
        "config": {
            "steps": steps, "rho": rho, "eta": eta,
            "trials_per_arm": trials, "seed": seed,
            "randomness": "LOCAL_DETERMINISTIC_PSEUDORANDOM",
        },
        "source": {"original_retrobound_r1_py_sha256": SOURCE_SHA256},
        "theory": {
            "distribution": "0.5 * product(K_rho(x[t+1]|x[t])) * (1 + eta*b*x[T])",
            "hidden_early_correlation": eta * rho ** steps,
            "hidden_early_guess_accuracy_if_exposed": (1 + eta * rho ** steps) / 2,
            "public_parity_record_total_variation_distance": public_tv,
            "hidden_spin_total_variation_distance": private_tv,
            "postselection_exactly_equivalent": True,
            "postselection_acceptance_rate": 1 / (1 + eta),
            "enumeration_steps": enum_steps,
        },
        "arms": arms,
        "checks": checks,
        "all_checks_passed": all(checks.values()),
        "scientific_boundary": {
            "late_choice_created_independently_after_frozen_early_record": False,
            "public_early_record": "ADJACENT_SPIN_PARITIES_ONLY",
            "hidden_spin_must_not_be_available_before_future_choice": True,
            "physical_retrocausality_established": False,
            "operational_information_from_future_established": False,
            "postselection_explanation_not_excluded": True,
            "human_consciousness_or_memory_measured": False,
            "original_R5F_model_or_production_changed": False,
        },
    }
    return report


def gated_research_receipt(report: dict) -> dict:
    """Fail-closed boundary: synthetic output CANNOT certify physics."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ValueError("unknown simulation schema")
    if report.get("classification") != "SYNTHETIC_OFFLINE_MODEL_ONLY":
        raise ValueError("not an admitted offline R1 result")
    checks = report.get("checks")
    if not isinstance(checks, dict) or not checks or any(type(x) is not bool for x in checks.values()):
        raise ValueError("missing or malformed checks")
    boundary = report.get("scientific_boundary", {})
    if not isinstance(boundary, dict):
        raise ValueError("missing scientific boundary")
    mandatory_false = (
        "late_choice_created_independently_after_frozen_early_record",
        "physical_retrocausality_established",
        "operational_information_from_future_established",
        "human_consciousness_or_memory_measured",
        "original_R5F_model_or_production_changed",
    )
    if any(boundary.get(key) is not False for key in mandatory_false):
        raise ValueError("R1 offline receipt may not certify physical/human/production effects")
    if boundary.get("postselection_explanation_not_excluded") is not True:
        raise ValueError("postselection alternative must remain admitted")
    theory = report.get("theory", {})
    if not isinstance(theory, dict) or theory.get("postselection_exactly_equivalent") is not True:
        raise ValueError("R1 requires its exact conventional conditioning baseline")
    return {
        "schema": "janus.demihead.tachyon.retrobound.r1.gate.v1",
        "experiment_schema": SCHEMA,
        "mathematical_model": "CHECKS_PASSED" if all(checks.values()) else "CHECKS_FAILED",
        "proposed_past_future_dependency": "CONDITIONAL_HIDDEN_STATE_ONLY",
        "conventional_postselection_mathematically_equivalent": True,
        "early_observable_scope": "PARITY_RECORD_RESTRICTED_BY_CONSTRUCTION",
        "operational_retro_signal": "NOT_ESTABLISHED",
        "independent_future_choice_after_frozen_early_record": False,
        "external_custodian": False,
        "external_clock_or_sensor_data": False,
        "physical_retrocausality": "NOT_TESTED_NOT_ESTABLISHED",
        "rule001_subjective_time": "SEPARATE_DOMAIN_NOT_TESTED",
        "r5f_forward_replay": "UNCHANGED_AND_NOT_TESTED_BY_THIS_RUN",
        "model_adoption": "HOLD",
        "next_prospective_gate": "FREEZE_EARLY_PUBLIC_RECORD_BEFORE_INDEPENDENT_LATE_ENTROPY__INCLUDE_ALL_TRIALS__NO_POSTSELECTION__PREDECLARE_FORWARD_NULL__EXTERNAL_AUDIT",
    }


def run_gated(**kwargs) -> dict:
    report = run_experiment(**kwargs)
    report["tachyon_gate"] = gated_research_receipt(report)
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="TACHYON RETROBOUND R1 offline simulation (not physical time travel)")
    p.add_argument("--steps", type=int, default=8)
    p.add_argument("--rho", type=float, default=0.85)
    p.add_argument("--eta", type=float, default=0.9)
    p.add_argument("--trials", type=int, default=40000)
    p.add_argument("--seed", type=int, default=20261123)
    args = p.parse_args()
    print(json.dumps(run_gated(steps=args.steps, rho=args.rho, eta=args.eta,
                               trials=args.trials, seed=args.seed),
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
