from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import sys
import time
from pathlib import Path
from typing import Any, MutableSet


FRAME_SCHEMA = "janus.demihead.nexus_transport_frame.v1"
TRANSPORT_CONTRACT = "JANUS_NEXUS_LOCAL_TRANSPORT_V1"
NEXUS_ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v1"
MAX_FRAME_BYTES = 64 * 1024
DEFAULT_TTL_MS = 30_000
MAX_TTL_MS = 120_000
MAX_FUTURE_SKEW_MS = 5_000


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _auth_payload(frame: dict[str, Any]) -> dict[str, Any]:
    unsigned = json.loads(json.dumps(frame))
    unsigned.pop("auth", None)
    return unsigned


def _hmac_hex(key: bytes, payload: dict[str, Any]) -> str:
    return hmac.new(key, canonical_json_bytes(payload), hashlib.sha256).hexdigest()


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
    if not isinstance(envelope, dict) or envelope.get("schema") != NEXUS_ENVELOPE_SCHEMA:
        raise ValueError("Transport accepts only Nexus envelopes")
    if not sender_id.strip() or not key_id.strip():
        raise ValueError("sender_id and key_id are required")
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
    raw_size = len(canonical_json_bytes(frame))
    if raw_size > MAX_FRAME_BYTES:
        raise ValueError("transport frame exceeds maximum size")
    frame["auth"] = {
        "algorithm": "HMAC-SHA256",
        "tag": _hmac_hex(key, _auth_payload(frame)),
    }
    return frame


def validate_frame(
    frame: dict[str, Any],
    *,
    key_lookup: dict[str, bytes],
    now_ms: int | None = None,
    replay_cache: MutableSet[str] | None = None,
    queue_depth: int = 0,
    queue_capacity: int = 128,
) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != FRAME_SCHEMA:
        raise ValueError("Unexpected transport frame schema")
    if frame.get("contract") != TRANSPORT_CONTRACT:
        raise ValueError("Transport contract mismatch")

    key_id = frame.get("key_id")
    if not isinstance(key_id, str) or key_id not in key_lookup:
        raise ValueError("Unknown transport key_id")
    key = key_lookup[key_id]
    if not isinstance(key, bytes) or len(key) < 16:
        raise ValueError("Invalid transport key material")

    envelope = frame.get("envelope")
    if not isinstance(envelope, dict) or envelope.get("schema") != NEXUS_ENVELOPE_SCHEMA:
        raise ValueError("Transport frame does not contain a Nexus envelope")
    if frame.get("envelope_sha256") != sha256(envelope):
        raise ValueError("Envelope hash binding mismatch")

    auth = frame.get("auth")
    if not isinstance(auth, dict) or auth.get("algorithm") != "HMAC-SHA256":
        raise ValueError("Unsupported transport authentication")
    tag = auth.get("tag")
    if not isinstance(tag, str) or len(tag) != 64:
        raise ValueError("Invalid HMAC tag")
    expected = _hmac_hex(key, _auth_payload(frame))
    if not hmac.compare_digest(tag, expected):
        raise ValueError("Transport HMAC verification failed")

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

    replay_key = f"{frame.get('sender_id')}:{key_id}:{nonce}"
    if replay_cache is not None and replay_key in replay_cache:
        raise ValueError("Replay detected")

    if isinstance(queue_capacity, bool) or not isinstance(queue_capacity, int) or queue_capacity < 1:
        raise ValueError("queue_capacity must be an integer >= 1")
    if isinstance(queue_depth, bool) or not isinstance(queue_depth, int) or queue_depth < 0:
        raise ValueError("queue_depth must be an integer >= 0")
    if queue_depth >= queue_capacity:
        return {
            "schema": "janus.demihead.nexus_transport_admission.v1",
            "status": "HOLD_BACKPRESSURE",
            "frame_sha256": sha256(frame),
            "replay_key": replay_key,
            "queue": {
                "depth": queue_depth,
                "capacity": queue_capacity,
            },
            "control": {
                "automatic_retry_permitted": False,
                "delivery_performed": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }

    if replay_cache is not None:
        replay_cache.add(replay_key)

    return {
        "schema": "janus.demihead.nexus_transport_admission.v1",
        "status": "AUTHENTICATED_FRAME_ADMITTED",
        "frame_sha256": sha256(frame),
        "envelope_sha256": frame["envelope_sha256"],
        "sender_id": frame.get("sender_id"),
        "key_id": key_id,
        "replay_key": replay_key,
        "freshness": {
            "age_ms": max(0, age_ms),
            "ttl_ms": ttl_ms,
        },
        "control": {
            "delivery_performed": False,
            "target_execution_performed": False,
            "authentication_is_human_identity": False,
            "authentication_is_authorization": False,
            "automatic_retry_permitted": False,
            "network_io_performed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def self_test() -> dict[str, Any]:
    key = b"test-only-non-production-key"
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
    cache: set[str] = set()
    admitted = validate_frame(
        frame,
        key_lookup={"TEST_KEY": key},
        now_ms=issued + 100,
        replay_cache=cache,
    )
    checks = {
        "authenticated_frame_admitted": admitted["status"] == "AUTHENTICATED_FRAME_ADMITTED",
        "delivery_not_performed": admitted["control"]["delivery_performed"] is False,
        "auth_not_human_identity": admitted["control"]["authentication_is_human_identity"] is False,
        "auth_not_authorization": admitted["control"]["authentication_is_authorization"] is False,
        "network_io_not_performed": admitted["control"]["network_io_performed"] is False,
    }

    try:
        validate_frame(
            frame,
            key_lookup={"TEST_KEY": key},
            now_ms=issued + 200,
            replay_cache=cache,
        )
    except ValueError:
        checks["replay_rejected"] = True
    else:
        checks["replay_rejected"] = False

    stale = json.loads(json.dumps(frame))
    try:
        validate_frame(stale, key_lookup={"TEST_KEY": key}, now_ms=issued + 31_000)
    except ValueError:
        checks["stale_rejected"] = True
    else:
        checks["stale_rejected"] = False

    tampered = json.loads(json.dumps(frame))
    tampered["sender_id"] = "ATTACKER"
    try:
        validate_frame(tampered, key_lookup={"TEST_KEY": key}, now_ms=issued + 100)
    except ValueError:
        checks["tamper_rejected"] = True
    else:
        checks["tamper_rejected"] = False

    backpressure = validate_frame(
        frame,
        key_lookup={"TEST_KEY": key},
        now_ms=issued + 100,
        replay_cache=set(),
        queue_depth=8,
        queue_capacity=8,
    )
    checks["backpressure_holds"] = backpressure["status"] == "HOLD_BACKPRESSURE"
    checks["backpressure_no_retry"] = backpressure["control"]["automatic_retry_permitted"] is False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "frame": frame,
        "admission": admitted,
        "backpressure": backpressure,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected a top-level JSON object")
    return value


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
