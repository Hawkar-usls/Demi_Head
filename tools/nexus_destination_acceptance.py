from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from nexus_habitat import HEADS, validate_envelope
from nexus_local_transport import FRAME_SCHEMA, canonical_json_bytes, sha256


ACCEPTANCE_CONTRACT = "JANUS_NEXUS_DESTINATION_ACCEPTANCE_V1"
ACCEPTANCE_SCHEMA = "janus.demihead.nexus_destination_acceptance.v1"
ADMISSION_SCHEMA = "janus.demihead.nexus_transport_admission.v1"
POLICY_SCHEMA = "janus.demihead.nexus_endpoint_policy.v1"


def validate_endpoint_policy(policy: dict[str, Any]) -> None:
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise ValueError("Unexpected Nexus endpoint policy schema")
    endpoint_id = policy.get("endpoint_id")
    if not isinstance(endpoint_id, str) or not endpoint_id.strip():
        raise ValueError("endpoint_id must be a non-empty string")
    if not isinstance(policy.get("enabled"), bool):
        raise ValueError("endpoint enabled must be boolean")
    accepted = policy.get("accepted_target_heads")
    if not isinstance(accepted, list) or not accepted:
        raise ValueError("accepted_target_heads must be a non-empty array")
    if len(set(accepted)) != len(accepted):
        raise ValueError("accepted_target_heads contains duplicates")
    for head in accepted:
        if head not in HEADS:
            raise ValueError(f"Unknown accepted target head: {head}")
    if policy.get("local_dispatch_only") is not True:
        raise ValueError("v1 endpoint policy requires local_dispatch_only=true")
    if policy.get("external_effect_permitted") is not False:
        raise ValueError("endpoint policy cannot authorize external effects")
    if policy.get("authority_delta") != 0 or policy.get("mass_effect_budget_delta") != 0:
        raise ValueError("endpoint policy cannot alter authority or mass-effect budget")


