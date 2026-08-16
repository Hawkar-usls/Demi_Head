from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


ALLOWED_RELATIONS = {"NEW_STRICT_ROOT", "NEW_UNCERTAIN_ROOT", "ABSORBED_BASELINE_ROOT", "REFERENCE_ONLY"}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def analyze(document: dict[str, Any]) -> dict[str, Any]:
    baseline = document.get("baseline_counts", {})
    strict0 = int(baseline.get("strict_phenomenon_session_roots", -1))
    uncertain0 = int(baseline.get("uncertain_phenomenology_roots", -1))
    inclusive0 = int(baseline.get("inclusive_phenomenology_roots", -1))
    if (strict0, uncertain0, inclusive0) != (24, 3, 27):
        raise ValueError("overlay requires frozen baseline 24 strict / 3 uncertain / 27 inclusive")

    candidates = document.get("candidates")
    if not isinstance(candidates, list):
        raise ValueError("candidates must be a list")
    ids = [str(row.get("candidate_id")) for row in candidates]
    expected = {f"NP-C0{index}" for index in range(30, 36)}
    if set(ids) != expected or len(ids) != 6:
        raise ValueError("overlay must contain exactly NP-C030..NP-C035")

    counts: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    new_strict_roots: set[str] = set()
    new_uncertain_roots: set[str] = set()
    absorbed: list[str] = []
    reference_only: list[str] = []

    for row in candidates:
        relation = str(row.get("atomic_relation"))
        if relation not in ALLOWED_RELATIONS:
            raise ValueError(f"{row.get('candidate_id')}: invalid atomic_relation")
        counts[relation] += 1
        root_id = row.get("root_id")
        if relation == "NEW_STRICT_ROOT":
            if not root_id:
                raise ValueError(f"{row['candidate_id']}: strict root requires root_id")
            new_strict_roots.add(str(root_id))
        elif relation == "NEW_UNCERTAIN_ROOT":
            if not root_id:
                raise ValueError(f"{row['candidate_id']}: uncertain root requires root_id")
            new_uncertain_roots.add(str(root_id))
        elif relation == "ABSORBED_BASELINE_ROOT":
            baseline_root = row.get("baseline_root")
            if not baseline_root:
                raise ValueError(f"{row['candidate_id']}: absorbed root requires baseline_root")
            absorbed.append(str(row["candidate_id"]))
        elif relation == "REFERENCE_ONLY":
            reference_only.append(str(row["candidate_id"]))
        rows.append({
            "candidate_id": row["candidate_id"],
            "atomic_relation": relation,
            "root_id": root_id,
            "baseline_root": row.get("baseline_root"),
            "selection_process_root": row.get("selection_process_root"),
            "independence_note": row.get("independence_note"),
            "claim_ceiling": row.get("claim_ceiling"),
        })

    if new_strict_roots & new_uncertain_roots:
        raise ValueError("root cannot be strict and uncertain")

    strict1 = strict0 + len(new_strict_roots)
    uncertain1 = uncertain0 + len(new_uncertain_roots)
    inclusive1 = strict1 + uncertain1

    frozen = document.get("frozen_expected_overlay_result", {})
    if frozen:
        expected_tuple = (
            int(frozen.get("expanded_strict_roots", strict1)),
            int(frozen.get("expanded_uncertain_roots", uncertain1)),
            int(frozen.get("expanded_inclusive_roots", inclusive1)),
        )
        if expected_tuple != (strict1, uncertain1, inclusive1):
            raise ValueError("overlay frozen count drift")

    return {
        "schema": "janus.demihead.not_prediction_overlay_atomic_result.v1",
        "baseline": {"strict": strict0, "uncertain": uncertain0, "inclusive": inclusive0},
        "overlay_delta": {
            "new_strict_roots": len(new_strict_roots),
            "new_uncertain_roots": len(new_uncertain_roots),
            "absorbed_baseline_candidates": len(absorbed),
            "reference_only_candidates": len(reference_only),
        },
        "expanded_accounting": {
            "strict_phenomenon_session_roots": strict1,
            "uncertain_phenomenology_roots": uncertain1,
            "inclusive_phenomenology_roots": inclusive1,
        },
        "relation_counts": dict(sorted(counts.items())),
        "candidates": sorted(rows, key=lambda x: x["candidate_id"]),
        "absorbed_candidates": sorted(absorbed),
        "reference_only_candidates": sorted(reference_only),
        "prediction_claim": "NOT_PROMOTED",
        "truth_claim": "NOT_MADE",
        "invariants": [
            "OVERLAY_CANDIDATE_COUNT != EVENT_ROOT_DELTA",
            "ABSORBED_BASELINE_ROOT_ADDS_ZERO",
            "REFERENCE_CHRONOLOGY_ADDS_ZERO_PHENOMENOLOGY_ROOTS",
            "SHARED_CLOCK_SELECTION_REQUIRES_MATCHED_NULL",
            "ONE_EXPERIMENT_WITH_MANY_TRIALS != MANY_INDEPENDENT_EVENTS",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DemiHead atomic overlay analyzer for NP-C030..NP-C035.")
    parser.add_argument("overlay", type=Path)
    args = parser.parse_args()
    print(json.dumps(analyze(load_json(args.overlay)), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
