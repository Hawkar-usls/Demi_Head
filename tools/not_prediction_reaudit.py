from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REQUIRED_CANDIDATE_FIELDS = {
    "candidate_id",
    "name",
    "canonical_path",
    "raw_observation",
    "event_time_or_anchor",
    "first_repository_commit",
    "source_root",
    "later_interpretation",
    "shared_context",
    "independence_state",
    "alternative_explanation",
    "claim_ceiling",
    "snapshot_relation",
    "admission_status",
}

BLIND_REMOVE_KEYS = {
    "candidate_id",
    "name",
    "later_interpretation",
    "shared_context",
    "claim_ceiling",
    "admission_status",
    "canonical_path",
}

ONTOLOGY_TERMS = {
    "janus": "TOKEN_PROJECT",
    "door": "TOKEN_BOUNDARY",
    "doors": "TOKEN_BOUNDARY",
    "threshold": "TOKEN_BOUNDARY",
    "home": "TOKEN_PLACE",
    "return": "TOKEN_TRANSITION",
    "witness": "TOKEN_ROLE_A",
    "guard": "TOKEN_ROLE_B",
    "past": "TOKEN_TIME_A",
    "future": "TOKEN_TIME_B",
    "sign": "TOKEN_MARKER",
    "source": "TOKEN_ORIGIN",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def candidate_sections(document: dict[str, Any]) -> list[dict[str, Any]]:
    keys = (
        "pre_snapshot_strong_omissions",
        "pre_snapshot_family_decomposition_candidates",
        "post_snapshot_additions",
    )
    rows: list[dict[str, Any]] = []
    for key in keys:
        value = document.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"{key} must be a list")
        rows.extend(value)
    return rows


def validate_candidate(candidate: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_CANDIDATE_FIELDS - set(candidate))
    if missing:
        raise ValueError(
            f"Candidate {candidate.get('candidate_id', '<unknown>')} missing fields: {', '.join(missing)}"
        )


def root_collapse(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    roots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        validate_candidate(candidate)
        roots[str(candidate["source_root"])].append(candidate)

    rows = []
    for root_id, members in sorted(roots.items()):
        rows.append(
            {
                "source_root": root_id,
                "candidate_ids": sorted(str(x["candidate_id"]) for x in members),
                "presentation_count": len(members),
                "snapshot_relations": sorted({str(x["snapshot_relation"]) for x in members}),
                "independence_states": sorted({str(x["independence_state"]) for x in members}),
            }
        )

    return {
        "candidate_count": len(candidates),
        "root_count": len(roots),
        "roots": rows,
        "invariant": "PRESENTATION_COUNT != INDEPENDENT_ROOT_COUNT",
    }


def normalize_text(value: Any) -> Any:
    if isinstance(value, str):
        words = value.split()
        normalized: list[str] = []
        for word in words:
            bare = word.strip(".,;:!?()[]{}<>\"'`).-_/").casefold()
            replacement = ONTOLOGY_TERMS.get(bare)
            normalized.append(replacement if replacement else word)
        return " ".join(normalized)
    if isinstance(value, list):
        return [normalize_text(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize_text(item) for key, item in value.items()}
    return value


def blind_candidate(candidate: dict[str, Any], ontology_blind: bool = False) -> dict[str, Any]:
    validate_candidate(candidate)
    blinded = {key: value for key, value in candidate.items() if key not in BLIND_REMOVE_KEYS}
    if ontology_blind:
        blinded = normalize_text(blinded)
    return blinded


def audit(document: dict[str, Any]) -> dict[str, Any]:
    candidates = candidate_sections(document)
    for candidate in candidates:
        validate_candidate(candidate)

    collapsed = root_collapse(candidates)
    status_counts = Counter(str(x["admission_status"]) for x in candidates)
    snapshot_counts = Counter(str(x["snapshot_relation"]) for x in candidates)

    blind_packets = [blind_candidate(x, ontology_blind=False) for x in candidates]
    ontology_blind_packets = [blind_candidate(x, ontology_blind=True) for x in candidates]

    authoritative = int(document.get("counting_state", {}).get("authoritative_current_total", 0))
    baseline = int(document.get("counting_state", {}).get("baseline_admitted", 0))
    if authoritative != baseline:
        raise ValueError("Re-audit must not silently promote candidate cases")

    forbidden_promotions = (
        "prediction_promoted",
        "prophecy_promoted",
        "precognition_promoted",
        "physical_retrocausality_promoted",
        "supernatural_causation_promoted",
    )
    boundary = document.get("final_boundary", {})
    promoted = [key for key in forbidden_promotions if boundary.get(key) is True]
    if promoted:
        raise ValueError(f"Forbidden silent promotion: {', '.join(promoted)}")

    return {
        "schema": "janus.demihead.not_prediction_reaudit_result.v1",
        "artifact_id": document.get("artifact_id"),
        "root_collapse": collapsed,
        "status_counts": dict(sorted(status_counts.items())),
        "snapshot_relation_counts": dict(sorted(snapshot_counts.items())),
        "blind_packets": blind_packets,
        "ontology_blind_packets": ontology_blind_packets,
        "authoritative_total_preserved": authoritative,
        "truth_claim": "NOT_MADE",
        "prediction_claim": "NOT_PROMOTED",
        "requires_matched_null": True,
        "requires_external_replication_for_strong_external_recurrence": True,
        "release_control": "OPEN_REVIEW",
        "invariants": [
            "SOURCE_COUNT != INDEPENDENT_ROOT_COUNT",
            "PRESENTATION_COUNT != EVENT_COUNT",
            "REPOSITORY_RECURRENCE != INDEPENDENT_REPLICATION",
            "MODEL_OUTPUT != EVIDENCE",
            "UNRESOLVED != FAILURE",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="DemiHead deterministic source-root and blinding helper for JANUS nonprediction re-audits."
    )
    parser.add_argument("reaudit", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = audit(load_json(args.reaudit))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
