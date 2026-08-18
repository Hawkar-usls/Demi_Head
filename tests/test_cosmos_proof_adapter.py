from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from cosmos_proof_adapter import (  # noqa: E402
    PROVIDER_SHA,
    build_receipt,
    build_request,
    verify_cosmos_result,
    verify_receipt,
    verify_request,
)
from goldprompt_intent_handoff import CONTEXT_TIERS, sha256  # noqa: E402


def anchor() -> dict:
    payload = {
        "schema": "janus.goldprompt.intent_anchor.v1",
        "current_turn_digest": "1" * 64,
        "requested_operation": "VERIFY_OSIRIS_CANONICAL_GATE",
        "primary_entities": {"OSIRIS": ["osiris"], "S_PHALLUS_H": ["s𓂸ḥ", "s-phallus-h"]},
        "must_answer_points": ["Verify the exact frozen S𓂸ḥ/2 gate on the pinned Cosmos provider revision"],
        "required_answer_evidence": [["execution receipt"], ["provider sha"], ["P_VS_NP OPEN"]],
        "operation_markers": ["verify", "execute"],
        "optional_association_markers": ["janus", "cosmos"],
        "explicit_constraints": ["no P=NP promotion", "authority delta remains zero"],
        "allow_anaphoric_continuation": False,
        "context_priority": [CONTEXT_TIERS[i] for i in sorted(CONTEXT_TIERS)],
    }
    payload["intent_id"] = sha256(payload)
    return payload


def cosmos_result() -> dict:
    from cosmos_proof_adapter import _digest

    result = {
        "status": "PASS_KEEP_S_PHALLUS_H_GATE_2_BOUNDED_K_SCALING_HOLDOUT__MASTER_P_VS_NP_GATE_REMAINS_OPEN",
        "implementation_conformance": {
            "frozen_contract_unchanged": True,
            "frozen_fixture_corpus_unchanged": True,
            "Q0_priority_preserved": True,
            "auto_k_search_exact_for_budget_admitted_residuals": True,
            "inherited_budget_guard": "fixture",
            "new_posthoc_threshold_added": False,
            "hard_Tseitin_auto_k_not_invoked_after_parent_budget_reject": True,
            "P_VS_NP": "OPEN",
        },
        "synthetic_test_marker": "DEMIHEAD_COSMOS_BRIDGE_FIXTURE",
    }
    result["integrity_sha256"] = _digest(result)
    return result


class CosmosProofAdapterTests(unittest.TestCase):
    def test_good_intent_bound_execution_passes(self) -> None:
        req = build_request(anchor(), "COSMOS-E2E-0001")
        result = cosmos_result()
        receipt = build_receipt(req, result)
        self.assertTrue(verify_request(req))
        self.assertTrue(verify_cosmos_result(result))
        self.assertTrue(verify_receipt(req, result, receipt))
        self.assertEqual(receipt["intent_id"], req["intent_anchor"]["intent_id"])
        self.assertEqual(receipt["provider_sha"], PROVIDER_SHA)
        self.assertEqual(receipt["authority_delta"], 0)
        self.assertEqual(receipt["P_VS_NP"], "OPEN")

    def test_intent_substitution_fails_closed(self) -> None:
        req = build_request(anchor(), "COSMOS-E2E-0002")
        req["intent_anchor"]["requested_operation"] = "SOLVE_DIFFERENT_TASK"
        self.assertFalse(verify_request(req))

    def test_provider_sha_substitution_fails_closed(self) -> None:
        req = build_request(anchor(), "COSMOS-E2E-0003")
        req["provider_sha"] = "0" * 40
        self.assertFalse(verify_request(req))

    def test_input_hash_substitution_fails_closed(self) -> None:
        req = build_request(anchor(), "COSMOS-E2E-0004")
        req["input_sha256"] = "0" * 64
        self.assertFalse(verify_request(req))

    def test_cosmos_result_bitflip_fails_closed(self) -> None:
        result = cosmos_result()
        result["synthetic_test_marker"] = "BITFLIPPED"
        self.assertFalse(verify_cosmos_result(result))

    def test_p_vs_np_promotion_fails_closed(self) -> None:
        result = cosmos_result()
        result["implementation_conformance"]["P_VS_NP"] = "CLOSED"
        from cosmos_proof_adapter import _digest
        result.pop("integrity_sha256")
        result["integrity_sha256"] = _digest(result)
        self.assertFalse(verify_cosmos_result(result))

    def test_receipt_cannot_gain_authority(self) -> None:
        req = build_request(anchor(), "COSMOS-E2E-0005")
        result = cosmos_result()
        receipt = build_receipt(req, result)
        bad = copy.deepcopy(receipt)
        bad["authority_delta"] = 1
        self.assertFalse(verify_receipt(req, result, bad))


if __name__ == "__main__":
    unittest.main()
