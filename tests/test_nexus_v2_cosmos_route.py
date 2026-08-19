from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import cosmos_proof_adapter as cosmos  # noqa: E402
import nexus_habitat as v1  # noqa: E402
import nexus_habitat_v2 as v2  # noqa: E402
from goldprompt_intent_handoff import CONTEXT_TIERS, sha256  # noqa: E402


def anchor() -> dict:
    payload = {
        "schema": "janus.goldprompt.intent_anchor.v1",
        "current_turn_digest": "2" * 64,
        "requested_operation": "VERIFY_OSIRIS_CANONICAL_GATE",
        "primary_entities": {"OSIRIS": ["osiris"], "S_PHALLUS_H": ["s𓂸ḥ", "s-phallus-h"]},
        "must_answer_points": ["Verify the exact frozen S𓂸ḥ/2 gate on the pinned Cosmos provider revision"],
        "required_answer_evidence": [["execution receipt"], ["provider sha"], ["P_VS_NP OPEN"]],
        "operation_markers": ["verify", "execute"],
        "optional_association_markers": ["janus", "cosmos", "nexus-v2"],
        "explicit_constraints": ["no P=NP promotion", "authority delta remains zero"],
        "allow_anaphoric_continuation": False,
        "context_priority": [CONTEXT_TIERS[i] for i in sorted(CONTEXT_TIERS)],
    }
    payload["intent_id"] = sha256(payload)
    return payload


def cosmos_result() -> dict:
    result = {
        "status": "PASS_KEEP_S_PHALLUS_H_GATE_2_BOUNDED_K_SCALING_HOLDOUT__MASTER_P_VS_NP_GATE_REMAINS_OPEN",
        "implementation_conformance": {
            "frozen_contract_unchanged": True,
            "frozen_fixture_corpus_unchanged": True,
            "Q0_priority_preserved": True,
            "auto_k_search_exact_for_budget_admitted_residuals": True,
            "inherited_budget_guard": "nexus-v2-test-fixture",
            "new_posthoc_threshold_added": False,
            "hard_Tseitin_auto_k_not_invoked_after_parent_budget_reject": True,
            "P_VS_NP": "OPEN",
        },
        "synthetic_test_marker": "NEXUS_V2_COSMOS_ROUTE_FIXTURE",
    }
    result["integrity_sha256"] = cosmos._digest(result)
    return result


