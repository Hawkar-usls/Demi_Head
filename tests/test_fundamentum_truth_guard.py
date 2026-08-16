from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from epistemic_execution_gate import CASE_SCHEMA, CURRENT_STATE, EXACT_COMPUTATION  # noqa: E402
from fundamentum_truth_guard import (  # noqa: E402
    COMMIT_CASE_SCHEMA,
    CORRECTION_GRAPH_SCHEMA,
    LANGUAGE_BUNDLE_SCHEMA,
    assess_commit_case,
    assess_language_bundle,
    propagate_corrections,
    self_test,
)


def execution_receipt(value: str, *, origin: str = "trusted_local_tool") -> dict[str, object]:
    return {
        "kind": "execution_receipt",
        "origin": origin,
        "execution_state": "EXECUTED",
        "input_bound": True,
        "result_bound": True,
        "computed_value": value,
    }


class FundamentumTruthGuardTests(unittest.TestCase):
    def test_model_only_winner_cannot_cross_commit_threshold(self) -> None:
        result = assess_commit_case({
            "schema": COMMIT_CASE_SCHEMA,
            "case_id": "MODEL_ONLY",
            "candidate_manifest": ["A"],
            "proposed_commit_id": "A",
            "witness_ledger": [{
                "candidate_id": "A",
                "terminal": "retained",
                "provenance": {"generator": "face-A"},
                "epistemic_case": {
                    "schema": CASE_SCHEMA,
                    "case_id": "A",
                    "claim_type": EXACT_COMPUTATION,
                    "claim": "computed value",
                    "claimed_value": "x",
                    "evidence": [{"kind": "model_output", "text": "x"}],
                },
            }],
        })
        self.assertEqual(result["commit_state"], "OPEN_INSUFFICIENT_EVIDENCE")
        self.assertFalse(result["definitive_claim_permitted"])

    def test_verified_winner_can_commit_only_when_losing_branch_is_preserved(self) -> None:
        result = assess_commit_case({
            "schema": COMMIT_CASE_SCHEMA,
            "case_id": "PRESERVE_LOSER",
            "candidate_manifest": ["A", "B"],
            "proposed_commit_id": "A",
            "witness_ledger": [
                {
                    "candidate_id": "A",
                    "terminal": "retained",
                    "provenance": {"generator": "face-A"},
                    "epistemic_case": {
                        "schema": CASE_SCHEMA,
                        "case_id": "A",
                        "claim_type": EXACT_COMPUTATION,
                        "claim": "computed value",
                        "claimed_value": "good",
                        "evidence": [execution_receipt("good")],
                    },
                },
                {
                    "candidate_id": "B",
                    "terminal": "failed_verification",
                    "reason": "Executed receipt refuted this candidate",
                    "provenance": {"generator": "face-B"},
                    "epistemic_case": {
                        "schema": CASE_SCHEMA,
                        "case_id": "B",
                        "claim_type": EXACT_COMPUTATION,
                        "claim": "computed value",
                        "claimed_value": "bad",
                        "evidence": [execution_receipt("good")],
                    },
                },
            ],
        })
        self.assertEqual(result["commit_state"], "COMMIT_SUPPORTED_WITHIN_RECEIPT_SCOPE")
        self.assertTrue(result["definitive_claim_permitted"])
        self.assertTrue(result["witness_ledger_complete"])
        self.assertEqual(len(result["candidate_rows"]), 2)

    def test_missing_candidate_from_witness_ledger_is_non_fundamentum(self) -> None:
        result = assess_commit_case({
            "schema": COMMIT_CASE_SCHEMA,
            "case_id": "MISSING",
            "candidate_manifest": ["A", "B"],
            "proposed_commit_id": "A",
            "witness_ledger": [{
                "candidate_id": "A",
                "terminal": "retained",
                "provenance": {"generator": "face-A"},
                "epistemic_case": {
                    "schema": CASE_SCHEMA,
                    "case_id": "A",
                    "claim_type": EXACT_COMPUTATION,
                    "claim": "computed value",
                    "claimed_value": "good",
                    "evidence": [execution_receipt("good")],
                },
            }],
        })
        self.assertEqual(result["commit_state"], "NON_FUNDAMENTUM_LEDGER_INVALID")
        self.assertFalse(result["witness_ledger_complete"])

    def test_live_material_plurality_blocks_premature_collapse(self) -> None:
        result = assess_commit_case({
            "schema": COMMIT_CASE_SCHEMA,
            "case_id": "PLURALITY",
            "candidate_manifest": ["A", "B"],
            "proposed_commit_id": "A",
            "witness_ledger": [
                {
                    "candidate_id": "A",
                    "terminal": "retained",
                    "material": True,
                    "provenance": {"generator": "face-A"},
                    "epistemic_case": {
                        "schema": CASE_SCHEMA,
                        "case_id": "A",
                        "claim_type": EXACT_COMPUTATION,
                        "claim": "computed value",
                        "claimed_value": "good",
                        "evidence": [execution_receipt("good")],
                    },
                },
                {
                    "candidate_id": "B",
                    "terminal": "unresolved",
                    "reason": "Awaiting independent source",
                    "material": True,
                    "provenance": {"generator": "face-B"},
                    "epistemic_case": {
                        "schema": CASE_SCHEMA,
                        "case_id": "B",
                        "claim_type": CURRENT_STATE,
                        "claim": "external state",
                        "claimed_value": True,
                        "evidence": [],
                    },
                },
            ],
        })
        self.assertEqual(result["commit_state"], "HOLD_PLURALITY")
        self.assertFalse(result["definitive_claim_permitted"])

    def test_translation_may_change_text_but_not_epistemic_semantics(self) -> None:
        shared = {
            "claim_type": "EXTERNAL_FACT",
            "evidence_state": "CONTESTED",
            "uncertainty": "HIGH",
            "urgency": "NORMAL",
            "user_rights": ["APPEAL", "EXIT"],
            "authority_delta": 0,
            "mass_effect_budget": 0,
            "source_root_ids": ["root-A", "root-B"],
            "correction_links": ["corr-1"],
            "release_control": "SHOW_CONFLICT_AND_RELEASE",
        }
        result = assess_language_bundle({
            "schema": LANGUAGE_BUNDLE_SCHEMA,
            "bundle_id": "UA_RU_EN",
            "variants": [
                {"language": "en", "text": "Sources disagree.", "semantic": shared},
                {"language": "ru", "text": "Источники расходятся.", "semantic": dict(shared)},
                {"language": "uk", "text": "Джерела суперечать одне одному.", "semantic": dict(shared)},
            ],
        })
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["style_text_may_differ"])

    def test_translation_cannot_upgrade_urgency(self) -> None:
        base = {
            "claim_type": "EXTERNAL_FACT",
            "evidence_state": "UNRESOLVED",
            "uncertainty": "HIGH",
            "urgency": "NORMAL",
            "user_rights": ["APPEAL", "EXIT"],
            "authority_delta": 0,
            "mass_effect_budget": 0,
            "source_root_ids": ["root-A"],
            "correction_links": [],
            "release_control": "WAIT_OR_EXIT",
        }
        changed = dict(base)
        changed["urgency"] = "CRITICAL"
        result = assess_language_bundle({
            "schema": LANGUAGE_BUNDLE_SCHEMA,
            "bundle_id": "URGENCY_DRIFT",
            "variants": [
                {"language": "en", "semantic": base},
                {"language": "ru", "semantic": changed},
            ],
        })
        self.assertEqual(result["status"], "INVARIANCE_VIOLATION")
        self.assertEqual(result["mismatches"][0]["field"], "urgency")

    def test_verified_root_correction_propagates_to_all_known_descendants(self) -> None:
        result = propagate_corrections({
            "schema": CORRECTION_GRAPH_SCHEMA,
            "graph_id": "DESCENDANTS",
            "nodes": [
                {"node_id": "root"},
                {"node_id": "article"},
                {"node_id": "translation"},
                {"node_id": "quote"},
            ],
            "edges": [
                {"from": "root", "to": "article"},
                {"from": "article", "to": "translation"},
                {"from": "root", "to": "quote"},
            ],
            "corrections": [{"correction_id": "corr-1", "target_root_id": "root", "verified": True}],
        })
        for node_id in ("root", "article", "translation", "quote"):
            self.assertEqual(result["correction_annotations"][node_id][0]["correction_id"], "corr-1")
        self.assertFalse(result["historical_nodes_deleted"])
        self.assertFalse(result["historical_claim_text_rewritten"])

    def test_unverified_correction_is_preserved_pending_not_propagated_as_fact(self) -> None:
        result = propagate_corrections({
            "schema": CORRECTION_GRAPH_SCHEMA,
            "graph_id": "PENDING",
            "nodes": [{"node_id": "root"}, {"node_id": "child"}],
            "edges": [{"from": "root", "to": "child"}],
            "corrections": [{"correction_id": "corr-pending", "target_root_id": "root", "verified": False}],
        })
        self.assertEqual(result["pending_unverified_corrections"], ["corr-pending"])
        self.assertEqual(result["correction_annotations"]["child"], [])

    def test_builtin_self_test_passes(self) -> None:
        result = self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed"], result["total"])
        json.dumps(result, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
