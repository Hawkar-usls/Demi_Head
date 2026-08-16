from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2, TABLE
from nexus_loopback_lifecycle_gate import (
    AMBIGUOUS_TERMINAL_PHASE,
    REUSABLE_TERMINAL_PHASES,
    SqliteLifecycleLedger,
)

CONTRACT = "JANUS_NEXUS_PHASE_BOUNDARY_RECOVERY_V1"
SCHEMA = "janus.demihead.nexus_phase_boundary_recovery_receipt.v1"

PRE_DISPATCH_RECOVERABLE_PHASES = {
    "STARTING",
    "LISTENER_BOUND",
    "ACCEPTING",
    "CONNECTED",
    "REQUEST_RECEIVED",
    "TRANSPORT_ADMITTED",
    "DISPATCH_HOLD_NO_INVOCATION",
}

POST_DISPATCH_AMBIGUOUS_PHASES = {
    "DISPATCH_STARTED",
    "DISPATCH_AMBIGUOUS",
    "DISPATCH_COMPLETED",
    "RECEIPT_PENDING",
    "RECEIPT_SENT",
    "UNKNOWN_FAIL_CLOSED",
}


class DispatchEvidenceUnavailable(OSError):
    pass


def _now_ms(explicit: int | None = None) -> int:
    return int(time.time() * 1000) if explicit is None else int(explicit)


def _valid_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value.lower())


def inspect_dispatch_evidence(
    dispatch_ledger: SqliteDispatchLedgerV2,
    frame_sha256: str | None,
) -> dict[str, Any]:
    if not isinstance(dispatch_ledger, SqliteDispatchLedgerV2):
        raise DispatchEvidenceUnavailable("SqliteDispatchLedgerV2 is required for recovery evidence")
    if frame_sha256 is None:
        return {
            "available": True,
            "frame_bound": False,
            "entry_count": 0,
            "states": [],
            "entries": [],
        }
    if not _valid_sha256(frame_sha256):
        raise DispatchEvidenceUnavailable("lifecycle frame_sha256 is invalid")
    try:
        db = sqlite3.connect(
            str(dispatch_ledger.path),
            timeout=max(0.001, dispatch_ledger.busy_timeout_ms / 1000.0),
        )
        db.row_factory = sqlite3.Row
        try:
            db.execute(f"PRAGMA busy_timeout={dispatch_ledger.busy_timeout_ms}")
            rows = db.execute(
                f"""
                SELECT intent_sha256, dispatch_sha256, state, result_sha256, failure_code,
                       started_at_ms, updated_at_ms
                FROM {TABLE}
                WHERE frame_sha256 = ?
                ORDER BY started_at_ms, dispatch_sha256
                """,
                (frame_sha256.lower(),),
            ).fetchall()
        finally:
            db.close()
    except (sqlite3.Error, OSError) as exc:
        raise DispatchEvidenceUnavailable("dispatch evidence store unavailable") from exc

    entries = [
        {
            "intent_sha256": row["intent_sha256"],
            "dispatch_sha256": row["dispatch_sha256"],
            "state": row["state"],
            "result_sha256": row["result_sha256"],
            "failure_code": row["failure_code"],
            "started_at_ms": int(row["started_at_ms"]),
            "updated_at_ms": int(row["updated_at_ms"]),
        }
        for row in rows
    ]
    return {
        "available": True,
        "frame_bound": True,
        "entry_count": len(entries),
        "states": sorted({entry["state"] for entry in entries}),
        "entries": entries,
    }


def _receipt(
    status: str,
    *,
    service_id: str,
    expected_instance_id: str,
    observed_phase: str | None,
    final_phase: str | None,
    mutation_performed: bool,
    dispatch_evidence: dict[str, Any] | None,
    reason: str,
    manual_ack_required: bool,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "binding": {
            "service_id": service_id,
            "expected_instance_id": expected_instance_id,
            "observed_phase": observed_phase,
            "final_phase": final_phase,
        },
        "recovery": {
            "mutation_performed": mutation_performed,
            "reason": reason,
            "manual_ack_required": manual_ack_required,
            "automatic_recovery_permitted": False,
            "process_dead_attestation_is_operator_claim_not_independent_proof": True,
        },
        "dispatch_evidence": dispatch_evidence,
        "control": {
            "dispatch_ledger_deleted_or_reset": False,
            "replay_ledger_deleted_or_reset": False,
            "automatic_restart_permitted": False,
            "automatic_retry_permitted": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "process_death_independently_verified": False,
            "exactly_once_delivery_established": False,
            "semantic_duplicate_prevention_established": False,
            "cross_host_transport": False,
            "persistent_daemon": False,
            "production_recovery_controller": False,
        },
    }


