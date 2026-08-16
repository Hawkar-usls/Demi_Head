from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2  # noqa: E402
from nexus_loopback_lifecycle_gate import SqliteLifecycleLedger  # noqa: E402
from nexus_replay_ledger import SqliteReplayGuard  # noqa: E402
from nexus_storage_fault_gate import preflight_evidence_stores, storage_guarded_recovery  # noqa: E402


class NexusStorageFaultGateTests(unittest.TestCase):
    NOW = 1_800_000_030_000
    SERVICE = "DEMIHEAD.NEXUS.STORAGE.TEST"
    INSTANCE = "storage-instance-001"
    FRAME = "a" * 64

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lifecycle_path = self.root / "lifecycle.db"
        self.dispatch_path = self.root / "dispatch.db"
        self.replay_path = self.root / "replay.db"

    def tearDown(self):
        self.temp.cleanup()

    def seed_healthy(self, *, lifecycle_phase: str | None = None):
        lifecycle = SqliteLifecycleLedger(self.lifecycle_path)
        dispatch = SqliteDispatchLedgerV2(self.dispatch_path)
        replay = SqliteReplayGuard(self.replay_path)
        if lifecycle_phase is not None:
            begin = lifecycle.begin(self.SERVICE, self.INSTANCE, now_ms=self.NOW)
            self.assertTrue(begin["admitted"])
            if lifecycle_phase != "STARTING":
                lifecycle.transition(
                    self.SERVICE,
                    self.INSTANCE,
                    lifecycle_phase,
                    now_ms=self.NOW + 1,
                    frame_sha256=self.FRAME,
                    detail_code=f"STORAGE_TEST_{lifecycle_phase}",
                )
        return lifecycle, dispatch, replay

    @staticmethod
    def sha(path: Path) -> str:
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def preflight(self):
        return preflight_evidence_stores(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=self.replay_path,
        )

    def test_frozen_manifest_hash_and_case_count(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_storage_fault_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "1e7939a1572d7b91fc9711041153b1ad1f32be496f92015287d979ef44662046")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 10)
        self.assertFalse(corpus["freeze_payload"]["invariants"]["missing_store_auto_creation"])

    def test_healthy_stores_pass_read_only_integrity_and_schema_preflight(self):
        self.seed_healthy()
        before = {p.name: self.sha(p) for p in (self.lifecycle_path, self.dispatch_path, self.replay_path)}
        receipt = self.preflight()
        after = {p.name: self.sha(p) for p in (self.lifecycle_path, self.dispatch_path, self.replay_path)}
        self.assertEqual(receipt["status"], "STORAGE_PREFLIGHT_PASS")
        self.assertEqual(before, after)
        for store in receipt["stores"].values():
            self.assertTrue(store["healthy"])
            self.assertTrue(store["bytes_unchanged"])
            self.assertTrue(store["read_only_preflight"])
            self.assertFalse(store["mutation_performed"])

    def test_missing_lifecycle_store_holds_without_creating_it(self):
        SqliteDispatchLedgerV2(self.dispatch_path)
        SqliteReplayGuard(self.replay_path)
        self.assertFalse(self.lifecycle_path.exists())
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertEqual(receipt["stores"]["lifecycle"]["status"], "MISSING")
        self.assertFalse(self.lifecycle_path.exists())

    def test_corrupt_lifecycle_store_holds_without_replacement(self):
        self.seed_healthy()
        self.lifecycle_path.write_bytes(b"JANUS-CORRUPT-LIFECYCLE\x00\xff" * 32)
        before = self.lifecycle_path.read_bytes()
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertFalse(receipt["stores"]["lifecycle"]["healthy"])
        self.assertEqual(self.lifecycle_path.read_bytes(), before)

    def test_truncated_lifecycle_store_holds_without_replacement(self):
        self.seed_healthy()
        original = self.lifecycle_path.read_bytes()
        self.assertGreater(len(original), 256)
        self.lifecycle_path.write_bytes(original[:128])
        before = self.lifecycle_path.read_bytes()
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertFalse(receipt["stores"]["lifecycle"]["healthy"])
        self.assertEqual(self.lifecycle_path.read_bytes(), before)

    def test_missing_dispatch_store_holds_without_creation(self):
        SqliteLifecycleLedger(self.lifecycle_path)
        SqliteReplayGuard(self.replay_path)
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertEqual(receipt["stores"]["dispatch"]["status"], "MISSING")
        self.assertFalse(self.dispatch_path.exists())

    def test_corrupt_dispatch_store_holds_without_replacement(self):
        self.seed_healthy()
        self.dispatch_path.write_bytes(b"NOT-A-SQLITE-DISPATCH-LEDGER" * 40)
        before = self.dispatch_path.read_bytes()
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertFalse(receipt["stores"]["dispatch"]["healthy"])
        self.assertEqual(self.dispatch_path.read_bytes(), before)

    def test_missing_replay_store_holds_without_creation(self):
        SqliteLifecycleLedger(self.lifecycle_path)
        SqliteDispatchLedgerV2(self.dispatch_path)
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertEqual(receipt["stores"]["replay"]["status"], "MISSING")
        self.assertFalse(self.replay_path.exists())

    def test_corrupt_replay_store_holds_without_replacement(self):
        self.seed_healthy()
        self.replay_path.write_bytes(b"REPLAY-EVIDENCE-CORRUPTED" * 48)
        before = self.replay_path.read_bytes()
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertFalse(receipt["stores"]["replay"]["healthy"])
        self.assertEqual(self.replay_path.read_bytes(), before)

    def test_valid_sqlite_with_wrong_schema_holds_without_auto_migration(self):
        self.seed_healthy()
        self.dispatch_path.unlink()
        with sqlite3.connect(self.dispatch_path) as db:
            db.execute("CREATE TABLE unrelated_table (id INTEGER PRIMARY KEY)")
            db.commit()
        before = self.sha(self.dispatch_path)
        receipt = self.preflight()
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertEqual(receipt["stores"]["dispatch"]["status"], "SCHEMA_MISMATCH")
        self.assertIn("nexus_dispatch_ledger_v2", receipt["stores"]["dispatch"]["missing_required_tables"])
        self.assertEqual(self.sha(self.dispatch_path), before)
        with sqlite3.connect(f"file:{self.dispatch_path}?mode=ro", uri=True) as db:
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("nexus_dispatch_ledger_v2", tables)

    def test_storage_guarded_recovery_runs_only_after_all_three_stores_pass(self):
        self.seed_healthy(lifecycle_phase="LISTENER_BOUND")
        receipt = storage_guarded_recovery(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=self.replay_path,
            service_id=self.SERVICE,
            expected_instance_id=self.INSTANCE,
            operator_ack=True,
            process_dead_attested=True,
            now_ms=self.NOW + 100,
        )
        self.assertEqual(receipt["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")
        self.assertEqual(receipt["recovery"]["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")
        self.assertFalse(receipt["storage_gate_blocked_recovery_mutation"])
        self.assertEqual(SqliteLifecycleLedger(self.lifecycle_path).state(self.SERVICE)["phase"], "CLOSED_CLEAN")

    def test_corrupt_replay_store_blocks_otherwise_recoverable_lifecycle_without_mutation(self):
        self.seed_healthy(lifecycle_phase="LISTENER_BOUND")
        self.replay_path.write_bytes(b"BROKEN-REPLAY-STORE" * 64)
        receipt = storage_guarded_recovery(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=self.replay_path,
            service_id=self.SERVICE,
            expected_instance_id=self.INSTANCE,
            operator_ack=True,
            process_dead_attested=True,
            now_ms=self.NOW + 100,
        )
        self.assertEqual(receipt["status"], "HOLD_STORAGE_EVIDENCE_UNAVAILABLE")
        self.assertTrue(receipt["storage_gate_blocked_recovery_mutation"])
        state = SqliteLifecycleLedger(self.lifecycle_path).state(self.SERVICE)
        self.assertEqual(state["phase"], "LISTENER_BOUND")


if __name__ == "__main__":
    unittest.main()
