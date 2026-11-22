"""TACHYON R5F-N999: fail-closed operation-budget validation experiment.

The user requests available graph-search operations = -999. A resource budget is
a nonnegative capacity, so -999 is invalid. The gate MUST stop execution before
invoking any forward, reverse, replay, strong-provenance or abstention algorithm.

This standalone test imports but NEVER mutates the original R5F or X100 modules,
does not replace -999 with 0 or +999, and does not claim an inference accuracy.
Only synthetic cases are dispatched. Dataset preparation is not graph searching.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter

from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN, forward_only, reverse_only, reverse_then_forward, always_abstain,
    run_split, digest,
)

REQUESTED_AVAILABLE_OPERATIONS = -999
INVALID_NEGATIVE_BUDGET = "INVALID_NEGATIVE_OPERATION_BUDGET"
INVALID_BUDGET_TYPE = "INVALID_OPERATION_BUDGET_TYPE"
ARMS = {
    "A_FORWARD_ONLY_EXHAUSTIVE": forward_only,
    "B_REVERSE_ONLY_UNVERIFIED": reverse_only,
    "C_REVERSE_PLUS_FORWARD_REPLAY": reverse_then_forward,
    "D_STRONG_EXHAUSTIVE_PROVENANCE": forward_only,
    "E_ALWAYS_ABSTAIN": always_abstain,
}


def guarded_call(fn, evidence, available_operations: int):
    """Validate BEFORE calling fn, accessing graph edges, or scoring history.

    For a nonnegative budget, delegates to existing research algorithm; this
    experiment uses only negative budgets. This gate does not retrofit the
    legacy positive-budget algorithms' post-hoc cost checks into hard preemptive
    execution limits.
    """
    if type(available_operations) is not int:
        return {
            "status": INVALID_BUDGET_TYPE,
            "requested_available_operations": available_operations,
            "prediction": ABSTAIN,
            "graph_operations_performed": 0,
            "algorithm_invoked": False,
            "causal_claim_issued": False,
            "budget_exceeded": None,
        }
    if available_operations < 0:
        return {
            "status": INVALID_NEGATIVE_BUDGET,
            "requested_available_operations": available_operations,
            "prediction": ABSTAIN,
            "graph_operations_performed": 0,
            "algorithm_invoked": False,
            "causal_claim_issued": False,
            "budget_exceeded": None,
        }
    # Not part of N999 assessment; retained so the gate is usable for
    # legitimate nonnegative budgets. Legacy algorithms are unmodified.
    out = fn(evidence, budget=available_operations)
    return {
        "status": "ALGORITHM_DISPATCHED",
        "requested_available_operations": available_operations,
        "prediction": out["prediction"],
        "graph_operations_performed": out["operations"],
        "algorithm_invoked": True,
        "causal_claim_issued": out["prediction"] != ABSTAIN,
        "budget_exceeded": out["budget_exceeded"],
    }


def run_negative_budget_audit() -> dict:
    rows = run_split("heldout")
    if len(rows) != 600:
        raise AssertionError("Original R5F synthetic heldout population changed")

    observations = {name: Counter() for name in ARMS}
    unusual = {}
    for inp, scenario, family in rows:
        for name, fn in ARMS.items():
            outcome = guarded_call(fn, inp, REQUESTED_AVAILABLE_OPERATIONS)
            stats = observations[name]
            stats["dispatch_attempts"] += 1
            stats["rejected_before_dispatch"] += int(
                outcome["status"] == INVALID_NEGATIVE_BUDGET
                and not outcome["algorithm_invoked"])
            stats["graph_operations_performed"] += outcome["graph_operations_performed"]
            stats["causal_claims"] += int(outcome["causal_claim_issued"])
            stats["abstentions"] += int(outcome["prediction"] == ABSTAIN)
            stats["actually_invoked_algorithms"] += int(outcome["algorithm_invoked"])
            stats["invalid_status"] += int(outcome["status"] == INVALID_NEGATIVE_BUDGET)
            if outcome["status"] != INVALID_NEGATIVE_BUDGET:
                unusual.setdefault(name, []).append(inp["case_ref"])

    arms = {name: {
        "attempted_cases": 600,
        "requested_available_operations": REQUESTED_AVAILABLE_OPERATIONS,
        "status": INVALID_NEGATIVE_BUDGET,
        "rejected_before_dispatch": counters["rejected_before_dispatch"],
        "actually_invoked_algorithms": counters["actually_invoked_algorithms"],
        "graph_operations_performed": counters["graph_operations_performed"],
        "causal_claims": counters["causal_claims"],
        "abstentions": counters["abstentions"],
        "accuracy": None,
        "unsupported_assertions": 0,
        "no_score_reason": "No algorithm was allowed to run; no predicted physical history exists.",
    } for name, counters in observations.items()}

    result = {
        "schema": "janus.demihead.tachyon.r5f_negative999_budget_guard.v1",
        "experiment": "R5F_NEGATIVE_AVAILABLE_OPERATIONS_FAIL_CLOSED",
        "status": "INVALID_BUDGET_CORRECTLY_REJECTED__ENGINEERING_GUARD_PASS__SCIENCE_HOLD",
        "requested_available_operations": REQUESTED_AVAILABLE_OPERATIONS,
        "budget_valid": False,
        "budget_error": INVALID_NEGATIVE_BUDGET,
        "negative_budget_normalized_to_positive_or_zero": False,
        "dataset_source": "UNMODIFIED_R5F_DEVELOPER_GENERATED_SYNTHETIC_HELDOUT",
        "heldout_cases": len(rows),
        "arms_count": len(ARMS),
        "total_algorithm_dispatch_attempts": len(rows)*len(ARMS),
        "total_algorithm_invocations": sum(v["actually_invoked_algorithms"] for v in arms.values()),
        "total_graph_operations_performed": sum(v["graph_operations_performed"] for v in arms.values()),
        "total_causal_claims_issued": sum(v["causal_claims"] for v in arms.values()),
        "total_abstentions": sum(v["abstentions"] for v in arms.values()),
        "all_requests_rejected_before_graph_search": all(v["rejected_before_dispatch"] == 600 for v in arms.values()),
        "no_scored_accuracy": True,
        "input_population_sha256": digest(rows),
        "arms": arms,
        "unexpected_status_case_refs": unusual,
        "inference_ground_truth_inspected": False,
        "science_limits": {
            "real_witness_data_used": False,
            "external_custodian": False,
            "physical_reverse_time_proven": False,
            "neural_gain_established": False,
            "human_memory_measured": False,
            "production_weights_changed": False,
            "source_R5F_unchanged": True,
            "source_R5F_X100_unchanged": True,
            "scientific_gate": "HOLD_INVALID_NEGATIVE_RESOURCE_REQUEST_ONLY",
        },
        "interpretation": (
            "This tests rejection of invalid resource capacity, not ability to "
            "reconstruct causes. 0 graph operations, 0 causal claims and 3000 "
            "abstentions are expected safeguards; do not score as 100% "
            "causal accuracy. Dataset construction is separate overhead."
        ),
    }
    assert result["total_algorithm_dispatch_attempts"] == 3000
    assert result["total_algorithm_invocations"] == 0
    assert result["total_graph_operations_performed"] == 0
    assert result["total_causal_claims_issued"] == 0
    assert result["all_requests_rejected_before_graph_search"]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if not args.audit:
        parser.error("--audit required")
    print(json.dumps(run_negative_budget_audit(), indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
