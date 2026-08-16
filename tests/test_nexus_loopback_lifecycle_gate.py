from __future__ import annotations

import hashlib
import json
import socket
import sqlite3
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2  # noqa: E402
from nexus_local_transport import build_frame, sha256  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler  # noqa: E402
from nexus_loopback_exchange import WireProtocolError, _recv_packet, build_request, client_exchange_once  # noqa: E402
from nexus_loopback_lifecycle_gate import (  # noqa: E402
    PreparedLifecycleListener,
    SqliteLifecycleLedger,
    default_lifecycle_policy,
    prepare_lifecycle_listener,
    serve_one_exchange_lifecycle,
)
from nexus_loopback_socket_guard import default_config  # noqa: E402
from nexus_replay_ledger import SqliteReplayGuard  # noqa: E402

class BrokenReplayGuard:
    persistent = True
    kind = "BROKEN_TEST_DOUBLE"

    def seen(self, replay_key: str, *, now_ms: int) -> bool:
        raise sqlite3.OperationalError("simulated replay store outage")

    def consume(self, replay_key: str, *, expires_at_ms: int, now_ms: int) -> bool:
        raise sqlite3.OperationalError("simulated replay store outage")

class NexusOneShotLifecycleGateTests(unittest.TestCase):
    KEY = b"one-shot-lifecycle-gate-test-key"
    ISSUED = 1_800_000_000_000
    SERVICE = "DEMIHEAD.NEXUS.ONE_SHOT.TEST"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lifecycle = SqliteLifecycleLedger(self.root / "lifecycle.db")
        self.replay_path = self.root / "replay.db"
        self.dispatch_path = self.root / "dispatch.db"
        self.calls: list[str] = []

    def tearDown(self):
        self.temp.cleanup()

    def policy(self):
        policy = default_lifecycle_policy()
        policy["startup_enabled"] = True
        policy["accept_timeout_ms"] = 120
        policy["read_timeout_ms"] = 120
        policy["write_timeout_ms"] = 120
        return policy

    def config(self):
        config = default_config("127.0.0.1")
        config["listener_enabled"] = True
        config["accept_timeout_ms"] = 120
        return config

    def payload(self):
        return {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}

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
        return {"GUARDIAN_E1": runtime}, {"GUARDIAN_E1": public}

    def frame(self, *, payload=None, nonce="lifecycle-gate-nonce-000001"):
        payload = payload or self.payload()
        envelope = {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "one-shot-lifecycle-gate-test",
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
        return build_frame(
            envelope,
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce=nonce,
            ttl_ms=30_000,
        )

    def catalog(self):
        return {
            "schema": "janus.demihead.nexus_endpoint_catalog.v1",
            "live_network_endpoints": False,
            "endpoints": [{
                "schema": "janus.demihead.nexus_endpoint_policy.v1",
                "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
                "enabled": True,
                "accepted_target_heads": ["RELEASE_CONTROL"],
                "local_dispatch_only": True,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            }],
        }

    def handlers(self):
        def callback(payload):
            self.calls.append(sha256(payload))
            return {"schema": "janus.demihead.lifecycle_ack.v1", "status": "ACK_LOCAL_ONLY"}
        return {
            "RELEASE_CONTROL": LocalHandler(
                handler_id="RELEASE_CONTROL.LIFECYCLE_ACK.V1",
                target_head="RELEASE_CONTROL",
                callback=callback,
            )
        }

    def prepare(self, instance_id: str, *, service_id: str | None = None, policy=None):
        return prepare_lifecycle_listener(
            self.config(),
            self.policy() if policy is None else policy,
            lifecycle_ledger=self.lifecycle,
            service_id=service_id or self.SERVICE,
            instance_id=instance_id,
            explicit_enable=True,
            now_ms=self.ISSUED + 100,
        )

    def start_server(self, prepared, *, replay_guard=None, receipt_sender=None, dispatch_path=None):
        runtime, public = self.principals()
        box: dict[str, object] = {}
        def target():
            try:
                box["outcome"] = serve_one_exchange_lifecycle(
                    prepared,
                    principal_lookup=runtime,
                    public_principal_lookup=public,
                    endpoint_catalog=self.catalog(),
                    handlers=self.handlers(),
                    replay_guard=replay_guard or SqliteReplayGuard(self.replay_path),
                    dispatch_ledger=SqliteDispatchLedgerV2(dispatch_path or self.dispatch_path),
                    now_ms=self.ISSUED + 200,
                    receipt_sender=receipt_sender,
                )
            except BaseException as exc:
                box["error"] = exc
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread, box

    def assert_server_clean(self, thread, box):
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "lifecycle server did not terminate")
        if "error" in box:
            raise box["error"]
        self.assertIn("outcome", box)

    def request(self):
        payload = self.payload()
        return build_request(self.frame(payload=payload), payload)

    def test_frozen_manifest_hash_and_case_set(self):
        path = ROOT / "fixtures" / "nexus_one_shot_lifecycle_holdout_v1.json"
        corpus = json.loads(path.read_text(encoding="utf-8"))
        payload = corpus["freeze_payload"]
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "21b49045bea3853f53112f1ec4917d40b37a9fc4a13ce63dea80a19bb09e1dd6")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertTrue(payload["frozen_before_first_execution"])
        self.assertEqual(len(payload["cases"]), 9)
        self.assertFalse(payload["invariants"]["automatic_retry_permitted"])
        self.assertFalse(payload["invariants"]["persistent_daemon"])

    def test_startup_disabled_creates_no_socket_and_no_ledger_row(self):
        result = self.prepare("run-disabled", policy=default_lifecycle_policy())
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "HOLD_STARTUP_DISABLED")
        self.assertFalse(result["lifecycle"]["socket_created"])
        self.assertIsNone(self.lifecycle.state(self.SERVICE))

    def test_concurrent_start_is_rejected_by_persistent_lifecycle_lease(self):
        first = self.prepare("run-1")
        self.assertIsInstance(first, PreparedLifecycleListener)
        second = self.prepare("run-2")
        self.assertIsInstance(second, dict)
        self.assertEqual(second["status"], "HOLD_LIFECYCLE_BUSY_OR_AMBIGUOUS")
        self.assertEqual(second["lifecycle"]["phase"], "LISTENER_BOUND")
        first.close_clean(now_ms=self.ISSUED + 150)
        third = self.prepare("run-3")
        self.assertIsInstance(third, PreparedLifecycleListener)
        third.close_clean(now_ms=self.ISSUED + 160)

    def test_crash_like_nonterminal_state_blocks_automatic_restart(self):
        first = self.prepare("run-crash")
        self.assertIsInstance(first, PreparedLifecycleListener)
        first.listener.close()
        second = self.prepare("run-after-crash")
        self.assertIsInstance(second, dict)
        self.assertEqual(second["status"], "HOLD_LIFECYCLE_BUSY_OR_AMBIGUOUS")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "LISTENER_BOUND")
        self.assertFalse(second["control"]["automatic_restart_permitted"])

    def test_accept_timeout_is_clean_terminal_and_never_auto_restarts(self):
        prepared = self.prepare("run-timeout")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        old_port = prepared.port
        runtime, public = self.principals()
        outcome = serve_one_exchange_lifecycle(
            prepared,
            principal_lookup=runtime,
            public_principal_lookup=public,
            endpoint_catalog=self.catalog(),
            handlers=self.handlers(),
            replay_guard=SqliteReplayGuard(self.replay_path),
            dispatch_ledger=SqliteDispatchLedgerV2(self.dispatch_path),
            now_ms=self.ISSUED + 200,
        )
        self.assertEqual(outcome["status"], "HOLD_ACCEPT_TIMEOUT")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "CLOSED_CLEAN")
        self.assertFalse(outcome["control"]["automatic_restart_permitted"])
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", old_port), timeout=0.1)

    def test_read_timeout_fails_closed_without_dispatch(self):
        prepared = self.prepare("run-read-timeout")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        thread, box = self.start_server(prepared)
        sock = socket.create_connection(("127.0.0.1", prepared.port), timeout=1.0)
        try:
            receipt = _recv_packet(sock)
        finally:
            sock.close()
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "HOLD_WIRE_PROTOCOL")
        self.assertEqual(self.calls, [])
        self.assertEqual(box["outcome"]["status"], "CLOSED_CLEAN")

    def test_replay_store_failure_fails_closed_before_dispatch(self):
        prepared = self.prepare("run-replay-failure")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        thread, box = self.start_server(prepared, replay_guard=BrokenReplayGuard())
        receipt = client_exchange_once("127.0.0.1", prepared.port, self.request())
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "HOLD_TRANSPORT_REJECTED")
        self.assertEqual(receipt["rejection"]["stage"], "TRANSPORT_OR_REPLAY_STATE")
        self.assertEqual(self.calls, [])
        self.assertEqual(box["outcome"]["status"], "CLOSED_CLEAN")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "CLOSED_CLEAN")

    def test_completed_dispatch_with_lost_receipt_is_ambiguous_and_never_retried_automatically(self):
        prepared = self.prepare("run-response-loss")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        def fail_send(sock, receipt):
            raise socket.timeout("simulated response send timeout")
        thread, box = self.start_server(prepared, receipt_sender=fail_send)
        with self.assertRaises((WireProtocolError, OSError)):
            client_exchange_once("127.0.0.1", prepared.port, self.request())
        self.assert_server_clean(thread, box)
        outcome = box["outcome"]
        self.assertEqual(outcome["status"], "CLOSED_AMBIGUOUS")
        self.assertEqual(outcome["lifecycle"]["detail_code"], "DISPATCH_COMPLETED_RECEIPT_UNCONFIRMED")
        self.assertTrue(outcome["lifecycle"]["manual_ack_required"])
        self.assertFalse(outcome["lifecycle"]["wire_receipt_send_completed"])
        self.assertTrue(outcome["dispatch"]["completion_established"])
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "CLOSED_AMBIGUOUS")
        blocked = self.prepare("run-blocked")
        self.assertIsInstance(blocked, dict)
        self.assertEqual(blocked["status"], "HOLD_LIFECYCLE_BUSY_OR_AMBIGUOUS")
        self.assertTrue(blocked["lifecycle"]["manual_ack_required"])
        self.assertTrue(self.lifecycle.acknowledge_ambiguous(
            self.SERVICE,
            "run-response-loss",
            operator_ack=True,
            now_ms=self.ISSUED + 300,
        ))
        replay_lost = self.root / "fresh-replay-after-ack.db"
        retry = self.prepare("run-after-manual-ack")
        self.assertIsInstance(retry, PreparedLifecycleListener)
        thread2, box2 = self.start_server(retry, replay_guard=SqliteReplayGuard(replay_lost))
        receipt2 = client_exchange_once("127.0.0.1", retry.port, self.request())
        self.assert_server_clean(thread2, box2)
        self.assertEqual(receipt2["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_HOLD")
        self.assertEqual(receipt2["binding"]["dispatch_status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(box2["outcome"]["status"], "CLOSED_CLEAN")

    def test_happy_roundtrip_records_clean_lifecycle_and_allows_new_explicit_instance(self):
        prepared = self.prepare("run-happy")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        thread, box = self.start_server(prepared)
        receipt = client_exchange_once("127.0.0.1", prepared.port, self.request())
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED")
        outcome = box["outcome"]
        self.assertEqual(outcome["status"], "CLOSED_CLEAN")
        self.assertTrue(outcome["lifecycle"]["wire_receipt_send_completed"])
        self.assertTrue(outcome["dispatch"]["completion_established"])
        self.assertFalse(outcome["control"]["automatic_retry_permitted"])
        self.assertEqual(len(self.calls), 1)
        next_instance = self.prepare("run-next-explicit")
        self.assertIsInstance(next_instance, PreparedLifecycleListener)
        next_instance.close_clean(now_ms=self.ISSUED + 400)

if __name__ == "__main__":
    unittest.main()
