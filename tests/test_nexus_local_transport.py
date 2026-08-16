from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_local_transport import MAX_FRAME_BYTES, build_frame, self_test, validate_frame  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard, SqliteReplayGuard  # noqa: E402


class NexusLocalTransportTests(unittest.TestCase):
    KEY = b"unit-test-only-shared-key"
    ISSUED = 1_800_000_000_000

    def principals(self, *, enabled=True, sender_id="DEMIHEAD.LOCAL", allowed=None):
        return {
            "TEST_KEY": {
                "key": self.KEY,
                "sender_id": sender_id,
                "allowed_source_heads": allowed or ["GUARDIAN"],
                "enabled": enabled,
            }
        }

    def envelope(self):
        return {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "transport-unit-001",
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

    def frame(self, *, sender_id="DEMIHEAD.LOCAL", envelope=None, nonce="00112233445566778899aabbccddeeff"):
        return build_frame(
            envelope or self.envelope(),
            sender_id=sender_id,
            key_id="TEST_KEY",
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce=nonce,
            ttl_ms=30_000,
        )

    def test_valid_authenticated_frame_is_principal_bound_but_not_delivered(self):
        admission = validate_frame(
            self.frame(),
            principal_lookup=self.principals(),
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        self.assertEqual(admission["status"], "AUTHENTICATED_FRAME_ADMITTED")
        self.assertTrue(admission["authentication"]["hmac_verified"])
        self.assertTrue(admission["authentication"]["key_bound_sender_verified"])
        self.assertTrue(admission["authentication"]["key_bound_source_head_verified"])
        self.assertFalse(admission["authentication"]["human_identity_established"])
        self.assertFalse(admission["authentication"]["world_effect_authorization_established"])
        self.assertTrue(admission["replay_protection"]["nonce_consumed_atomically"])
        self.assertFalse(admission["replay_protection"]["persistent"])
        self.assertFalse(admission["control"]["delivery_performed"])
        self.assertFalse(admission["control"]["target_execution_performed"])
        self.assertFalse(admission["control"]["network_io_performed"])

    def test_valid_key_cannot_impersonate_sender(self):
        frame = self.frame(sender_id="OTHER", nonce="11112222333344445555666677778888")
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), replay_guard=MemoryReplayGuard(), now_ms=self.ISSUED + 100)

    def test_valid_key_cannot_impersonate_source_head(self):
        envelope = self.envelope()
        envelope.update({"source_head": "FUNDAMENTUM", "target_head": "GUARDIAN", "payload_kind": "HOLD_RECEIPT"})
        frame = self.frame(envelope=envelope, nonce="99990000111122223333444455556666")
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), replay_guard=MemoryReplayGuard(), now_ms=self.ISSUED + 100)

    def test_disabled_principal_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_frame(
                self.frame(),
                principal_lookup=self.principals(enabled=False),
                replay_guard=MemoryReplayGuard(),
                now_ms=self.ISSUED + 100,
            )

    def test_replay_is_rejected_atomically(self):
        frame = self.frame()
        guard = MemoryReplayGuard()
        validate_frame(frame, principal_lookup=self.principals(), replay_guard=guard, now_ms=self.ISSUED + 100)
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), replay_guard=guard, now_ms=self.ISSUED + 200)

    def test_consumed_replay_is_rejected_before_backpressure(self):
        frame = self.frame()
        guard = MemoryReplayGuard()
        validate_frame(frame, principal_lookup=self.principals(), replay_guard=guard, now_ms=self.ISSUED + 100)
        with self.assertRaises(ValueError):
            validate_frame(
                frame,
                principal_lookup=self.principals(),
                replay_guard=guard,
                now_ms=self.ISSUED + 200,
                queue_depth=4,
                queue_capacity=4,
            )

    def test_sqlite_replay_guard_survives_restart(self):
        frame = self.frame()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.db"
            first = SqliteReplayGuard(path)
            admission = validate_frame(
                frame,
                principal_lookup=self.principals(),
                replay_guard=first,
                now_ms=self.ISSUED + 100,
            )
            self.assertTrue(admission["replay_protection"]["persistent"])
            self.assertEqual(admission["replay_protection"]["guard_kind"], "SQLITE")
            restarted = SqliteReplayGuard(path)
            with self.assertRaises(ValueError):
                validate_frame(
                    frame,
                    principal_lookup=self.principals(),
                    replay_guard=restarted,
                    now_ms=self.ISSUED + 200,
                )

    def test_replay_guard_is_required_for_admission(self):
        with self.assertRaises(ValueError):
            validate_frame(self.frame(), principal_lookup=self.principals(), replay_guard=None, now_ms=self.ISSUED + 100)

    def test_stale_and_future_frames_are_rejected(self):
        frame = self.frame()
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), replay_guard=MemoryReplayGuard(), now_ms=self.ISSUED + 30_000)
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), replay_guard=MemoryReplayGuard(), now_ms=self.ISSUED - 5_001)

    def test_authenticated_tamper_is_rejected(self):
        frame = self.frame()
        for mutate in (
            lambda value: value.__setitem__("sender_id", "OTHER"),
            lambda value: value["envelope"].__setitem__("target_head", "REGISTRY"),
            lambda value: value["transport_control"].__setitem__("authority_delta", 1),
        ):
            tampered = copy.deepcopy(frame)
            mutate(tampered)
            with self.assertRaises(ValueError):
                validate_frame(tampered, principal_lookup=self.principals(), replay_guard=MemoryReplayGuard(), now_ms=self.ISSUED + 100)

    def test_invalid_nexus_route_cannot_be_framed(self):
        envelope = self.envelope()
        envelope["target_head"] = "PORTAL"
        with self.assertRaises(ValueError):
            self.frame(envelope=envelope, nonce="ffeeddccbbaa99887766554433221100")

    def test_oversized_frame_is_rejected(self):
        envelope = self.envelope()
        envelope["payload_ref"]["locator"] = "x" * (MAX_FRAME_BYTES + 1)
        with self.assertRaises(ValueError):
            self.frame(envelope=envelope, nonce="abcdefabcdefabcdefabcdefabcdefab")

    def test_backpressure_holds_without_consuming_nonce_or_retry_permission(self):
        guard = MemoryReplayGuard()
        frame = self.frame(nonce="abcdef00112233445566778899abcdef")
        result = validate_frame(
            frame,
            principal_lookup=self.principals(),
            replay_guard=guard,
            now_ms=self.ISSUED + 100,
            queue_depth=4,
            queue_capacity=4,
        )
        self.assertEqual(result["status"], "HOLD_BACKPRESSURE")
        self.assertFalse(result["control"]["automatic_retry_permitted"])
        self.assertFalse(result["control"]["delivery_performed"])
        self.assertFalse(result["replay_protection"]["nonce_consumed"])
        admitted = validate_frame(
            frame,
            principal_lookup=self.principals(),
            replay_guard=guard,
            now_ms=self.ISSUED + 200,
            queue_depth=0,
            queue_capacity=4,
        )
        self.assertEqual(admitted["status"], "AUTHENTICATED_FRAME_ADMITTED")

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
