from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from goldprompt_handshake import verify_receipt as verify_goldprompt_receipt  # noqa: E402
from hemisphere_bridge import combine_packets, verify_receipt_chain_result  # noqa: E402
from nexus_fundamentum_adapter import assess_bicameral_context  # noqa: E402
from nexus_guardian_ingress import guardian_ingest, release_control  # noqa: E402
from nexus_habitat import route_receipt, sha256  # noqa: E402


class NexusGuardianChainTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_frozen_v1_local_bicameral_hold_chain_replays_exactly(self):
        # Historical frozen vector remains immutable even after the current runtime
        # moves to receipt-carrying v2 packets/results.
        bicameral = self.load("examples/nexus_bicameral_result.json")
        self.assertEqual(bicameral["schema"], "janus.demihead.bicameral_result.v1")
        self.assertEqual(sha256(bicameral), "527483db3e5970ea9cfe3fba69a80a70a757b00e9a060cdea1dac023f78f5566")

        bridge_route = self.load("examples/nexus_bicameral_to_fundamentum.json")
        self.assertEqual(bridge_route["payload_ref"]["sha256"], sha256(bicameral))
        bridge_route_receipt = route_receipt(bridge_route)
        self.assertFalse(bridge_route_receipt["claim_ceiling"]["delivery_performed"])

        hold = assess_bicameral_context(bicameral)
        self.assertEqual(hold, self.load("examples/nexus_fundamentum_hold_receipt.json"))
        self.assertEqual(sha256(hold), "434b78adb5a04253cbe9c5317d4c2ada1487c9a32e435b03999706be27273679")

        guard_route = self.load("examples/nexus_fundamentum_to_guardian_hold.json")
        self.assertEqual(guard_route["payload_ref"]["sha256"], sha256(hold))
        guard_route_receipt = route_receipt(guard_route)
        self.assertFalse(guard_route_receipt["claim_ceiling"]["delivery_performed"])

        guardian = guardian_ingest("HOLD_RECEIPT", hold)
        self.assertEqual(guardian, self.load("examples/nexus_guardian_hold_result.json"))
        self.assertEqual(sha256(guardian), "a506df8891d40f60220c873f244fead7cbe983c6685648f22bdfd87bc32a904e")
        self.assertEqual(guardian["status"], "HOLD_PRESERVED")
        self.assertFalse(guardian["bounded_result"]["definitive_claim_permitted"])
        self.assertFalse(guardian["control"]["automatic_retry_permitted"])

        release_route = self.load("examples/nexus_guardian_to_release.json")
        self.assertEqual(release_route["payload_ref"]["sha256"], sha256(guardian))
        release_route_receipt = route_receipt(release_route)
        self.assertFalse(release_route_receipt["claim_ceiling"]["delivery_performed"])

        release = release_control(guardian)
        self.assertEqual(release, self.load("examples/nexus_release_wait_receipt.json"))
        self.assertEqual(sha256(release), "8ff708608e9aef8224b2c43dcbf9e447f667a23d4af05df5225e75efc8b5679b")
        self.assertEqual(release["status"], "WAIT_FOR_NEW_EVIDENCE")
        self.assertTrue(release["control"]["return_control_to_human"])
        self.assertFalse(release["control"]["automatic_retry_permitted"])
        self.assertFalse(release["control"]["automatic_external_effect_permitted"])

        registry_route = self.load("examples/nexus_release_to_registry.json")
        self.assertEqual(registry_route["payload_ref"]["sha256"], sha256(release))
        registry_route_receipt = route_receipt(registry_route)
        self.assertEqual(registry_route_receipt["target_head"], "REGISTRY")
        self.assertFalse(registry_route_receipt["claim_ceiling"]["delivery_performed"])
        self.assertFalse(registry_route_receipt["routing"]["external_effect_permitted"])

    def test_current_v2_chain_reaches_same_hold_class_without_historical_hash_alias(self):
        left = self.load("examples/hemisphere_left_hrain.json")
        right = self.load("examples/hemisphere_right_inaihr.json")
        bicameral = combine_packets(left=left, right=right)
        self.assertEqual(bicameral["schema"], "janus.demihead.bicameral_result.v2")
        self.assertTrue(verify_goldprompt_receipt(bicameral["goldprompt_receipt"]))
        self.assertTrue(verify_receipt_chain_result(bicameral))
        self.assertTrue(bicameral["receipt_chain"]["end_to_end_receipt_binding_established"])
        self.assertFalse(bicameral["receipt_chain"]["origin_authentication_established"])

        hold = assess_bicameral_context(bicameral)
        frozen_hold = self.load("examples/nexus_fundamentum_hold_receipt.json")
        self.assertNotEqual(hold["input"]["sha256"], frozen_hold["input"]["sha256"])
        self.assertEqual(hold["payload_kind"], "HOLD_RECEIPT")
        self.assertEqual(hold["assessment"]["evidence_state"], "CONTEXT_ONLY_NOT_EVIDENCE")
        self.assertFalse(hold["assessment"]["definitive_claim_permitted"])
        self.assertEqual(hold["control"]["authority_delta"], 0)
        self.assertFalse(hold["control"]["external_effect_permitted"])

        guardian = guardian_ingest("HOLD_RECEIPT", hold)
        self.assertEqual(guardian["status"], "HOLD_PRESERVED")
        self.assertFalse(guardian["bounded_result"]["definitive_claim_permitted"])
        self.assertFalse(guardian["control"]["automatic_retry_permitted"])

        release = release_control(guardian)
        self.assertEqual(release["status"], "WAIT_FOR_NEW_EVIDENCE")
        self.assertTrue(release["control"]["return_control_to_human"])
        self.assertFalse(release["control"]["automatic_external_effect_permitted"])

    def test_forged_guardian_retry_permission_fails_closed(self):
        guardian = self.load("examples/nexus_guardian_hold_result.json")
        guardian["control"]["automatic_retry_permitted"] = True
        with self.assertRaises(ValueError):
            release_control(guardian)

    def test_forged_hold_definitive_claim_fails_closed(self):
        hold = self.load("examples/nexus_fundamentum_hold_receipt.json")
        hold["assessment"]["definitive_claim_permitted"] = True
        with self.assertRaises(ValueError):
            guardian_ingest("HOLD_RECEIPT", hold)


if __name__ == "__main__":
    unittest.main()
