import hashlib
import json
from datetime import datetime, timezone

from probes.network_sender_approval_binding import approval_coordinates, verify_binding


def _canon(x):
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _envelope():
    body = {
        "schema": "janus.sender_request_envelope.v1",
        "status": "NETWORK_SEND_REQUEST_UNAUTHORIZED",
        "bindings": {"target": "http://a", "path": "/api/device/data"},
        "authority": {"authorized": False},
    }
    body["envelope_sha256"] = hashlib.sha256(_canon(body)).hexdigest()
    return body


def _approval(envelope, expires_at="2099-01-01T00:00:00Z"):
    coords = approval_coordinates(envelope)
    body = {
        "schema": "janus.sovereign_lock.approval.v2",
        "proposal_sha256": coords["proposal_sha256"],
        "target_path": coords["target_path"],
        "approved_by_label": "human-review",
        "nonce": "n-1",
        "expires_at": expires_at,
        "identity_boundary": "LABEL_IS_NOT_CRYPTOGRAPHIC_IDENTITY_PROOF",
    }
    body["approval_id"] = hashlib.sha256(_canon(body)).hexdigest()
    return body


def test_valid_binding_still_does_not_grant_network_authority():
    env = _envelope()
    approval = _approval(env)
    r = verify_binding(env, approval, now=datetime(2026, 8, 25, tzinfo=timezone.utc))
    assert r["binding_valid"] is True
    assert r["network_authorized"] is False
    assert r["status"] == "BINDING_VALID_NETWORK_AUTHORITY_STILL_BLOCKED"


def test_target_or_envelope_change_fails_binding():
    env = _envelope()
    approval = _approval(env)
    approval["target_path"] = "network::http://b/api/device/data"
    check = dict(approval); check.pop("approval_id")
    approval["approval_id"] = hashlib.sha256(_canon(check)).hexdigest()
    assert verify_binding(env, approval)["reason"] == "target_mismatch"


def test_expiry_and_replay_fail_closed():
    env = _envelope()
    expired = _approval(env, "2020-01-01T00:00:00Z")
    r = verify_binding(env, expired, now=datetime(2026, 8, 25, tzinfo=timezone.utc))
    assert r["reason"] == "expired"
    good = _approval(env)
    replay = verify_binding(env, good, consumed_approval_ids=[good["approval_id"]])
    assert replay["reason"] == "replay"
