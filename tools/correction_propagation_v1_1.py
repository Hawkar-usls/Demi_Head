from __future__ import annotations

from typing import Any

from fundamentum_truth_guard import CORRECTION_GRAPH_SCHEMA, propagate_corrections


HARDENED_CORRECTION_RESULT_SCHEMA = "janus.demihead.correction_graph_result.v1_1"

INVARIANTS_V1_1 = [
    "CORRECTION_ID != REUSABLE_MUTATION_CHANNEL",
    "DUPLICATE_CORRECTION_ID => INVALID_GRAPH",
    "CORRECTION != DELETION",
    "DESCENDANT != IMMUNE_TO_ROOT_CORRECTION",
    "UNVERIFIED_CORRECTION != APPLIED_CORRECTION",
]


def propagate_corrections_hardened(graph: dict[str, Any]) -> dict[str, Any]:
    """Run v1 propagation after enforcing immutable correction identifiers.

    The v1 propagator correctly preserves cycles and historical nodes, but it
    accepted the same ``correction_id`` more than once.  A repeated id could make
    one logical correction appear both pending and verified, or create duplicate
    annotations.  v1.1 rejects that ambiguity before any propagation occurs.
    """

    if graph.get("schema") != CORRECTION_GRAPH_SCHEMA:
        raise ValueError(f"Unsupported correction graph schema; expected {CORRECTION_GRAPH_SCHEMA}")

    corrections = graph.get("corrections", [])
    if not isinstance(corrections, list):
        raise ValueError("corrections must be a list")

    correction_ids: list[str] = []
    for index, correction in enumerate(corrections):
        if not isinstance(correction, dict):
            raise ValueError(f"Correction at index {index} must be an object")
        correction_id = str(correction.get("correction_id", "")).strip()
        if not correction_id:
            raise ValueError("Correction requires a non-empty correction_id")
        correction_ids.append(correction_id)

    duplicates = sorted({item for item in correction_ids if correction_ids.count(item) > 1})
    if duplicates:
        raise ValueError(f"DUPLICATE_CORRECTION_ID:{duplicates}")

    result = dict(propagate_corrections(graph))
    result["schema"] = HARDENED_CORRECTION_RESULT_SCHEMA
    result["hardening_version"] = "v1.1"
    result["correction_id_uniqueness_enforced"] = True
    result["duplicate_correction_ids"] = []
    result["invariants_v1_1"] = INVARIANTS_V1_1
    result["claim_ceiling"] = (
        "v1.1 establishes deterministic propagation for unique correction identifiers in this supplied graph. "
        "It does not establish that a correction is true merely because verified=true was supplied, and it never "
        "authorizes destructive historical rewriting or an external effect."
    )
    return result


__all__ = [
    "HARDENED_CORRECTION_RESULT_SCHEMA",
    "INVARIANTS_V1_1",
    "propagate_corrections_hardened",
]
