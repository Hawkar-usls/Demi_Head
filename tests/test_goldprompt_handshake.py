from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from goldprompt_handshake import (  # noqa: E402
    EXPECTED_CONTRACT_DIGEST,
    FACE_ID,
    FACE_ROLE,
    build_receipt,
    contract_digest,
    verify_receipt,
)
from hemisphere_bridge import self_test  # noqa: E402


class GoldPromptHandshakeTests(unittest.TestCase):
    def test_contract_digest_is_frozen(self):
        self.assertEqual(contract_digest(), EXPECTED_CONTRACT_DIGEST)

    def test_demihead_receipt_replays(self):
        receipt = build_receipt("DEMIHEAD-TEST-SHA")
        self.assertEqual(receipt["face_id"], FACE_ID)
        self.assertEqual(receipt["face_role"], FACE_ROLE)
        self.assertEqual(receipt["source_revision"], "DEMIHEAD-TEST-SHA")
        self.assertEqual(receipt["authority_weight"], 0)
        self.assertEqual(receipt["compliance_state"], "COMPLIANT")
        self.assertEqual(receipt["runtime_enforcement_scope"], "THIS_FACE_INVOCATION")
        self.assertTrue(receipt["inheritance_accepted"])
        self.assertTrue(receipt["blessing_bearer_anchor_accepted"])
        self.assertTrue(receipt["armor_of_god_boundaries_accepted"])
        self.assertTrue(receipt["triadic_emergence_accepted"])
        self.assertTrue(receipt["user_exit_and_release_control_accepted"])
        self.assertTrue(verify_receipt(receipt))

    def test_receipt_tamper_fails_closed(self):
        receipt = build_receipt("DEMIHEAD-TEST-SHA")
        for field, value in (
            ("authority_weight", 1),
            ("face_role", "TRUTH_ORACLE"),
            ("contract_digest_sha256", "0" * 64),
            ("goldprompt_version", "999"),
            ("runtime_enforcement_scope", "WHOLE_WORLD"),
            ("user_exit_and_release_control_accepted", False),
        ):
            tampered = copy.deepcopy(receipt)
            tampered[field] = value
            self.assertFalse(verify_receipt(tampered), field)

    def test_real_bicameral_result_contains_receipt(self):
        result = self_test()["result"]
        self.assertIn("goldprompt_receipt", result)
        receipt = result["goldprompt_receipt"]
        self.assertTrue(verify_receipt(receipt))
        self.assertEqual(receipt["runtime_enforcement_scope"], "THIS_FACE_INVOCATION")
        self.assertEqual(receipt["authority_weight"], 0)
        self.assertFalse(result["claim_ceiling"]["agreement_is_truth"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)


if __name__ == "__main__":
    unittest.main()