def accept_destination(
    frame: dict[str, Any],
    admission: dict[str, Any],
    endpoint_policy: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(frame, dict) or frame.get("schema") != FRAME_SCHEMA:
        raise ValueError("Unexpected transport frame schema")
    if len(canonical_json_bytes(frame)) > 64 * 1024:
        raise ValueError("Transport frame exceeds acceptance size ceiling")

    envelope = frame.get("envelope")
    validate_envelope(envelope)

    if not isinstance(admission, dict) or admission.get("schema") != ADMISSION_SCHEMA:
        raise ValueError("Unexpected transport admission schema")
    if admission.get("status") != "AUTHENTICATED_FRAME_ADMITTED":
        raise ValueError("Destination accepts only fully admitted transport frames")
    if admission.get("frame_sha256") != sha256(frame):
        raise ValueError("Transport admission is not bound to this frame")
    if admission.get("envelope_sha256") != frame.get("envelope_sha256"):
        raise ValueError("Transport admission envelope binding mismatch")
    if admission.get("source_head") != envelope.get("source_head"):
        raise ValueError("Transport admission source-head binding mismatch")

    admission_control = admission.get("control")
    if not isinstance(admission_control, dict):
        raise ValueError("Transport admission control is required")
    if admission_control.get("delivery_performed") is not False:
        raise ValueError("Acceptance cannot consume an admission that claims delivery")
    if admission_control.get("target_execution_performed") is not False:
        raise ValueError("Acceptance cannot consume an admission that claims execution")
    if admission_control.get("authority_delta") != 0 or admission_control.get("mass_effect_budget_delta") != 0:
        raise ValueError("Transport admission cannot carry authority escalation")

    validate_endpoint_policy(endpoint_policy)
    if endpoint_policy["enabled"] is not True:
        raise ValueError("Destination endpoint is disabled")
    target_head = envelope.get("target_head")
    if target_head not in endpoint_policy["accepted_target_heads"]:
        raise ValueError("Destination endpoint is not bound to envelope target_head")

    frame_control = frame.get("transport_control")
    if not isinstance(frame_control, dict):
        raise ValueError("Transport frame control is required")
    if frame_control.get("network_io_performed_by_reference") is not False:
        raise ValueError("Offline acceptance cannot follow a frame claiming network I/O")
    if frame_control.get("socket_listener_enabled") is not False:
        raise ValueError("Offline acceptance cannot follow a frame with listener enabled")
    if frame_control.get("authority_delta") != 0 or frame_control.get("mass_effect_budget_delta") != 0:
        raise ValueError("Transport frame cannot alter authority")

    return {
        "schema": ACCEPTANCE_SCHEMA,
        "contract": ACCEPTANCE_CONTRACT,
        "status": "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH",
        "endpoint": {
            "endpoint_id": endpoint_policy["endpoint_id"],
            "target_head": target_head,
            "local_dispatch_only": True,
        },
        "binding": {
            "frame_sha256": sha256(frame),
            "envelope_sha256": frame["envelope_sha256"],
            "transport_admission_sha256": sha256(admission),
            "source_head": envelope["source_head"],
            "target_head": target_head,
            "payload_kind": envelope["payload_kind"],
        },
        "acceptance": {
            "endpoint_enabled": True,
            "target_head_binding_verified": True,
            "transport_admission_verified": True,
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
            "TRANSPORT_ADMISSION != DESTINATION_ACCEPTANCE",
            "DESTINATION_ACCEPTANCE != DELIVERY",
            "DESTINATION_ACCEPTANCE != EXECUTION",
            "DESTINATION_ACCEPTANCE != TRUTH",
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

    key = b"destination-test-key-1234"
    issued = 1_800_000_000_000
    envelope = {
        "schema": "janus.demihead.nexus_envelope.v1",
        "contract": "JANUS_NEXUS_HABITAT_V1",
        "envelope_id": "destination-selftest-001",
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
        nonce="destination-selftest-nonce-0001",
    )
    principals = {
        "GUARDIAN_E1": {
            "key": key,
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
    }
    admission = validate_frame(
        frame,
        principal_lookup=principals,
        replay_guard=MemoryReplayGuard(),
        now_ms=issued + 100,
    )
    policy = {
        "schema": POLICY_SCHEMA,
        "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
        "enabled": True,
        "accepted_target_heads": ["RELEASE_CONTROL"],
        "local_dispatch_only": True,
        "external_effect_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    receipt = accept_destination(frame, admission, policy)
    checks = {
        "destination_accepts_matching_frame": receipt["status"] == "DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH",
        "delivery_not_claimed": receipt["acceptance"]["delivery_performed"] is False,
        "execution_not_claimed": receipt["acceptance"]["target_execution_performed"] is False,
        "truth_not_claimed": receipt["acceptance"]["acceptance_is_truth"] is False,
        "world_effect_not_authorized": receipt["acceptance"]["acceptance_is_world_effect_authorization"] is False,
    }

    wrong = json.loads(json.dumps(policy))
    wrong["accepted_target_heads"] = ["REGISTRY"]
    try:
        accept_destination(frame, admission, wrong)
    except ValueError:
        checks["wrong_target_endpoint_rejected"] = True
    else:
        checks["wrong_target_endpoint_rejected"] = False

    disabled = json.loads(json.dumps(policy))
    disabled["enabled"] = False
    try:
        accept_destination(frame, admission, disabled)
    except ValueError:
        checks["disabled_endpoint_rejected"] = True
    else:
        checks["disabled_endpoint_rejected"] = False

    forged = json.loads(json.dumps(admission))
    forged["frame_sha256"] = "f" * 64
    try:
        accept_destination(frame, forged, policy)
    except ValueError:
        checks["forged_admission_binding_rejected"] = True
    else:
        checks["forged_admission_binding_rejected"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "receipt": receipt,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Issue local destination acceptance receipts for admitted Nexus frames.")
    parser.add_argument("--frame", type=Path)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--policy", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            if args.frame is None or args.admission is None or args.policy is None:
                parser.error("provide --frame, --admission and --policy, or --self-test")
            result = accept_destination(load_json(args.frame), load_json(args.admission), load_json(args.policy))
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return 0 if result.get("status") != "FAIL" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_destination_acceptance: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
