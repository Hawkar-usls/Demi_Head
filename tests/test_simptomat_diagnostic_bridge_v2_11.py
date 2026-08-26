from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from simptomat_diagnostic_bridge_v2_11 import (  # noqa: E402
    build_review,
    choose_decision,
    verify_packet,
    verify_review,
)


def packet() -> dict:
    return {
        "schema": "janus.simptomat.diagnostic_reasoning_packet.v1",
        "packet_id": "SIM-DEMI-E2E-0001",
        "session_scope": "EPHEMERAL_CONVERSATION",
        "consent_scope": {
            "conversation_processing_allowed": True,
            "public_case_persistence_consent": False,
        },
        "target_question": "Which live hypothesis best explains the current self-reported pattern?",
        "ranked_differential": [
            {"candidate": "common_local_explanation", "state": "SUPPORTED", "research_score": 3.0},
            {"candidate": "target_rare_condition", "state": "WEAKLY_COMPATIBLE", "research_score": 1.0},
        ],
        "supporting_features": ["stable focal symptom"],
        "contradicting_features": ["no progressive functional loss"],
        "uncertainties": ["no physical examination"],
        "next_best_question": "Has the symptom objectively progressed?",
        "next_confirmation_step": {
            "kind": "MORE_HISTORY",
            "description": "Clarify progression before external testing.",
            "requires_external_measurement": False,
        },
        "urgent_red_flags": [],
        "claim_ceiling": "RESEARCH_DIAGNOSTIC_HYPOTHESIS_ONLY",
        "clinical_confirmation_claimed": False,
        "authority_delta": 0,
    }


class SimptomatDiagnosticBridgeV211Tests(unittest.TestCase):
    def test_good_minimized_packet_passes_as_research_hypothesis(self) -> None:
        p = packet()
        self.assertTrue(verify_packet(p))
        review = build_review(p)
        self.assertEqual(review["decision"], "PASS_AS_RESEARCH_HYPOTHESIS")
        self.assertFalse(review["clinical_confirmation_granted"])
        self.assertFalse(review["reference_label_granted"])
        self.assertEqual(review["authority_delta"], 0)
        self.assertTrue(verify_review(p, review))

    def test_direct_identifier_is_rejected(self) -> None:
        p = packet()
        p["email"] = "participant@example.invalid"
        self.assertFalse(verify_packet(p))
        with self.assertRaises(ValueError):
            build_review(p)

    def test_raw_transcript_is_rejected(self) -> None:
        p = packet()
        p["raw_chat_transcript"] = "sensitive raw conversation"
        self.assertFalse(verify_packet(p))

    def test_clinical_confirmation_claim_is_rejected_as_promotion(self) -> None:
        p = packet()
        p["clinical_confirmation_claimed"] = True
        self.assertTrue(verify_packet(p))
        self.assertEqual(choose_decision(p), "REJECT_UNSAFE_PROMOTION")

    def test_uncalibrated_clinical_probability_is_rejected(self) -> None:
        p = packet()
        p["ranked_differential"][0]["clinical_probability"] = 0.9
        p["ranked_differential"][0]["probability_calibration"] = "RESEARCH_ONLY"
        self.assertTrue(verify_packet(p))
        self.assertEqual(choose_decision(p), "REJECT_UNSAFE_PROMOTION")

    def test_urgent_red_flag_escalates(self) -> None:
        p = packet()
        p["urgent_red_flags"] = ["acute neurological red flag"]
        self.assertEqual(choose_decision(p), "ESCALATE_FOR_REAL_WORLD_EVALUATION")

    def test_measurement_handoff_holds_instead_of_inventing_evidence(self) -> None:
        p = packet()
        p["next_confirmation_step"] = {
            "kind": "IMAGING",
            "description": "External imaging is required to discriminate the remaining candidates.",
            "requires_external_measurement": True,
        }
        self.assertEqual(choose_decision(p), "HOLD_FOR_EXTERNAL_MEASUREMENT")

    def test_review_tamper_cannot_add_authority(self) -> None:
        p = packet()
        review = build_review(p)
        bad = copy.deepcopy(review)
        bad["authority_delta"] = 1
        self.assertFalse(verify_review(p, bad))

    def test_review_tamper_cannot_grant_clinical_confirmation(self) -> None:
        p = packet()
        review = build_review(p)
        bad = copy.deepcopy(review)
        bad["clinical_confirmation_granted"] = True
        self.assertFalse(verify_review(p, bad))


if __name__ == "__main__":
    unittest.main()
