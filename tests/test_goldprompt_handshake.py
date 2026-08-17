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
from hemisphere_bridge import combine_packets, self_test  # noqa: E402


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
        self.assertTrue(verify_receipt(receipt))

    def test_receipt_tamper_fails_closed(self):
        receipt = build_receipt("DEMIHEAD-TEST-SHA")
        for field, value in (
            ("authority_weight", 1),
            ("face_role", "TRUTH_ORACLE"),
            ("contract_digest_sha256", "0" * 64),
            ("goldprompt_version", "999"),
        ):
            tampered = copy.deepcopy(receipt)
            tampered[field] = value
            self.assertFalse(verify_receipt(tampered), field)

    def test_real_bicameral_result_contains_receipt(self):
        result = self_test()["result"]
        self.assertIn("goldprompt_receipt", result)
        self.assertTrue(verify_receipt(result["goldprompt_receipt"]))
        self.assertFalse(result["claim_ceiling"]["agreement_is_truth"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)

    def test_missing_face_does_not_create_more_authority(self):
        result = combine_packets(left=self_test()["result"]["packet_receipts"] if False else None)
        self.assertIsNone(result)  # unreachable guard; combine_packets already covered by bridge tests


if __name__ == "__main__":
    unittest.main()
