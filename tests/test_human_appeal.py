import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "human_appeal.py"
SPEC = importlib.util.spec_from_file_location("human_appeal", MODULE_PATH)
appeal = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(appeal)


class HumanAppealTests(unittest.TestCase):
    def base_bundle(self):
        decision = {
            "receipt_id": "decision-1",
            "evidence_state": "CONTESTED",
            "release_control": "SHOW_CONFLICT_AND_ALLOW_EXIT",
        }
        return {
            "schema": appeal.INPUT_SCHEMA,
            "case_id": "case-1",
            "decision_receipt": decision,
            "decision_receipt_sha256": appeal.canonical_sha256(decision),
            "appeal": {
                "appeal_id": "appeal-1",
                "ground": "REVIEW_DISAGREEMENT",
                "requested_action": "REVIEW",
                "statement": "The disagreement should be inspected.",
                "user_requested": True,
            },
            "resolution": None,
        }

    def test_pending_appeal_is_recorded_not_auto_resolved(self):
        result = appeal.evaluate_appeal(self.base_bundle())
        self.assertEqual(result["status"], "APPEAL_RECORDED_NEEDS_HUMAN_REVIEW")
        self.assertTrue(result["needs_human_review"])
        self.assertTrue(result["decision_binding_verified"])

    def test_decision_sha_mismatch_is_invalid(self):
        bundle = self.base_bundle()
        bundle["decision_receipt"]["evidence_state"] = "SUPPORTED_BY_PRESENT_SOURCES"
        result = appeal.evaluate_appeal(bundle)
        self.assertEqual(result["status"], "INVALID_APPEAL")
        self.assertIn("DECISION_RECEIPT_SHA256_MISMATCH", result["failures"])

    def test_unsupported_ground_is_invalid(self):
        bundle = self.base_bundle()
        bundle["appeal"]["ground"] = "MAKE_ME_WIN"
        result = appeal.evaluate_appeal(bundle)
        self.assertEqual(result["status"], "INVALID_APPEAL")

    def test_other_explained_requires_statement(self):
        bundle = self.base_bundle()
        bundle["appeal"]["ground"] = "OTHER_EXPLAINED"
        bundle["appeal"]["statement"] = ""
        result = appeal.evaluate_appeal(bundle)
        self.assertIn("OTHER_EXPLAINED_REQUIRES_STATEMENT", result["failures"])

    def test_user_request_must_be_confirmed(self):
        bundle = self.base_bundle()
        bundle["appeal"]["user_requested"] = False
        result = appeal.evaluate_appeal(bundle)
        self.assertIn("USER_REQUEST_NOT_CONFIRMED", result["failures"])

    def test_no_change_resolution_preserves_decision(self):
        bundle = self.base_bundle()
        original = json.loads(json.dumps(bundle["decision_receipt"]))
        bundle["resolution"] = {
            "resolution_id": "res-1",
            "reviewer_id": "reviewer-1",
            "verifier_status": "PASS",
            "resolution_type": "NO_CHANGE",
        }
        result = appeal.evaluate_appeal(bundle)
        self.assertEqual(result["status"], "APPEAL_RESOLVED_NO_CHANGE")
        self.assertEqual(result["history"]["decision_receipt"], original)
        self.assertFalse(result["invariants"]["original_decision_rewritten"])

    def test_correction_link_requires_id(self):
        bundle = self.base_bundle()
        bundle["resolution"] = {
            "resolution_id": "res-1",
            "reviewer_id": "reviewer-1",
            "verifier_status": "PASS",
            "resolution_type": "CORRECTION_LINKED",
        }
        result = appeal.evaluate_appeal(bundle)
        self.assertIn("CORRECTION_LINKED_REQUIRES_CORRECTION_ID", result["failures"])

    def test_correction_link_does_not_apply_correction(self):
        bundle = self.base_bundle()
        bundle["resolution"] = {
            "resolution_id": "res-1",
            "reviewer_id": "reviewer-1",
            "verifier_status": "PASS",
            "resolution_type": "CORRECTION_LINKED",
            "correction_id": "corr-1",
        }
        result = appeal.evaluate_appeal(bundle)
        self.assertEqual(result["status"], "APPEAL_RESOLVED_CORRECTION_LINKED")
        self.assertFalse(result["resolution_effect"]["correction_applied"])
        self.assertEqual(result["resolution_effect"]["next_gate_owner"], "KETO_CORRECTION_PROPAGATOR")
        self.assertFalse(result["invariants"]["evidence_state_mutated_by_appeal_gate"])

    def test_resolution_verifier_must_pass(self):
        bundle = self.base_bundle()
        bundle["resolution"] = {
            "resolution_id": "res-1",
            "reviewer_id": "reviewer-1",
            "verifier_status": "FAIL",
            "resolution_type": "NO_CHANGE",
        }
        result = appeal.evaluate_appeal(bundle)
        self.assertIn("RESOLUTION_VERIFIER_NOT_PASS", result["failures"])

    def test_appeal_is_not_error_admission_or_authority(self):
        result = appeal.evaluate_appeal(self.base_bundle())
        inv = result["invariants"]
        self.assertFalse(inv["appeal_is_admission_of_error"])
        self.assertFalse(inv["appeal_request_is_outcome_override"])
        self.assertEqual(inv["authority_delta"], 0)
        self.assertEqual(inv["mass_effect_budget_delta"], 0)

    def test_software_does_not_prove_human_resolver_identity(self):
        bundle = self.base_bundle()
        bundle["resolution"] = {
            "resolution_id": "res-1",
            "reviewer_id": "reviewer-1",
            "verifier_status": "PASS",
            "resolution_type": "NOTE_ADDED",
            "note": "Reviewed; original decision retained.",
        }
        result = appeal.evaluate_appeal(bundle)
        self.assertFalse(result["human_reviewer_identity_proven_by_software"])

    def test_self_test(self):
        self.assertEqual(appeal.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
