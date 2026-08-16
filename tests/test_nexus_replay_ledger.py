from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_replay_ledger import MemoryReplayGuard, SqliteReplayGuard, replay_digest, self_test  # noqa: E402


class NexusReplayLedgerTests(unittest.TestCase):
    NOW = 1_800_000_000_000
    REPLAY_KEY = "DEMIHEAD.GUARDIAN:KEY:nonce-001"

    def test_memory_guard_rejects_replay_until_expiry(self):
        guard = MemoryReplayGuard()
        self.assertTrue(guard.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 1000, now_ms=self.NOW))
        self.assertFalse(guard.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 1000, now_ms=self.NOW + 1))
        self.assertTrue(guard.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 2000, now_ms=self.NOW + 1001))

    def test_sqlite_guard_persists_hashed_replay_key_across_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "replay.db"
            first = SqliteReplayGuard(path)
            self.assertTrue(first.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 30_000, now_ms=self.NOW))

            second = SqliteReplayGuard(path)
            self.assertFalse(second.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 30_000, now_ms=self.NOW + 1))

            with sqlite3.connect(path) as db:
                row = db.execute("SELECT replay_sha256 FROM nexus_replay_ledger").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row[0], replay_digest(self.REPLAY_KEY))
            self.assertNotEqual(row[0], self.REPLAY_KEY)

    def test_sqlite_expiry_prunes_and_allows_fresh_epoch(self):
        with tempfile.TemporaryDirectory() as directory:
            guard = SqliteReplayGuard(Path(directory) / "replay.db")
            self.assertTrue(guard.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 1000, now_ms=self.NOW))
            self.assertEqual(guard.count_active(now_ms=self.NOW + 1001), 0)
            self.assertTrue(guard.consume(self.REPLAY_KEY, expires_at_ms=self.NOW + 2000, now_ms=self.NOW + 1001))

    def test_expired_key_cannot_be_consumed(self):
        with self.assertRaises(ValueError):
            MemoryReplayGuard().consume(self.REPLAY_KEY, expires_at_ms=self.NOW, now_ms=self.NOW)

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
