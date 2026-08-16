from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_local_transport import build_frame, sha256, validate_frame  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler, dispatch_loopback, self_test  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard  # noqa: E402


class NexusLoopbackDispatcherTests(unittest.TestCase):
    KEY = b"unit-loopback-dispatch-key"
    ISSUED = 1_800_000_000_000

    def payload(self):
        return {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}

    def envelope(self, payload=None, *, target_head="RELEASE_CONTROL"):
        payload = payload or self.payload()
        return {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "loopback-unit-001",
            "source_head": "GUARDIAN",
            "target_head": target_head,
            "payload_kind": "GUARDIAN_RESULT",
            "payload_ref": {"sha256": sha256(payload)},
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

    def principals(self):
        runtime = {
            "key": self.KEY,
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        public = {
            "key_id": "GUARDIAN_E1",
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        return runtime, public

    def frame_and_admission(self, payload=None):
        payload = payload or self.payload()
        frame = build_frame(
            self.envelope(payload),
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="loopback-unit-nonce-00000001",
        )
        runtime, public = self.principals()
        admission = validate_frame(
            frame,
            principal_lookup={"GUARDIAN_E1": runtime},
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        return frame, admission, public

    def catalog(self, *, enabled=True):
        return {
            "schema": "janus.demihead.nexus_endpoint_catalog.v1",
            "live_network_endpoints": False,
            "endpoints": [{
                "schema": "janus.demihead.nexus_endpoint_policy.v1",
                "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
                "enabled": enabled,
                "accepted_target_heads": ["RELEASE_CONTROL"],
                "local_dispatch_only": True,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            }],
        }

    def handler(self, callback=None, **kwargs):
        callback = callback or (lambda payload: {
            "status": "ACK_LOCAL_ONLY",
            "input_sha256": sha256(payload),
        })
        return LocalHandler(
            handler_id="RELEASE_CONTROL.UNIT_ACK.V1",
            target_head="RELEASE_CONTROL",
            callback=callback,
            **kwargs,
        )

    def test_valid_dispatch_performs_only_local_in_process_delivery(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        result = dispatch_loopback(
            frame,
            admission,
            public,
            self.catalog(),
            payload,
            {"RELEASE_CONTROL": self.handler()},
            now_ms=self.ISSUED + 200,
        )
        self.assertEqual(result["status"], "LOOPBACK_DISPATCH_COMPLETED_LOCAL")
        self.assertTrue(result["dispatch"]["local_reference_handler_invoked"])
        self.assertTrue(result["dispatch"]["local_in_process_delivery_performed"])
        self.assertFalse(result["control"]["network_io_performed"])
        self.assertFalse(result["control"]["external_delivery_performed"])
        self.assertFalse(result["control"]["world_effect_performed"])
        self.assertFalse(result["claim_ceiling"]["exactly_once_delivery_established"])

    def test_payload_hash_tamper_is_rejected_before_handler(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []
        handler = self.handler(lambda value: calls.append(value) or {"status": "SHOULD_NOT_RUN"})
        tampered = dict(payload)
        tampered["decision"] = "MUTATED"
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), tampered,
                {"RELEASE_CONTROL": handler}, now_ms=self.ISSUED + 200,
            )
        self.assertEqual(calls, [])

    def test_missing_endpoint_holds_without_invocation(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []
        handler = self.handler(lambda value: calls.append(value) or {"status": "ACK"})
        result = dispatch_loopback(
            frame, admission, public, self.catalog(enabled=False), payload,
            {"RELEASE_CONTROL": handler}, now_ms=self.ISSUED + 200,
        )
        self.assertEqual(result["status"], "HOLD_NO_LOCAL_ENDPOINT")
        self.assertFalse(result["control"]["automatic_retry_permitted"])
        self.assertEqual(calls, [])

    def test_missing_handler_holds(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        result = dispatch_loopback(
            frame, admission, public, self.catalog(), payload, {},
            now_ms=self.ISSUED + 200,
        )
        self.assertEqual(result["status"], "HOLD_NO_LOCAL_HANDLER")
        self.assertFalse(result["control"]["local_in_process_delivery_performed"])

    def test_ambiguous_enabled_endpoints_fail_closed(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        catalog = self.catalog()
        second = dict(catalog["endpoints"][0])
        second["endpoint_id"] = "DEMIHEAD.RELEASE_CONTROL.LOCAL.2"
        catalog["endpoints"].append(second)
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, catalog, payload,
                {"RELEASE_CONTROL": self.handler()}, now_ms=self.ISSUED + 200,
            )

    def test_live_network_catalog_fails_closed(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        catalog = self.catalog()
        catalog["live_network_endpoints"] = True
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, catalog, payload,
                {"RELEASE_CONTROL": self.handler()}, now_ms=self.ISSUED + 200,
            )

    def test_handler_requesting_network_io_is_rejected_before_invocation(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []
        handler = self.handler(
            lambda value: calls.append(value) or {"status": "ACK"},
            network_io_permitted=True,
        )
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), payload,
                {"RELEASE_CONTROL": handler}, now_ms=self.ISSUED + 200,
            )
        self.assertEqual(calls, [])

    def test_revoked_principal_fails_before_handler(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        public["revoked"] = True
        calls = []
        handler = self.handler(lambda value: calls.append(value) or {"status": "ACK"})
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), payload,
                {"RELEASE_CONTROL": handler}, now_ms=self.ISSUED + 200,
            )
        self.assertEqual(calls, [])

    def test_handler_exception_holds_and_forbids_automatic_retry(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)

        def explode(_payload):
            raise RuntimeError("synthetic")

        result = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": self.handler(explode)}, now_ms=self.ISSUED + 200,
        )
        self.assertEqual(result["status"], "HOLD_HANDLER_FAILURE")
        self.assertTrue(result["hold"]["handler_invocation_attempted"])
        self.assertFalse(result["hold"]["completion_established"])
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_handler_input_is_deep_copy(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)

        def mutate(value):
            value["decision"] = "LOCAL_MUTATION"
            return {"status": "ACK"}

        dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": self.handler(mutate)}, now_ms=self.ISSUED + 200,
        )
        self.assertEqual(payload["decision"], "WAIT_FOR_NEW_EVIDENCE")

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
