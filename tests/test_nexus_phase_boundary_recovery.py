from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import (  # noqa: E402
    SqliteDispatchLedgerV2,
    dispatch_digest,
    intent_digest,
)
from nexus_lifecycle_recovery import reconcile_stale_lifecycle  # noqa: E402
from nexus_loopback_lifecycle_gate import SqliteLifecycleLedger  # noqa: E402


class NexusPhaseBoundaryRecoveryTests(unittest.TestCase):
    SERVICE = "DEMIHEAD.NEXUS.RECOVERY.TEST"
    INSTANCE = "recovery-instance-001"
    NOW = 1_800_000_010_000
    FRAME = "a" * 64

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.lifecycle = SqliteLifecycleLedger(self.root / "lifecycle.db")
        self.dispatch = SqliteDispatchLedgerV2(self.root / "dispatch.db")

    def tearDown(self):
        self.temp.cleanup()

    def seed_phase(self, phase: str, *, frame_sha256: str | None = None, instance_id: str | None = None):
        instance = instance_id or self.INSTANCE
        begin = self.lifecycle.begin(self.SERVICE, instance, now_ms=self.NOW)
        self.assertTrue(begin["admitted"])
        if phase != "STARTING":
            self.lifecycle.transition(
                self.SERVICE,
                instance,
                phase,
                now_ms=self.NOW + 1,
                frame_sha256=frame_sha256,
                detail_code=f"TEST_CRASH_BOUNDARY_{phase}",
            )

    def seed_dispatch(self, *, frame_sha256: str | None = None, state: str = "STARTED"):
        frame = frame_sha256 or self.FRAME
        bindings = {
            "frame_sha256": frame,
            "acceptance_sha256": "b" * 64,
            "payload_sha256": "c" * 64,
            "target_head": "RELEASE_CONTROL",
        }
        intent = intent_digest(bindings)
        dispatch = dispatch_digest(intent, "RELEASE_CONTROL.RECOVERY.TEST.V1")
        result = self.dispatch.begin(
            intent_sha256=intent,
            dispatch_sha256=dispatch,
            intent_bindings=bindings,
            handler_id="RELEASE_CONTROL.RECOVERY.TEST.V1",
            now_ms=self.NOW + 2,
        )
        self.assertTrue(result["admitted"])
        if state == "COMPLETED":
            self.assertTrue(self.dispatch.complete(dispatch, result_sha256="d" * 64, now_ms=self.NOW + 3))
        elif state == "FAILED_AMBIGUOUS":
            self.assertTrue(self.dispatch.fail_ambiguous(dispatch, failure_code="TEST_CRASH", now_ms=self.NOW + 3))
        elif state != "STARTED":
            raise ValueError(state)
        return intent, dispatch

    def recover(self, *, expected_instance_id: str | None = None, operator_ack=True,
                process_dead_attested=True, dispatch_ledger=None):
        return reconcile_stale_lifecycle(
            self.lifecycle,
            dispatch_ledger or self.dispatch,
            service_id=self.SERVICE,
            expected_instance_id=expected_instance_id or self.INSTANCE,
            operator_ack=operator_ack,
            process_dead_attested=process_dead_attested,
            now_ms=self.NOW + 100,
        )

    def test_frozen_manifest_hash_and_case_count(self):
        corpus = json.loads((ROOT / "fixtures" / "nexus_phase_boundary_crash_recovery_holdout_v1.json").read_text(encoding="utf-8"))
        raw = json.dumps(corpus["freeze_payload"], ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        actual = hashlib.sha256(raw).hexdigest()
        self.assertEqual(actual, "e3946b4f95262598203f46c46ca2998ffffaa26a9124b52a877424acc963452d")
        self.assertEqual(corpus["freeze_sha256"], actual)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])
        self.assertEqual(len(corpus["freeze_payload"]["cases"]), 13)
        self.assertFalse(corpus["freeze_payload"]["invariants"]["automatic_recovery"])
        self.assertTrue(corpus["freeze_payload"]["invariants"]["pre_dispatch_recovery_requires_zero_dispatch_evidence"])

    def test_stale_pre_dispatch_boundaries_can_only_close_clean_with_zero_dispatch_evidence(self):
        for index, phase in enumerate(("STARTING", "LISTENER_BOUND", "REQUEST_RECEIVED", "TRANSPORT_ADMITTED"), start=1):
            with self.subTest(phase=phase):
                service = f"{self.SERVICE}.{index}"
                instance = f"pre-{index}"
                begin = self.lifecycle.begin(service, instance, now_ms=self.NOW)
                self.assertTrue(begin["admitted"])
                if phase != "STARTING":
                    self.lifecycle.transition(service, instance, phase, now_ms=self.NOW + 1,
                                              frame_sha256=self.FRAME, detail_code="CRASH_INJECTED")
                receipt = reconcile_stale_lifecycle(
                    self.lifecycle, self.dispatch,
                    service_id=service, expected_instance_id=instance,
                    operator_ack=True, process_dead_attested=True, now_ms=self.NOW + 100,
                )
                self.assertEqual(receipt["status"], "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN")
                self.assertEqual(self.lifecycle.state(service)["phase"], "CLOSED_CLEAN")
                self.assertFalse(receipt["control"]["automatic_restart_permitted"])
                self.assertFalse(receipt["control"]["automatic_retry_permitted"])

    def test_dispatch_started_without_dispatch_evidence_is_still_ambiguous(self):
        self.seed_phase("DISPATCH_STARTED", frame_sha256=self.FRAME)
        receipt = self.recover()
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["dispatch_evidence"]["entry_count"], 0)
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "CLOSED_AMBIGUOUS")
        self.assertTrue(receipt["recovery"]["manual_ack_required"])

    def test_dispatch_started_with_started_evidence_is_ambiguous(self):
        self.seed_phase("DISPATCH_STARTED", frame_sha256=self.FRAME)
        self.seed_dispatch(state="STARTED")
        receipt = self.recover()
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["dispatch_evidence"]["states"], ["STARTED"])
        self.assertEqual(self.dispatch.count(), 1)

    def test_dispatch_completed_with_completed_evidence_is_ambiguous(self):
        self.seed_phase("DISPATCH_COMPLETED", frame_sha256=self.FRAME)
        self.seed_dispatch(state="COMPLETED")
        receipt = self.recover()
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["dispatch_evidence"]["states"], ["COMPLETED"])
        self.assertEqual(self.dispatch.count(), 1)
        self.assertFalse(receipt["control"]["dispatch_ledger_deleted_or_reset"])

    def test_receipt_pending_with_completed_evidence_is_ambiguous(self):
        self.seed_phase("RECEIPT_PENDING", frame_sha256=self.FRAME)
        self.seed_dispatch(state="COMPLETED")
        receipt = self.recover()
        self.assertEqual(receipt["status"], "RECOVERED_TO_CLOSED_AMBIGUOUS")
        self.assertEqual(receipt["binding"]["final_phase"], "CLOSED_AMBIGUOUS")
        self.assertTrue(receipt["recovery"]["manual_ack_required"])

    def test_pre_dispatch_phase_with_unexpected_dispatch_evidence_is_not_mutated(self):
        self.seed_phase("TRANSPORT_ADMITTED", frame_sha256=self.FRAME)
        self.seed_dispatch(state="STARTED")
        receipt = self.recover()
        self.assertEqual(receipt["status"], "HOLD_UNEXPECTED_DISPATCH_EVIDENCE")
        self.assertFalse(receipt["recovery"]["mutation_performed"])
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "TRANSPORT_ADMITTED")

    def test_operator_and_process_dead_attestation_are_both_required(self):
        self.seed_phase("LISTENER_BOUND", frame_sha256=self.FRAME)
        no_operator = self.recover(operator_ack=False, process_dead_attested=True)
        self.assertEqual(no_operator["status"], "HOLD_OPERATOR_ATTESTATION_REQUIRED")
        no_dead_attestation = self.recover(operator_ack=True, process_dead_attested=False)
        self.assertEqual(no_dead_attestation["status"], "HOLD_OPERATOR_ATTESTATION_REQUIRED")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "LISTENER_BOUND")

    def test_wrong_instance_identity_is_rejected_without_mutation(self):
        self.seed_phase("REQUEST_RECEIVED", frame_sha256=self.FRAME)
        receipt = self.recover(expected_instance_id="wrong-instance")
        self.assertEqual(receipt["status"], "HOLD_INSTANCE_MISMATCH")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "REQUEST_RECEIVED")

    def test_dispatch_evidence_store_unavailable_fails_closed_without_mutation(self):
        self.seed_phase("DISPATCH_STARTED", frame_sha256=self.FRAME)
        broken = SqliteDispatchLedgerV2(self.root / "temporary-valid.db")
        broken.path = self.root / "nonexistent-parent" / "dispatch.db"
        receipt = self.recover(dispatch_ledger=broken)
        self.assertEqual(receipt["status"], "HOLD_DISPATCH_EVIDENCE_UNAVAILABLE")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "DISPATCH_STARTED")

    def test_unknown_phase_has_no_recovery_semantics(self):
        self.seed_phase("PHASE_FROM_FUTURE", frame_sha256=self.FRAME)
        receipt = self.recover()
        self.assertEqual(receipt["status"], "HOLD_UNKNOWN_PHASE_NO_MUTATION")
        self.assertEqual(self.lifecycle.state(self.SERVICE)["phase"], "PHASE_FROM_FUTURE")


if __name__ == "__main__":
    unittest.main()
