from __future__ import annotations

import copy
import hashlib
from collections import defaultdict
from typing import Any

from reviewer_appeal_gate import (
    REVIEW_BUNDLE_SCHEMA,
    assess_review_bundle as assess_review_bundle_v1,
    validate_appeal_package,
)


HARDENED_REVIEW_RESULT_SCHEMA = "janus.demihead.review_result.v1_1"

INVARIANTS_V1_1 = [
    "DECLARED_ROOT_ID != PROVEN_INDEPENDENCE",
    "SAME_REVIEWER_ID => SAME_EFFECTIVE_REVIEW_COMPONENT",
    "SHARED_EVIDENCE_ROOT => SAME_EFFECTIVE_REVIEW_COMPONENT",
    "REVIEWER_COUNT != INDEPENDENT_ROOT_COUNT",
    "CONSENSUS != EXTERNAL_EFFECT_AUTHORIZATION",
    "STRUCTURAL_INDEPENDENCE != REAL_WORLD_IDENTITY_PROOF",
    "DISAGREEMENT != ERROR",
]


class _UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, value: int) -> int:
        while self.parent[value] != value:
            self.parent[value] = self.parent[self.parent[value]]
            value = self.parent[value]
        return value

    def union(self, left: int, right: int) -> None:
        a = self.find(left)
        b = self.find(right)
        if a == b:
            return
        if self.rank[a] < self.rank[b]:
            a, b = b, a
        self.parent[b] = a
        if self.rank[a] == self.rank[b]:
            self.rank[a] += 1


def _normalize_evidence_roots(value: Any) -> tuple[list[str], bool]:
    if not isinstance(value, list):
        return [], False
    roots = sorted({str(item).strip() for item in value if str(item).strip()})
    return roots, bool(roots)


def _component_id(rows: list[dict[str, Any]]) -> str:
    tokens: list[str] = []
    for row in rows:
        tokens.append(f"reviewer:{row['reviewer_id']}")
        tokens.append(f"declared-root:{row['declared_root_id']}")
        tokens.extend(f"evidence:{root}" for root in row["evidence_root_ids"])
    material = "\n".join(sorted(set(tokens))).encode("utf-8")
    return "COMP-" + hashlib.sha256(material).hexdigest()[:16]


