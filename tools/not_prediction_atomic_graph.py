from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


HARD_COLLAPSE_EDGE_TYPES = {"DIRECT_PARENT", "SAME_EVENT_LINEAGE", "RECURSIVE_LINEAGE"}
SOFT_DEPENDENCY_EDGE_TYPES = {
    "SHARED_SOURCE_PLATFORM",
    "SHARED_SELECTION_PROCESS",
    "SHARED_ONTOLOGY",
    "SHARED_REFERENCE_CORPUS",
}


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _root_set(cases: list[dict[str, Any]], key: str) -> set[str]:
    roots: set[str] = set()
    for case in cases:
        value = case.get(key, [])
        if not isinstance(value, list):
            raise ValueError(f"{case.get('case_id')}: {key} must be a list")
        roots.update(str(item) for item in value)
    return roots


def _validate_case(case: dict[str, Any]) -> None:
    required = {
        "case_id",
        "case_class",
        "phenomenon_session_roots",
        "uncertain_phenomenology_roots",
        "reference_anchor_roots",
        "method_roots",
        "comparison_edges",
        "subevent_count",
        "claim_ceiling",
    }
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"{case.get('case_id', '<unknown>')} missing: {', '.join(missing)}")
    if not isinstance(case["subevent_count"], int) or case["subevent_count"] < 0:
        raise ValueError(f"{case['case_id']}: subevent_count must be a non-negative integer")


