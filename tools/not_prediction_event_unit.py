from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SELECTION_RISK = {
    "UNCONDITIONED_OR_PREREGISTERED": 0,
    "UNKNOWN": 1,
    "POST_HOC_DISCOVERY": 2,
    "SALIENCE_TRIGGERED": 3,
    "LOOKUP_CONDITIONED": 4,
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def event_keys(row: dict[str, Any]) -> list[str]:
    if row.get("event_roots"):
        roots = row["event_roots"]
        if not isinstance(roots, list) or not roots:
            raise ValueError("event_roots must be a non-empty list")
        return sorted({str(x) for x in roots})
    if row.get("event_root"):
        return [str(row["event_root"])]
    if row.get("source_root"):
        return [f"FALLBACK_SOURCE::{row['source_root']}"]
    raise ValueError("row requires event_root, event_roots, or source_root")


def collapse_events(rows: list[dict[str, Any]]) -> dict[str, Any]:
    events: dict[str, set[str]] = defaultdict(set)
    fallback_rows = 0
    for row in rows:
        row_id = str(row.get("candidate_id") or row.get("packet_id") or "UNNAMED")
        keys = event_keys(row)
        if all(key.startswith("FALLBACK_SOURCE::") for key in keys):
            fallback_rows += 1
        for key in keys:
            events[key].add(row_id)

    return {
        "row_count": len(rows),
        "event_root_count": len(events),
        "fallback_to_source_root_rows": fallback_rows,
        "events": [
            {
                "event_root": key,
                "row_ids": sorted(value),
                "row_reference_count": len(value),
            }
            for key, value in sorted(events.items())
        ],
        "invariants": [
            "PRESENTATION_COUNT != SOURCE_ROOT_COUNT",
            "SOURCE_ROOT_COUNT != EVENT_ROOT_COUNT",
        ],
    }


def assess_selection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    output_rows: list[dict[str, Any]] = []
    mode_counts: Counter[str] = Counter()

    for row in rows:
        selection = row.get("observation_selection") or {}
        mode = str(selection.get("mode", "UNKNOWN"))
        if mode not in SELECTION_RISK:
            raise ValueError(f"unsupported observation selection mode: {mode}")
        risk = SELECTION_RISK[mode]
        sampling_frame_known = bool(selection.get("sampling_frame_known", False))
        all_opportunities_logged = bool(selection.get("all_opportunities_logged", False))
        mode_counts[mode] += 1
        output_rows.append(
            {
                "row_id": str(row.get("candidate_id") or row.get("packet_id") or "UNNAMED"),
                "mode": mode,
                "risk_level": risk,
                "sampling_frame_known": sampling_frame_known,
                "all_opportunities_logged": all_opportunities_logged,
                "note": selection.get("note"),
            }
        )

    conditioned = any(x["risk_level"] >= 2 for x in output_rows)
    naive_uniform_forbidden = any(
        x["risk_level"] >= 3
        or not x["sampling_frame_known"]
        or not x["all_opportunities_logged"]
        for x in output_rows
    )

    return {
        "mode_counts": dict(sorted(mode_counts.items())),
        "requires_selection_matched_null": conditioned,
        "naive_uniform_frequency_inference_forbidden": naive_uniform_forbidden,
        "rows": output_rows,
        "invariants": [
            "RECORDED_EVENT_COUNT != OPPORTUNITY_COUNT",
            "SALIENCE_TRIGGERED_SAMPLE != RANDOM_SAMPLE",
            "LOOKUP_CONDITIONED_MATCHES != INDEPENDENT_CONFIRMATIONS",
        ],
    }


def analyze(document: dict[str, Any]) -> dict[str, Any]:
    rows = document.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("document.rows must be a non-empty list")

    event_result = collapse_events(rows)
    selection_result = assess_selection(rows)

    return {
        "schema": "janus.demihead.not_prediction_event_unit_result.v1",
        "artifact_id": document.get("artifact_id"),
        "event_collapse": event_result,
        "selection_gate": selection_result,
        "claim_ceiling": "UNIT_OF_ANALYSIS_AND_SELECTION_ACCOUNTING_ONLY",
        "truth_claim": "NOT_MADE",
        "prediction_claim": "NOT_PROMOTED",
        "requires_matched_null": True,
        "release_control": "OPEN_REVIEW",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DemiHead event-unit and selection-bias gate for Not-Prediction audits."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = analyze(load_json(args.manifest))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
