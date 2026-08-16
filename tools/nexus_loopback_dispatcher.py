from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import Any, Callable

from nexus_destination_acceptance import validate_endpoint_policy
from nexus_destination_acceptance_revalidation import accept_destination_revalidated
from nexus_habitat import validate_envelope
from nexus_local_transport import FRAME_SCHEMA, canonical_json_bytes, sha256


CONTRACT = "JANUS_NEXUS_LOOPBACK_DISPATCH_V1"
SCHEMA = "janus.demihead.nexus_loopback_dispatch_result.v1"
CATALOG_SCHEMA = "janus.demihead.nexus_endpoint_catalog.v1"
MAX_PAYLOAD_BYTES = 64 * 1024
MAX_HANDLER_OUTPUT_BYTES = 64 * 1024


@dataclass(frozen=True)
class LocalHandler:
    handler_id: str
    target_head: str
    callback: Callable[[dict[str, Any]], dict[str, Any]]
    deterministic_reference: bool = True
    network_io_permitted: bool = False
    filesystem_io_permitted: bool = False
    external_effect_permitted: bool = False
    authority_delta: int = 0
    mass_effect_budget_delta: int = 0


def _json_size(value: Any) -> int:
    try:
        return len(canonical_json_bytes(value))
    except (TypeError, ValueError) as exc:
        raise ValueError("Value must be canonical-JSON serializable") from exc


def validate_endpoint_catalog(catalog: dict[str, Any]) -> None:
    if not isinstance(catalog, dict) or catalog.get("schema") != CATALOG_SCHEMA:
        raise ValueError("Unexpected Nexus endpoint catalog schema")
    if catalog.get("live_network_endpoints") is not False:
        raise ValueError("Loopback v1 requires live_network_endpoints=false")
    endpoints = catalog.get("endpoints")
    if not isinstance(endpoints, list) or not endpoints:
        raise ValueError("Endpoint catalog must contain a non-empty endpoints array")

    ids: set[str] = set()
    for endpoint in endpoints:
        validate_endpoint_policy(endpoint)
        endpoint_id = endpoint["endpoint_id"]
        if endpoint_id in ids:
            raise ValueError(f"Duplicate endpoint_id: {endpoint_id}")
        ids.add(endpoint_id)


def _select_endpoint(catalog: dict[str, Any], target_head: str) -> dict[str, Any] | None:
    validate_endpoint_catalog(catalog)
    matches = [
        endpoint
        for endpoint in catalog["endpoints"]
        if endpoint["enabled"] is True and target_head in endpoint["accepted_target_heads"]
    ]
    if len(matches) > 1:
        raise ValueError("Ambiguous loopback destination: multiple enabled endpoints accept target_head")
    return matches[0] if matches else None


def _validate_handler(handler: LocalHandler, target_head: str) -> None:
    if not isinstance(handler, LocalHandler):
        raise ValueError("Loopback handler must be a LocalHandler descriptor")
    if not handler.handler_id.strip():
        raise ValueError("Loopback handler_id must be non-empty")
    if handler.target_head != target_head:
        raise ValueError("Loopback handler target_head mismatch")
    if handler.deterministic_reference is not True:
        raise ValueError("Loopback v1 admits only deterministic reference handlers")
    if handler.network_io_permitted is not False:
        raise ValueError("Loopback v1 handler cannot permit network I/O")
    if handler.filesystem_io_permitted is not False:
        raise ValueError("Loopback v1 handler cannot permit filesystem I/O")
    if handler.external_effect_permitted is not False:
        raise ValueError("Loopback v1 handler cannot permit external effects")
    if handler.authority_delta != 0 or handler.mass_effect_budget_delta != 0:
        raise ValueError("Loopback handler cannot alter authority or mass-effect budget")
    if not callable(handler.callback):
        raise ValueError("Loopback handler callback must be callable")


