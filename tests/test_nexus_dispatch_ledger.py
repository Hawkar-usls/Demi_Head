from __future__ import annotations

import tempfile
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger import SqliteDispatchLedger, dispatch_digest, self_test  # noqa: E402


class NexusDispatchLedgerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "dispatch.db"
        self.now = 1_800_000_000_000
        self.bindings = {
            "frame_sha256": "1" * 64,
            "acceptance_sha256": "2" * 64,
            "payload_sha256": "3" * 64,
            "handler_id": "RELEASE_CONTROL.UNIT.V1",
        }
        self.dispatch_sha = dispatch_digest(self.bindings)

    def tearDown(self):
        self.temp.cleanup()

    def test_started_record_survives_restart_and_blocks_duplicate(self):
        first = SqliteDispatchLedger(self.path)
        admitted = first.begin(self.dispatch_sha, bindings=self.bindings, now_ms=self.now)
        self.assertTrue(admitted["admitted"])
        restarted = SqliteDispatchLedger(self.path)
        duplicate = restarted.begin(self.dispatch_sha, bindings=self.bindings, now_ms=self.now + 1)
        self.assertFalse(duplicate["admitted"])
        self.assertEqual(duplicate["existing"]["state"], "STARTED")

    def test_completion_survives_restart(self):
        ledger = SqliteDispatchLedger(self.path)
        ledger.begin(self.dispatch_sha, bindings=self.bindings, now_ms=self.now)
        self.assertTrue(ledger.complete(self.dispatch_sha, result_sha256="4" * 64, now_ms=self.now + 1))
        entry = SqliteDispatchLedger(self.path).get(self.dispatch_sha)
        self.assertEqual(entry["state"], "COMPLETED")
        self.assertEqual(entry["result_sha256"], "4" * 64)
        self.assertFalse(entry["control"]["automatic_retry_permitted"])

    def test_ambiguous_failure_survives_restart_and_cannot_complete_later(self):
        ledger = SqliteDispatchLedger(self.path)
        ledger.begin(self.dispatch_sha, bindings=self.bindings, now_ms=self.now)
        self.assertTrue(ledger.fail_ambiguous(self.dispatch_sha, failure_code="HANDLER_EXCEPTION", now_ms=self.now + 1))
        restarted = SqliteDispatchLedger(self.path)
        entry = restarted.get(self.dispatch_sha)
        self.assertEqual(entry["state"], "FAILED_AMBIGUOUS")
        self.assertFalse(restarted.complete(self.dispatch_sha, result_sha256="4" * 64, now_ms=self.now + 2))
        duplicate = restarted.begin(self.dispatch_sha, bindings=self.bindings, now_ms=self.now + 3)
        self.assertFalse(duplicate["admitted"])
        self.assertEqual(duplicate["existing"]["state"], "FAILED_AMBIGUOUS")

    def test_dispatch_key_binds_acceptance_payload_frame_and_handler(self):
        base = dispatch_digest(self.bindings)
        for field, value in (
            ("frame_sha256", "a" * 64),
            ("acceptance_sha256", "b" * 64),
            ("payload_sha256", "c" * 64),
            ("handler_id", "OTHER.HANDLER.V1"),
        ):
            changed = dict(self.bindings)
            changed[field] = value
            self.assertNotEqual(base, dispatch_digest(changed))

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
