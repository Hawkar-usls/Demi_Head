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

    def frame(self):
        return build_frame(
            self.envelope(),
            sender_id="DEMIHEAD.LOCAL",
            key_id="TEST_KEY",
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="00112233445566778899aabbccddeeff",
            ttl_ms=30_000,
        )

    def test_valid_authenticated_frame_is_admitted_but_not_delivered(self):
        admission = validate_frame(
            self.frame(),
            key_lookup={"TEST_KEY": self.KEY},
            now_ms=self.ISSUED + 100,
            replay_cache=set(),
        )
        self.assertEqual(admission["status"], "AUTHENTICATED_FRAME_ADMITTED")
        self.assertFalse(admission["control"]["delivery_performed"])
        self.assertFalse(admission["control"]["target_execution_performed"])
        self.assertFalse(admission["control"]["authentication_is_human_identity"])
        self.assertFalse(admission["control"]["authentication_is_authorization"])
        self.assertFalse(admission["control"]["network_io_performed"])

    def test_replay_is_rejected(self):
        frame = self.frame()
        cache = set()
        validate_frame(
            frame,
            key_lookup={"TEST_KEY": self.KEY},
            now_ms=self.ISSUED + 100,
            replay_cache=cache,
        )
        with self.assertRaises(ValueError):
            validate_frame(
                frame,
                key_lookup={"TEST_KEY": self.KEY},
                now_ms=self.ISSUED + 200,
                replay_cache=cache,
            )

    def test_stale_and_future_frames_are_rejected(self):
        frame = self.frame()
        with self.assertRaises(ValueError):
            validate_frame(frame, key_lookup={"TEST_KEY": self.KEY}, now_ms=self.ISSUED + 30_001)
        with self.assertRaises(ValueError):
            validate_frame(frame, key_lookup={"TEST_KEY": self.KEY}, now_ms=self.ISSUED - 5_001)

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
                validate_frame(tampered, key_lookup={"TEST_KEY": self.KEY}, now_ms=self.ISSUED + 100)

    def test_invalid_nexus_route_cannot_be_framed(self):
        envelope = self.envelope()
        envelope["target_head"] = "PORTAL"
        with self.assertRaises(ValueError):
            build_frame(
                envelope,
                sender_id="DEMIHEAD.LOCAL",
                key_id="TEST_KEY",
                key=self.KEY,
                issued_at_ms=self.ISSUED,
                nonce="ffeeddccbbaa99887766554433221100",
            )

    def test_oversized_frame_is_rejected(self):
        envelope = self.envelope()
        envelope["payload_ref"]["locator"] = "x" * (MAX_FRAME_BYTES + 1)
        with self.assertRaises(ValueError):
            build_frame(
                envelope,
                sender_id="DEMIHEAD.LOCAL",
                key_id="TEST_KEY",
                key=self.KEY,
                issued_at_ms=self.ISSUED,
                nonce="abcdefabcdefabcdefabcdefabcdefab",
            )

    def test_backpressure_holds_without_retry_permission(self):
        result = validate_frame(
            self.frame(),
            key_lookup={"TEST_KEY": self.KEY},
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
