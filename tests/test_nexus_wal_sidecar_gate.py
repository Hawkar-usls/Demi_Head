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
from nexus_storage_fault_gate import _inspect_main_db_envelope  # noqa: E402
from nexus_wal_sidecar_gate import (  # noqa: E402
    WAL_FORMAT_VERSION,
    WAL_MAGIC,
    inspect_wal_sidecar,
    preflight_evidence_stores_with_wal,
    wal_guarded_recovery,
)


class NexusPhysicalWalSidecarTests(unittest.TestCase):
    NOW = 1_800_000_050_000
    SERVICE = "DEMIHEAD.NEXUS.WAL.TEST"
    INSTANCE = "wal-instance-001"
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
                    detail_code=f"WAL_TEST_{lifecycle_phase}",
                )
        return lifecycle, dispatch, replay

    def remove_checkpointed_sidecars(self):
        for path in (self.lifecycle_path, self.dispatch_path, self.replay_path):
            with sqlite3.connect(str(path)) as db:
                db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()

    def page_size(self, db_path: Path) -> int:
        envelope = _inspect_main_db_envelope(db_path)
        self.assertTrue(envelope["valid"])
        return int(envelope["page_size"])

    def write_synthetic_wal(self, db_path: Path, *, magic: int | None = None,
                            version: int = WAL_FORMAT_VERSION, page_size: int | None = None,
                            frames: int = 1, trailing_bytes: bytes = b"", page_number: int = 1):
        target = Path(str(db_path) + "-wal")
        ps = page_size or self.page_size(db_path)
        selected_magic = next(iter(WAL_MAGIC)) if magic is None else magic
        header = (
            selected_magic.to_bytes(4, "big")
            + version.to_bytes(4, "big")
            + ps.to_bytes(4, "big")
            + (0).to_bytes(4, "big")
            + (1).to_bytes(4, "big")
            + (2).to_bytes(4, "big")
            + (0).to_bytes(4, "big")
            + (0).to_bytes(4, "big")
        )
        payload = bytearray(header)
        for _ in range(frames):
            frame_header = (
                int(page_number).to_bytes(4, "big")
                + (0).to_bytes(4, "big")
                + (1).to_bytes(4, "big")
                + (2).to_bytes(4, "big")
                + (0).to_bytes(4, "big")
                + (0).to_bytes(4, "big")
            )
            payload.extend(frame_header)
            payload.extend(b"\x00" * ps)
        payload.extend(trailing_bytes)
        target.write_bytes(bytes(payload))
        return target

    def test_frozen_manifest_hash_and_case_count(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_wal_sidecar_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "e8b1b689525ae09ed95f631ae2aa89514d794acd4761bebb036ab98b3e07dfc3")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 8)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])

    def test_checkpointed_absent_wal_is_permitted(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        receipt = preflight_evidence_stores_with_wal(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=self.replay_path,
        )
        self.assertEqual(receipt["status"], "WAL_STORAGE_PREFLIGHT_PASS")
        for item in receipt["wal_sidecars"].values():
            self.assertEqual(item["status"], "ABSENT_CHECKPOINTED_STATE_PERMITTED")
            self.assertTrue(item["healthy"])

    def test_real_sqlite_wal_physical_envelope_passes(self):
        self.seed_healthy(lifecycle_phase="LISTENER_BOUND")
        keeper = sqlite3.connect(str(self.lifecycle_path), isolation_level=None)
        try:
            keeper.execute("PRAGMA journal_mode=WAL")
            keeper.execute("PRAGMA wal_autocheckpoint=0")
            keeper.execute("BEGIN IMMEDIATE")
            keeper.execute(
                "INSERT INTO nexus_one_shot_lifecycle_events (service_id, instance_id, phase, recorded_at_ms, detail_code) VALUES (?, ?, ?, ?, ?)",
                (self.SERVICE, self.INSTANCE, "REAL_WAL_TEST", self.NOW + 10, "KEEP_WAL_UNCHECKPOINTED"),
            )
            keeper.execute("COMMIT")
            wal = Path(str(self.lifecycle_path) + "-wal")
            self.assertTrue(wal.exists())
            receipt = inspect_wal_sidecar(self.lifecycle_path)
            self.assertEqual(receipt["status"], "WAL_SIDECAR_HEALTHY")
            self.assertTrue(receipt["healthy"])
            self.assertGreaterEqual(receipt["frame_count"], 1)
            self.assertTrue(receipt["bytes_unchanged"])
            self.assertFalse(receipt["checksum_chain_verified"])
        finally:
            keeper.close()

    def test_corrupt_wal_magic_holds(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        wal = self.write_synthetic_wal(self.lifecycle_path, magic=0xDEADBEEF)
        before = wal.read_bytes()
        receipt = inspect_wal_sidecar(self.lifecycle_path)
        self.assertEqual(receipt["status"], "WAL_PHYSICAL_ENVELOPE_FAIL")
        self.assertEqual(receipt["reason"], "WAL_MAGIC_MISMATCH")
        self.assertEqual(wal.read_bytes(), before)

    def test_truncated_wal_header_holds(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        wal = Path(str(self.lifecycle_path) + "-wal")
        wal.write_bytes(b"\x37\x7f\x06\x82" + b"\x00" * 12)
        before = wal.read_bytes()
        receipt = inspect_wal_sidecar(self.lifecycle_path)
        self.assertEqual(receipt["status"], "WAL_PHYSICAL_ENVELOPE_FAIL")
        self.assertEqual(receipt["reason"], "WAL_TRUNCATED_BELOW_HEADER")
        self.assertEqual(wal.read_bytes(), before)

    def test_invalid_wal_page_size_holds(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        self.write_synthetic_wal(self.lifecycle_path, page_size=1234, frames=0)
        receipt = inspect_wal_sidecar(self.lifecycle_path)
        self.assertEqual(receipt["status"], "WAL_PHYSICAL_ENVELOPE_FAIL")
        self.assertEqual(receipt["reason"], "WAL_INVALID_PAGE_SIZE")

    def test_incomplete_wal_frame_alignment_holds(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        self.write_synthetic_wal(self.lifecycle_path, frames=1, trailing_bytes=b"TRUNCATED")
        receipt = inspect_wal_sidecar(self.lifecycle_path)
        self.assertEqual(receipt["status"], "WAL_PHYSICAL_ENVELOPE_FAIL")
        self.assertEqual(receipt["reason"], "WAL_FRAME_ALIGNMENT_MISMATCH")

    def test_wal_main_page_size_mismatch_holds(self):
        self.seed_healthy()
        self.remove_checkpointed_sidecars()
        main_page = self.page_size(self.lifecycle_path)
        mismatch = 8192 if main_page != 8192 else 4096
        self.write_synthetic_wal(self.lifecycle_path, page_size=mismatch, frames=0)
        receipt = inspect_wal_sidecar(self.lifecycle_path)
        self.assertEqual(receipt["status"], "WAL_PHYSICAL_ENVELOPE_FAIL")
        self.assertEqual(receipt["reason"], "WAL_MAIN_PAGE_SIZE_MISMATCH")

    def test_damaged_replay_wal_blocks_otherwise_recoverable_lifecycle(self):
        self.seed_healthy(lifecycle_phase="LISTENER_BOUND")
        self.remove_checkpointed_sidecars()
        wal = self.write_synthetic_wal(self.replay_path, magic=0x11111111)
        before = wal.read_bytes()
        receipt = wal_guarded_recovery(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=self.replay_path,
            service_id=self.SERVICE,
            expected_instance_id=self.INSTANCE,
            operator_ack=True,
            process_dead_attested=True,
            now_ms=self.NOW + 100,
        )
        self.assertEqual(receipt["status"], "HOLD_WAL_EVIDENCE_UNAVAILABLE")
        self.assertTrue(receipt["wal_gate_blocked_recovery_mutation"])
        self.assertEqual(SqliteLifecycleLedger(self.lifecycle_path).state(self.SERVICE)["phase"], "LISTENER_BOUND")
        self.assertEqual(wal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
