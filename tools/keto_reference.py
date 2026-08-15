from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


CURRENT = "current"
SUPPORTS = "supports"
CONTRADICTS = "contradicts"


def load_case(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if data.get("schema") != "janus.demihead.keto_case.v1":
        raise ValueError("Unsupported case schema")
    if not data.get("presentations"):
        raise ValueError("Case must contain at least one presentation")
    return data


def root_key(presentation: dict[str, Any]) -> str:
    root_id = presentation.get("root_id")
    if root_id:
        return str(root_id)
    return f"UNKNOWN::{presentation['presentation_id']}"


def summarize_case(case: dict[str, Any]) -> dict[str, Any]:
    presentations = case["presentations"]
    roots: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in presentations:
        roots[root_key(item)].append(item)

    current_support_roots: set[str] = set()
    current_contradiction_roots: set[str] = set()
    official_roots: set[str] = set()
    authenticated_independent_roots: set[str] = set()
    stale_presentations: list[str] = []
    unknown_freshness_presentations: list[str] = []

    root_rows: list[dict[str, Any]] = []
    for root_id, members in sorted(roots.items()):
        current_members = [m for m in members if m.get("freshness") == CURRENT]
        relations = sorted({m.get("relation", "unknown") for m in current_members})
        source_classes = sorted({m.get("source_class", "unknown") for m in members})
        independence_states = sorted({m.get("independence", "unknown") for m in members})

        if any(m.get("source_class") == "official" for m in current_members):
            official_roots.add(root_id)
        if any(m.get("independence") == "authenticated_independent" for m in current_members):
            authenticated_independent_roots.add(root_id)
        if any(m.get("relation") == SUPPORTS for m in current_members):
            current_support_roots.add(root_id)
        if any(m.get("relation") == CONTRADICTS for m in current_members):
            current_contradiction_roots.add(root_id)

        root_rows.append(
            {
                "root_id": root_id,
                "presentation_count": len(members),
                "current_presentation_count": len(current_members),
                "source_classes": source_classes,
                "current_relations": relations,
                "independence_states": independence_states,
            }
        )

    for item in presentations:
        freshness = item.get("freshness")
        if freshness == "stale":
            stale_presentations.append(item["presentation_id"])
        elif freshness == "unknown":
            unknown_freshness_presentations.append(item["presentation_id"])

    if current_support_roots and current_contradiction_roots:
        evidence_state = "CONTESTED"
    elif current_support_roots:
        evidence_state = "SUPPORTED_BY_PRESENT_SOURCES"
    elif current_contradiction_roots:
        evidence_state = "CONTRADICTED_BY_PRESENT_SOURCES"
    else:
        evidence_state = "UNRESOLVED"

    if evidence_state == "CONTESTED":
        release_control = "SHOW_CONFLICT_AND_STOP_ESCALATION_UNLESS_NEW_EVIDENCE"
    elif evidence_state == "UNRESOLVED":
        release_control = "WAIT_FOR_PRIMARY_OR_INDEPENDENT_EVIDENCE"
    else:
        release_control = "SHOW_ROOTS_AND_ALLOW_USER_TO_EXIT"

    return {
        "schema": "janus.demihead.keto_result.v1",
        "case_id": case["case_id"],
        "claim": case["claim"],
        "accounting": {
            "presentation_count": len(presentations),
            "root_count": len(roots),
            "current_support_root_count": len(current_support_roots),
            "current_contradiction_root_count": len(current_contradiction_roots),
            "official_position_root_count": len(official_roots),
            "authenticated_independent_root_count": len(authenticated_independent_roots),
            "stale_presentation_count": len(stale_presentations),
            "unknown_freshness_presentation_count": len(unknown_freshness_presentations),
        },
        "roots": root_rows,
        "official_position_roots": sorted(official_roots),
        "authenticated_independent_roots": sorted(authenticated_independent_roots),
        "current_support_roots": sorted(current_support_roots),
        "current_contradiction_roots": sorted(current_contradiction_roots),
        "stale_presentations": sorted(stale_presentations),
        "unknown_freshness_presentations": sorted(unknown_freshness_presentations),
        "evidence_state": evidence_state,
        "truth_claim": "NOT_MADE",
        "mass_effect_budget": 0,
        "release_control": release_control,
        "invariants": [
            "SOURCE_COUNT != INDEPENDENT_ROOT_COUNT",
            "OFFICIAL_POSITION != EXCLUSIVE_OBJECTIVE_TRUTH",
            "STALE != CURRENT",
            "NO_SOURCE != FALSE",
            "MODEL_OUTPUT != EVIDENCE",
            "MORE_FACES != MORE_RIGHTS",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Deterministic local reference analyzer for a JANUS DemiHead KETO/CETUS case."
    )
    parser.add_argument("case", type=Path, help="Path to a janus.demihead.keto_case.v1 JSON document")
    parser.add_argument("--output", type=Path, default=None, help="Optional output JSON path")
    args = parser.parse_args()

    result = summarize_case(load_case(args.case))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
