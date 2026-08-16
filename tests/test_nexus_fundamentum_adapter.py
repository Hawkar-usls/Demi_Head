from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from hemisphere_bridge import combine_packets  # noqa: E402
from nexus_fundamentum_adapter import assess_bicameral_context  # noqa: E402
from nexus_habitat import HEADS, route_receipt, sha256  # noqa: E402


class NexusFundamentumAdapterTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_frozen_bicameral_result_replays_exactly(self):
        left = self.load("examples/hemisphere_left_hrain.json")
        right = self.load("examples/hemisphere_right_inaihr.json")
        expected = self.load("examples/nexus_bicameral_result.json")
        observed = combine_packets(left=left, right=right)
        self.assertEqual(observed, expected)
        self.assertEqual(
            sha256(expected),
            "527483db3e5970ea9cfe3fba69a80a70a757b00e9a060cdea1dac023f78f5566",
        )

    def test_bicameral_context_replays_to_hold_not_evidence(self):
        bicameral = self.load("examples/nexus_bicameral_result.json")
        expected = self.load("examples/nexus_fundamentum_hold_receipt.json")
        observed = assess_bicameral_context(bicameral)
        self.assertEqual(observed, expected)
        self.assertEqual(observed["payload_kind"], "HOLD_RECEIPT")
        self.assertEqual(observed["assessment"]["evidence_state"], "CONTEXT_ONLY_NOT_EVIDENCE")
        self.assertFalse(observed["assessment"]["definitive_claim_permitted"])
        self.assertFalse(observed["control"]["may_be_promoted_to_evidence_receipt_without_new_witness"])
        self.assertEqual(
            sha256(expected),
            "434b78adb5a04253cbe9c5317d4c2ada1487c9a32e435b03999706be27273679",
        )

    def test_bicameral_to_fundamentum_nexus_route_is_hash_bound(self):
        payload = self.load("examples/nexus_bicameral_result.json")
        envelope = self.load("examples/nexus_bicameral_to_fundamentum.json")
        self.assertEqual(envelope["payload_ref"]["sha256"], sha256(payload))
        receipt = route_receipt(envelope)
        self.assertEqual(receipt["source_head"], "BICAMERAL_BRIDGE")
        self.assertEqual(receipt["target_head"], "FUNDAMENTUM")
        self.assertEqual(receipt["target_repository"], "Hawkar-usls/Demi_Head")
        self.assertEqual(
            receipt["target_descriptor"]["lineage_repository"],
            "Hawkar-usls/Janus-Fundamentum",
        )
        self.assertFalse(receipt["target_descriptor"]["lineage_is_runtime_ownership"])
        self.assertFalse(receipt["claim_ceiling"]["delivery_performed"])

    def test_fundamentum_hold_to_guardian_route_is_hash_bound(self):
        payload = self.load("examples/nexus_fundamentum_hold_receipt.json")
        envelope = self.load("examples/nexus_fundamentum_to_guardian_hold.json")
        self.assertEqual(envelope["payload_ref"]["sha256"], sha256(payload))
        receipt = route_receipt(envelope)
        self.assertEqual(receipt["source_head"], "FUNDAMENTUM")
        self.assertEqual(receipt["source_repository"], "Hawkar-usls/Demi_Head")
        self.assertEqual(receipt["target_head"], "GUARDIAN")
        self.assertFalse(receipt["routing"]["external_effect_permitted"])
        self.assertEqual(receipt["routing"]["authority_delta"], 0)
        self.assertEqual(receipt["routing"]["mass_effect_budget_delta"], 0)
        self.assertFalse(receipt["claim_ceiling"]["truth_claim_made"])

    def test_fundamentum_head_has_runtime_and_lineage_separated(self):
        head = HEADS["FUNDAMENTUM"]
        self.assertEqual(head.repository, "Hawkar-usls/Demi_Head")
        self.assertEqual(head.lineage_repository, "Hawkar-usls/Janus-Fundamentum")

    def test_forged_bicameral_evidence_upgrade_is_rejected(self):
        bicameral = self.load("examples/nexus_bicameral_result.json")
        bicameral["claim_ceiling"]["association_is_evidence"] = True
        with self.assertRaises(ValueError):
            assess_bicameral_context(bicameral)


if __name__ == "__main__":
    unittest.main()
