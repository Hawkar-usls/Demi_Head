from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


TRACE_SCHEMA = "janus.demihead.flow_gate_trace.v1"
RESULT_SCHEMA = "janus.demihead.flow_gate_result.v1"
ALLOWED_OUTCOMES = {"completed", "failed", "unknown"}


def load_trace(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != TRACE_SCHEMA:
        raise ValueError("Unsupported flow-gate trace schema")
    return data


def run_flow_gate(trace: dict[str, Any]) -> dict[str, Any]:
    config = trace.get("config", {})
    quota = config.get("quota")
    max_waves = config.get("max_waves")
    if not isinstance(quota, int) or isinstance(quota, bool) or quota <= 0:
        raise ValueError("quota must be a positive integer")
    if not isinstance(max_waves, int) or isinstance(max_waves, bool) or max_waves <= 0:
        raise ValueError("max_waves must be a positive integer")

    work = trace.get("work")
    if not isinstance(work, list) or not work:
        raise ValueError("work must be a non-empty list")

    ids: list[str] = []
    normalized: list[dict[str, str]] = []
    for row in work:
        if not isinstance(row, dict):
            raise ValueError("each work item must be an object")
        work_id = row.get("work_id")
        outcome = row.get("observed_outcome", "unknown")
        if not isinstance(work_id, str) or not work_id:
            raise ValueError("work_id must be a non-empty string")
        if outcome not in ALLOWED_OUTCOMES:
            raise ValueError(f"unsupported observed_outcome for {work_id}: {outcome}")
        ids.append(work_id)
        normalized.append({"work_id": work_id, "observed_outcome": outcome})

    if len(ids) != len(set(ids)):
        raise ValueError("work_id values must be unique")

    admission_limit = quota * max_waves
    admitted = normalized[:admission_limit]
    deferred = normalized[admission_limit:]

    waves: list[dict[str, Any]] = []
    state_trace: list[dict[str, Any]] = []
    for start in range(0, len(admitted), quota):
        wave_items = admitted[start : start + quota]
        wave_index = len(waves)
        outcome_counts = Counter(item["observed_outcome"] for item in wave_items)

        state_trace.append({"state": "OPEN", "wave_index": wave_index})
        state_trace.append(
            {
                "state": "ADMIT",
                "wave_index": wave_index,
                "work_ids": [item["work_id"] for item in wave_items],
            }
        )
        state_trace.append({"state": "HOLD", "wave_index": wave_index})
        state_trace.append(
            {
                "state": "DRAIN",
                "wave_index": wave_index,
                "observed_outcomes": dict(sorted(outcome_counts.items())),
            }
        )
        state_trace.append({"state": "CLEAN_VALLEY", "wave_index": wave_index})

        waves.append(
            {
                "wave_index": wave_index,
                "size": len(wave_items),
                "work_ids": [item["work_id"] for item in wave_items],
                "observed_outcomes": dict(sorted(outcome_counts.items())),
                "quota_respected": len(wave_items) <= quota,
                "clean_valley_recorded": True,
            }
        )

        if start + quota < len(admitted):
            state_trace.append({"state": "REOPEN", "wave_index": wave_index + 1})

    outcome_counts = Counter(item["observed_outcome"] for item in admitted)
    max_wave_size = max((wave["size"] for wave in waves), default=0)

    return {
        "schema": RESULT_SCHEMA,
        "trace_id": trace.get("trace_id", "UNSPECIFIED"),
        "mode": "DETERMINISTIC_REFERENCE_NO_REAL_SLEEP",
        "config": {"quota": quota, "max_waves": max_waves},
        "accounting": {
            "input_work_count": len(normalized),
            "admitted_count": len(admitted),
            "deferred_count": len(deferred),
            "wave_count": len(waves),
            "max_wave_size": max_wave_size,
            "completed_observed_count": outcome_counts.get("completed", 0),
            "failed_observed_count": outcome_counts.get("failed", 0),
            "unknown_observed_count": outcome_counts.get("unknown", 0),
        },
        "waves": waves,
        "deferred": deferred,
        "state_trace": state_trace,
        "invariants": {
            "quota_respected": max_wave_size <= quota,
            "deferred_is_false": False,
            "flow_control_is_evidence_control": False,
            "queue_priority_is_truth_priority": False,
            "faster_is_truer": False,
            "evidence_state_mutated": False,
            "source_roots_mutated": False,
            "provenance_mutated": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "established": [
                "This deterministic reference partitions admitted work into bounded waves and preserves deferred items.",
                "No admitted wave exceeds the configured quota.",
            ],
            "not_established": [
                "wall-clock speed improvement",
                "resource savings",
                "production scheduler behavior",
                "truth or evidence improvement from scheduling",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    trace = {
        "schema": TRACE_SCHEMA,
        "trace_id": "SELF_TEST",
        "config": {"quota": 2, "max_waves": 2},
        "work": [
            {"work_id": "w0", "observed_outcome": "completed"},
            {"work_id": "w1", "observed_outcome": "unknown"},
            {"work_id": "w2", "observed_outcome": "failed"},
            {"work_id": "w3", "observed_outcome": "completed"},
            {"work_id": "w4", "observed_outcome": "completed"},
        ],
    }
    result = run_flow_gate(trace)
    checks = {
        "quota_respected": result["invariants"]["quota_respected"],
        "two_waves": result["accounting"]["wave_count"] == 2,
        "one_deferred": result["accounting"]["deferred_count"] == 1,
        "unknown_preserved": result["accounting"]["unknown_observed_count"] == 1,
        "no_authority_growth": result["invariants"]["authority_delta"] == 0,
        "no_mass_effect_growth": result["invariants"]["mass_effect_budget_delta"] == 0,
        "no_evidence_mutation": not result["invariants"]["evidence_state_mutated"],
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
    parser = argparse.ArgumentParser(description="Bounded deterministic KETO flow-gate reference head")
    parser.add_argument("trace", type=Path, nargs="?", help="Input flow trace JSON")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.self_test:
        render(self_test(), args.output)
        return
    if args.trace is None:
        parser.error("trace is required unless --self-test is used")
    render(run_flow_gate(load_trace(args.trace)), args.output)


if __name__ == "__main__":
    main()
