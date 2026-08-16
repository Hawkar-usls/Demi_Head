from __future__ import annotations

import argparse
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from epistemic_execution_gate import CASE_SCHEMA, EXACT_COMPUTATION, assess_case


COMMIT_CASE_SCHEMA = "janus.demihead.fundamentum_commit_case.v1"
COMMIT_RESULT_SCHEMA = "janus.demihead.fundamentum_commit_result.v1"
LANGUAGE_BUNDLE_SCHEMA = "janus.demihead.language_invariance_bundle.v1"
LANGUAGE_RESULT_SCHEMA = "janus.demihead.language_invariance_result.v1"
CORRECTION_GRAPH_SCHEMA = "janus.demihead.correction_graph.v1"
CORRECTION_RESULT_SCHEMA = "janus.demihead.correction_graph_result.v1"

ALLOWED_TERMINALS = {
    "retained",
    "rejected_with_reason",
    "failed_verification",
    "timed_out",
    "budget_exhausted",
    "deferred",
    "unresolved",
}

SEMANTIC_FIELDS = (
    "claim_type",
    "evidence_state",
    "uncertainty",
    "urgency",
    "user_rights",
    "authority_delta",
    "mass_effect_budget",
    "source_root_ids",
    "correction_links",
    "release_control",
)

INVARIANTS = [
    "ANSWER_WITHOUT_WITNESS_LEDGER => NON_FUNDAMENTUM",
    "GENERATION != VERIFICATION",
    "CONFIDENCE != VERIFIER",
    "UNVERIFIED_WINNER != COMMIT",
    "REJECTED_BRANCH != ERASED_BRANCH",
    "DISAGREEMENT != ERROR",
    "UNRESOLVED != FAILURE",
    "OPEN_TERMINAL != FABRICATED_CLOSURE",
    "TRANSLATION != EVIDENCE_UPGRADE",
    "TRANSLATION != URGENCY_UPGRADE",
    "TRANSLATION != AUTHORITY_UPGRADE",
    "CORRECTION != DELETION",
    "DESCENDANT != IMMUNE_TO_ROOT_CORRECTION",
    "MORE_COMPUTE != MORE_TRUTH",
    "LATENCY != AUTHORITY",
    "MASS_EFFECT_BUDGET_DEFAULT = 0",
]


