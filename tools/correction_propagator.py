from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


INPUT_SCHEMA = "janus.demihead.correction_graph.v1"
RESULT_SCHEMA = "janus.demihead.correction_propagation_result.v1"


class CorrectionGraphError(ValueError):
    pass


def load_graph(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        graph = json.load(handle)
    if graph.get("schema") != INPUT_SCHEMA:
        raise CorrectionGraphError("Unsupported correction graph schema")
    return graph


def _unique_index(rows: list[dict[str, Any]], key: str, label: str) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for row in rows:
        value = row.get(key)
        if not isinstance(value, str) or not value:
            raise CorrectionGraphError(f"{label} requires non-empty {key}")
        if value in index:
            raise CorrectionGraphError(f"Duplicate {label} {key}: {value}")
        index[value] = row
    return index


def _build_correction_maps(
    corrections: list[dict[str, Any]],
    roots: dict[str, dict[str, Any]],
) -> dict[str, dict[str, tuple[str, str]]]:
    by_root: dict[str, dict[str, tuple[str, str]]] = {root_id: {} for root_id in roots}

    for correction in corrections:
        correction_id = correction["correction_id"]
        root_id = correction.get("root_id")
        superseded = correction.get("superseded_revision_id")
        replacement = correction.get("replacement_revision_id")

        if root_id not in roots:
            raise CorrectionGraphError(f"Correction {correction_id} references unknown root: {root_id}")
        if not isinstance(superseded, str) or not superseded:
            raise CorrectionGraphError(f"Correction {correction_id} requires superseded_revision_id")
        if not isinstance(replacement, str) or not replacement:
            raise CorrectionGraphError(f"Correction {correction_id} requires replacement_revision_id")
        if superseded == replacement:
            raise CorrectionGraphError(f"Correction {correction_id} cannot replace a revision with itself")
        if superseded in by_root[root_id]:
            raise CorrectionGraphError(
                f"Ambiguous correction branch for root {root_id}, revision {superseded}"
            )
        by_root[root_id][superseded] = (replacement, correction_id)

    for root_id, transitions in by_root.items():
        current = roots[root_id].get("current_revision_id")
        if not isinstance(current, str) or not current:
            raise CorrectionGraphError(f"Root {root_id} requires current_revision_id")
        if current in transitions:
            raise CorrectionGraphError(f"Current revision {current} of {root_id} is itself superseded")

        for start in transitions:
            seen: set[str] = set()
            revision = start
            while revision in transitions:
                if revision in seen:
                    raise CorrectionGraphError(f"Correction cycle detected for root {root_id}")
                seen.add(revision)
                revision = transitions[revision][0]
            if revision != current:
                raise CorrectionGraphError(
                    f"Correction chain for root {root_id} does not terminate at current revision {current}"
                )

    return by_root


def propagate_corrections(graph: dict[str, Any]) -> dict[str, Any]:
    roots_list = graph.get("roots")
    presentations = graph.get("presentations")
    corrections = graph.get("corrections")
    if not isinstance(roots_list, list) or not roots_list:
        raise CorrectionGraphError("roots must be a non-empty list")
    if not isinstance(presentations, list):
        raise CorrectionGraphError("presentations must be a list")
    if not isinstance(corrections, list):
        raise CorrectionGraphError("corrections must be a list")

    roots = _unique_index(roots_list, "root_id", "root")
    _unique_index(presentations, "presentation_id", "presentation")
    corrections_index = _unique_index(corrections, "correction_id", "correction")
    transitions_by_root = _build_correction_maps(list(corrections_index.values()), roots)

    rows: list[dict[str, Any]] = []
    counts = {
        "CURRENT": 0,
        "AFFECTED_BY_CORRECTION": 0,
        "UNKNOWN_LINEAGE": 0,
        "UNKNOWN_REVISION_LINEAGE": 0,
    }

    for presentation in presentations:
        presentation_id = presentation["presentation_id"]
        root_id = presentation.get("root_id")
        bound_revision = presentation.get("bound_revision_id")

        if not isinstance(root_id, str) or not root_id or root_id not in roots:
            status = "UNKNOWN_LINEAGE"
            row = {
                "presentation_id": presentation_id,
                "root_id": root_id,
                "bound_revision_id": bound_revision,
                "status": status,
                "correction_chain": [],
                "current_revision_id": None,
                "reason": "NO_KNOWN_ROOT_BINDING",
            }
            counts[status] += 1
            rows.append(row)
            continue

        current = roots[root_id]["current_revision_id"]
        if not isinstance(bound_revision, str) or not bound_revision:
            status = "UNKNOWN_REVISION_LINEAGE"
            chain: list[str] = []
            reason = "NO_BOUND_REVISION"
        elif bound_revision == current:
            status = "CURRENT"
            chain = []
            reason = "BOUND_TO_CURRENT_REVISION"
        else:
            transitions = transitions_by_root[root_id]
            revision = bound_revision
            chain = []
            seen: set[str] = set()
            while revision in transitions:
                if revision in seen:
                    raise CorrectionGraphError(f"Correction cycle encountered while classifying {presentation_id}")
                seen.add(revision)
                replacement, correction_id = transitions[revision]
                chain.append(correction_id)
                revision = replacement

            if chain and revision == current:
                status = "AFFECTED_BY_CORRECTION"
                reason = "BOUND_REVISION_SUPERSEDED_BY_EXPLICIT_CORRECTION_CHAIN"
            else:
                status = "UNKNOWN_REVISION_LINEAGE"
                reason = "BOUND_REVISION_NOT_CONNECTED_TO_CURRENT_REVISION"

        counts[status] += 1
        rows.append(
            {
                "presentation_id": presentation_id,
                "root_id": root_id,
                "bound_revision_id": bound_revision,
                "status": status,
                "correction_chain": chain,
                "current_revision_id": current,
                "reason": reason,
            }
        )

    return {
        "schema": RESULT_SCHEMA,
        "graph_id": graph.get("graph_id", "UNSPECIFIED"),
        "status": "PROPAGATION_COMPLETE_EXPLICIT_LINEAGE_ONLY",
        "accounting": {
            "root_count": len(roots_list),
            "presentation_count": len(presentations),
            "correction_count": len(corrections),
            **{key.lower() + "_count": value for key, value in counts.items()},
        },
        "presentations": rows,
        "history": {
            "roots": roots_list,
            "presentations": presentations,
            "corrections": corrections,
        },
        "invariants": {
            "history_deleted": False,
            "source_text_rewritten": False,
            "unknown_lineage_invented": False,
            "correction_is_truth_proof": False,
            "evidence_authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "established": [
                "Explicit known descendants of explicitly superseded revisions are marked with their explicit correction chain.",
                "Historical roots, presentations and correction records are preserved in the output receipt.",
            ],
            "not_established": [
                "completeness of real-world source discovery",
                "objective truth of a correction",
                "unknown descendant lineage",
                "automatic source-text rewriting",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    graph = {
        "schema": INPUT_SCHEMA,
        "graph_id": "SELF_TEST",
        "roots": [{"root_id": "root-A", "current_revision_id": "r3"}],
        "corrections": [
            {
                "correction_id": "c1",
                "root_id": "root-A",
                "superseded_revision_id": "r1",
                "replacement_revision_id": "r2",
            },
            {
                "correction_id": "c2",
                "root_id": "root-A",
                "superseded_revision_id": "r2",
                "replacement_revision_id": "r3",
            },
        ],
        "presentations": [
            {"presentation_id": "old", "root_id": "root-A", "bound_revision_id": "r1"},
            {"presentation_id": "mid", "root_id": "root-A", "bound_revision_id": "r2"},
            {"presentation_id": "new", "root_id": "root-A", "bound_revision_id": "r3"},
            {"presentation_id": "unknown", "root_id": None, "bound_revision_id": None},
        ],
    }
    result = propagate_corrections(graph)
    by_id = {row["presentation_id"]: row for row in result["presentations"]}
    checks = {
        "old_has_full_chain": by_id["old"]["correction_chain"] == ["c1", "c2"],
        "mid_has_one_correction": by_id["mid"]["correction_chain"] == ["c2"],
        "new_is_current": by_id["new"]["status"] == "CURRENT",
        "unknown_stays_unknown": by_id["unknown"]["status"] == "UNKNOWN_LINEAGE",
        "history_preserved": result["history"] == {
            "roots": graph["roots"],
            "presentations": graph["presentations"],
            "corrections": graph["corrections"],
        },
        "authority_delta_zero": result["invariants"]["evidence_authority_delta"] == 0,
        "mass_effect_delta_zero": result["invariants"]["mass_effect_budget_delta"] == 0,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    return {"self_test": "PASS", "checks": checks, "result": result}


def _render(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description="DemiHead explicit correction propagation reference gate")
    parser.add_argument("graph", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        _render(self_test(), args.output)
        return
    if args.graph is None:
        parser.error("graph is required unless --self-test is used")
    _render(propagate_corrections(load_graph(args.graph)), args.output)


if __name__ == "__main__":
    main()
