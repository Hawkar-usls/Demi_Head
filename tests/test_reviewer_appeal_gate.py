from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from reviewer_appeal_gate import (  # noqa: E402
    APPEAL_REQUEST_SCHEMA,
    REVIEW_BUNDLE_SCHEMA,
    assess_review_bundle,
    freeze_appeal,
    self_test,
    validate_appeal_package,
)


class ReviewerAppealGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original = {
            "decision_id": "D-001",
            "state": "CONTESTED",
            "evidence_state": "CONTESTED",
            "claim": "synthetic claim",
        }
        self.request = {
            "schema": APPEAL_REQUEST_SCHEMA,
            "appeal_id": "A-001",
            "original_decision_locator": "synthetic:D-001",
            "grounds": ["FACTUAL_ACCURACY", "SOURCE_PROVENANCE"],
            "high_stakes": True,
            "user_exit_available": True,
            "penalty_for_appeal": False,
            "surveillance_escalation_for_appeal": False,
        }
        self.package = freeze_appeal(self.original, self.request)

    def attestation(self, reviewer: str, root: str, verdict: str, **overrides):
        row = {
            "reviewer_id": reviewer,
            "independence_root_id": root,
            "verdict": verdict,
            "appeal_id": self.package["appeal_id"],
            "appeal_package_digest_sha256": self.package["appeal_package_digest_sha256"],
            "original_decision_digest_sha256": self.package["original_decision_digest_sha256"],
            "independent_submission": True,
            "saw_other_verdicts_before_submission": False,
            "package_bound": True,
            "evidence_root_ids": [f"source:{root}"],
        }
        row.update(overrides)
        return row

    def bundle(self, attestations, **overrides):
        value = {
            "schema": REVIEW_BUNDLE_SCHEMA,
            "appeal_id": self.package["appeal_id"],
            "appeal_package_digest_sha256": self.package["appeal_package_digest_sha256"],
            "attestations": attestations,
        }
        value.update(overrides)
        return value

    def test_appeal_freezes_original_digest_without_penalty_or_effect_authority(self):
        self.assertTrue(self.package["original_decision_preserved"])
        self.assertFalse(self.package["automatic_overrule"])
        self.assertFalse(self.package["external_effect_authorized"])
        self.assertFalse(self.package["penalty_for_appeal"])
        self.assertFalse(self.package["surveillance_escalation_for_appeal"])
        self.assertTrue(self.package["user_exit_available"])
        self.assertEqual(self.package["authority_delta"], 0)
        self.assertEqual(self.package["mass_effect_budget_delta"], 0)
        validate_appeal_package(self.package)

    def test_modified_appeal_package_fails_digest_validation(self):
        tampered = copy.deepcopy(self.package)
        tampered["grounds"] = ["PROPOSED_ACTION"]
        with self.assertRaisesRegex(ValueError, "APPEAL_PACKAGE_DIGEST_MISMATCH"):
            validate_appeal_package(tampered)

    def test_two_independent_matching_review_roots_create_review_consensus_not_permission(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "root-A", "UPHOLD"),
            self.attestation("reviewer-B", "root-B", "UPHOLD"),
        ]))
        self.assertEqual(result["status"], "CONSENSUS_UPHOLD")
        self.assertEqual(result["independent_root_count"], 2)
        self.assertFalse(result["automatic_overrule"])
        self.assertFalse(result["external_effect_authorized"])

    def test_independent_reviewer_disagreement_is_terminal_not_error(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "root-A", "UPHOLD"),
            self.attestation("reviewer-B", "root-B", "CORRECTION_SUPPORTED"),
        ]))
        self.assertEqual(result["status"], "DISAGREEMENT")
        self.assertFalse(result["automatic_overrule"])
        self.assertTrue(result["original_decision_preserved"])

    def test_two_reviewers_same_root_do_not_count_as_two_independent_witnesses(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "same-root", "UPHOLD"),
            self.attestation("reviewer-B", "same-root", "UPHOLD"),
        ]))
        self.assertEqual(result["reviewer_submission_count"], 2)
        self.assertEqual(result["independent_root_count"], 1)
        self.assertEqual(result["status"], "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED")
        self.assertEqual(len(result["dependent_duplicates"]), 1)

    def test_conflict_inside_same_root_is_preserved_as_disagreement(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "same-root", "UPHOLD"),
            self.attestation("reviewer-B", "same-root", "CORRECTION_SUPPORTED"),
        ]))
        self.assertEqual(result["status"], "DISAGREEMENT")
        self.assertEqual(result["root_outcomes"][0]["verdict"], "INTERNAL_DISAGREEMENT")

    def test_correction_consensus_produces_proposal_not_rewrite(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "root-A", "CORRECTION_SUPPORTED"),
            self.attestation("reviewer-B", "root-B", "CORRECTION_SUPPORTED"),
        ]))
        self.assertEqual(result["status"], "CONSENSUS_CORRECTION_SUPPORTED")
        proposal = result["correction_proposal"]
        self.assertEqual(proposal["status"], "REVIEW_SUPPORTED_NOT_APPLIED")
        self.assertTrue(proposal["requires_separate_correction_propagation"])
        self.assertFalse(proposal["automatic_rewrite"])
        self.assertFalse(result["automatic_overrule"])

    def test_one_independent_reviewer_is_not_high_stakes_consensus(self):
        result = assess_review_bundle(self.package, self.bundle([
            self.attestation("reviewer-A", "root-A", "UPHOLD"),
        ]))
        self.assertEqual(result["status"], "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED")

    def test_exact_package_binding_failure_fails_closed(self):
        bad = self.attestation("reviewer-A", "root-A", "UPHOLD")
        bad["original_decision_digest_sha256"] = "0" * 64
        result = assess_review_bundle(self.package, self.bundle([bad]))
        self.assertEqual(result["status"], "PACKAGE_BINDING_FAILURE")
        self.assertEqual(result["binding_failures"][0]["reasons"], ["ORIGINAL_DECISION_DIGEST_MISMATCH"])
        self.assertFalse(result["external_effect_authorized"])

    def test_reviewer_blinding_claim_is_required(self):
        bad = self.attestation(
            "reviewer-A",
            "root-A",
            "UPHOLD",
            saw_other_verdicts_before_submission=True,
        )
        result = assess_review_bundle(self.package, self.bundle([bad]))
        self.assertEqual(result["status"], "PACKAGE_BINDING_FAILURE")
        self.assertIn("BLINDING_NOT_PRESERVED", result["binding_failures"][0]["reasons"])

    def test_review_count_cannot_request_authority_multiplier(self):
        with self.assertRaisesRegex(ValueError, "REVIEW_COUNT_TO_AUTHORITY_FORBIDDEN"):
            assess_review_bundle(
                self.package,
                self.bundle(
                    [
                        self.attestation("reviewer-A", "root-A", "UPHOLD"),
                        self.attestation("reviewer-B", "root-B", "UPHOLD"),
                    ],
                    requested_reviewer_authority_multiplier=2,
                ),
            )

    def test_appeal_cannot_disable_user_exit(self):
        request = dict(self.request)
        request["user_exit_available"] = False
        with self.assertRaisesRegex(ValueError, "user_exit_available"):
            freeze_appeal(self.original, request)

    def test_appeal_cannot_create_penalty_or_surveillance_escalation(self):
        for field in ("penalty_for_appeal", "surveillance_escalation_for_appeal"):
            request = dict(self.request)
            request[field] = True
            with self.subTest(field=field), self.assertRaises(ValueError):
                freeze_appeal(self.original, request)

    def test_builtin_self_test_passes(self):
        result = self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["checks"].values()))


if __name__ == "__main__":
    unittest.main()