def _hold(
    status: str,
    *,
    frame: dict[str, Any],
    target_head: str,
    reason: str,
    endpoint_id: str | None = None,
    handler_id: str | None = None,
    invocation_attempted: bool = False,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "binding": {
            "frame_sha256": sha256(frame),
            "target_head": target_head,
            "endpoint_id": endpoint_id,
            "handler_id": handler_id,
        },
        "hold": {
            "reason": reason,
            "handler_invocation_attempted": invocation_attempted,
            "completion_established": False,
        },
        "control": {
            "local_in_process_delivery_performed": invocation_attempted,
            "network_io_performed": False,
            "external_delivery_performed": False,
            "world_effect_performed": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "laws": [
            "HOLD != FAILURE_PERMISSION_TO_RETRY",
            "LOCAL_DISPATCH != NETWORK_DELIVERY",
            "LOCAL_HANDLER_INVOCATION != WORLD_EFFECT_AUTHORITY",
        ],
    }


def dispatch_loopback(
    frame: dict[str, Any],
    admission: dict[str, Any],
    principal_state: dict[str, Any],
    endpoint_catalog: dict[str, Any],
    payload: dict[str, Any],
    handlers: dict[str, LocalHandler],
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != FRAME_SCHEMA:
        raise ValueError("Unexpected transport frame schema")
    envelope = frame.get("envelope")
    validate_envelope(envelope)
    target_head = envelope["target_head"]

    if not isinstance(payload, dict):
        raise ValueError("Loopback v1 payload must be a JSON object")
    payload_size = _json_size(payload)
    if payload_size > MAX_PAYLOAD_BYTES:
        raise ValueError("Loopback payload exceeds maximum size")
    payload_sha256 = sha256(payload)
    if envelope["payload_ref"]["sha256"] != payload_sha256:
        raise ValueError("Loopback payload hash does not match envelope payload_ref")

    endpoint = _select_endpoint(endpoint_catalog, target_head)
    if endpoint is None:
        return _hold(
            "HOLD_NO_LOCAL_ENDPOINT",
            frame=frame,
            target_head=target_head,
            reason="No enabled local endpoint accepts the target head.",
        )

    handler = handlers.get(target_head)
    if handler is None:
        return _hold(
            "HOLD_NO_LOCAL_HANDLER",
            frame=frame,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            reason="Destination exists but no local reference handler is registered.",
        )
    _validate_handler(handler, target_head)

    acceptance = accept_destination_revalidated(
        frame,
        admission,
        endpoint,
        principal_state,
        now_ms=now_ms,
    )

    safe_input = copy.deepcopy(payload)
    try:
        output = handler.callback(safe_input)
    except Exception as exc:
        return _hold(
            "HOLD_HANDLER_FAILURE",
            frame=frame,
            target_head=target_head,
            endpoint_id=endpoint["endpoint_id"],
            handler_id=handler.handler_id,
            reason=f"Local reference handler raised {type(exc).__name__}.",
            invocation_attempted=True,
        )

    if not isinstance(output, dict):
        raise ValueError("Loopback handler output must be a JSON object")
    output_size = _json_size(output)
    if output_size > MAX_HANDLER_OUTPUT_BYTES:
        raise ValueError("Loopback handler output exceeds maximum size")

    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "LOOPBACK_DISPATCH_COMPLETED_LOCAL",
        "binding": {
            "frame_sha256": sha256(frame),
            "envelope_sha256": frame["envelope_sha256"],
            "acceptance_sha256": sha256(acceptance),
            "payload_sha256": payload_sha256,
            "handler_output_sha256": sha256(output),
            "source_head": envelope["source_head"],
            "target_head": target_head,
            "payload_kind": envelope["payload_kind"],
            "endpoint_id": endpoint["endpoint_id"],
            "handler_id": handler.handler_id,
        },
        "dispatch": {
            "endpoint_selected_uniquely": True,
            "payload_hash_verified": True,
            "current_principal_revalidated": True,
            "destination_acceptance_verified": True,
            "handler_descriptor_verified": True,
            "handler_input_size_bytes": payload_size,
            "handler_output_size_bytes": output_size,
            "local_reference_handler_invoked": True,
            "local_in_process_delivery_performed": True,
            "completion_established": True,
        },
        "handler_output": output,
        "control": {
            "socket_listener_enabled": False,
            "network_io_performed": False,
            "filesystem_io_performed_by_dispatcher": False,
            "external_delivery_performed": False,
            "world_effect_performed": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "exactly_once_delivery_established": False,
            "process_isolation_established": False,
            "handler_side_effect_attestation_established": False,
            "cross_repository_delivery_established": False,
            "human_identity_established": False,
            "world_effect_authorization_established": False,
        },
        "laws": [
            "DESTINATION_ACCEPTANCE != DELIVERY",
            "LOOPBACK_DISPATCH = LOCAL_IN_PROCESS_DELIVERY_ONLY",
            "LOCAL_HANDLER_INVOCATION != EXTERNAL_EFFECT",
            "LOCAL_COMPLETION != EXACTLY_ONCE_DELIVERY",
            "DISPATCH != AUTHORITY",
        ],
    }


def self_test() -> dict[str, Any]:
    from nexus_local_transport import build_frame, validate_frame
    from nexus_replay_ledger import MemoryReplayGuard

    key = b"loopback-dispatch-test-key"
    issued = 1_800_000_000_000
    payload = {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}
    envelope = {
        "schema": "janus.demihead.nexus_envelope.v1",
        "contract": "JANUS_NEXUS_HABITAT_V1",
        "envelope_id": "loopback-selftest-001",
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
        key=key,
        issued_at_ms=issued,
        nonce="loopback-selftest-nonce-0001",
    )
    runtime_principal = {
        "key": key,
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
        now_ms=issued + 100,
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
        "schema": CATALOG_SCHEMA,
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
    handlers = {
        "RELEASE_CONTROL": LocalHandler(
            handler_id="RELEASE_CONTROL.REFERENCE_ACK.V1",
            target_head="RELEASE_CONTROL",
            callback=lambda value: {
                "schema": "janus.demihead.loopback_reference_ack.v1",
                "status": "ACK_LOCAL_ONLY",
                "input_sha256": sha256(value),
            },
        )
    }
    result = dispatch_loopback(
        frame,
        admission,
        public_principal,
        catalog,
        payload,
        handlers,
        now_ms=issued + 200,
    )
    checks = {
        "local_dispatch_completed": result["status"] == "LOOPBACK_DISPATCH_COMPLETED_LOCAL",
        "local_delivery_recorded": result["dispatch"]["local_in_process_delivery_performed"] is True,
        "network_io_not_claimed": result["control"]["network_io_performed"] is False,
        "world_effect_not_claimed": result["control"]["world_effect_performed"] is False,
        "exactly_once_not_claimed": result["claim_ceiling"]["exactly_once_delivery_established"] is False,
    }

    tampered = dict(payload)
    tampered["decision"] = "MUTATED"
    try:
        dispatch_loopback(frame, admission, public_principal, catalog, tampered, handlers, now_ms=issued + 200)
    except ValueError:
        checks["tampered_payload_rejected_before_dispatch"] = True
    else:
        checks["tampered_payload_rejected_before_dispatch"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "result": result,
    }
