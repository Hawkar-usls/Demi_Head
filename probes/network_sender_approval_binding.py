from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable

ENVELOPE_SCHEMA = "janus.sender_request_envelope.v1"
APPROVAL_SCHEMA = "janus.sovereign_lock.approval.v2"


def _canon(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _valid_envelope(envelope: dict[str, Any]) -> tuple[bool, str]:
    if not isinstance(envelope, dict) or envelope.get("schema") != ENVELOPE_SCHEMA:
        return False, "envelope_schema"
    claimed = envelope.get("envelope_sha256")
    body = dict(envelope)
    body.pop("envelope_sha256", None)
    actual = hashlib.sha256(_canon(body)).hexdigest()
    if claimed != actual:
        return False, "envelope_hash_mismatch"
    if envelope.get("status") != "NETWORK_SEND_REQUEST_UNAUTHORIZED":
        return False, "unexpected_envelope_status"
    if (envelope.get("authority") or {}).get("authorized") is not False:
        return False, "envelope_authority_boundary"
    return True, "ok"


def approval_coordinates(envelope: dict[str, Any]) -> dict[str, str]:
    valid, reason = _valid_envelope(envelope)
    if not valid:
        raise ValueError(reason)
    bindings = envelope.get("bindings") or {}
    target = str(bindings.get("target") or "").rstrip("/")
    path = str(bindings.get("path") or "")
    if not target or not path.startswith("/"):
        raise ValueError("invalid network target binding")
    return {
        "proposal_sha256": hashlib.sha256(_canon(envelope)).hexdigest(),
        "target_path": f"network::{target}{path}",
        "envelope_sha256": envelope["envelope_sha256"],
    }


def verify_binding(
    envelope: dict[str, Any],
    approval: dict[str, Any],
    *,
    consumed_approval_ids: Iterable[str] = (),
    now: datetime | None = None,
) -> dict[str, Any]:
    valid, reason = _valid_envelope(envelope)
    if not valid:
        return {"binding_valid": False, "network_authorized": False, "reason": reason}
    if not isinstance(approval, dict) or approval.get("schema") != APPROVAL_SCHEMA:
        return {"binding_valid": False, "network_authorized": False, "reason": "approval_schema"}

    coords = approval_coordinates(envelope)
    if approval.get("proposal_sha256") != coords["proposal_sha256"]:
        return {"binding_valid": False, "network_authorized": False, "reason": "proposal_hash_mismatch"}
    if approval.get("target_path") != coords["target_path"]:
        return {"binding_valid": False, "network_authorized": False, "reason": "target_mismatch"}

    check = dict(approval)
    claimed_id = check.pop("approval_id", None)
    if hashlib.sha256(_canon(check)).hexdigest() != claimed_id:
        return {"binding_valid": False, "network_authorized": False, "reason": "approval_receipt_tampered"}

    if claimed_id in {str(x) for x in consumed_approval_ids}:
        return {"binding_valid": False, "network_authorized": False, "reason": "replay"}

    expires_at = approval.get("expires_at")
    if expires_at:
        try:
            exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
            t = now or datetime.now(timezone.utc)
        except Exception:
            return {"binding_valid": False, "network_authorized": False, "reason": "expiry_parse"}
        if t > exp:
            return {"binding_valid": False, "network_authorized": False, "reason": "expired"}

    return {
        "binding_valid": True,
        "network_authorized": False,
        "status": "BINDING_VALID_NETWORK_AUTHORITY_STILL_BLOCKED",
        "approval_id": claimed_id,
        "envelope_sha256": coords["envelope_sha256"],
        "proposal_sha256": coords["proposal_sha256"],
        "target_path": coords["target_path"],
        "boundary": "SOVEREIGN_LOCK_V2_BINDS_HASH_TARGET_NONCE_EXPIRY_REPLAY_BUT_APPROVER_LABEL_IS_NOT_CRYPTOGRAPHIC_IDENTITY_AND_VERIFY_IS_NOT_NETWORK_WRITE_AUTHORITY",
        "next_gate": "EXTERNAL_AUTHORITY_OR_CRYPTOGRAPHIC_IDENTITY_PROOF_THAT_EXPLICITLY_GRANTS_ONE_NETWORK_ATTEMPT",
    }
