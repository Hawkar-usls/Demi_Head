from __future__ import annotations

import hashlib
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2  # noqa: E402
from nexus_loopback_lifecycle_gate import SqliteLifecycleLedger  # noqa: E402


@unittest.skipUnless(os.name == "posix", "real kill holdout is frozen for POSIX CI semantics")
class NexusRealSubprocessTerminationTests(unittest.TestCase):
    NOW = 1_800_000_020_000

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.probe = ROOT / "tools" / "nexus_crash_probe.py"
        self.recovery = ROOT / "tools" / "nexus_lifecycle_recovery.py"

    def tearDown(self):
        self.temp.cleanup()

    def wait_marker(self, marker: Path, proc: subprocess.Popen, timeout: float = 5.0) -> dict:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if marker.exists():
                return json.loads(marker.read_text(encoding="utf-8"))
            if proc.poll() is not None:
                stdout, stderr = proc.communicate(timeout=1)
                self.fail(f"probe exited before marker: rc={proc.returncode} stdout={stdout!r} stderr={stderr!r}")
            time.sleep(0.02)
        proc.kill()
        proc.wait(timeout=2)
        self.fail("probe did not publish durable phase marker")

    def launch_and_kill(self, *, case_id: str, phase: str, dispatch_evidence: str = "NONE", real_loopback_bind: bool = False):
        case_root = self.root / case_id
        case_root.mkdir()
        lifecycle_db = case_root / "lifecycle.db"
        dispatch_db = case_root / "dispatch.db"
        marker = case_root / "ready.json"
        service = f"DEMIHEAD.NEXUS.REAL_KILL.{case_id}"
        instance = f"instance-{case_id}"
        cmd = [
            sys.executable,
            str(self.probe),
            "--lifecycle-db", str(lifecycle_db),
            "--dispatch-db", str(dispatch_db),
            "--service-id", service,
            "--instance-id", instance,
            "--phase", phase,
            "--marker", str(marker),
            "--dispatch-evidence", dispatch_evidence,
            "--now-ms", str(self.NOW),
        ]
        if real_loopback_bind:
            cmd.append("--real-loopback-bind")
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        marker_payload = self.wait_marker(marker, proc)
        self.assertTrue(marker_payload["ready_for_parent_termination"])
        self.assertEqual(marker_payload["phase"], phase)
        proc.kill()
        proc.wait(timeout=3)
        self.assertLess(proc.returncode, 0)
        state = SqliteLifecycleLedger(lifecycle_db).state(service)
        self.assertIsNotNone(state)
        self.assertEqual(state["phase"], phase)
        return {
            "root": case_root,
            "lifecycle_db": lifecycle_db,
            "dispatch_db": dispatch_db,
            "marker": marker_payload,
            "service": service,
            "instance": instance,
            "state_after_kill": state,
        }

    def recover_in_second_process(self, case: dict) -> dict:
        completed = subprocess.run(
            [
                sys.executable,
                str(self.recovery),
                "--lifecycle-db", str(case["lifecycle_db"]),
                "--dispatch-db", str(case["dispatch_db"]),
                "--service-id", case["service"],
                "--expected-instance-id", case["instance"],
                "--operator-ack",
                "--process-dead-attested",
                "--now-ms", str(self.NOW + 1000),
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        return json.loads(completed.stdout)

    def test_frozen_real_kill_manifest_hash(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_real_subprocess_termination_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "0b815e6864bedcba152add9c17861cb30115f24d772ce3a01b3613868ec9f159")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 5)

    def test_real_kill_at_starting_survives_and_second_process_recovers_clean(self):
        case = self.launch_and_kill(case_id="KILL-01", phase="STARTING")
        receipt = self.recover_in_second_process(case)
        self.assertEqual(receipt["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")
        self.assertEqual(SqliteLifecycleLedger(case["lifecycle_db"]).state(case["service"])["phase"], "CLOSED_CLEAN")

    def test_real_kill_with_actual_loopback_listener_releases_socket_and_recovers(self):
        case = self.launch_and_kill(case_id="KILL-02", phase="LISTENER_BOUND", real_loopback_bind=True)
        port = case["marker"]["bound_port"]
        self.assertIsInstance(port, int)
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            probe.bind(("127.0.0.1", port))
        finally:
            probe.close()
        receipt = self.recover_in_second_process(case)
        self.assertEqual(receipt["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")

    def test_real_kill_after_transport_admission_marker_recovers_only_with_zero_dispatch_evidence(self):
        case = self.launch_and_kill(case_id="KILL-03", phase="TRANSPORT_ADMITTED")
        receipt = self.recover_in_second_process(case)
        self.assertEqual(receipt["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")
        self.assertEqual(receipt["dispatch_evidence"]["entry_count"], 0)

    def test_real_kill_at_dispatch_started_with_started_evidence_becomes_ambiguous(self):
        case = self.launch_and_kill(case_id="KILL-04", phase="DISPATCH_STARTED", dispatch_evidence="STARTED")
        before = SqliteDispatchLedgerV2(case["dispatch_db"]).count()
        self.assertEqual(before, 1)
        receipt = self.recover_in_second_process(case)
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["dispatch_evidence"]["states"], ["STARTED"])
        self.assertEqual(SqliteDispatchLedgerV2(case["dispatch_db"]).count(), 1)
        self.assertEqual(SqliteLifecycleLedger(case["lifecycle_db"]).state(case["service"])["phase"], "CLOSED_AMBIGUOUS")

    def test_real_kill_after_completed_dispatch_evidence_becomes_ambiguous(self):
        case = self.launch_and_kill(case_id="KILL-05", phase="DISPATCH_COMPLETED", dispatch_evidence="COMPLETED")
        receipt = self.recover_in_second_process(case)
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["dispatch_evidence"]["states"], ["COMPLETED"])
        self.assertTrue(receipt["recovery"]["manual_ack_required"])
        self.assertFalse(receipt["control"]["automatic_retry_permitted"])


if __name__ == "__main__":
    unittest.main()
