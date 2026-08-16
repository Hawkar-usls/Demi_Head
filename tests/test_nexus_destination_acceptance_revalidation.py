from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_destination_acceptance_revalidation import accept_destination_revalidated, self_test  # noqa: E402
from nexus_local_transport import build_frame, validate_frame  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard  # noqa: E402


class NexusDestinationAcceptanceRevalidationTests(unittest.TestCase):
    KEY = b"destination-revalidation-unit-key"
    ISSUED = 1_800_000_000_000

    def envelope(self):
        return {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "destination-revalidation-unit-001",
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

    def runtime_principal(self):
        return {
            "key": self.KEY,
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }

    def public_principal(self):
        value = dict(self.runtime_principal())
        value.pop("key")
        value["key_id"] = "GUARDIAN_E1"
        return value

    def endpoint(self):
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

    def frame_and_admission(self):
        frame = build_frame(
            self.envelope(),
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="destination-revalidation-unit-nonce",
        )
        admission = validate_frame(
            frame,
            principal_lookup={"GUARDIAN_E1": self.runtime_principal()},
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        return frame, admission

    def test_current_policy_is_revalidated_before_acceptance(self):
        frame, admission = self.frame_and_admission()
        receipt = accept_destination_revalidated(
            frame,
            admission,
            self.endpoint(),
            self.public_principal(),
            now_ms=self.ISSUED + 200,
        )
        self.assertEqual(receipt["status"], "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH_REVALIDATED")
        self.assertTrue(receipt["principal_revalidation"]["revocation_rechecked_at_acceptance"])
        self.assertTrue(receipt["acceptance"]["current_revocation_state_verified"])
        self.assertTrue(receipt["acceptance"]["current_epoch_verified"])
        self.assertFalse(receipt["acceptance"]["delivery_performed"])
        self.assertFalse(receipt["acceptance"]["target_execution_performed"])

    def test_revocation_after_transport_admission_blocks_destination(self):
        frame, admission = self.frame_and_admission()
        current = self.public_principal()
        current["revoked"] = True
        with self.assertRaises(ValueError):
            accept_destination_revalidated(frame, admission, self.endpoint(), current, now_ms=self.ISSUED + 200)

    def test_epoch_rollover_after_admission_blocks_old_epoch(self):
        frame, admission = self.frame_and_admission()
        current = self.public_principal()
        current["epoch"] = 2
        with self.assertRaises(ValueError):
            accept_destination_revalidated(frame, admission, self.endpoint(), current, now_ms=self.ISSUED + 200)

    def test_expiry_between_admission_and_acceptance_blocks_destination(self):
        frame, admission = self.frame_and_admission()
        current = self.public_principal()
        current["not_after_ms"] = self.ISSUED + 150
        with self.assertRaises(ValueError):
            accept_destination_revalidated(frame, admission, self.endpoint(), current, now_ms=self.ISSUED + 200)

    def test_sender_or_source_policy_drift_blocks_destination(self):
        frame, admission = self.frame_and_admission()
        for mutate in (
            lambda current: current.__setitem__("sender_id", "OTHER"),
            lambda current: current.__setitem__("allowed_source_heads", ["OBSERVER"]),
            lambda current: current.__setitem__("enabled", False),
        ):
            current = copy.deepcopy(self.public_principal())
            mutate(current)
            with self.assertRaises(ValueError):
                accept_destination_revalidated(frame, admission, self.endpoint(), current, now_ms=self.ISSUED + 200)

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