def assess_review_bundle_hardened(package: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    """Conservatively derive effective review components before v1 consensus.

    The v1 gate already prevents duplicate declared ``independence_root_id`` values
    from multiplying authority.  This v1.1 layer closes two additional structural
    loopholes without pretending to prove human identity in the real world:

    * one reviewer id cannot manufacture multiple independent roots;
    * roots sharing any evidence root are treated as one dependency component.

    Real-world aliases, collusion, expertise and organizational independence remain
    outside the claim ceiling and require an external identity/provenance system.
    """

    validate_appeal_package(package)
    if bundle.get("schema") != REVIEW_BUNDLE_SCHEMA:
        raise ValueError(f"Unsupported review bundle schema; expected {REVIEW_BUNDLE_SCHEMA}")

    # Preserve all v1 exact-package/blinding checks first.  If they fail, do not
    # attempt to reinterpret an invalid package as an independence problem.
    base_probe = assess_review_bundle_v1(package, bundle)
    if base_probe.get("status") == "PACKAGE_BINDING_FAILURE":
        result = dict(base_probe)
        result["schema"] = HARDENED_REVIEW_RESULT_SCHEMA
        result["hardening_version"] = "v1.1"
        result["dependency_analysis_performed"] = False
        result["real_world_independence_established"] = False
        result["invariants_v1_1"] = INVARIANTS_V1_1
        return result

    attestations = bundle.get("attestations", [])
    if not isinstance(attestations, list):
        raise ValueError("attestations must be a list")

    rows: list[dict[str, Any]] = []
    metadata_gaps: list[dict[str, Any]] = []
    for index, attestation in enumerate(attestations):
        # The v1 probe above has already rejected non-object or otherwise invalid
        # attestations.  Keep this guard for callers that change v1 behavior later.
        if not isinstance(attestation, dict):
            raise ValueError("ATTESTATION_NOT_OBJECT_AFTER_V1_VALIDATION")
        reviewer_id = str(attestation.get("reviewer_id", "")).strip()
        declared_root_id = str(attestation.get("independence_root_id", "")).strip()
        evidence_roots, complete = _normalize_evidence_roots(attestation.get("evidence_root_ids"))
        if not complete:
            metadata_gaps.append(
                {
                    "index": index,
                    "reviewer_id": reviewer_id or None,
                    "reason": "EVIDENCE_ROOT_IDS_REQUIRED_FOR_V1_1_INDEPENDENCE",
                }
            )
        rows.append(
            {
                "index": index,
                "reviewer_id": reviewer_id,
                "declared_root_id": declared_root_id,
                "evidence_root_ids": evidence_roots,
            }
        )

    uf = _UnionFind(len(rows))
    by_declared_root: dict[str, list[int]] = defaultdict(list)
    by_reviewer: dict[str, list[int]] = defaultdict(list)
    by_evidence_root: dict[str, list[int]] = defaultdict(list)

    for row in rows:
        idx = row["index"]
        by_declared_root[row["declared_root_id"]].append(idx)
        by_reviewer[row["reviewer_id"]].append(idx)
        for root in row["evidence_root_ids"]:
            by_evidence_root[root].append(idx)

    def union_group(indices: list[int]) -> None:
        if len(indices) < 2:
            return
        first = indices[0]
        for other in indices[1:]:
            uf.union(first, other)

    for indices in by_declared_root.values():
        union_group(indices)
    for indices in by_reviewer.values():
        union_group(indices)
    for indices in by_evidence_root.values():
        union_group(indices)

    components: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        components[uf.find(row["index"])].append(row)

    component_ids: dict[int, str] = {
        root: _component_id(component_rows)
        for root, component_rows in components.items()
    }

    dependency_collapses: list[dict[str, Any]] = []
    for root, component_rows in sorted(components.items(), key=lambda item: component_ids[item[0]]):
        declared_roots = sorted({row["declared_root_id"] for row in component_rows})
        reviewers = sorted({row["reviewer_id"] for row in component_rows})
        evidence_roots = sorted({value for row in component_rows for value in row["evidence_root_ids"]})
        reasons: list[str] = []
        if len(component_rows) > 1:
            if len(reviewers) < len(component_rows):
                reasons.append("REVIEWER_ID_REUSED_ACROSS_SUBMISSIONS")
            if len(declared_roots) > 1:
                shared = [
                    evidence_root
                    for evidence_root, indices in by_evidence_root.items()
                    if len(indices) > 1 and any(index in {row['index'] for row in component_rows} for index in indices)
                ]
                if shared:
                    reasons.append("DECLARED_ROOTS_SHARE_EVIDENCE_ROOT")
            if len(declared_roots) == 1:
                reasons.append("SAME_DECLARED_ROOT")
        if reasons:
            dependency_collapses.append(
                {
                    "effective_component_id": component_ids[root],
                    "declared_root_ids": declared_roots,
                    "reviewer_ids": reviewers,
                    "evidence_root_ids": evidence_roots,
                    "reasons": sorted(set(reasons)),
                }
            )

    rewritten = copy.deepcopy(bundle)
    rewritten_attestations = rewritten.get("attestations", [])
    for row in rows:
        component_root = uf.find(row["index"])
        rewritten_attestations[row["index"]]["declared_independence_root_id"] = row["declared_root_id"]
        rewritten_attestations[row["index"]]["independence_root_id"] = component_ids[component_root]

    hardened = assess_review_bundle_v1(package, rewritten)
    result = dict(hardened)
    result["schema"] = HARDENED_REVIEW_RESULT_SCHEMA
    result["base_result_schema"] = hardened.get("schema")
    result["hardening_version"] = "v1.1"
    result["dependency_analysis_performed"] = True
    result["declared_independence_root_count"] = len({row["declared_root_id"] for row in rows})
    result["effective_independence_component_count"] = len(components)
    result["dependency_collapses"] = dependency_collapses
    result["independence_metadata_complete"] = not metadata_gaps
    result["independence_metadata_gaps"] = metadata_gaps
    result["real_world_independence_established"] = False
    result["invariants_v1_1"] = INVARIANTS_V1_1

    # Missing evidence-root metadata is a claim-ceiling problem, not a package
    # tamper problem.  Preserve the review ledger but do not allow a structural
    # consensus terminal to masquerade as independently rooted consensus.
    if metadata_gaps and str(result.get("status", "")).startswith("CONSENSUS_"):
        result["status_before_independence_metadata_gate"] = result["status"]
        result["status"] = "OPEN_INDEPENDENCE_METADATA_REQUIRED"
        result["correction_proposal"] = None

    result["claim_ceiling"] = (
        "This v1.1 result conservatively collapses submissions that share a declared root, reviewer id, "
        "or evidence root. It still does not prove reviewer identity, expertise, honesty, alias uniqueness, "
        "organizational independence, world truth, or permission for an external effect."
    )
    return result


__all__ = [
    "HARDENED_REVIEW_RESULT_SCHEMA",
    "INVARIANTS_V1_1",
    "assess_review_bundle_hardened",
]