def analyze(document: dict[str, Any]) -> dict[str, Any]:
    cases = document.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("document.cases must be a non-empty list")

    for case in cases:
        _validate_case(case)

    ids = [str(case["case_id"]) for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case_id")

    expected_ids = {f"NP-{index:03d}" for index in range(1, 30)}
    if set(ids) != expected_ids:
        missing = sorted(expected_ids - set(ids))
        extra = sorted(set(ids) - expected_ids)
        raise ValueError(f"baseline must contain NP-001..NP-029; missing={missing}; extra={extra}")

    strict_roots = _root_set(cases, "phenomenon_session_roots")
    uncertain_roots = _root_set(cases, "uncertain_phenomenology_roots")
    reference_roots = _root_set(cases, "reference_anchor_roots")
    method_roots = _root_set(cases, "method_roots")

    if strict_roots & uncertain_roots:
        raise ValueError("a root cannot be both strict and uncertain phenomenology")

    comparison_edges: list[dict[str, Any]] = []
    class_counts: Counter[str] = Counter()
    total_subevents = 0
    per_case: list[dict[str, Any]] = []
    for case in cases:
        class_counts[str(case["case_class"])] += 1
        edges = case["comparison_edges"]
        if not isinstance(edges, list):
            raise ValueError(f"{case['case_id']}: comparison_edges must be a list")
        for edge in edges:
            row = dict(edge)
            row["case_id"] = case["case_id"]
            comparison_edges.append(row)
        total_subevents += int(case["subevent_count"])
        per_case.append(
            {
                "case_id": case["case_id"],
                "case_class": case["case_class"],
                "strict_phenomenon_session_count": len(set(case["phenomenon_session_roots"])),
                "uncertain_phenomenology_count": len(set(case["uncertain_phenomenology_roots"])),
                "subevent_count": case["subevent_count"],
                "selection_process_root": case.get("selection_process_root"),
            }
        )

    components = document.get("dependency_components", [])
    if not isinstance(components, list):
        raise ValueError("dependency_components must be a list")
    component_rows: list[dict[str, Any]] = []
    hard_pairs: set[tuple[str, str]] = set()
    soft_pairs: set[tuple[str, str]] = set()
    for component in components:
        edge_type = str(component["edge_type"])
        members = sorted({str(x) for x in component.get("members", [])})
        if len(members) < 2:
            raise ValueError(f"dependency component {component.get('component_id')} needs >=2 members")
        unknown = sorted(set(members) - set(ids))
        if unknown:
            raise ValueError(f"dependency component references unknown cases: {unknown}")
        pairs = {(members[i], members[j]) for i in range(len(members)) for j in range(i + 1, len(members))}
        if edge_type in HARD_COLLAPSE_EDGE_TYPES:
            hard_pairs.update(pairs)
            strength = "HARD_INDEPENDENCE_COLLAPSE"
        elif edge_type in SOFT_DEPENDENCY_EDGE_TYPES:
            soft_pairs.update(pairs)
            strength = "SOFT_NULL_MODEL_DEPENDENCY"
        else:
            strength = "DECLARED_OTHER"
        component_rows.append(
            {
                "component_id": component["component_id"],
                "edge_type": edge_type,
                "members": members,
                "independence_effect": strength,
                "note": component.get("note"),
            }
        )

    selection_groups: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        root = case.get("selection_process_root")
        if root:
            selection_groups[str(root)].append(str(case["case_id"]))

    strict_count = len(strict_roots)
    inclusive_count = len(strict_roots | uncertain_roots)
    expected = document.get("frozen_expected_counts", {})
    if expected:
        if int(expected.get("case_family_count", len(cases))) != len(cases):
            raise ValueError("case family count drift")
        if int(expected.get("strict_phenomenon_session_root_count", strict_count)) != strict_count:
            raise ValueError("strict phenomenon root count drift")
        if int(expected.get("inclusive_phenomenology_root_count", inclusive_count)) != inclusive_count:
            raise ValueError("inclusive phenomenon root count drift")

    return {
        "schema": "janus.demihead.not_prediction_atomic_graph_result.v1",
        "artifact_id": document.get("artifact_id"),
        "counting": {
            "semantic_case_family_count": len(cases),
            "strict_phenomenon_session_root_count": strict_count,
            "uncertain_phenomenology_root_count": len(uncertain_roots),
            "inclusive_phenomenology_root_count": inclusive_count,
            "unique_reference_anchor_root_count": len(reference_roots),
            "unique_method_root_count": len(method_roots),
            "comparison_edge_count": len(comparison_edges),
            "subevent_count_not_independence_adjusted": total_subevents,
        },
        "class_counts": dict(sorted(class_counts.items())),
        "per_case": sorted(per_case, key=lambda row: row["case_id"]),
        "dependency_components": component_rows,
        "hard_dependency_pair_count": len(hard_pairs),
        "soft_dependency_pair_count": len(soft_pairs),
        "selection_process_groups": [
            {"selection_process_root": key, "case_ids": sorted(value), "case_count": len(set(value))}
            for key, value in sorted(selection_groups.items())
        ],
        "claim_ceiling": "ACCOUNTING_AND_DEPENDENCY_GRAPH_ONLY",
        "truth_claim": "NOT_MADE",
        "prediction_claim": "NOT_PROMOTED",
        "prophecy_claim": "NOT_PROMOTED",
        "precognition_claim": "NOT_PROMOTED",
        "physical_retrocausality_claim": "NOT_PROMOTED",
        "invariants": [
            "SEMANTIC_CASE_FAMILY_COUNT != PHENOMENON_SESSION_ROOT_COUNT",
            "PRESENTATION_COUNT != SOURCE_ROOT_COUNT != EVENT_ROOT_COUNT",
            "SUBEVENT_COUNT != SESSION_ROOT_COUNT",
            "METHOD_ROOT != PHENOMENON_EVENT",
            "COMPARISON_EDGE != PREDICTION",
            "SAME_EVENT_ROOT != INDEPENDENT_CONFIRMATION",
            "SHARED_SELECTION_ROOT != INDEPENDENT_SAMPLE",
            "SHARED_ONTOLOGY_REQUIRES_MATCHED_NULL",
            "MODEL_OUTPUT != EVIDENCE",
        ],
        "release_control": "OPEN_REVIEW",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="DemiHead atomic event/session/dependency analyzer for JANUS Not-Prediction baseline cases.")
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
