from __future__ import annotations

import hashlib
import unittest

from demihead_nohand_agent import Calibrator, DemiHeadNohandAgent
from nohand_pair_protocol import DEMIHEAD_HEAD, NAS_HEAD, build_message

GUARD = {
    "safety_contract_sha256": "c" * 64,
    "guardian_of_guardian": "PASS",
    "preservation_sentinel": "PASS",
    "mutation_frozen": False,
    "destructive_permissions": [],
}

class AgentTests(unittest.TestCase):
    def setUp(self):
        self.agent = DemiHeadNohandAgent("8309fd0d8d76d94a97d8e0583db9fe27ab79ec27")

    def test_offer_local_is_advisory(self):
        message = self.agent.offer_local(path="tools/example.py", content=b"print('x')\n")
        self.assertEqual(message["sender"], DEMIHEAD_HEAD)
        self.assertEqual(message["kind"], "OFFER")
        self.assertEqual(message["control"]["authority_weight"], 0)
        self.assertFalse(message["control"]["message_is_command"])

    def test_secret_path_not_offered(self):
        with self.assertRaises(ValueError):
            self.agent.offer_local(path="tools/private_token.txt", content=b"x")

    def test_nas_offer_can_request_copy(self):
        content = b'{"hello":"world"}'
        offer = build_message(
            message_id="nas1", sender=NAS_HEAD, target=DEMIHEAD_HEAD, kind="OFFER", source_revision="nas-source-1",
            object_ref={"origin_kind": "NAS_LOCAL", "sha256": hashlib.sha256(content).hexdigest(), "size": len(content), "locator": {"path": "services/example.json"}},
            guard=GUARD,
        )
        decision = self.agent.evaluate_nas_offer(offer)
        self.assertEqual(decision["decision"]["state"], "REQUEST_COPY")

    def test_large_offer_is_hold_for_transfer_node(self):
        offer = build_message(
            message_id="nas2", sender=NAS_HEAD, target=DEMIHEAD_HEAD, kind="OFFER", source_revision="nas-source-1",
            object_ref={"origin_kind": "NAS_LOCAL", "sha256": "d" * 64, "size": 2_000_000, "locator": {"path": "services/big.json"}},
            guard=GUARD,
        )
        decision = self.agent.evaluate_nas_offer(offer)
        self.assertEqual(decision["kind"], "HOLD")
        self.assertEqual(decision["decision"]["reason"], "PAYLOAD_TOO_LARGE_USE_TRANSFER_NODE")

    def test_calibrator_deduplicates_action_event_root(self):
        calibrator = Calibrator()
        prediction = calibrator.predict(action="REQUEST_FROM_NAS", size=100, action_event_root="event-1", selection_process_root="selection-A")
        observation = {
            "action_event_root": prediction["action_event_root"],
            "selection_process_root": prediction["selection_process_root"],
            "key": prediction["key"],
            "p_success": prediction["p_success"],
            "success": True,
            "latency_ms": 10,
        }
        self.assertTrue(calibrator.observe(observation))
        self.assertFalse(calibrator.observe(observation))
        self.assertEqual(calibrator.summary()["event_root_count"], 1)

if __name__ == "__main__":
    unittest.main()