class NexusV2CosmosRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.request = cosmos.build_request(anchor(), "NEXUS-V2-COSMOS-0001")
        self.result = cosmos_result()
        self.receipt = cosmos.build_receipt(self.request, self.result)
        self.request_envelope = v2.build_cosmos_request_envelope(self.request)
        self.receipt_envelope = v2.build_cosmos_receipt_envelope(self.request, self.result, self.receipt)

    def test_v2_is_additive_and_v1_contract_remains_parent(self) -> None:
        self.assertEqual(v2.CONTRACT, "JANUS_NEXUS_HABITAT_V2")
        self.assertEqual(v1.CONTRACT, "JANUS_NEXUS_HABITAT_V1")
        self.assertTrue(set(v1.HEADS).issubset(v2.HEADS))
        self.assertTrue(set(v1.ROUTES).issubset(v2.ROUTES))
        self.assertEqual(set(v2.ROUTES) - set(v1.ROUTES), set(v2.NEW_ROUTES))
        self.assertEqual(set(v2.HEADS) - set(v1.HEADS), {"PROOF_BROKER", "COSMOS"})

    def test_exact_two_new_routes_are_admitted(self) -> None:
        self.assertEqual(
            set(v2.NEW_ROUTES),
            {
                ("PROOF_BROKER", "COSMOS", "COSMOS_PROOF_REQUEST"),
                ("COSMOS", "PROOF_BROKER", "COSMOS_PROOF_RECEIPT"),
            },
        )
        self.assertEqual(v2.route_receipt(self.request_envelope)["status"], "ROUTE_ADMITTED_READ_ONLY")
        self.assertEqual(v2.route_receipt(self.receipt_envelope)["status"], "ROUTE_ADMITTED_READ_ONLY")

    def test_good_request_and_receipt_bind_end_to_end(self) -> None:
        self.assertTrue(v2.verify_cosmos_request_envelope(self.request_envelope, self.request))
        self.assertTrue(v2.verify_cosmos_receipt_envelope(self.receipt_envelope, self.request, self.result, self.receipt))
        self.assertEqual(self.request_envelope["payload_ref"]["sha256"], self.request["request_sha256"])
        self.assertEqual(self.receipt_envelope["payload_ref"]["sha256"], self.receipt["receipt_sha256"])
        self.assertEqual(self.receipt["intent_id"], self.request["intent_anchor"]["intent_id"])

    def test_unadmitted_route_rejects(self) -> None:
        bad = copy.deepcopy(self.request_envelope)
        bad["target_head"] = "REGISTRY"
        with self.assertRaises(ValueError):
            v2.validate_envelope(bad)

    def test_type_compatibility_alone_does_not_create_route(self) -> None:
        original = v2.HEADS
        try:
            synthetic = dict(original)
            synthetic["SYNTHETIC_REQUEST_SINK"] = v1.HeadRule(
                role="TEST_ONLY_COMPATIBLE_SINK",
                repository="test/none",
                accepts=(v2.PROOF_REQUEST_KIND,),
                emits=(),
            )
            v2.HEADS = synthetic
            bad = copy.deepcopy(self.request_envelope)
            bad["target_head"] = "SYNTHETIC_REQUEST_SINK"
            with self.assertRaisesRegex(ValueError, "Route is not explicitly admitted"):
                v2.validate_envelope(bad)
        finally:
            v2.HEADS = original

    def test_request_payload_hash_substitution_rejects(self) -> None:
        bad = copy.deepcopy(self.request_envelope)
        bad["payload_ref"]["sha256"] = "0" * 64
        self.assertFalse(v2.verify_cosmos_request_envelope(bad, self.request))

    def test_receipt_payload_hash_substitution_rejects(self) -> None:
        bad = copy.deepcopy(self.receipt_envelope)
        bad["payload_ref"]["sha256"] = "0" * 64
        self.assertFalse(v2.verify_cosmos_receipt_envelope(bad, self.request, self.result, self.receipt))

    def test_intent_substitution_rejects(self) -> None:
        bad_request = copy.deepcopy(self.request)
        bad_request["intent_anchor"]["requested_operation"] = "DIFFERENT_TASK"
        self.assertFalse(v2.verify_cosmos_request_envelope(self.request_envelope, bad_request))

    def test_provider_sha_substitution_rejects(self) -> None:
        bad_request = copy.deepcopy(self.request)
        bad_request["provider_sha"] = "0" * 40
        self.assertFalse(v2.verify_cosmos_request_envelope(self.request_envelope, bad_request))

    def test_execution_result_substitution_rejects(self) -> None:
        bad_result = copy.deepcopy(self.result)
        bad_result["synthetic_test_marker"] = "SUBSTITUTED"
        self.assertFalse(v2.verify_cosmos_receipt_envelope(self.receipt_envelope, self.request, bad_result, self.receipt))

    def test_authority_escalation_rejects(self) -> None:
        bad = copy.deepcopy(self.request_envelope)
        bad["control"]["authority_delta"] = 1
        with self.assertRaisesRegex(ValueError, "authority_delta"):
            v2.validate_envelope(bad)

    def test_mass_effect_escalation_rejects(self) -> None:
        bad = copy.deepcopy(self.request_envelope)
        bad["control"]["mass_effect_budget_delta"] = 1
        with self.assertRaisesRegex(ValueError, "mass_effect_budget_delta"):
            v2.validate_envelope(bad)

    def test_p_vs_np_promotion_in_receipt_rejects_even_if_rehashed(self) -> None:
        bad_receipt = copy.deepcopy(self.receipt)
        bad_receipt["P_VS_NP"] = "CLOSED"
        bad_receipt.pop("receipt_sha256")
        bad_receipt["receipt_sha256"] = cosmos._digest(bad_receipt)
        self.assertFalse(v2.verify_cosmos_receipt_envelope(self.receipt_envelope, self.request, self.result, bad_receipt))

    def test_route_as_delivery_claim_rejects(self) -> None:
        bad = copy.deepcopy(self.request_envelope)
        bad["control"]["delivery_claimed"] = True
        with self.assertRaisesRegex(ValueError, "cannot claim delivery"):
            v2.validate_envelope(bad)

    def test_route_receipt_never_claims_delivery_execution_truth_or_authority(self) -> None:
        route = v2.route_receipt(self.receipt_envelope)
        self.assertFalse(route["routing"]["delivery_performed"])
        self.assertFalse(route["routing"]["provider_execution_performed_by_router"])
        self.assertFalse(route["claim_ceiling"]["route_is_truth"])
        self.assertFalse(route["claim_ceiling"]["route_is_authority"])
        self.assertEqual(route["claim_ceiling"]["P_VS_NP"], "OPEN")


if __name__ == "__main__":
    unittest.main()