def _render(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def _normalized_semantic_value(field: str, value: Any) -> Any:
    if field in {"user_rights", "source_root_ids", "correction_links"}:
        if not isinstance(value, list):
            return value
        return sorted(json.dumps(item, ensure_ascii=False, sort_keys=True) for item in value)
    return value


def assess_language_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    if bundle.get("schema") != LANGUAGE_BUNDLE_SCHEMA:
        raise ValueError(f"Unsupported language bundle schema; expected {LANGUAGE_BUNDLE_SCHEMA}")

    variants = bundle.get("variants")
    if not isinstance(variants, list) or len(variants) < 2:
        raise ValueError("Language invariance requires at least two language variants")

    seen_languages: set[str] = set()
    normalized_rows: list[dict[str, Any]] = []
    missing_fields: list[dict[str, Any]] = []
    for variant in variants:
        language = str(variant.get("language", "")).strip()
        if not language:
            raise ValueError("Every language variant requires a language identifier")
        if language in seen_languages:
            raise ValueError(f"Duplicate language variant: {language}")
        seen_languages.add(language)

        semantic = variant.get("semantic")
        if not isinstance(semantic, dict):
            raise ValueError(f"Variant {language} requires a semantic object")

        row: dict[str, Any] = {"language": language}
        for field in SEMANTIC_FIELDS:
            if field not in semantic:
                missing_fields.append({"language": language, "field": field})
                row[field] = "__MISSING__"
            else:
                row[field] = _normalized_semantic_value(field, semantic[field])
        normalized_rows.append(row)

    reference = normalized_rows[0]
    mismatches: list[dict[str, Any]] = []
    for row in normalized_rows[1:]:
        for field in SEMANTIC_FIELDS:
            if row[field] != reference[field]:
                mismatches.append(
                    {
                        "language": row["language"],
                        "reference_language": reference["language"],
                        "field": field,
                        "reference_value": reference[field],
                        "observed_value": row[field],
                    }
                )

    status = "PASS" if not mismatches and not missing_fields else "INVARIANCE_VIOLATION"
    return {
        "schema": LANGUAGE_RESULT_SCHEMA,
        "bundle_id": bundle.get("bundle_id", "UNKNOWN"),
        "status": status,
        "languages": sorted(seen_languages),
        "semantic_fields": list(SEMANTIC_FIELDS),
        "missing_fields": missing_fields,
        "mismatches": mismatches,
        "style_text_may_differ": True,
        "semantic_upgrade_permitted_by_translation": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "invariants": INVARIANTS,
    }


def propagate_corrections(graph: dict[str, Any]) -> dict[str, Any]:
    if graph.get("schema") != CORRECTION_GRAPH_SCHEMA:
        raise ValueError(f"Unsupported correction graph schema; expected {CORRECTION_GRAPH_SCHEMA}")

    node_ids = [str(node.get("node_id", "")) for node in graph.get("nodes", [])]
    if not node_ids or any(not item for item in node_ids):
        raise ValueError("Correction graph requires non-empty node_id values")
    if len(node_ids) != len(set(node_ids)):
        raise ValueError("Correction graph contains duplicate node_id values")
    node_set = set(node_ids)

    children: dict[str, list[str]] = defaultdict(list)
    for edge in graph.get("edges", []):
        source = str(edge.get("from", ""))
        target = str(edge.get("to", ""))
        if source not in node_set or target not in node_set:
            raise ValueError("Correction graph edge references an unknown node")
        children[source].append(target)

    annotations: dict[str, list[dict[str, Any]]] = {node_id: [] for node_id in node_ids}
    pending: list[str] = []
    for correction in graph.get("corrections", []):
        correction_id = str(correction.get("correction_id", ""))
        root_id = str(correction.get("target_root_id", ""))
        if not correction_id or root_id not in node_set:
            raise ValueError("Correction requires correction_id and a known target_root_id")
        if correction.get("verified") is not True:
            pending.append(correction_id)
            continue

        queue: deque[tuple[str, int]] = deque([(root_id, 0)])
        visited: set[str] = set()
        while queue:
            node_id, depth = queue.popleft()
            if node_id in visited:
                continue
            visited.add(node_id)
            annotations[node_id].append(
                {
                    "correction_id": correction_id,
                    "origin_root_id": root_id,
                    "distance_from_root": depth,
                    "relation": "ROOT_CORRECTION" if depth == 0 else "INHERITED_ROOT_CORRECTION",
                }
            )
            for child in children.get(node_id, []):
                queue.append((child, depth + 1))

    annotations = {
        node_id: sorted(rows, key=lambda row: (row["correction_id"], row["distance_from_root"]))
        for node_id, rows in annotations.items()
    }
    return {
        "schema": CORRECTION_RESULT_SCHEMA,
        "graph_id": graph.get("graph_id", "UNKNOWN"),
        "status": "PASS",
        "correction_annotations": annotations,
        "pending_unverified_corrections": sorted(pending),
        "historical_nodes_deleted": False,
        "historical_claim_text_rewritten": False,
        "destructive_rewrite_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "invariants": INVARIANTS,
    }


def assess_commit_case(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("schema") != COMMIT_CASE_SCHEMA:
        raise ValueError(f"Unsupported commit case schema; expected {COMMIT_CASE_SCHEMA}")

    manifest = [str(item) for item in case.get("candidate_manifest", [])]
    ledger = case.get("witness_ledger", [])
    if not manifest:
        raise ValueError("candidate_manifest must not be empty")
    if len(manifest) != len(set(manifest)):
        raise ValueError("candidate_manifest contains duplicate ids")
    if not isinstance(ledger, list):
        raise ValueError("witness_ledger must be a list")

    ledger_ids = [str(item.get("candidate_id", "")) for item in ledger]
    duplicate_ledger_ids = sorted({item for item in ledger_ids if ledger_ids.count(item) > 1})
    missing = sorted(set(manifest) - set(ledger_ids))
    unexpected = sorted(set(ledger_ids) - set(manifest))

    rows: list[dict[str, Any]] = []
    structural_errors: list[str] = []
    if duplicate_ledger_ids:
        structural_errors.append(f"duplicate ledger candidate ids: {duplicate_ledger_ids}")
    if missing:
        structural_errors.append(f"manifest candidates missing from witness ledger: {missing}")
    if unexpected:
        structural_errors.append(f"unexpected ledger candidates absent from manifest: {unexpected}")

    retained_material: list[str] = []
    live_material: list[str] = []
    contested_material: list[str] = []
    for entry in ledger:
        candidate_id = str(entry.get("candidate_id", ""))
        terminal = entry.get("terminal")
        material = entry.get("material", True) is not False
        provenance = entry.get("provenance")
        reason = entry.get("reason")
        epistemic_case = entry.get("epistemic_case")

        if terminal not in ALLOWED_TERMINALS:
            structural_errors.append(f"candidate {candidate_id}: invalid terminal {terminal!r}")
        if not provenance:
            structural_errors.append(f"candidate {candidate_id}: provenance is required")
        if terminal != "retained" and not reason:
            structural_errors.append(f"candidate {candidate_id}: non-retained terminal requires a reason")
        if not isinstance(epistemic_case, dict):
            structural_errors.append(f"candidate {candidate_id}: epistemic_case is required")
            assessment = {
                "evidence_state": "EVIDENCE_INSUFFICIENT",
                "definitive_claim_permitted": False,
                "response_policy": "DO_NOT_COMMIT",
            }
        else:
            assessment = assess_case(epistemic_case)

        state = assessment["evidence_state"]
        if material and terminal == "retained":
            retained_material.append(candidate_id)
        if material and terminal in {"retained", "deferred", "unresolved", "timed_out", "budget_exhausted"}:
            live_material.append(candidate_id)
        if material and state.startswith("CONTESTED"):
            contested_material.append(candidate_id)
            if terminal == "rejected_with_reason":
                structural_errors.append(
                    f"candidate {candidate_id}: contested material branch cannot be silently closed as rejected"
                )

        rows.append(
            {
                "candidate_id": candidate_id,
                "terminal": terminal,
                "material": material,
                "provenance_present": bool(provenance),
                "reason": reason,
                "epistemic_assessment": assessment,
            }
        )

    proposed_commit_id = case.get("proposed_commit_id")
    commit_state = "OPEN_INSUFFICIENT_EVIDENCE"
    definitive_claim_permitted = False
    reasons: list[str] = []

    if structural_errors:
        commit_state = "NON_FUNDAMENTUM_LEDGER_INVALID"
        reasons.extend(structural_errors)
    elif contested_material:
        commit_state = "HOLD_CONTESTED"
        reasons.append(f"Material contested branches remain live: {sorted(contested_material)}")
    elif proposed_commit_id is None:
        commit_state = "OPEN_INSUFFICIENT_EVIDENCE"
        reasons.append("No proposed commit was supplied; open terminal is preserved without fabricated closure.")
    elif str(proposed_commit_id) not in set(manifest):
        commit_state = "NON_FUNDAMENTUM_UNKNOWN_WINNER"
        reasons.append("Proposed commit id is not present in the candidate manifest.")
    else:
        winner = next(row for row in rows if row["candidate_id"] == str(proposed_commit_id))
        if winner["terminal"] != "retained":
            commit_state = "NON_FUNDAMENTUM_WINNER_NOT_RETAINED"
            reasons.append("Proposed winner is not retained in the witness ledger.")
        elif not winner["epistemic_assessment"]["definitive_claim_permitted"]:
            commit_state = "OPEN_INSUFFICIENT_EVIDENCE"
            reasons.append("Proposed winner lacks an admissible verification path.")
        else:
            unresolved_others = sorted(
                candidate_id for candidate_id in live_material if candidate_id != str(proposed_commit_id)
            )
            if unresolved_others:
                commit_state = "HOLD_PLURALITY"
                reasons.append(f"Other material branches remain live: {unresolved_others}")
            elif len(retained_material) != 1:
                commit_state = "HOLD_PLURALITY"
                reasons.append("Exactly one material retained branch is required for a definitive commit.")
            else:
                commit_state = "COMMIT_SUPPORTED_WITHIN_RECEIPT_SCOPE"
                definitive_claim_permitted = True
                reasons.append("Winner is verified within its receipt scope and every manifested branch remains accounted for.")

    return {
        "schema": COMMIT_RESULT_SCHEMA,
        "case_id": case.get("case_id", "UNKNOWN"),
        "commit_state": commit_state,
        "proposed_commit_id": proposed_commit_id,
        "definitive_claim_permitted": definitive_claim_permitted,
        "candidate_manifest": manifest,
        "witness_ledger_complete": not missing and not unexpected and not duplicate_ledger_ids,
        "candidate_rows": rows,
        "reasons": reasons,
        "claim_ceiling": "A successful commit means only that the proposed candidate passed the configured receipt-bound verification and complete-witness-ledger gates. It does not establish universal truth, consciousness, infallibility, or authority over a human.",
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "invariants": INVARIANTS,
    }


def self_test() -> dict[str, Any]:
    good = "good"
    bad = "bad"
    verified_evidence = [{
        "kind": "execution_receipt",
        "origin": "trusted_local_tool",
        "execution_state": "EXECUTED",
        "input_bound": True,
        "result_bound": True,
        "computed_value": good,
    }]
    refuted_evidence = verified_evidence

    cases: list[tuple[str, bool]] = []

    model_only = assess_commit_case({
        "schema": COMMIT_CASE_SCHEMA,
        "case_id": "MODEL_ONLY_WINNER",
        "candidate_manifest": ["A"],
        "proposed_commit_id": "A",
        "witness_ledger": [{
            "candidate_id": "A",
            "terminal": "retained",
            "material": True,
            "provenance": {"origin": "generator"},
            "epistemic_case": {
                "schema": CASE_SCHEMA,
                "case_id": "MODEL_ONLY_A",
                "claim_type": EXACT_COMPUTATION,
                "claim": "computed value",
                "claimed_value": good,
                "evidence": [{"kind": "model_output", "text": good}],
            },
        }],
    })
    cases.append(("model_only_winner_blocked", model_only["commit_state"] == "OPEN_INSUFFICIENT_EVIDENCE"))

    verified = assess_commit_case({
        "schema": COMMIT_CASE_SCHEMA,
        "case_id": "VERIFIED_WITH_REJECTED_ALT",
        "candidate_manifest": ["A", "B"],
        "proposed_commit_id": "A",
        "witness_ledger": [
            {
                "candidate_id": "A",
                "terminal": "retained",
                "material": True,
                "provenance": {"origin": "candidate-generator"},
                "epistemic_case": {
                    "schema": CASE_SCHEMA,
                    "case_id": "A",
                    "claim_type": EXACT_COMPUTATION,
                    "claim": "computed value",
                    "claimed_value": good,
                    "evidence": verified_evidence,
                },
            },
            {
                "candidate_id": "B",
                "terminal": "failed_verification",
                "reason": "Conflicts with executed receipt",
                "material": True,
                "provenance": {"origin": "candidate-generator"},
                "epistemic_case": {
                    "schema": CASE_SCHEMA,
                    "case_id": "B",
                    "claim_type": EXACT_COMPUTATION,
                    "claim": "computed value",
                    "claimed_value": bad,
                    "evidence": refuted_evidence,
                },
            },
        ],
    })
    cases.append(("verified_winner_with_preserved_loser_commits", verified["commit_state"] == "COMMIT_SUPPORTED_WITHIN_RECEIPT_SCOPE"))

    incomplete = assess_commit_case({
        "schema": COMMIT_CASE_SCHEMA,
        "case_id": "MISSING_BRANCH",
        "candidate_manifest": ["A", "B"],
        "proposed_commit_id": "A",
        "witness_ledger": [{
            "candidate_id": "A",
            "terminal": "retained",
            "material": True,
            "provenance": {"origin": "candidate-generator"},
            "epistemic_case": {
                "schema": CASE_SCHEMA,
                "case_id": "A2",
                "claim_type": EXACT_COMPUTATION,
                "claim": "computed value",
                "claimed_value": good,
                "evidence": verified_evidence,
            },
        }],
    })
    cases.append(("missing_witness_branch_fails_closed", incomplete["commit_state"] == "NON_FUNDAMENTUM_LEDGER_INVALID"))

    language = assess_language_bundle({
        "schema": LANGUAGE_BUNDLE_SCHEMA,
        "bundle_id": "UA_RU_EN",
        "variants": [
            {"language": "en", "semantic": {"claim_type": "EXTERNAL_FACT", "evidence_state": "CONTESTED", "uncertainty": "HIGH", "urgency": "NORMAL", "user_rights": ["APPEAL", "EXIT"], "authority_delta": 0, "mass_effect_budget": 0, "source_root_ids": ["R1", "R2"], "correction_links": [], "release_control": "SHOW_AND_RELEASE"}},
            {"language": "uk", "semantic": {"claim_type": "EXTERNAL_FACT", "evidence_state": "CONTESTED", "uncertainty": "HIGH", "urgency": "URGENT", "user_rights": ["APPEAL", "EXIT"], "authority_delta": 0, "mass_effect_budget": 0, "source_root_ids": ["R1", "R2"], "correction_links": [], "release_control": "SHOW_AND_RELEASE"}},
        ],
    })
    cases.append(("translation_cannot_upgrade_urgency", language["status"] == "INVARIANCE_VIOLATION"))

    correction = propagate_corrections({
        "schema": CORRECTION_GRAPH_SCHEMA,
        "graph_id": "CORRECTION_CHAIN",
        "nodes": [{"node_id": "ROOT"}, {"node_id": "D1"}, {"node_id": "D2"}],
        "edges": [{"from": "ROOT", "to": "D1"}, {"from": "D1", "to": "D2"}],
        "corrections": [{"correction_id": "C1", "target_root_id": "ROOT", "verified": True}],
    })
    cases.append(("root_correction_reaches_descendants", [row["correction_id"] for row in correction["correction_annotations"]["D2"]] == ["C1"]))
    cases.append(("correction_preserves_history", correction["historical_nodes_deleted"] is False and correction["historical_claim_text_rewritten"] is False))

    passed = sum(1 for _, ok in cases if ok)
    return {
        "schema": "janus.demihead.fundamentum_truth_guard_self_test.v1",
        "status": "PASS" if passed == len(cases) else "FAIL",
        "passed": passed,
        "total": len(cases),
        "results": [{"name": name, "pass": ok} for name, ok in cases],
        "invariants": INVARIANTS,
    }


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Input JSON must be an object")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="JANUS Fundamentum truth guard: complete witness ledger, translation invariance, and correction propagation."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--commit-case", type=Path, help="Assess a Fundamentum candidate/commit case")
    mode.add_argument("--language-bundle", type=Path, help="Check semantic invariance across language variants")
    mode.add_argument("--correction-graph", type=Path, help="Propagate verified root corrections to known descendants")
    mode.add_argument("--self-test", action="store_true", help="Run deterministic built-in regression tests")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    if args.commit_case is not None:
        result = assess_commit_case(_load(args.commit_case))
    elif args.language_bundle is not None:
        result = assess_language_bundle(_load(args.language_bundle))
    elif args.correction_graph is not None:
        result = propagate_corrections(_load(args.correction_graph))
    else:
        result = self_test()

    _render(result, args.output)


if __name__ == "__main__":
    main()
