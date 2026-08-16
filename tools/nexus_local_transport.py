from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any

from nexus_habitat import validate_envelope
from nexus_replay_ledger import MemoryReplayGuard


FRAME_SCHEMA = "janus.demihead.nexus_transport_frame.v1"
TRANSPORT_CONTRACT = "JANUS_NEXUS_LOCAL_TRANSPORT_V1"
NEXUS_ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v1"
MAX_FRAME_BYTES = 64 * 1024
DEFAULT_TTL_MS = 30_000
MAX_TTL_MS = 120_000
MAX_FUTURE_SKEW_MS = 5_000


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _auth_payload(frame: dict[str, Any]) -> dict[str, Any]:
    unsigned = json.loads(json.dumps(frame))
    unsigned.pop("auth", None)
    return unsigned


def _hmac_hex(key: bytes, payload: dict[str, Any]) -> str:
    return hmac.new(key, canonical_json_bytes(payload), hashlib.sha256).hexdigest()


def _principal(principal_lookup: dict[str, dict[str, Any]], key_id: str) -> tuple[bytes, str, tuple[str, ...]]:
    principal = principal_lookup.get(key_id)
    if not isinstance(principal, dict):
        raise ValueError("Unknown transport key_id")
    if principal.get("enabled") is not True:
        raise ValueError("Transport principal is disabled")
    key = principal.get("key")
    sender_id = principal.get("sender_id")
    allowed_source_heads = principal.get("allowed_source_heads")
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("Invalid transport key material")
    if not isinstance(sender_id, str) or not sender_id.strip():
        raise ValueError("Transport principal sender_id is invalid")
    if not isinstance(allowed_source_heads, (list, tuple)) or not allowed_source_heads:
        raise ValueError("Transport principal requires allowed_source_heads")
    if any(not isinstance(item, str) or not item for item in allowed_source_heads):
        raise ValueError("Transport principal contains an invalid source head")
    return key, sender_id, tuple(allowed_source_heads)


