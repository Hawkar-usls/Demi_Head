from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _baseline_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for case in document.get("cases", []):
        strict_count = len(set(case.get("phenomenon_session_roots", [])))
        if strict_count == 0:
            continue
        selection_root = case.get("selection_process_root")
        if not selection_root:
            raise ValueError(f"{case.get('case_id')}: strict roots require selection_process_root")
        rows.append({"id": str(case["case_id"]), "count": strict_count, "selection": str(selection_root)})
    return rows


def _overlay_rows(document: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for candidate in document.get("candidates", []):
        if candidate.get("atomic_relation") != "NEW_STRICT_ROOT":
            continue
        selection_root = candidate.get("selection_process_root")
        if not selection_root:
            raise ValueError(f"{candidate.get('candidate_id')}: strict overlay root requires selection_process_root")
        rows.append({"id": str(candidate["candidate_id"]), "count": 1, "selection": str(selection_root)})
    return rows


def analyze(baseline: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    rows = _baseline_rows(baseline) + _overlay_rows(overlay)
    total = sum(row["count"] for row in rows)
    if total != 27:
        raise ValueError(f"expanded strict root total must be 27, got {total}")

    counts: Counter[str] = Counter()
    members: dict[str, list[str]] = {}
    for row in rows:
        counts[row["selection"]] += row["count"]
        members.setdefault(row["selection"], []).append(row["id"])

    family_rows = []
    for selection, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        family_rows.append({
            "selection_process_root": selection,
            "strict_root_count": count,
            "share_of_strict_roots": count / total,
            "source_case_ids": sorted(members[selection]),
        })

    concentration = sum((count / total) ** 2 for count in counts.values())
    effective_family_number = 1.0 / concentration
    top_count = family_rows[0]["strict_root_count"]
    top_two_count = sum(row["strict_root_count"] for row in family_rows[:2])

    return {
        "schema": "janus.demihead.not_prediction_selection_concentration.v1",
        "strict_root_count": total,
        "selection_process_family_count": len(counts),
        "families": family_rows,
        "concentration": {
            "largest_family_root_count": top_count,
            "largest_family_share": top_count / total,
            "top_two_family_root_count": top_two_count,
            "top_two_family_share": top_two_count / total,
            "herfindahl_index_descriptive_only": concentration,
            "inverse_herfindahl_family_equivalent_descriptive_only": effective_family_number,
        },
        "claim_ceiling": "DESCRIPTIVE_SELECTION_CONCENTRATION_ONLY_NOT_EFFECTIVE_SAMPLE_SIZE",
        "independent_evidence_root_count": "NOT_ESTIMATED",
        "prediction_claim": "NOT_PROMOTED",
        "invariants": [
            "EVENT_ROOT_COUNT != INDEPENDENT_SELECTION_PROCESS_COUNT",
            "SELECTION_PROCESS_FAMILY_COUNT != EFFECTIVE_SAMPLE_SIZE",
            "SHARED_SELECTION_PROCESS_REQUIRES_MATCHED_NULL",
            "CLOCK_SALIENCE_ROOTS_ARE_NOT_IID_MINUTE_DRAWS",
            "DESCRIPTIVE_CONCENTRATION != CAUSAL_EXPLANATION",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure selection/instrument-family concentration in normalized Not-Prediction strict roots.")
    parser.add_argument("baseline", type=Path)
    parser.add_argument("overlay", type=Path)
    args = parser.parse_args()
    result = analyze(load_json(args.baseline), load_json(args.overlay))
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
