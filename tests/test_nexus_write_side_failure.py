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
from nexus_local_transport import build_frame, sha256, validate_frame  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler  # noqa: E402
from nexus_loopback_dispatcher_v2 import dispatch_loopback_v2  # noqa: E402
from nexus_loopback_exchange import WireProtocolError, build_request, client_exchange_once  # noqa: E402
from nexus_loopback_lifecycle_gate import (  # noqa: E402
    PreparedLifecycleListener,
    default_lifecycle_policy,
    prepare_lifecycle_listener,
    serve_one_exchange_lifecycle,
)
from nexus_loopback_socket_guard import default_config  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard, SqliteReplayGuard  # noqa: E402
from nexus_write_fault_injection import (  # noqa: E402
    FaultInjectingDispatchLedger,
    FaultInjectingLifecycleLedger,
)


class NexusWriteSideFailureTests(unittest.TestCase):
    KEY = b"write-side-storage-fault-key"
    ISSUED = 1_800_000_040_000
    SERVICE = "DEMIHEAD.NEXUS.WRITE.TEST"

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.calls: list[str] = []

    def tearDown(self):
        self.temp.cleanup()

    def payload(self):
        return {"decision": "WAIT_FOR_DURABLE_EVIDENCE", "authority_delta": 0}

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

    def frame(self, *, payload=None, nonce="write-side-fault-nonce-0001"):
        payload = payload or self.payload()
        envelope = {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "write-side-fault-test",
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

    def handler(self, *, raises: bool = False):
        def callback(payload):
            self.calls.append(sha256(payload))
            if raises:
                raise RuntimeError("injected handler failure after invocation")
            return {"schema": "janus.demihead.write_fault_ack.v1", "status": "ACK_LOCAL_ONLY"}
        return LocalHandler(
            handler_id="RELEASE_CONTROL.WRITE_FAULT_ACK.V1",
            target_head="RELEASE_CONTROL",
            callback=callback,
        )

    def admitted(self, frame):
        runtime, public = self.principals()
        admission = validate_frame(
            frame,
            principal_lookup=runtime,
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        return admission, public["GUARDIAN_E1"]

    def direct_dispatch(self, ledger, *, raises: bool = False, nonce="write-side-direct-nonce-001"):
        payload = self.payload()
        frame = self.frame(payload=payload, nonce=nonce)
        admission, public = self.admitted(frame)
        return dispatch_loopback_v2(
            frame,
            admission,
            public,
            self.catalog(),
            payload,
            {"RELEASE_CONTROL": self.handler(raises=raises)},
            dispatch_ledger=ledger,
            now_ms=self.ISSUED + 200,
        )

    def lifecycle_policy(self):
        policy = default_lifecycle_policy()
        policy["startup_enabled"] = True
        policy["accept_timeout_ms"] = 150
        policy["read_timeout_ms"] = 150
        policy["write_timeout_ms"] = 150
        return policy

    def socket_config(self):
        config = default_config("127.0.0.1")
        config["listener_enabled"] = True
        config["accept_timeout_ms"] = 150
        return config

    def prepare(self, ledger, instance_id):
        return prepare_lifecycle_listener(
            self.socket_config(),
            self.lifecycle_policy(),
            lifecycle_ledger=ledger,
            service_id=self.SERVICE,
            instance_id=instance_id,
            explicit_enable=True,
            now_ms=self.ISSUED + 100,
        )

    def start_server(self, prepared, dispatch_ledger):
        runtime, public = self.principals()
        box: dict[str, object] = {}
        def target():
            try:
                box["outcome"] = serve_one_exchange_lifecycle(
                    prepared,
                    principal_lookup=runtime,
                    public_principal_lookup=public,
                    endpoint_catalog=self.catalog(),
                    handlers={"RELEASE_CONTROL": self.handler()},
                    replay_guard=SqliteReplayGuard(self.root / "lifecycle-replay.db"),
                    dispatch_ledger=dispatch_ledger,
                    now_ms=self.ISSUED + 200,
                )
            except BaseException as exc:
                box["error"] = exc
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread, box

    def request(self, *, nonce="write-side-lifecycle-nonce-001"):
        payload = self.payload()
        return build_request(self.frame(payload=payload, nonce=nonce), payload)

    def join(self, thread, box):
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "server thread did not terminate")
        if "error" in box:
            raise box["error"]
        self.assertIn("outcome", box)
        return box["outcome"]

    def test_frozen_manifest_hash_and_case_count(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_write_side_failure_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "4297fd48ccff1d32fee9d9729759afba37345b69fe51c0cc40e0647ef3dcb41e")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 10)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])

    def test_lifecycle_begin_write_failure_creates_no_listener(self):
        lifecycle = FaultInjectingLifecycleLedger(self.root / "life-begin.db", fail_begin=True)
        result = self.prepare(lifecycle, "write-01")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["status"], "HOLD_LIFECYCLE_LEDGER_UNAVAILABLE")
        self.assertFalse(result["lifecycle"]["socket_created"])
        self.assertEqual(self.calls, [])

    def test_dispatch_begin_injected_failure_holds_before_handler(self):
        ledger = FaultInjectingDispatchLedger(self.root / "dispatch-begin.db", fail_operations={"begin"})
        result = self.direct_dispatch(ledger, nonce="write-02-nonce-000001")
        self.assertEqual(result["status"], "HOLD_LEDGER_UNAVAILABLE")
        self.assertFalse(result["hold"]["handler_invocation_attempted"])
        self.assertEqual(ledger.count(), 0)
        self.assertEqual(self.calls, [])

    def test_dispatch_begin_real_sqlite_lock_holds_before_handler(self):
        path = self.root / "dispatch-lock.db"
        ledger = SqliteDispatchLedgerV2(path, busy_timeout_ms=25)
        locker = sqlite3.connect(str(path), timeout=0.1, isolation_level=None)
        try:
            locker.execute("PRAGMA journal_mode=WAL")
            locker.execute("BEGIN IMMEDIATE")
            result = self.direct_dispatch(ledger, nonce="write-03-nonce-000001")
        finally:
            try:
                locker.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            locker.close()
        self.assertEqual(result["status"], "HOLD_LEDGER_UNAVAILABLE")
        self.assertFalse(result["hold"]["handler_invocation_attempted"])
        self.assertEqual(self.calls, [])
        self.assertEqual(ledger.count(), 0)

    def test_handler_failure_with_durable_ambiguous_finalization(self):
        ledger = FaultInjectingDispatchLedger(self.root / "handler-fail-recorded.db")
        result = self.direct_dispatch(ledger, raises=True, nonce="write-04-nonce-000001")
        self.assertEqual(result["status"], "HOLD_HANDLER_FAILURE")
        self.assertTrue(result["hold"]["handler_invocation_attempted"])
        self.assertEqual(result["ledger"]["dispatch_state"], "FAILED_AMBIGUOUS")
        entry = ledger.get_by_intent(result["binding"]["intent_sha256"])
        self.assertEqual(entry["state"], "FAILED_AMBIGUOUS")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_handler_failure_and_ambiguous_write_failure_leaves_started(self):
        ledger = FaultInjectingDispatchLedger(self.root / "handler-fail-finalize.db", fail_operations={"fail_ambiguous"})
        result = self.direct_dispatch(ledger, raises=True, nonce="write-05-nonce-000001")
        self.assertEqual(result["status"], "HOLD_LEDGER_FINALIZATION_FAILURE")
        self.assertTrue(result["hold"]["handler_invocation_attempted"])
        self.assertEqual(result["ledger"]["dispatch_state"], "STARTED")
        entry = ledger.get_by_intent(result["binding"]["intent_sha256"])
        self.assertEqual(entry["state"], "STARTED")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_handler_success_and_completed_write_failure_leaves_started(self):
        ledger = FaultInjectingDispatchLedger(self.root / "complete-fail.db", fail_operations={"complete"})
        result = self.direct_dispatch(ledger, nonce="write-06-nonce-000001")
        self.assertEqual(result["status"], "HOLD_LEDGER_FINALIZATION_FAILURE")
        self.assertTrue(result["hold"]["handler_invocation_attempted"])
        entry = ledger.get_by_intent(result["binding"]["intent_sha256"])
        self.assertEqual(entry["state"], "STARTED")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_lifecycle_dispatch_started_write_failure_prevents_dispatch_entry(self):
        lifecycle = FaultInjectingLifecycleLedger(self.root / "life-dispatch-start.db", fail_phases={"DISPATCH_STARTED"})
        prepared = self.prepare(lifecycle, "write-07")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        dispatch = SqliteDispatchLedgerV2(self.root / "life-dispatch-start-ledger.db")
        thread, box = self.start_server(prepared, dispatch)
        with self.assertRaises((WireProtocolError, OSError)):
            client_exchange_once("127.0.0.1", prepared.port, self.request(nonce="write-07-nonce-000001"))
        outcome = self.join(thread, box)
        self.assertEqual(outcome["status"], "HOLD_LIFECYCLE_LEDGER_UNAVAILABLE")
        self.assertFalse(outcome["dispatch"]["handler_invocation_attempted"])
        self.assertFalse(outcome["dispatch"]["completion_established"])
        self.assertEqual(dispatch.count(), 0)
        self.assertEqual(self.calls, [])

    def test_lifecycle_dispatch_completed_write_failure_preserves_durable_dispatch_completion(self):
        lifecycle = FaultInjectingLifecycleLedger(self.root / "life-dispatch-complete.db", fail_phases={"DISPATCH_COMPLETED"})
        prepared = self.prepare(lifecycle, "write-08")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        dispatch = SqliteDispatchLedgerV2(self.root / "life-dispatch-complete-ledger.db")
        thread, box = self.start_server(prepared, dispatch)
        with self.assertRaises((WireProtocolError, OSError)):
            client_exchange_once("127.0.0.1", prepared.port, self.request(nonce="write-08-nonce-000001"))
        outcome = self.join(thread, box)
        self.assertEqual(outcome["status"], "HOLD_LIFECYCLE_LEDGER_UNAVAILABLE")
        self.assertTrue(outcome["dispatch"]["handler_invocation_attempted"])
        self.assertTrue(outcome["dispatch"]["completion_established"])
        self.assertEqual(dispatch.count(), 1)
        with sqlite3.connect(str(dispatch.path)) as db:
            state = db.execute("SELECT state FROM nexus_dispatch_ledger_v2").fetchone()[0]
        self.assertEqual(state, "COMPLETED")
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(outcome["control"]["automatic_retry_permitted"])

    def test_lifecycle_receipt_pending_write_failure_preserves_completed_dispatch_and_sends_no_receipt(self):
        lifecycle = FaultInjectingLifecycleLedger(self.root / "life-receipt-pending.db", fail_phases={"RECEIPT_PENDING"})
        prepared = self.prepare(lifecycle, "write-09")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        dispatch = SqliteDispatchLedgerV2(self.root / "life-receipt-pending-ledger.db")
        thread, box = self.start_server(prepared, dispatch)
        with self.assertRaises((WireProtocolError, OSError)):
            client_exchange_once("127.0.0.1", prepared.port, self.request(nonce="write-09-nonce-000001"))
        outcome = self.join(thread, box)
        self.assertEqual(outcome["status"], "HOLD_LIFECYCLE_LEDGER_UNAVAILABLE")
        self.assertTrue(outcome["dispatch"]["completion_established"])
        self.assertFalse(outcome["lifecycle"]["wire_receipt_send_completed"])
        self.assertEqual(dispatch.count(), 1)
        with sqlite3.connect(str(dispatch.path)) as db:
            state = db.execute("SELECT state FROM nexus_dispatch_ledger_v2").fetchone()[0]
        self.assertEqual(state, "COMPLETED")
        self.assertEqual(len(self.calls), 1)

    def test_healthy_write_path_remains_clean_one_shot(self):
        lifecycle = FaultInjectingLifecycleLedger(self.root / "life-healthy.db")
        prepared = self.prepare(lifecycle, "write-10")
        self.assertIsInstance(prepared, PreparedLifecycleListener)
        dispatch = FaultInjectingDispatchLedger(self.root / "dispatch-healthy.db")
        thread, box = self.start_server(prepared, dispatch)
        receipt = client_exchange_once("127.0.0.1", prepared.port, self.request(nonce="write-10-nonce-000001"))
        outcome = self.join(thread, box)
        self.assertEqual(receipt["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED")
        self.assertEqual(outcome["status"], "CLOSED_CLEAN")
        self.assertTrue(outcome["dispatch"]["completion_established"])
        self.assertEqual(len(self.calls), 1)
        self.assertFalse(outcome["control"]["automatic_retry_permitted"])


if __name__ == "__main__":
    unittest.main()
