from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from correction_propagation_v1_1 import propagate_corrections_hardened  # noqa: E402
from fundamentum_truth_guard import CORRECTION_GRAPH_SCHEMA  # noqa: E402
from reviewer_appeal_gate import (  # noqa: E402
    APPEAL_REQUEST_SCHEMA,
    REVIEW_BUNDLE_SCHEMA,
    freeze_appeal,
)
from reviewer_appeal_gate_v1_1 import assess_review_bundle_hardened  # noqa: E402


class ReviewerIndependenceHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        original = {
            "decision_id": "D-HARDEN",
            "state": "CONTESTED",
            "claim": "synthetic hardening claim",
        }
        request = {
            "schema": APPEAL_REQUEST_SCHEMA,
            "appeal_id": "A-HARDEN",
            "original_decision_locator": "synthetic:D-HARDEN",
            "grounds": ["FACTUAL_ACCURACY"],
            "high_stakes": True,
            "user_exit_available": True,
            "penalty_for_appeal": False,
            "surveillance_escalation_for_appeal": False,
        }
        self.package = freeze_appeal(original, request)

    def attestation(self, reviewer: str, root: str, verdict: str, evidence_roots=None):
        if evidence_roots is None:
            evidence_roots = [f"evidence:{root}"]
        return {
            "reviewer_id": reviewer,
            "independence_root_id": root,
            "verdict": verdict,
            "appeal_id": self.package["appeal_id"],
            "appeal_package_digest_sha256": self.package["appeal_package_digest_sha256"],
            "original_decision_digest_sha256": self.package["original_decision_digest_sha256"],
            "independent_submission": True,
            "saw_other_verdicts_before_submission": False,
            "package_bound": True,
            "evidence_root_ids": evidence_roots,
        }

    def bundle(self, attestations):
        return {
            "schema": REVIEW_BUNDLE_SCHEMA,
            "appeal_id": self.package["appeal_id"],
            "appeal_package_digest_sha256": self.package["appeal_package_digest_sha256"],
            "attestations": attestations,
        }

    def test_same_reviewer_cannot_manufacture_two_independent_roots(self):
        result = assess_review_bundle_hardened(
            self.package,
            self.bundle(
                [
                    self.attestation("reviewer-A", "declared-root-A", "UPHOLD", ["evidence:A"]),
                    self.attestation("reviewer-A", "declared-root-B", "UPHOLD", ["evidence:B"]),
                ]
            ),
        )
        self.assertEqual(result["declared_independence_root_count"], 2)
        self.assertEqual(result["effective_independence_component_count"], 1)
        self.assertEqual(result["independent_root_count"], 1)
        self.assertEqual(result["status"], "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED")
        reasons = {reason for item in result["dependency_collapses"] for reason in item["reasons"]}
        self.assertIn("REVIEWER_ID_REUSED_ACROSS_SUBMISSIONS", reasons)

    def test_shared_evidence_root_collapses_declared_independence(self):
        result = assess_review_bundle_hardened(
            self.package,
            self.bundle(
                [
                    self.attestation("reviewer-A", "declared-root-A", "UPHOLD", ["evidence:shared"]),
                    self.attestation("reviewer-B", "declared-root-B", "UPHOLD", ["evidence:shared"]),
                ]
            ),
        )
        self.assertEqual(result["declared_independence_root_count"], 2)
        self.assertEqual(result["effective_independence_component_count"], 1)
        self.assertEqual(result["status"], "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED")
        reasons = {reason for item in result["dependency_collapses"] for reason in item["reasons"]}
        self.assertIn("DECLARED_ROOTS_SHARE_EVIDENCE_ROOT", reasons)

    def test_independent_reviewer_and_evidence_roots_still_reach_structural_consensus(self):
        result = assess_review_bundle_hardened(
            self.package,
            self.bundle(
                [
                    self.attestation("reviewer-A", "declared-root-A", "UPHOLD", ["evidence:A"]),
                    self.attestation("reviewer-B", "declared-root-B", "UPHOLD", ["evidence:B"]),
                ]
            ),
        )
        self.assertEqual(result["effective_independence_component_count"], 2)
        self.assertEqual(result["status"], "CONSENSUS_UPHOLD")
        self.assertFalse(result["real_world_independence_established"])
        self.assertFalse(result["external_effect_authorized"])

    def test_conflict_inside_dependency_component_is_preserved(self):
        result = assess_review_bundle_hardened(
            self.package,
            self.bundle(
                [
                    self.attestation("reviewer-A", "declared-root-A", "UPHOLD", ["evidence:shared"]),
                    self.attestation("reviewer-B", "declared-root-B", "CORRECTION_SUPPORTED", ["evidence:shared"]),
                ]
            ),
        )
        self.assertEqual(result["effective_independence_component_count"], 1)
        self.assertEqual(result["status"], "DISAGREEMENT")

    def test_missing_evidence_root_metadata_cannot_reach_consensus_terminal(self):
        result = assess_review_bundle_hardened(
            self.package,
            self.bundle(
                [
                    self.attestation("reviewer-A", "root-A", "UPHOLD", []),
                    self.attestation("reviewer-B", "root-B", "UPHOLD", []),
                ]
            ),
        )
        self.assertEqual(result["status"], "OPEN_INDEPENDENCE_METADATA_REQUIRED")
        self.assertFalse(result["independence_metadata_complete"])
        self.assertIsNone(result["correction_proposal"])


class CorrectionIdentityHardeningTests(unittest.TestCase):
    @staticmethod
    def graph(corrections):
        return {
            "schema": CORRECTION_GRAPH_SCHEMA,
            "graph_id": "G-HARDEN",
            "nodes": [
                {"node_id": "root"},
                {"node_id": "child"},
            ],
            "edges": [{"from": "root", "to": "child"}],
            "corrections": corrections,
        }

    def test_duplicate_correction_id_is_rejected_before_propagation(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_CORRECTION_ID"):
            propagate_corrections_hardened(
                self.graph(
                    [
                        {"correction_id": "C1", "target_root_id": "root", "verified": False},
                        {"correction_id": "C1", "target_root_id": "root", "verified": True},
                    ]
                )
            )

    def test_unique_verified_correction_propagates_without_deleting_history(self):
        result = propagate_corrections_hardened(
            self.graph(
                [
                    {"correction_id": "C1", "target_root_id": "root", "verified": True},
                ]
            )
        )
        self.assertEqual(result["schema"], "janus.demihead.correction_graph_result.v1_1")
        self.assertTrue(result["correction_id_uniqueness_enforced"])
        self.assertFalse(result["historical_nodes_deleted"])
        self.assertFalse(result["historical_claim_text_rewritten"])
        self.assertEqual(result["correction_annotations"]["root"][0]["correction_id"], "C1")
        self.assertEqual(result["correction_annotations"]["child"][0]["correction_id"], "C1")


if __name__ == "__main__":
    unittest.main()
