from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger import SqliteDispatchLedger  # noqa: E402
from nexus_local_transport import build_frame, sha256, validate_frame  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler, dispatch_loopback, self_test  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard  # noqa: E402


class NexusLoopbackDispatcherTests(unittest.TestCase):
    KEY = b"unit-loopback-dispatch-key"
    ISSUED = 1_800_000_000_000

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.ledger_path = Path(self.temp.name) / "dispatch.db"

    def tearDown(self):
        self.temp.cleanup()

    def ledger(self):
        return SqliteDispatchLedger(self.ledger_path)

    def payload(self):
        return {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}

    def envelope(self, payload=None):
        payload = payload or self.payload()
        return {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "loopback-unit-001",
            "source_head": "GUARDIAN",
            "target_head": "RELEASE_CONTROL",
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

    def dispatch(self, *, payload=None, public=None, catalog=None, handlers=None, now_offset=200, ledger=None):
        payload = payload or self.payload()
        frame, admission, default_public = self.frame_and_admission(payload)
        return dispatch_loopback(
            frame,
            admission,
            public or default_public,
            catalog or self.catalog(),
            payload,
            handlers or {"RELEASE_CONTROL": self.handler()},
            dispatch_ledger=ledger or self.ledger(),
            now_ms=self.ISSUED + now_offset,
        )

    def test_valid_dispatch_commits_started_before_handler_and_completion_after(self):
        result = self.dispatch()
        self.assertEqual(result["status"], "LOOPBACK_DISPATCH_COMPLETED_LOCAL")
        self.assertTrue(result["dispatch"]["durable_started_record_committed_before_handler"])
        self.assertTrue(result["dispatch"]["durable_completion_recorded"])
        self.assertTrue(result["ledger"]["persistent"])
        self.assertEqual(result["ledger"]["dispatch_state"], "COMPLETED")
        self.assertFalse(result["control"]["network_io_performed"])
        self.assertFalse(result["control"]["external_delivery_performed"])
        self.assertFalse(result["control"]["world_effect_performed"])
        self.assertFalse(result["claim_ceiling"]["exactly_once_delivery_established"])
        self.assertTrue(result["claim_ceiling"]["crash_safe_local_duplicate_attempt_suppression_established"])

    def test_same_admission_cannot_invoke_handler_twice_after_ledger_restart(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []
        handler = self.handler(lambda value: calls.append(value) or {"status": "ACK"})
        first = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": handler}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        second = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": handler}, dispatch_ledger=SqliteDispatchLedger(self.ledger_path), now_ms=self.ISSUED + 300,
        )
        self.assertEqual(first["status"], "LOOPBACK_DISPATCH_COMPLETED_LOCAL")
        self.assertEqual(second["status"], "HOLD_DUPLICATE_DISPATCH")
        self.assertEqual(second["ledger"]["dispatch_state"], "COMPLETED")
        self.assertEqual(len(calls), 1)
        self.assertFalse(second["control"]["automatic_retry_permitted"])

    def test_handler_exception_becomes_persistent_ambiguous_hold_and_never_retries(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []

        def explode(_payload):
            calls.append("attempt")
            raise RuntimeError("synthetic")

        handler = self.handler(explode)
        first = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": handler}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        second = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": handler}, dispatch_ledger=SqliteDispatchLedger(self.ledger_path), now_ms=self.ISSUED + 300,
        )
        self.assertEqual(first["status"], "HOLD_HANDLER_FAILURE")
        self.assertEqual(first["ledger"]["dispatch_state"], "FAILED_AMBIGUOUS")
        self.assertEqual(second["status"], "HOLD_DUPLICATE_DISPATCH")
        self.assertEqual(second["ledger"]["dispatch_state"], "FAILED_AMBIGUOUS")
        self.assertEqual(calls, ["attempt"])

    def test_invalid_handler_output_is_persistent_ambiguous_hold(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        result = dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": self.handler(lambda _value: "not-json-object")},
            dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        self.assertEqual(result["status"], "HOLD_HANDLER_OUTPUT_INVALID")
        self.assertEqual(result["ledger"]["dispatch_state"], "FAILED_AMBIGUOUS")
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_payload_hash_tamper_rejected_before_handler_and_ledger(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        calls = []
        tampered = dict(payload)
        tampered["decision"] = "MUTATED"
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), tampered,
                {"RELEASE_CONTROL": self.handler(lambda value: calls.append(value) or {"status": "ACK"})},
                dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.ledger().count(), 0)

    def test_revoked_principal_fails_before_handler_and_ledger(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        public["revoked"] = True
        calls = []
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), payload,
                {"RELEASE_CONTROL": self.handler(lambda value: calls.append(value) or {"status": "ACK"})},
                dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
            )
        self.assertEqual(calls, [])
        self.assertEqual(self.ledger().count(), 0)

    def test_missing_endpoint_and_handler_hold_without_ledger_entry(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        no_endpoint = dispatch_loopback(
            frame, admission, public, self.catalog(enabled=False), payload,
            {"RELEASE_CONTROL": self.handler()}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        self.assertEqual(no_endpoint["status"], "HOLD_NO_LOCAL_ENDPOINT")
        self.assertEqual(self.ledger().count(), 0)

        no_handler = dispatch_loopback(
            frame, admission, public, self.catalog(), payload, {},
            dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        self.assertEqual(no_handler["status"], "HOLD_NO_LOCAL_HANDLER")
        self.assertEqual(self.ledger().count(), 0)

    def test_ambiguous_or_network_endpoint_catalog_fails_closed(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        ambiguous = self.catalog()
        second = dict(ambiguous["endpoints"][0])
        second["endpoint_id"] = "DEMIHEAD.RELEASE_CONTROL.LOCAL.2"
        ambiguous["endpoints"].append(second)
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, ambiguous, payload,
                {"RELEASE_CONTROL": self.handler()}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
            )

        networked = self.catalog()
        networked["live_network_endpoints"] = True
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, networked, payload,
                {"RELEASE_CONTROL": self.handler()}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
            )

    def test_handler_requesting_network_io_is_rejected_before_ledger(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)
        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), payload,
                {"RELEASE_CONTROL": self.handler(network_io_permitted=True)},
                dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
            )
        self.assertEqual(self.ledger().count(), 0)

    def test_handler_input_is_deep_copy(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)

        def mutate(value):
            value["decision"] = "LOCAL_MUTATION"
            return {"status": "ACK"}

        dispatch_loopback(
            frame, admission, public, self.catalog(), payload,
            {"RELEASE_CONTROL": self.handler(mutate)}, dispatch_ledger=self.ledger(), now_ms=self.ISSUED + 200,
        )
        self.assertEqual(payload["decision"], "WAIT_FOR_NEW_EVIDENCE")

    def test_persistent_ledger_is_mandatory(self):
        payload = self.payload()
        frame, admission, public = self.frame_and_admission(payload)

        class MemoryLikeLedger:
            persistent = False

        with self.assertRaises(ValueError):
            dispatch_loopback(
                frame, admission, public, self.catalog(), payload,
                {"RELEASE_CONTROL": self.handler()}, dispatch_ledger=MemoryLikeLedger(), now_ms=self.ISSUED + 200,
            )

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