def build_frame(
    envelope: dict[str, Any],
    *,
    sender_id: str,
    key_id: str,
    key: bytes,
    issued_at_ms: int | None = None,
    nonce: str | None = None,
    ttl_ms: int = DEFAULT_TTL_MS,
) -> dict[str, Any]:
    validate_envelope(envelope)
    if not isinstance(sender_id, str) or not sender_id.strip():
        raise ValueError("sender_id is required")
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("key_id is required")
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("transport key must be bytes with length >= 16")
    if not isinstance(ttl_ms, int) or isinstance(ttl_ms, bool) or not 1 <= ttl_ms <= MAX_TTL_MS:
        raise ValueError(f"ttl_ms must be an integer in [1, {MAX_TTL_MS}]")

    issued = int(time.time() * 1000) if issued_at_ms is None else int(issued_at_ms)
    frame_nonce = secrets.token_hex(16) if nonce is None else str(nonce)
    if len(frame_nonce) < 16:
        raise ValueError("nonce must contain at least 16 characters")

    frame = {
        "schema": FRAME_SCHEMA,
        "contract": TRANSPORT_CONTRACT,
        "sender_id": sender_id,
        "key_id": key_id,
        "issued_at_ms": issued,
        "ttl_ms": ttl_ms,
        "nonce": frame_nonce,
        "envelope_sha256": sha256(envelope),
        "envelope": envelope,
        "transport_control": {
            "network_io_performed_by_reference": False,
            "socket_listener_enabled": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    if len(canonical_json_bytes(frame)) > MAX_FRAME_BYTES:
        raise ValueError("transport frame exceeds maximum size")
    frame["auth"] = {"algorithm": "HMAC-SHA256", "tag": _hmac_hex(key, _auth_payload(frame))}
    if len(canonical_json_bytes(frame)) > MAX_FRAME_BYTES:
        raise ValueError("authenticated transport frame exceeds maximum size")
    return frame


def validate_frame(
    frame: dict[str, Any],
    *,
    principal_lookup: dict[str, dict[str, Any]],
    replay_guard: Any,
    now_ms: int | None = None,
    queue_depth: int = 0,
    queue_capacity: int = 128,
) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != FRAME_SCHEMA:
        raise ValueError("Unexpected transport frame schema")
    if len(canonical_json_bytes(frame)) > MAX_FRAME_BYTES:
        raise ValueError("Incoming transport frame exceeds maximum size")
    if frame.get("contract") != TRANSPORT_CONTRACT:
        raise ValueError("Transport contract mismatch")
    if replay_guard is None or not callable(getattr(replay_guard, "consume", None)):
        raise ValueError("A replay guard with atomic consume() is required")

    sender_id = frame.get("sender_id")
    key_id = frame.get("key_id")
    if not isinstance(sender_id, str) or not sender_id.strip():
        raise ValueError("Invalid sender_id")
    if not isinstance(key_id, str) or not key_id.strip():
        raise ValueError("Invalid key_id")
    key, bound_sender_id, allowed_source_heads = _principal(principal_lookup, key_id)

    auth = frame.get("auth")
    if not isinstance(auth, dict) or auth.get("algorithm") != "HMAC-SHA256":
        raise ValueError("Unsupported transport authentication")
    tag = auth.get("tag")
    if not isinstance(tag, str) or len(tag) != 64:
        raise ValueError("Invalid HMAC tag")
    if not hmac.compare_digest(tag, _hmac_hex(key, _auth_payload(frame))):
        raise ValueError("Transport HMAC verification failed")

    envelope = frame.get("envelope")
    validate_envelope(envelope)
    if frame.get("envelope_sha256") != sha256(envelope):
        raise ValueError("Envelope hash binding mismatch")
    if sender_id != bound_sender_id:
        raise ValueError("Authenticated key is not bound to claimed sender_id")
    source_head = envelope.get("source_head")
    if source_head not in allowed_source_heads:
        raise ValueError("Authenticated principal is not admitted for envelope source_head")

    control = frame.get("transport_control")
    if not isinstance(control, dict):
        raise ValueError("transport_control is required")
    if control.get("network_io_performed_by_reference") is not False:
        raise ValueError("Reference transport must not claim network I/O")
    if control.get("socket_listener_enabled") is not False:
        raise ValueError("Reference transport must not enable a socket listener")
    if control.get("automatic_retry_permitted") is not False:
        raise ValueError("Automatic retry must remain disabled")
    if control.get("authority_delta") != 0 or control.get("mass_effect_budget_delta") != 0:
        raise ValueError("Transport cannot alter authority or mass-effect budget")

    issued_at_ms = frame.get("issued_at_ms")
    ttl_ms = frame.get("ttl_ms")
    nonce = frame.get("nonce")
    if isinstance(issued_at_ms, bool) or not isinstance(issued_at_ms, int):
        raise ValueError("issued_at_ms must be an integer")
    if isinstance(ttl_ms, bool) or not isinstance(ttl_ms, int) or not 1 <= ttl_ms <= MAX_TTL_MS:
        raise ValueError("Invalid ttl_ms")
    if not isinstance(nonce, str) or len(nonce) < 16:
        raise ValueError("Invalid transport nonce")

    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if issued_at_ms > now + MAX_FUTURE_SKEW_MS:
        raise ValueError("Frame timestamp is too far in the future")
    age_ms = now - issued_at_ms
    if age_ms > ttl_ms:
        raise ValueError("Frame is stale")

    replay_key = f"{sender_id}:{key_id}:{nonce}"
    expires_at_ms = issued_at_ms + ttl_ms

    if isinstance(queue_capacity, bool) or not isinstance(queue_capacity, int) or queue_capacity < 1:
        raise ValueError("queue_capacity must be an integer >= 1")
    if isinstance(queue_depth, bool) or not isinstance(queue_depth, int) or queue_depth < 0:
        raise ValueError("queue_depth must be an integer >= 0")
    if queue_depth >= queue_capacity:
        return {
            "schema": "janus.demihead.nexus_transport_admission.v1",
            "status": "HOLD_BACKPRESSURE",
            "frame_sha256": sha256(frame),
            "replay_key_sha256": hashlib.sha256(replay_key.encode("utf-8")).hexdigest(),
            "queue": {"depth": queue_depth, "capacity": queue_capacity},
            "control": {
                "automatic_retry_permitted": False,
                "delivery_performed": False,
                "replay_nonce_consumed": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }

    if not replay_guard.consume(replay_key, expires_at_ms=expires_at_ms, now_ms=now):
        raise ValueError("Replay detected")

    persistent_replay = bool(getattr(replay_guard, "persistent", False))
    replay_kind = str(getattr(replay_guard, "kind", "UNKNOWN"))
    return {
        "schema": "janus.demihead.nexus_transport_admission.v1",
        "status": "AUTHENTICATED_FRAME_ADMITTED",
        "frame_sha256": sha256(frame),
        "envelope_sha256": frame["envelope_sha256"],
        "sender_id": sender_id,
        "key_id": key_id,
        "source_head": source_head,
        "replay_key_sha256": hashlib.sha256(replay_key.encode("utf-8")).hexdigest(),
        "freshness": {"age_ms": max(0, age_ms), "ttl_ms": ttl_ms},
        "authentication": {
            "hmac_verified": True,
            "key_bound_sender_verified": True,
            "key_bound_source_head_verified": True,
            "human_identity_established": False,
            "world_effect_authorization_established": False,
        },
        "replay_protection": {
            "guard_kind": replay_kind,
            "persistent": persistent_replay,
            "nonce_consumed_atomically": True,
        },
        "control": {
            "delivery_performed": False,
            "target_execution_performed": False,
            "automatic_retry_permitted": False,
            "network_io_performed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def _test_principals(key: bytes) -> dict[str, dict[str, Any]]:
    return {
        "TEST_KEY": {
            "key": key,
            "sender_id": "DEMIHEAD.LOCAL",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
        }
    }


def self_test() -> dict[str, Any]:
    key = b"test-only-non-production-key"
    principals = _test_principals(key)
    envelope = {
        "schema": NEXUS_ENVELOPE_SCHEMA,
        "contract": "JANUS_NEXUS_HABITAT_V1",
        "envelope_id": "transport-selftest-001",
        "source_head": "GUARDIAN",
        "target_head": "RELEASE_CONTROL",
        "payload_kind": "GUARDIAN_RESULT",
        "payload_ref": {"sha256": "0" * 64},
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
    issued = 1_800_000_000_000
    frame = build_frame(
        envelope,
        sender_id="DEMIHEAD.LOCAL",
        key_id="TEST_KEY",
        key=key,
        issued_at_ms=issued,
        nonce="00112233445566778899aabbccddeeff",
        ttl_ms=30_000,
    )
    guard = MemoryReplayGuard()
    admitted = validate_frame(frame, principal_lookup=principals, replay_guard=guard, now_ms=issued + 100)
    checks = {
        "authenticated_frame_admitted": admitted["status"] == "AUTHENTICATED_FRAME_ADMITTED",
        "sender_binding_verified": admitted["authentication"]["key_bound_sender_verified"] is True,
        "source_head_binding_verified": admitted["authentication"]["key_bound_source_head_verified"] is True,
        "human_identity_not_claimed": admitted["authentication"]["human_identity_established"] is False,
        "world_effect_authorization_not_claimed": admitted["authentication"]["world_effect_authorization_established"] is False,
        "delivery_not_performed": admitted["control"]["delivery_performed"] is False,
        "network_io_not_performed": admitted["control"]["network_io_performed"] is False,
        "replay_consumed_atomically": admitted["replay_protection"]["nonce_consumed_atomically"] is True,
        "memory_replay_guard_not_claimed_persistent": admitted["replay_protection"]["persistent"] is False,
    }

    try:
        validate_frame(frame, principal_lookup=principals, replay_guard=guard, now_ms=issued + 200)
    except ValueError:
        checks["replay_rejected"] = True
    else:
        checks["replay_rejected"] = False

    try:
        validate_frame(frame, principal_lookup=principals, replay_guard=MemoryReplayGuard(), now_ms=issued + 31_000)
    except ValueError:
        checks["stale_rejected"] = True
    else:
        checks["stale_rejected"] = False

    tampered = json.loads(json.dumps(frame))
    tampered["sender_id"] = "ATTACKER"
    try:
        validate_frame(tampered, principal_lookup=principals, replay_guard=MemoryReplayGuard(), now_ms=issued + 100)
    except ValueError:
        checks["hmac_tamper_rejected"] = True
    else:
        checks["hmac_tamper_rejected"] = False

    impersonating = build_frame(
        envelope,
        sender_id="ATTACKER",
        key_id="TEST_KEY",
        key=key,
        issued_at_ms=issued,
        nonce="11112222333344445555666677778888",
    )
    try:
        validate_frame(impersonating, principal_lookup=principals, replay_guard=MemoryReplayGuard(), now_ms=issued + 100)
    except ValueError:
        checks["valid_key_sender_impersonation_rejected"] = True
    else:
        checks["valid_key_sender_impersonation_rejected"] = False

    other_source = json.loads(json.dumps(envelope))
    other_source.update({"source_head": "FUNDAMENTUM", "target_head": "GUARDIAN", "payload_kind": "HOLD_RECEIPT"})
    source_impersonation = build_frame(
        other_source,
        sender_id="DEMIHEAD.LOCAL",
        key_id="TEST_KEY",
        key=key,
        issued_at_ms=issued,
        nonce="99990000111122223333444455556666",
    )
    try:
        validate_frame(source_impersonation, principal_lookup=principals, replay_guard=MemoryReplayGuard(), now_ms=issued + 100)
    except ValueError:
        checks["valid_key_source_head_impersonation_rejected"] = True
    else:
        checks["valid_key_source_head_impersonation_rejected"] = False

    disabled = {
        "TEST_KEY": {
            "key": key,
            "enabled": False,
            "sender_id": "DEMIHEAD.LOCAL",
            "allowed_source_heads": ["GUARDIAN"],
        }
    }
    try:
        validate_frame(frame, principal_lookup=disabled, replay_guard=MemoryReplayGuard(), now_ms=issued + 100)
    except ValueError:
        checks["disabled_principal_rejected"] = True
    else:
        checks["disabled_principal_rejected"] = False

    backpressure = validate_frame(
        frame,
        principal_lookup=principals,
        replay_guard=MemoryReplayGuard(),
        now_ms=issued + 100,
        queue_depth=8,
        queue_capacity=8,
    )
    checks["backpressure_holds"] = backpressure["status"] == "HOLD_BACKPRESSURE"
    checks["backpressure_no_retry"] = backpressure["control"]["automatic_retry_permitted"] is False
    checks["backpressure_does_not_consume_nonce"] = backpressure["control"]["replay_nonce_consumed"] is False

    invalid_route = json.loads(json.dumps(envelope))
    invalid_route["target_head"] = "PORTAL"
    try:
        build_frame(
            invalid_route,
            sender_id="DEMIHEAD.LOCAL",
            key_id="TEST_KEY",
            key=key,
            issued_at_ms=issued,
            nonce="ffeeddccbbaa99887766554433221100",
        )
    except ValueError:
        checks["semantically_invalid_nexus_route_rejected"] = True
    else:
        checks["semantically_invalid_nexus_route_rejected"] = False

    oversized = json.loads(json.dumps(envelope))
    oversized["payload_ref"]["locator"] = "x" * (MAX_FRAME_BYTES + 1)
    try:
        build_frame(
            oversized,
            sender_id="DEMIHEAD.LOCAL",
            key_id="TEST_KEY",
            key=key,
            issued_at_ms=issued,
            nonce="abcdefabcdefabcdefabcdefabcdefab",
        )
    except ValueError:
        checks["oversized_frame_rejected"] = True
    else:
        checks["oversized_frame_rejected"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "frame": frame,
        "admission": admitted,
        "backpressure": backpressure,
    }


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline authenticated transport contract for JANUS Nexus Habitat.")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        result = self_test()
        write_json(result, args.output)
        return 0 if result["status"] == "PASS" else 1
    parser.error("Reference CLI exposes only --self-test; no socket or live transport is enabled.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
