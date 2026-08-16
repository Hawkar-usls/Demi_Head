from __future__ import annotations

import sqlite3
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2  # noqa: E402
from nexus_local_transport import build_frame, sha256, validate_frame  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler  # noqa: E402
from nexus_loopback_dispatcher_v2 import dispatch_loopback_v2  # noqa: E402
from nexus_replay_ledger import MemoryReplayGuard  # noqa: E402


class NexusDispatchAdversarialHoldoutTests(unittest.TestCase):
    KEY = b"adversarial-loopback-v2-key"
    ISSUED = 1_800_000_000_000

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "dispatch-v2.db"
        # Initialize the database before concurrency/lock tests.
        SqliteDispatchLedgerV2(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def payload(self):
        return {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}

    def context(self):
        payload = self.payload()
        envelope = {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "dispatch-adversarial-v2",
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
        frame = build_frame(
            envelope,
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED,
            nonce="adversarial-v2-nonce-000001",
        )
        runtime_principal = {
            "key": self.KEY,
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        admission = validate_frame(
            frame,
            principal_lookup={"GUARDIAN_E1": runtime_principal},
            replay_guard=MemoryReplayGuard(),
            now_ms=self.ISSUED + 100,
        )
        public_principal = {
            "key_id": "GUARDIAN_E1",
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        catalog = {
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
        return frame, admission, public_principal, catalog, payload

    def handler(self, handler_id="RELEASE_CONTROL.ADVERSARIAL.V1", callback=None):
        callback = callback or (lambda payload: {"status": "ACK_LOCAL_ONLY", "input_sha256": sha256(payload)})
        return LocalHandler(handler_id=handler_id, target_head="RELEASE_CONTROL", callback=callback)

    def dispatch(self, ledger, handler, *, now_offset=200):
        frame, admission, principal, catalog, payload = self.context()
        return dispatch_loopback_v2(
            frame,
            admission,
            principal,
            catalog,
            payload,
            {"RELEASE_CONTROL": handler},
            dispatch_ledger=ledger,
            now_ms=self.ISSUED + now_offset,
        )

    def test_concurrent_duplicate_submissions_invoke_handler_exactly_once(self):
        calls = []
        lock = threading.Lock()
        barrier = threading.Barrier(8)

        def callback(payload):
            with lock:
                calls.append(sha256(payload))
            return {"status": "ACK", "input_sha256": sha256(payload)}

        handler = self.handler(callback=callback)

        def worker(_index):
            ledger = SqliteDispatchLedgerV2(self.db_path, busy_timeout_ms=2000)
            barrier.wait()
            return self.dispatch(ledger, handler)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(worker, range(8)))

        statuses = [result["status"] for result in results]
        self.assertEqual(statuses.count("LOOPBACK_DISPATCH_COMPLETED_LOCAL"), 1)
        self.assertEqual(statuses.count("HOLD_DUPLICATE_INTENT"), 7)
        self.assertEqual(len(calls), 1)
        self.assertEqual(SqliteDispatchLedgerV2(self.db_path).count(), 1)

    def test_started_state_survives_restart_and_blocks_reinvocation(self):
        frame, admission, principal, catalog, payload = self.context()
        handler = self.handler()
        from nexus_destination_acceptance_revalidation import accept_destination_revalidated
        from nexus_dispatch_ledger_v2 import dispatch_digest, intent_digest

        acceptance = accept_destination_revalidated(
            frame, admission, catalog["endpoints"][0], principal, now_ms=self.ISSUED + 200
        )
        intent_bindings = {
            "frame_sha256": sha256(frame),
            "acceptance_sha256": sha256(acceptance),
            "payload_sha256": sha256(payload),
            "target_head": "RELEASE_CONTROL",
        }
        intent = intent_digest(intent_bindings)
        dispatch = dispatch_digest(intent, handler.handler_id)
        first = SqliteDispatchLedgerV2(self.db_path)
        self.assertTrue(first.begin(
            intent_sha256=intent,
            dispatch_sha256=dispatch,
            intent_bindings=intent_bindings,
            handler_id=handler.handler_id,
            now_ms=self.ISSUED + 200,
        )["admitted"])
        result = self.dispatch(SqliteDispatchLedgerV2(self.db_path), handler, now_offset=300)
        self.assertEqual(result["status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(result["ledger"]["dispatch_state"], "STARTED")

    def test_handler_version_change_cannot_bypass_intent_guard(self):
        first_calls = []
        second_calls = []
        first = self.handler(
            handler_id="RELEASE_CONTROL.ADVERSARIAL.V1",
            callback=lambda payload: first_calls.append("v1") or {"status": "ACK", "hash": sha256(payload)},
        )
        second = self.handler(
            handler_id="RELEASE_CONTROL.ADVERSARIAL.V2",
            callback=lambda payload: second_calls.append("v2") or {"status": "ACK", "hash": sha256(payload)},
        )
        result1 = self.dispatch(SqliteDispatchLedgerV2(self.db_path), first, now_offset=200)
        result2 = self.dispatch(SqliteDispatchLedgerV2(self.db_path), second, now_offset=300)
        self.assertEqual(result1["status"], "LOOPBACK_DISPATCH_COMPLETED_LOCAL")
        self.assertEqual(result2["status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(first_calls, ["v1"])
        self.assertEqual(second_calls, [])

    def test_completion_write_failure_leaves_started_and_blocks_second_attempt(self):
        calls = []

        class CompletionFailLedger(SqliteDispatchLedgerV2):
            def complete(self, dispatch_sha256, *, result_sha256, now_ms):
                raise sqlite3.OperationalError("synthetic completion write failure")

        handler = self.handler(callback=lambda payload: calls.append("invoked") or {"status": "ACK", "hash": sha256(payload)})
        first = self.dispatch(CompletionFailLedger(self.db_path), handler, now_offset=200)
        second = self.dispatch(SqliteDispatchLedgerV2(self.db_path), handler, now_offset=300)
        self.assertEqual(first["status"], "HOLD_LEDGER_FINALIZATION_FAILURE")
        self.assertEqual(first["ledger"]["dispatch_state"], "STARTED")
        self.assertEqual(second["status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(calls, ["invoked"])
        self.assertFalse(first["control"]["automatic_retry_permitted"])

    def test_real_sqlite_lock_contention_holds_before_handler(self):
        calls = []
        ledger = SqliteDispatchLedgerV2(self.db_path, busy_timeout_ms=20)
        blocker = sqlite3.connect(str(self.db_path), timeout=1.0, isolation_level=None)
        try:
            blocker.execute("PRAGMA journal_mode=WAL")
            blocker.execute("BEGIN IMMEDIATE")
            result = self.dispatch(
                ledger,
                self.handler(callback=lambda payload: calls.append("invoked") or {"status": "ACK"}),
                now_offset=200,
            )
        finally:
            try:
                blocker.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            blocker.close()
        self.assertEqual(result["status"], "HOLD_LEDGER_UNAVAILABLE")
        self.assertEqual(calls, [])
        self.assertFalse(result["control"]["automatic_retry_permitted"])

    def test_corrupt_database_fails_closed_during_ledger_initialization(self):
        corrupt = self.root / "corrupt.db"
        corrupt.write_bytes(b"JANUS-NOT-A-SQLITE-DATABASE")
        with self.assertRaises(sqlite3.DatabaseError):
            SqliteDispatchLedgerV2(corrupt, busy_timeout_ms=20)

    def test_unavailable_storage_path_fails_closed(self):
        parent_file = self.root / "not-a-directory"
        parent_file.write_text("occupied", encoding="utf-8")
        with self.assertRaises((FileExistsError, NotADirectoryError, OSError)):
            SqliteDispatchLedgerV2(parent_file / "dispatch.db")

    def test_handler_exception_is_failed_ambiguous_and_not_reinvoked(self):
        calls = []

        def explode(_payload):
            calls.append("attempt")
            raise RuntimeError("synthetic partial work")

        handler = self.handler(callback=explode)
        first = self.dispatch(SqliteDispatchLedgerV2(self.db_path), handler, now_offset=200)
        second = self.dispatch(SqliteDispatchLedgerV2(self.db_path), handler, now_offset=300)
        self.assertEqual(first["status"], "HOLD_HANDLER_FAILURE")
        self.assertEqual(first["ledger"]["dispatch_state"], "FAILED_AMBIGUOUS")
        self.assertEqual(second["status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(calls, ["attempt"])


if __name__ == "__main__":
    unittest.main()
