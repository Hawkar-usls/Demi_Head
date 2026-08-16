from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_destination_acceptance import accept_destination, self_test  # noqa: E402
from nexus_local_transport import build_frame, validate_frame  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard  # noqa: E402


class NexusDestinationAcceptanceTests(unittest.TestCase):
    KEY = b"destination-unit-test-key"
    ISSUED = 1_800_000_000_000

    def envelope(self):
        return {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "destination-unit-001",
            "source_head": "GUARDIAN",
            "target_head": "RELEASE_CONTROL",
            "payload_kind": "GUARDIAN_RESULT",
            "payload_ref": {"sha256": "0" * 64},
            "trace": [],
            "control": {
                "read_only_transfer": True,
                "direct_workspace_mutation": False,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
                "ttl_hops": 4,
            },
        }

    def principal_lookup(self):
        return {
            "GUARDIAN_E1": {
                "key": self.KEY,
                "sender_id": "DEMIHEAD.GUARDIAN",
                "allowed_source_heads": ["GUARDIAN"],
                "enabled": True,
                "revoked": False,
                "epoch": 1,
                "not_before_ms": 1_700_000_000_000,
                "not_after_ms": 1_900_000_000_000,
            }
        }

    def frame_and_admission(self):
        frame = build_frame(
            self.envelope(),
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="destination-unit-nonce-000001",
        )
        admission = validate_frame(
            frame,
            principal_lookup=self.principal_lookup(),
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        return frame, admission

    def policy(self):
        return {
            "schema": "janus.demihead.nexus_endpoint_policy.v1",
            "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
            "enabled": True,
            "accepted_target_heads": ["RELEASE_CONTROL"],
            "local_dispatch_only": True,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        }

    def test_matching_endpoint_accepts_without_claiming_delivery(self):
        frame, admission = self.frame_and_admission()
        receipt = accept_destination(frame, admission, self.policy())
        self.assertEqual(receipt["status"], "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH")
        self.assertTrue(receipt["acceptance"]["target_head_binding_verified"])
        self.assertTrue(receipt["acceptance"]["transport_admission_verified"])
        self.assertFalse(receipt["acceptance"]["delivery_performed"])
        self.assertFalse(receipt["acceptance"]["target_execution_performed"])
        self.assertFalse(receipt["acceptance"]["acceptance_is_truth"])
        self.assertFalse(receipt["acceptance"]["acceptance_is_world_effect_authorization"])
        self.assertFalse(receipt["control"]["external_effect_permitted"])
        self.assertEqual(receipt["control"]["authority_delta"], 0)

    def test_disabled_endpoint_is_rejected(self):
        frame, admission = self.frame_and_admission()
        policy = self.policy()
        policy["enabled"] = False
        with self.assertRaises(ValueError):
            accept_destination(frame, admission, policy)

    def test_wrong_target_endpoint_is_rejected(self):
        frame, admission = self.frame_and_admission()
        policy = self.policy()
        policy["accepted_target_heads"] = ["REGISTRY"]
        with self.assertRaises(ValueError):
            accept_destination(frame, admission, policy)

    def test_backpressure_admission_is_not_destination_acceptance(self):
        frame = build_frame(
            self.envelope(),
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="destination-unit-backpressure-001",
        )
        held = validate_frame(
            frame,
            principal_lookup=self.principal_lookup(),
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
            queue_depth=1,
            queue_capacity=1,
        )
        self.assertEqual(held["status"], "HOLD_BACKPRESSURE")
        with self.assertRaises(ValueError):
            accept_destination(frame, held, self.policy())

    def test_forged_admission_hash_is_rejected(self):
        frame, admission = self.frame_and_admission()
        forged = copy.deepcopy(admission)
        forged["frame_sha256"] = "f" * 64
        with self.assertRaises(ValueError):
            accept_destination(frame, forged, self.policy())

    def test_endpoint_cannot_grant_effect_or_authority(self):
        frame, admission = self.frame_and_admission()
        for field, value in (
            ("external_effect_permitted", True),
            ("authority_delta", 1),
            ("mass_effect_budget_delta", 1),
            ("local_dispatch_only", False),
        ):
            policy = self.policy()
            policy[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    accept_destination(frame, admission, policy)

    def test_admission_claiming_delivery_or_execution_is_rejected(self):
        frame, admission = self.frame_and_admission()
        for field in ("delivery_performed", "target_execution_performed"):
            forged = copy.deepcopy(admission)
            forged["control"][field] = True
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    accept_destination(frame, forged, self.policy())

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
