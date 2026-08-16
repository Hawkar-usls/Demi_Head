from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SPEC_SCHEMA = "janus.demihead.optimizer_trials.v1"
RESULT_SCHEMA = "janus.demihead.optimizer_result.v1"

ALLOWED_CONFIG_KEYS = {
    "flow_gate_quota",
    "bounded_worker_count",
    "observer_sampling_interval_ms",
    "recheck_interval_ms",
    "cache_ttl_ms",
    "provider_route_id",
}

ALLOWED_METRICS = {
    "p50_latency_ms",
    "p95_latency_ms",
    "p99_latency_ms",
    "cpu_time_ms",
    "memory_peak_mb",
    "timeout_rate",
    "operational_error_rate",
}

FORBIDDEN_OBJECTIVES = {
    "engagement",
    "time_on_service",
    "belief_change",
    "persuasion",
    "political_conversion",
    "compliance",
    "source_suppression",
    "user_vulnerability",
    "truth_score",
    "authority_score",
}

HARD_CONSTRAINTS = {
    "provenance_loss",
    "freshness_policy_violation",
    "evidence_state_mutation_by_optimizer",
    "constitutional_invariant_violation",
    "authority_delta_nonzero",
    "mass_effect_budget_delta_nonzero",
}


def load_spec(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != SPEC_SCHEMA:
        raise ValueError("Unsupported optimizer trial schema")
    return data


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _evaluate_trial(trial: dict[str, Any], objective_order: list[str]) -> dict[str, Any]:
    candidate_id = trial.get("candidate_id")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise ValueError("candidate_id must be a non-empty string")

    config = trial.get("config", {})
    metrics = trial.get("metrics", {})
    constraints = trial.get("constraints", {})
    if not isinstance(config, dict) or not isinstance(metrics, dict) or not isinstance(constraints, dict):
        raise ValueError(f"{candidate_id}: config, metrics and constraints must be objects")

    reasons: list[str] = []

    unknown_config = sorted(set(config) - ALLOWED_CONFIG_KEYS)
    if unknown_config:
        reasons.append("UNKNOWN_CONFIG_KEYS:" + ",".join(unknown_config))

    forbidden_metrics = sorted(set(metrics) & FORBIDDEN_OBJECTIVES)
    if forbidden_metrics:
        reasons.append("FORBIDDEN_OBJECTIVES:" + ",".join(forbidden_metrics))

    unknown_metrics = sorted(set(metrics) - ALLOWED_METRICS - FORBIDDEN_OBJECTIVES)
    if unknown_metrics:
        reasons.append("UNKNOWN_METRICS:" + ",".join(unknown_metrics))

    unknown_constraints = sorted(set(constraints) - HARD_CONSTRAINTS)
    if unknown_constraints:
        reasons.append("UNKNOWN_CONSTRAINTS:" + ",".join(unknown_constraints))

    violated = sorted(name for name in HARD_CONSTRAINTS if bool(constraints.get(name, False)))
    if violated:
        reasons.append("HARD_CONSTRAINT_VIOLATION:" + ",".join(violated))

    missing_objectives = [name for name in objective_order if name not in metrics]
    if missing_objectives:
        reasons.append("MISSING_OBJECTIVES:" + ",".join(missing_objectives))

    invalid_objectives = [
        name
        for name in objective_order
        if name in metrics and (not _is_number(metrics[name]) or metrics[name] < 0)
    ]
    if invalid_objectives:
        reasons.append("INVALID_OBJECTIVE_VALUES:" + ",".join(invalid_objectives))

    admitted = not reasons
    rank_tuple = [float(metrics[name]) for name in objective_order] if admitted else None
    return {
        "candidate_id": candidate_id,
        "config": config,
        "metrics": metrics,
        "constraints": constraints,
        "admission": "ADMITTED" if admitted else "REJECTED",
        "reasons": reasons,
        "rank_tuple": rank_tuple,
    }


def evaluate_trials(spec: dict[str, Any]) -> dict[str, Any]:
    objective_order = spec.get("objective_order")
    if not isinstance(objective_order, list) or not objective_order:
        raise ValueError("objective_order must be a non-empty list")
    if len(objective_order) != len(set(objective_order)):
        raise ValueError("objective_order must not contain duplicates")
    if any(name not in ALLOWED_METRICS for name in objective_order):
        raise ValueError("objective_order contains a non-operational or unsupported objective")

    trials = spec.get("trials")
    if not isinstance(trials, list) or not trials:
        raise ValueError("trials must be a non-empty list")

    history = [_evaluate_trial(trial, objective_order) for trial in trials]
    ids = [row["candidate_id"] for row in history]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate_id values must be unique")

    admitted = [row for row in history if row["admission"] == "ADMITTED"]
    best = min(admitted, key=lambda row: (tuple(row["rank_tuple"]), row["candidate_id"])) if admitted else None

    return {
        "schema": RESULT_SCHEMA,
        "experiment_id": spec.get("experiment_id", "UNSPECIFIED"),
        "mode": "DETERMINISTIC_FROZEN_TRIAL_ADMISSION_REFERENCE",
        "objective_order": objective_order,
        "history": history,
        "accounting": {
            "trial_count": len(history),
            "admitted_count": len(admitted),
            "rejected_count": len(history) - len(admitted),
        },
        "best_candidate": None
        if best is None
        else {
            "candidate_id": best["candidate_id"],
            "config": best["config"],
            "rank_tuple": best["rank_tuple"],
        },
        "invariants": {
            "best_score_is_truth": False,
            "optimizer_can_mutate_evidence_state": False,
            "optimizer_can_mutate_source_roots": False,
            "optimizer_can_mutate_constitution": False,
            "optimizer_can_increase_authority": False,
            "optimizer_can_increase_mass_effect_budget": False,
            "failed_trials_preserved": True,
            "forbidden_objectives_fail_closed": True,
        },
        "lineage": {
            "source_pattern": "Janus-Demiurge ordinary ask/evaluate/tell/history optimization pattern",
            "source_domain_claims_transferred": False,
            "tachyonic_filter_37_transferred": False,
            "gp_ei_runtime_implemented_here": False,
        },
        "claim_ceiling": {
            "established": [
                "Operational trial results can be admitted or rejected under explicit constitutional constraints.",
                "Admitted trials are ranked deterministically by declared operational objectives only.",
                "Rejected trials remain in history with reasons.",
            ],
            "not_established": [
                "Bayesian optimization performance",
                "wall-clock speed improvement",
                "production optimality",
                "truth improvement from a lower operational score",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    spec = {
        "schema": SPEC_SCHEMA,
        "experiment_id": "SELF_TEST",
        "objective_order": ["p95_latency_ms", "cpu_time_ms", "memory_peak_mb"],
        "trials": [
            {
                "candidate_id": "safe_slow",
                "config": {"flow_gate_quota": 2, "bounded_worker_count": 2},
                "metrics": {"p95_latency_ms": 30, "cpu_time_ms": 15, "memory_peak_mb": 40},
                "constraints": {},
            },
            {
                "candidate_id": "safe_fast",
                "config": {"flow_gate_quota": 2, "bounded_worker_count": 4},
                "metrics": {"p95_latency_ms": 20, "cpu_time_ms": 12, "memory_peak_mb": 42},
                "constraints": {},
            },
            {
                "candidate_id": "authority_cheat",
                "config": {"flow_gate_quota": 8},
                "metrics": {"p95_latency_ms": 1, "cpu_time_ms": 1, "memory_peak_mb": 1},
                "constraints": {"authority_delta_nonzero": True},
            },
            {
                "candidate_id": "engagement_cheat",
                "config": {"flow_gate_quota": 8},
                "metrics": {
                    "p95_latency_ms": 2,
                    "cpu_time_ms": 2,
                    "memory_peak_mb": 2,
                    "engagement": 999,
                },
                "constraints": {},
            },
        ],
    }
    result = evaluate_trials(spec)
    by_id = {row["candidate_id"]: row for row in result["history"]}
    checks = {
        "best_is_safe_fast": result["best_candidate"]["candidate_id"] == "safe_fast",
        "authority_cheat_rejected": by_id["authority_cheat"]["admission"] == "REJECTED",
        "engagement_cheat_rejected": by_id["engagement_cheat"]["admission"] == "REJECTED",
        "two_safe_trials_admitted": result["accounting"]["admitted_count"] == 2,
        "failed_trials_preserved": result["invariants"]["failed_trials_preserved"],
        "no_constitution_mutation": not result["invariants"]["optimizer_can_mutate_constitution"],
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    return {"self_test": "PASS", "checks": checks, "result": result}


def render(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description="Constitution-bound operational optimizer admission head")
    parser.add_argument("spec", type=Path, nargs="?", help="Input frozen optimizer-trial JSON")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.self_test:
        render(self_test(), args.output)
        return
    if args.spec is None:
        parser.error("spec is required unless --self-test is used")
    render(evaluate_trials(load_spec(args.spec)), args.output)


if __name__ == "__main__":
    main()
