from __future__ import annotations

import copy
import sqlite3
import time
from typing import Any

from nexus_destination_acceptance_revalidation import accept_destination_revalidated
from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2, dispatch_digest, intent_digest
from nexus_habitat import validate_envelope
from nexus_local_transport import FRAME_SCHEMA, canonical_json_bytes, sha256
from nexus_loopback_dispatcher import LocalHandler, _select_endpoint, _validate_handler


CONTRACT = "JANUS_NEXUS_LOOPBACK_DISPATCH_V2"
SCHEMA = "janus.demihead.nexus_loopback_dispatch_result.v2"
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_HANDLER_OUTPUT_BYTES = 64 * 1024


def _json_size(value: Any) -> int:
    try:
        return len(canonical_json_bytes(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("value must be canonical-JSON serializable") from exc


def _hold(
    status: str,
    *,
    frame_sha256: str,
    target_head: str,
    reason: str,
    endpoint_id: str | None = None,
    handler_id: str | None = None,
    intent_sha256: str | None = None,
    dispatch_sha256: str | None = None,
    ledger_state: str | None = None,
    invocation_attempted: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "binding": {
            "frame_sha256": frame_sha256,
            "target_head": target_head,
            "endpoint_id": endpoint_id,
            "handler_id": handler_id,
            "intent_sha256": intent_sha256,
            "dispatch_sha256": dispatch_sha256,
        },
        "hold": {
            "reason": reason,
            "handler_invocation_attempted": invocation_attempted,
            "completion_established": False,
        },
        "ledger": {
            "persistent_required": True,
            "intent_guarded": True,
            "dispatch_state": ledger_state,
            "duplicate_intent_reinvocation_permitted": False,
        },
        "control": {
            "network_io_performed": False,
            "external_delivery_performed": False,
            "world_effect_performed": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def dispatch_loopback_v2(
    frame: dict[str, Any],
    admission: dict[str, Any],
    principal_state: dict[str, Any],
    endpoint_catalog: dict[str, Any],
    payload: dict[str, Any],
    handlers: dict[str, LocalHandler],
    *,
    dispatch_ledger: SqliteDispatchLedgerV2,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != FRAME_SCHEMA:
        raise ValueError("unexpected transport frame schema")
    envelope = frame.get("envelope")
    validate_envelope(envelope)
    target_head = envelope["target_head"]
    frame_sha = sha256(frame)

    if not isinstance(payload, dict):
        raise ValueError("loopback v2 payload must be a JSON object")
    payload_size = _json_size(payload)
    if payload_size > MAX_PAYLOAD_BYTES:
        raise ValueError("loopback payload exceeds maximum size")
    payload_sha = sha256(payload)
    if envelope["payload_ref"]["sha256"] != payload_sha:
        raise ValueError("payload hash does not match envelope payload_ref")

    endpoint = _select_endpoint(endpoint_catalog, target_head)
    if endpoint is None:
        return _hold(
            "HOLD_NO_LOCAL_ENDPOINT",
            frame_sha256=frame_sha,
            target_head=target_head,
            reason="No enabled local endpoint accepts target_head.",
        )

    handler = handlers.get(target_head)
    if handler is None:
        return _hold(
            "HOLD_NO_LOCAL_HANDLER",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            reason="Endpoint exists but no local handler is registered.",
        )
    _validate_handler(handler, target_head)

    if not isinstance(dispatch_ledger, SqliteDispatchLedgerV2):
        raise ValueError("loopback v2 requires SqliteDispatchLedgerV2")

    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    acceptance = accept_destination_revalidated(
        frame,
        admission,
        endpoint,
        principal_state,
        now_ms=now,
    )
    acceptance_sha = sha256(acceptance)
    intent_bindings = {
        "frame_sha256": frame_sha,
        "acceptance_sha256": acceptance_sha,
        "payload_sha256": payload_sha,
        "target_head": target_head,
    }
    intent_sha = intent_digest(intent_bindings)
    dispatch_sha = dispatch_digest(intent_sha, handler.handler_id)

    try:
        begin = dispatch_ledger.begin(
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            intent_bindings=intent_bindings,
            handler_id=handler.handler_id,
            now_ms=now,
        )
    except (sqlite3.Error, OSError) as exc:
        return _hold(
            "HOLD_LEDGER_UNAVAILABLE",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            reason=f"Persistent ledger unavailable before handler invocation: {type(exc).__name__}.",
        )

    if begin.get("admitted") is not True:
        existing = begin.get("existing") or {}
        return _hold(
            "HOLD_DUPLICATE_INTENT",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            ledger_state=existing.get("state", "UNKNOWN"),
            reason="This admission intent already has a durable dispatch attempt; handler-version changes do not bypass the intent guard.",
        )

    safe_input = copy.deepcopy(payload)
    try:
        output = handler.callback(safe_input)
    except Exception as exc:
        try:
            recorded = dispatch_ledger.fail_ambiguous(
                dispatch_sha,
                failure_code=f"HANDLER_{type(exc).__name__.upper()}",
                now_ms=now,
            )
        except Exception:
            recorded = False
        return _hold(
            "HOLD_HANDLER_FAILURE" if recorded else "HOLD_LEDGER_FINALIZATION_FAILURE",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            ledger_state="FAILED_AMBIGUOUS" if recorded else "STARTED",
            reason="Handler completion is ambiguous; automatic retry is forbidden.",
            invocation_attempted=True,
        )

    try:
        if not isinstance(output, dict):
            raise ValueError("handler output must be a JSON object")
        output_size = _json_size(output)
        if output_size > MAX_HANDLER_OUTPUT_BYTES:
            raise ValueError("handler output exceeds maximum size")
    except ValueError:
        try:
            recorded = dispatch_ledger.fail_ambiguous(
                dispatch_sha,
                failure_code="INVALID_HANDLER_OUTPUT",
                now_ms=now,
            )
        except Exception:
            recorded = False
        return _hold(
            "HOLD_HANDLER_OUTPUT_INVALID" if recorded else "HOLD_LEDGER_FINALIZATION_FAILURE",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            ledger_state="FAILED_AMBIGUOUS" if recorded else "STARTED",
            reason="Handler ran but returned an inadmissible result; retry is forbidden.",
            invocation_attempted=True,
        )

    output_sha = sha256(output)
    try:
        completed = dispatch_ledger.complete(dispatch_sha, result_sha256=output_sha, now_ms=now)
    except Exception:
        completed = False
    if not completed:
        return _hold(
            "HOLD_LEDGER_FINALIZATION_FAILURE",
            frame_sha256=frame_sha,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            intent_sha256=intent_sha,
            dispatch_sha256=dispatch_sha,
            ledger_state="STARTED",
            reason="Handler returned but durable completion is not established; retry is forbidden.",
            invocation_attempted=True,
        )

    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "LOOPBACK_DISPATCH_COMPLETED_LOCAL",
        "binding": {
            "frame_sha256": frame_sha,
            "acceptance_sha256": acceptance_sha,
            "payload_sha256": payload_sha,
            "handler_output_sha256": output_sha,
            "intent_sha256": intent_sha,
            "dispatch_sha256": dispatch_sha,
            "source_head": envelope["source_head"],
            "target_head": target_head,
            "endpoint_id": endpoint["endpoint_id"],
            "handler_id": handler.handler_id,
        },
        "dispatch": {
            "intent_guard_independent_of_handler_version": True,
            "durable_started_before_handler": True,
            "local_handler_invoked": True,
            "local_in_process_delivery_performed": True,
            "durable_completed": True,
            "handler_input_size_bytes": payload_size,
            "handler_output_size_bytes": output_size,
        },
        "handler_output": output,
        "ledger": {
            "kind": dispatch_ledger.kind,
            "persistent": True,
            "state": "COMPLETED",
            "duplicate_intent_reinvocation_permitted": False,
        },
        "control": {
            "socket_listener_enabled": False,
            "network_io_performed": False,
            "external_delivery_performed": False,
            "world_effect_performed": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "crash_safe_local_duplicate_intent_suppression": True,
            "guaranteed_delivery": False,
            "exactly_once_delivery": False,
            "process_isolation": False,
            "cross_repository_delivery": False,
            "external_effect_authority": False,
        },
    }
