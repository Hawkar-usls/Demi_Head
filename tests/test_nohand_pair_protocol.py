from __future__ import annotations

import unittest

from nohand_pair_protocol import DEMIHEAD_HEAD, NAS_HEAD, build_message, make_nexus_envelope, validate_message

GUARD = {
    "safety_contract_sha256": "a" * 64,
    "guardian_of_guardian": "PASS",
    "preservation_sentinel": "PASS",
    "mutation_frozen": False,
    "destructive_permissions": [],
}

class PairProtocolTests(unittest.TestCase):
    def _offer(self):
        return build_message(
            message_id="m1",
            sender=NAS_HEAD,
            target=DEMIHEAD_HEAD,
            kind="OFFER",
            source_revision="nas-rev-1",
            object_ref={"origin_kind": "NAS_LOCAL", "sha256": "b" * 64, "size": 123, "locator": {"path": "services/example.py"}},
            guard=GUARD,
        )

    def test_offer_and_nexus_envelope(self):
        message = self._offer()
        validate_message(message)
        envelope = make_nexus_envelope(message)
        self.assertTrue(envelope["control"]["read_only_transfer"])
        self.assertFalse(envelope["control"]["direct_workspace_mutation"])
        self.assertEqual(envelope["source_head"], NAS_HEAD)
        self.assertEqual(envelope["target_head"], DEMIHEAD_HEAD)

    def test_authority_escalation_rejected(self):
        message = self._offer()
        message["control"]["authority_weight"] = 1
        with self.assertRaises(ValueError):
            validate_message(message)

    def test_destructive_guard_rejected(self):
        message = self._offer()
        message["guard"]["destructive_permissions"] = ["DELETE"]
        with self.assertRaises(ValueError):
            validate_message(message)

    def test_guard_is_snapshot_not_external_alias(self):
        guard = dict(GUARD)
        message = build_message(
            message_id="m2", sender=NAS_HEAD, target=DEMIHEAD_HEAD, kind="OFFER", source_revision="nas-rev-1",
            object_ref={"origin_kind": "NAS_LOCAL", "sha256": "c" * 64, "size": 1, "locator": {"path": "services/a.py"}}, guard=guard,
        )
        guard["destructive_permissions"] = ["DELETE"]
        validate_message(message)
        self.assertEqual(message["guard"]["destructive_permissions"], [])

    def test_tamper_hash_rejected(self):
        message = self._offer()
        message["object_ref"]["size"] = 124
        with self.assertRaises(ValueError):
            validate_message(message)

if __name__ == "__main__":
    unittest.main()