def reconcile_stale_lifecycle(
    lifecycle_ledger: SqliteLifecycleLedger,
    dispatch_ledger: SqliteDispatchLedgerV2,
    *,
    service_id: str,
    expected_instance_id: str,
    operator_ack: bool,
    process_dead_attested: bool,
    now_ms: int | None = None,
) -> dict[str, Any]:
    now = _now_ms(now_ms)
    if not isinstance(service_id, str) or not service_id.strip():
        raise ValueError("service_id is required")
    if not isinstance(expected_instance_id, str) or not expected_instance_id.strip():
        raise ValueError("expected_instance_id is required")
    if not isinstance(lifecycle_ledger, SqliteLifecycleLedger):
        raise ValueError("SqliteLifecycleLedger is required")

    try:
        state = lifecycle_ledger.state(service_id)
    except Exception:
        return _receipt(
            "HOLD_LIFECYCLE_EVIDENCE_UNAVAILABLE",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=None,
            final_phase=None,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Persistent lifecycle state could not be read; recovery fails closed.",
            manual_ack_required=True,
        )

    if state is None:
        return _receipt(
            "HOLD_NO_LIFECYCLE_STATE",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=None,
            final_phase=None,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="No lifecycle row exists for this service.",
            manual_ack_required=False,
        )

    phase = str(state["phase"])
    if state["instance_id"] != expected_instance_id:
        return _receipt(
            "HOLD_INSTANCE_MISMATCH",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Expected instance_id does not match the persistent lifecycle row.",
            manual_ack_required=True,
        )

    if phase in REUSABLE_TERMINAL_PHASES:
        return _receipt(
            "NO_ACTION_ALREADY_TERMINAL",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Lifecycle is already in a reusable terminal state.",
            manual_ack_required=False,
        )

    if phase == AMBIGUOUS_TERMINAL_PHASE:
        return _receipt(
            "HOLD_ALREADY_AMBIGUOUS",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Ambiguous lifecycle must use the separate explicit ambiguity acknowledgment path.",
            manual_ack_required=True,
        )

    if operator_ack is not True or process_dead_attested is not True:
        return _receipt(
            "HOLD_OPERATOR_ATTESTATION_REQUIRED",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Both explicit operator acknowledgment and process-dead attestation are required.",
            manual_ack_required=True,
        )

    if phase not in PRE_DISPATCH_RECOVERABLE_PHASES and phase not in POST_DISPATCH_AMBIGUOUS_PHASES:
        return _receipt(
            "HOLD_UNKNOWN_PHASE_NO_MUTATION",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Unknown lifecycle phase has no recovery semantics and is not mutated.",
            manual_ack_required=True,
        )

    try:
        evidence = inspect_dispatch_evidence(dispatch_ledger, state.get("frame_sha256"))
    except DispatchEvidenceUnavailable:
        return _receipt(
            "HOLD_DISPATCH_EVIDENCE_UNAVAILABLE",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=None,
            reason="Dispatch evidence could not be read; recovery fails closed.",
            manual_ack_required=True,
        )

    if phase in PRE_DISPATCH_RECOVERABLE_PHASES:
        if evidence["entry_count"] != 0:
            return _receipt(
                "HOLD_UNEXPECTED_DISPATCH_EVIDENCE",
                service_id=service_id,
                expected_instance_id=expected_instance_id,
                observed_phase=phase,
                final_phase=phase,
                mutation_performed=False,
                dispatch_evidence=evidence,
                reason="A phase classified as pre-dispatch has durable dispatch evidence; clean recovery is forbidden.",
                manual_ack_required=True,
            )
        try:
            lifecycle_ledger.transition(
                service_id,
                expected_instance_id,
                "CLOSED_CLEAN",
                now_ms=now,
                detail_code=f"OPERATOR_RECOVERED_STALE_PRE_DISPATCH_{phase}",
            )
        except Exception:
            return _receipt(
                "HOLD_LIFECYCLE_MUTATION_FAILED",
                service_id=service_id,
                expected_instance_id=expected_instance_id,
                observed_phase=phase,
                final_phase=phase,
                mutation_performed=False,
                dispatch_evidence=evidence,
                reason="Lifecycle terminalization could not be durably recorded.",
                manual_ack_required=True,
            )
        return _receipt(
            "RECOVERED_PRE_DISPATCH_CLOSED_CLEAN",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase="CLOSED_CLEAN",
            mutation_performed=True,
            dispatch_evidence=evidence,
            reason="Operator-abandoned stale pre-dispatch instance had zero dispatch evidence.",
            manual_ack_required=False,
        )

    try:
        lifecycle_ledger.transition(
            service_id,
            expected_instance_id,
            AMBIGUOUS_TERMINAL_PHASE,
            now_ms=now,
            detail_code=f"OPERATOR_RECONCILED_STALE_POST_DISPATCH_{phase}",
        )
    except Exception:
        return _receipt(
            "HOLD_LIFECYCLE_MUTATION_FAILED",
            service_id=service_id,
            expected_instance_id=expected_instance_id,
            observed_phase=phase,
            final_phase=phase,
            mutation_performed=False,
            dispatch_evidence=evidence,
            reason="Ambiguous terminalization could not be durably recorded.",
            manual_ack_required=True,
        )
    return _receipt(
        "RECOVERED_TO_CLOSED_AMBIGUOUS",
        service_id=service_id,
        expected_instance_id=expected_instance_id,
        observed_phase=phase,
        final_phase=AMBIGUOUS_TERMINAL_PHASE,
        mutation_performed=True,
        dispatch_evidence=evidence,
        reason="Post-dispatch or execution-uncertain phase is preserved as ambiguous regardless of observed dispatch evidence.",
        manual_ack_required=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Manual fail-closed recovery for stale JANUS Nexus one-shot lifecycle state.")
    parser.add_argument("--lifecycle-db", required=True, type=Path)
    parser.add_argument("--dispatch-db", required=True, type=Path)
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--expected-instance-id", required=True)
    parser.add_argument("--operator-ack", action="store_true")
    parser.add_argument("--process-dead-attested", action="store_true")
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args()
    try:
        result = reconcile_stale_lifecycle(
            SqliteLifecycleLedger(args.lifecycle_db),
            SqliteDispatchLedgerV2(args.dispatch_db),
            service_id=args.service_id,
            expected_instance_id=args.expected_instance_id,
            operator_ack=args.operator_ack,
            process_dead_attested=args.process_dead_attested,
            now_ms=args.now_ms,
        )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return 0
    except (ValueError, OSError, sqlite3.Error) as exc:
        sys.stderr.write(f"nexus_lifecycle_recovery: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
