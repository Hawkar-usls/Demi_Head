from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_local_transport import (  # noqa: E402
    MAX_FRAME_BYTES,
    build_frame,
    self_test,
    validate_frame,
)


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
            now_ms=self.ISSUED + 100,
            replay_cache=set(),
        )
        self.assertEqual(admission["status"], "AUTHENTICATED_FRAME_ADMITTED")
        self.assertTrue(admission["authentication"]["hmac_verified"])
        self.assertTrue(admission["authentication"]["key_bound_sender_verified"])
        self.assertTrue(admission["authentication"]["key_bound_source_head_verified"])
        self.assertFalse(admission["authentication"]["human_identity_established"])
        self.assertFalse(admission["authentication"]["world_effect_authorization_established"])
        self.assertFalse(admission["control"]["delivery_performed"])
        self.assertFalse(admission["control"]["target_execution_performed"])
        self.assertFalse(admission["control"]["network_io_performed"])
        self.assertFalse(admission["control"]["persistent_replay_ledger_used"])

    def test_valid_key_cannot_impersonate_sender(self):
        frame = self.frame(sender_id="OTHER", nonce="11112222333344445555666677778888")
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED + 100)

    def test_valid_key_cannot_impersonate_source_head(self):
        envelope = self.envelope()
        envelope.update({
            "source_head": "FUNDAMENTUM",
            "target_head": "GUARDIAN",
            "payload_kind": "HOLD_RECEIPT",
        })
        frame = self.frame(envelope=envelope, nonce="99990000111122223333444455556666")
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED + 100)

    def test_disabled_principal_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_frame(
                self.frame(),
                principal_lookup=self.principals(enabled=False),
                now_ms=self.ISSUED + 100,
            )

    def test_replay_is_rejected(self):
        frame = self.frame()
        cache = set()
        validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED + 100, replay_cache=cache)
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED + 200, replay_cache=cache)

    def test_stale_and_future_frames_are_rejected(self):
        frame = self.frame()
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED + 30_001)
        with self.assertRaises(ValueError):
            validate_frame(frame, principal_lookup=self.principals(), now_ms=self.ISSUED - 5_001)

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
                validate_frame(tampered, principal_lookup=self.principals(), now_ms=self.ISSUED + 100)

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

    def test_backpressure_holds_without_retry_permission(self):
        result = validate_frame(
            self.frame(),
            principal_lookup=self.principals(),
            now_ms=self.ISSUED + 100,
            replay_cache=set(),
            queue_depth=4,
            queue_capacity=4,
        )
        self.assertEqual(result["status"], "HOLD_BACKPRESSURE")
        self.assertFalse(result["control"]["automatic_retry_permitted"])
        self.assertFalse(result["control"]["delivery_performed"])

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
