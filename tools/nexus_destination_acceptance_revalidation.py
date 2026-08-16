from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from nexus_destination_acceptance import accept_destination
from nexus_local_transport import sha256


CONTRACT = "JANUS_NEXUS_DESTINATION_REVALIDATION_V1"
SCHEMA = "janus.demihead.nexus_destination_acceptance_revalidated.v1"


def _validate_current_principal(
    admission: dict[str, Any],
    principal_state: dict[str, Any],
    *,
    now_ms: int,
) -> dict[str, Any]:
    if not isinstance(principal_state, dict):
        raise ValueError("Current principal state is required")

    key_id = admission.get("key_id")
    key_epoch = admission.get("key_epoch")
    sender_id = admission.get("sender_id")
    source_head = admission.get("source_head")

    if principal_state.get("key_id") != key_id:
        raise ValueError("Current principal key_id does not match transport admission")
    if principal_state.get("sender_id") != sender_id:
        raise ValueError("Current principal sender_id does not match transport admission")
    if principal_state.get("epoch") != key_epoch:
        raise ValueError("Current principal epoch does not match admitted frame epoch")
    if principal_state.get("enabled") is not True:
        raise ValueError("Current principal is disabled")
    if principal_state.get("revoked") is not False:
        raise ValueError("Current principal was revoked after transport admission")

    allowed = principal_state.get("allowed_source_heads")
    if not isinstance(allowed, list) or source_head not in allowed:
        raise ValueError("Current principal no longer admits the source head")

    not_before_ms = principal_state.get("not_before_ms")
    not_after_ms = principal_state.get("not_after_ms")
    if isinstance(not_before_ms, bool) or not isinstance(not_before_ms, int):
        raise ValueError("Current principal not_before_ms is invalid")
    if isinstance(not_after_ms, bool) or not isinstance(not_after_ms, int):
        raise ValueError("Current principal not_after_ms is invalid")
    if not not_before_ms <= now_ms < not_after_ms:
        raise ValueError("Current principal is outside its validity window at destination acceptance")

    return {
        "key_id": key_id,
        "key_epoch": key_epoch,
        "sender_id": sender_id,
        "source_head": source_head,
        "enabled": True,
        "revoked": False,
        "valid_now": True,
        "revocation_rechecked_at_acceptance": True,
    }


def accept_destination_revalidated(
    frame: dict[str, Any],
    admission: dict[str, Any],
    endpoint_policy: dict[str, Any],
    principal_state: dict[str, Any],
    *,
    now_ms: int | None = None,
) -> dict[str, Any]:
    now = int(time.time() * 1000) if now_ms is None else int(now_ms)
    current = _validate_current_principal(admission, principal_state, now_ms=now)
    base = accept_destination(frame, admission, endpoint_policy)

    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH_REVALIDATED",
        "binding": {
            "frame_sha256": sha256(frame),
            "transport_admission_sha256": sha256(admission),
            "base_acceptance_sha256": sha256(base),
            "endpoint_id": base["endpoint"]["endpoint_id"],
            "source_head": base["binding"]["source_head"],
            "target_head": base["binding"]["target_head"],
            "payload_kind": base["binding"]["payload_kind"],
        },
        "principal_revalidation": current,
        "acceptance": {
            "endpoint_policy_verified": True,
            "current_revocation_state_verified": True,
            "current_epoch_verified": True,
            "delivery_performed": False,
            "target_execution_performed": False,
            "acceptance_is_truth": False,
            "acceptance_is_world_effect_authorization": False,
        },
        "control": {
            "external_effect_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "laws": [
            "TRANSPORT_ADMISSION != CURRENT_KEY_VALIDITY",
            "REVOCATION_MUST_BE_RECHECKED_AT_ACCEPTANCE",
            "DESTINATION_ACCEPTANCE != DELIVERY",
            "DESTINATION_ACCEPTANCE != EXECUTION",
            "DESTINATION_ACCEPTANCE != WORLD_EFFECT_AUTHORIZATION",
        ],
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected a top-level JSON object")
    return value


def self_test() -> dict[str, Any]:
    from nexus_local_transport import build_frame, validate_frame
    from nexus_replay_ledger import MemoryReplayGuard

    key = b"acceptance-revalidation-key"
    issued = 1_800_000_000_000
    envelope = {
        "schema": "janus.demihead.nexus_envelope.v1",
        "contract": "JANUS_NEXUS_HABITAT_V1",
        "envelope_id": "acceptance-revalidation-selftest",
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
    frame = build_frame(
        envelope,
        sender_id="DEMIHEAD.GUARDIAN",
        key_id="GUARDIAN_E1",
        key_epoch=1,
        key=key,
        issued_at_ms=issued,
        nonce="acceptance-revalidation-nonce-1",
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
    endpoint = {
        "schema": "janus.demihead.nexus_endpoint_policy.v1",
        "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
        "enabled": True,
        "accepted_target_heads": ["RELEASE_CONTROL"],
        "local_dispatch_only": True,
        "external_effect_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
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
    receipt = accept_destination_revalidated(
        frame,
        admission,
        endpoint,
        public_principal,
        now_ms=issued + 200,
    )
    checks = {
        "revalidated_acceptance_succeeds": receipt["status"] == "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH_REVALIDATED",
        "revocation_rechecked": receipt["principal_revalidation"]["revocation_rechecked_at_acceptance"] is True,
        "delivery_not_claimed": receipt["acceptance"]["delivery_performed"] is False,
        "execution_not_claimed": receipt["acceptance"]["target_execution_performed"] is False,
    }

    revoked = json.loads(json.dumps(public_principal))
    revoked["revoked"] = True
    try:
        accept_destination_revalidated(frame, admission, endpoint, revoked, now_ms=issued + 200)
    except ValueError:
        checks["revocation_after_admission_rejected"] = True
    else:
        checks["revocation_after_admission_rejected"] = False

    rolled = json.loads(json.dumps(public_principal))
    rolled["epoch"] = 2
    try:
        accept_destination_revalidated(frame, admission, endpoint, rolled, now_ms=issued + 200)
    except ValueError:
        checks["epoch_rollover_after_admission_rejected"] = True
    else:
        checks["epoch_rollover_after_admission_rejected"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "receipt": receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Revalidate current principal policy before local Nexus destination acceptance.")
    parser.add_argument("--frame", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--endpoint", type=Path)
    parser.add_argument("--principal", type=Path)
    parser.add_argument("--now-ms", type=int)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            if None in (args.frame, args.admission, args.endpoint, args.principal):
                parser.error("provide --frame, --admission, --endpoint and --principal, or --self-test")
            result = accept_destination_revalidated(
                load_json(args.frame),
                load_json(args.admission),
                load_json(args.endpoint),
                load_json(args.principal),
                now_ms=args.now_ms,
            )
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return 0 if result.get("status") != "FAIL" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_destination_acceptance_revalidation: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
