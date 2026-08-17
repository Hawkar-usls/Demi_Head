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
from nexus_wal_checksum_gate import (  # noqa: E402
    WAL_MAGIC_BIG_CHECKSUM_WORDS,
    inspect_wal_checksum_salt_chain,
    wal_integrity_guarded_recovery,
)
from nexus_wal_sidecar_gate import WAL_FORMAT_VERSION, inspect_wal_sidecar  # noqa: E402


class NexusWalChecksumSaltChainTests(unittest.TestCase):
    NOW = 1_800_000_060_000
    SERVICE = "DEMIHEAD.NEXUS.WALCHECK.TEST"
    INSTANCE = "walcheck-instance-001"
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
                    detail_code=f"WALCHECK_TEST_{lifecycle_phase}",
                )
        return lifecycle, dispatch, replay

    def open_real_lifecycle_wal(self, *, transactions: int = 3):
        self.seed_healthy()
        keeper = sqlite3.connect(str(self.lifecycle_path), isolation_level=None)
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        for index in range(transactions):
            keeper.execute("BEGIN IMMEDIATE")
            keeper.execute(
                "INSERT INTO nexus_one_shot_lifecycle_events (service_id, instance_id, phase, recorded_at_ms, detail_code) VALUES (?, ?, ?, ?, ?)",
                (self.SERVICE, self.INSTANCE, f"CHECKSUM_TX_{index}", self.NOW + 10 + index, "KEEP_REAL_WAL"),
            )
            keeper.execute("COMMIT")
        wal = Path(str(self.lifecycle_path) + "-wal")
        self.assertTrue(wal.exists())
        return keeper

    def copy_active_pair(self, source_db: Path, destination_name: str) -> Path:
        destination = self.root / destination_name
        destination.write_bytes(source_db.read_bytes())
        source_wal = Path(str(source_db) + "-wal")
        self.assertTrue(source_wal.exists())
        Path(str(destination) + "-wal").write_bytes(source_wal.read_bytes())
        return destination

    @staticmethod
    def flip(path: Path, offset: int):
        data = bytearray(path.read_bytes())
        if not 0 <= offset < len(data):
            raise AssertionError(f"offset {offset} outside file of {len(data)} bytes")
        data[offset] ^= 0x01
        path.write_bytes(bytes(data))

    def test_frozen_manifest_hash_and_case_count(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_wal_checksum_salt_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "a5928133096948447895e0001fb5705d6a4225f5413ea5438f4a333382236b39")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 8)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])

    def test_real_sqlite_wal_passes_header_frame_checksum_and_salt_chain(self):
        keeper = self.open_real_lifecycle_wal(transactions=3)
        try:
            receipt = inspect_wal_checksum_salt_chain(self.lifecycle_path)
            self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_HEALTHY")
            self.assertTrue(receipt["header_checksum_verified"])
            self.assertTrue(receipt["salt_chain_verified"])
            self.assertTrue(receipt["frame_checksum_chain_verified"])
            self.assertGreaterEqual(receipt["verified_frame_count"], 2)
            self.assertTrue(receipt["bytes_unchanged"])
        finally:
            keeper.close()

    def test_corrupt_header_checksum_is_rejected_without_repair(self):
        keeper = self.open_real_lifecycle_wal()
        try:
            copy = self.copy_active_pair(self.lifecycle_path, "header-checksum.db")
        finally:
            keeper.close()
        wal = Path(str(copy) + "-wal")
        self.flip(wal, 24)
        before = wal.read_bytes()
        receipt = inspect_wal_checksum_salt_chain(copy)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_FAIL")
        self.assertEqual(receipt["reason"], "WAL_HEADER_CHECKSUM_MISMATCH")
        self.assertEqual(wal.read_bytes(), before)

    def test_frame_salt_mismatch_is_rejected(self):
        keeper = self.open_real_lifecycle_wal()
        try:
            copy = self.copy_active_pair(self.lifecycle_path, "salt-mismatch.db")
        finally:
            keeper.close()
        wal = Path(str(copy) + "-wal")
        self.flip(wal, 32 + 8)
        receipt = inspect_wal_checksum_salt_chain(copy)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_FAIL")
        self.assertEqual(receipt["reason"], "WAL_FRAME_SALT_MISMATCH")
        self.assertEqual(receipt["failed_frame_index"], 1)

    def test_stored_frame_checksum_mismatch_is_rejected(self):
        keeper = self.open_real_lifecycle_wal()
        try:
            copy = self.copy_active_pair(self.lifecycle_path, "stored-frame-checksum.db")
        finally:
            keeper.close()
        wal = Path(str(copy) + "-wal")
        self.flip(wal, 32 + 16)
        receipt = inspect_wal_checksum_salt_chain(copy)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_FAIL")
        self.assertEqual(receipt["reason"], "WAL_FRAME_CHECKSUM_MISMATCH")
        self.assertEqual(receipt["failed_frame_index"], 1)

    def test_page_body_corruption_breaks_cumulative_checksum(self):
        keeper = self.open_real_lifecycle_wal()
        try:
            copy = self.copy_active_pair(self.lifecycle_path, "page-corruption.db")
        finally:
            keeper.close()
        wal = Path(str(copy) + "-wal")
        self.flip(wal, 32 + 24 + 7)
        receipt = inspect_wal_checksum_salt_chain(copy)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_FAIL")
        self.assertEqual(receipt["reason"], "WAL_FRAME_CHECKSUM_MISMATCH")
        self.assertEqual(receipt["failed_frame_index"], 1)

    def test_synthetic_big_endian_checksum_magic_vector_passes_known_checksums(self):
        db = self.root / "big-checksum-vector.db"
        main = bytearray(4096)
        main[:16] = b"SQLite format 3\x00"
        main[16:18] = (4096).to_bytes(2, "big")
        db.write_bytes(bytes(main))

        magic = WAL_MAGIC_BIG_CHECKSUM_WORDS
        first24 = (
            magic.to_bytes(4, "big")
            + WAL_FORMAT_VERSION.to_bytes(4, "big")
            + (4096).to_bytes(4, "big")
            + (0).to_bytes(4, "big")
            + (0x11223344).to_bytes(4, "big")
            + (0x55667788).to_bytes(4, "big")
        )
        # Independently frozen vector generated from the SQLite published recurrence.
        header_checksum = (656874011, 593918300)
        frame_checksum = (2599180039, 3840816585)
        header = first24 + header_checksum[0].to_bytes(4, "big") + header_checksum[1].to_bytes(4, "big")
        frame_first8 = (1).to_bytes(4, "big") + (1).to_bytes(4, "big")
        frame = (
            frame_first8
            + first24[16:24]
            + frame_checksum[0].to_bytes(4, "big")
            + frame_checksum[1].to_bytes(4, "big")
            + bytes(4096)
        )
        Path(str(db) + "-wal").write_bytes(header + frame)
        physical = inspect_wal_sidecar(db)
        self.assertEqual(physical["status"], "WAL_SIDECAR_HEALTHY")
        receipt = inspect_wal_checksum_salt_chain(db)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_HEALTHY")
        self.assertEqual(receipt["checksum_word_byteorder"], "big")
        self.assertEqual(receipt["verified_frame_count"], 1)

    def test_second_frame_cumulative_chain_corruption_is_rejected_at_second_frame(self):
        keeper = self.open_real_lifecycle_wal(transactions=4)
        try:
            copy = self.copy_active_pair(self.lifecycle_path, "second-frame-chain.db")
        finally:
            keeper.close()
        physical = inspect_wal_sidecar(copy)
        self.assertGreaterEqual(physical["frame_count"], 2)
        frame_size = 24 + int(physical["page_size"])
        wal = Path(str(copy) + "-wal")
        self.flip(wal, 32 + frame_size + 16)
        receipt = inspect_wal_checksum_salt_chain(copy)
        self.assertEqual(receipt["status"], "WAL_CHECKSUM_SALT_CHAIN_FAIL")
        self.assertEqual(receipt["reason"], "WAL_FRAME_CHECKSUM_MISMATCH")
        self.assertEqual(receipt["failed_frame_index"], 2)

    def test_damaged_replay_wal_checksum_blocks_otherwise_recoverable_lifecycle(self):
        self.seed_healthy(lifecycle_phase="LISTENER_BOUND")

        source_replay = self.root / "source-replay.db"
        SqliteReplayGuard(source_replay)
        keeper = sqlite3.connect(str(source_replay), isolation_level=None)
        keeper.execute("PRAGMA journal_mode=WAL")
        keeper.execute("PRAGMA wal_autocheckpoint=0")
        keeper.execute("BEGIN IMMEDIATE")
        keeper.execute(
            "INSERT INTO nexus_replay_ledger (replay_sha256, expires_at_ms, recorded_at_ms) VALUES (?, ?, ?)",
            ("b" * 64, self.NOW + 60_000, self.NOW),
        )
        keeper.execute("COMMIT")
        try:
            replay_copy = self.copy_active_pair(source_replay, "replay-corrupt-copy.db")
        finally:
            keeper.close()
        replay_wal = Path(str(replay_copy) + "-wal")
        self.flip(replay_wal, 32 + 24 + 3)
        before = replay_wal.read_bytes()

        receipt = wal_integrity_guarded_recovery(
            lifecycle_db=self.lifecycle_path,
            dispatch_db=self.dispatch_path,
            replay_db=replay_copy,
            service_id=self.SERVICE,
            expected_instance_id=self.INSTANCE,
            operator_ack=True,
            process_dead_attested=True,
            now_ms=self.NOW + 100,
        )
        self.assertEqual(receipt["status"], "HOLD_WAL_INTEGRITY_UNAVAILABLE")
        self.assertTrue(receipt["wal_integrity_gate_blocked_recovery_mutation"])
        self.assertEqual(SqliteLifecycleLedger(self.lifecycle_path).state(self.SERVICE)["phase"], "LISTENER_BOUND")
        self.assertEqual(replay_wal.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
