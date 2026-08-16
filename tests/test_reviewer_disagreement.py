import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "reviewer_disagreement.py"
SPEC = importlib.util.spec_from_file_location("reviewer_disagreement", MODULE_PATH)
review = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(review)


class ReviewerDisagreementTests(unittest.TestCase):
    def reviewer(self, reviewer_id, attestation_id, uncertainty="MATERIAL"):
        return {
            "reviewer_id": reviewer_id,
            "attestation_id": attestation_id,
            "frozen_package_id": "pkg",
            "verifier_status": "PASS",
            "declared_independent": True,
            "labels_frozen_before_model_reveal": True,
            "labels": {
                "evidence_state": "CONTESTED",
                "uncertainty_class": uncertainty,
            },
        }

    def collection(self, reviewers=None, required=2):
        return {
            "schema": review.INPUT_SCHEMA,
            "case_id": "case",
            "frozen_package_id": "pkg",
            "required_reviewers": required,
            "review_fields": ["evidence_state", "uncertainty_class"],
            "reviewers": reviewers or [],
        }

    def test_zero_reviewers_is_waiting_not_failure(self):
        result = review.evaluate_collection(self.collection())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["collection_state"], "WAITING_FOR_FIRST_REVIEWER")

    def test_one_reviewer_waits_for_second(self):
        result = review.evaluate_collection(self.collection([self.reviewer("R1", "A1")]))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["collection_state"], "WAITING_FOR_SECOND_REVIEWER")

    def test_two_valid_reviewers_are_ready(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R2", "A2")])
        )
        self.assertEqual(result["collection_state"], "READY_FOR_CONSENSUS")
        self.assertTrue(result["consensus_admission_ready"])

    def test_duplicate_reviewer_id_invalidates_collection(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R1", "A2")])
        )
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")
        self.assertIn("REVIEWER_IDS_NOT_DISTINCT", result["failures"])

    def test_duplicate_attestation_invalidates_collection(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R2", "A1")])
        )
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")
        self.assertIn("ATTESTATION_IDS_NOT_DISTINCT", result["failures"])

    def test_package_mismatch_invalidates_collection(self):
        bad = self.reviewer("R2", "A2")
        bad["frozen_package_id"] = "other"
        result = review.evaluate_collection(self.collection([self.reviewer("R1", "A1"), bad]))
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")

    def test_verifier_failure_invalidates_collection(self):
        bad = self.reviewer("R2", "A2")
        bad["verifier_status"] = "FAIL"
        result = review.evaluate_collection(self.collection([self.reviewer("R1", "A1"), bad]))
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")

    def test_declared_independence_false_invalidates_collection(self):
        bad = self.reviewer("R2", "A2")
        bad["declared_independent"] = False
        result = review.evaluate_collection(self.collection([self.reviewer("R1", "A1"), bad]))
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")

    def test_label_freeze_false_invalidates_collection(self):
        bad = self.reviewer("R2", "A2")
        bad["labels_frozen_before_model_reveal"] = False
        result = review.evaluate_collection(self.collection([self.reviewer("R1", "A1"), bad]))
        self.assertEqual(result["collection_state"], "INVALID_COLLECTION")

    def test_unanimous_field_is_preserved(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R2", "A2")])
        )
        self.assertEqual(result["consensus"]["fields"]["evidence_state"], "CONTESTED")

    def test_non_unanimous_field_becomes_disagreement(self):
        result = review.evaluate_collection(
            self.collection([
                self.reviewer("R1", "A1", "MATERIAL"),
                self.reviewer("R2", "A2", "HIGH"),
            ])
        )
        self.assertEqual(result["consensus"]["fields"]["uncertainty_class"], "DISAGREEMENT")

    def test_two_to_one_majority_still_disagreement(self):
        result = review.evaluate_collection(
            self.collection([
                self.reviewer("R1", "A1", "MATERIAL"),
                self.reviewer("R2", "A2", "MATERIAL"),
                self.reviewer("R3", "A3", "HIGH"),
            ], required=3)
        )
        self.assertEqual(result["consensus"]["fields"]["uncertainty_class"], "DISAGREEMENT")
        self.assertFalse(result["consensus"]["majority_vote_used"])

    def test_software_does_not_claim_human_independence(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R2", "A2")])
        )
        self.assertFalse(result["human_independence_proven_by_software"])
        self.assertFalse(result["personhood_proven_by_software"])
        self.assertFalse(result["off_channel_non_collusion_proven_by_software"])

    def test_no_authority_growth(self):
        result = review.evaluate_collection(
            self.collection([self.reviewer("R1", "A1"), self.reviewer("R2", "A2")])
        )
        self.assertEqual(result["invariants"]["authority_delta"], 0)
        self.assertEqual(result["invariants"]["mass_effect_budget_delta"], 0)

    def test_self_test(self):
        self.assertEqual(review.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
