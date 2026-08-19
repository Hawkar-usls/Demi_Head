from __future__ import annotations

from typing import Any, Mapping

import nexus_habitat as v1
import nexus_habitat_v2 as v2
import skingpt_observation_adapter as skin

CONTRACT = "JANUS_NEXUS_HABITAT_V2_1"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2_1"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2_1"

HEADS = dict(v2.HEADS)
HEADS["SKINGPT"] = v1.HeadRule(
    role="PHYSICAL_SENSORY_SHELL_TELEMETRY_SOURCE",
    repository=skin.SOURCE_REPOSITORY,
    accepts=(),
    emits=("TELEMETRY_SAMPLE",),
)
NEW_ROUTES = frozenset({("SKINGPT", "OBSERVER", "TELEMETRY_SAMPLE")})
ROUTES = frozenset(set(v2.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2.1 envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2.1 schema or contract mismatch")
    source = envelope.get("source_head")
    target = envelope.get("target_head")
    kind = envelope.get("payload_kind")
    if source not in HEADS or target not in HEADS:
        raise ValueError("Unknown source or target head")
    if kind not in HEADS[source].emits or kind not in HEADS[target].accepts:
        raise ValueError("Payload kind is not compatible with declared heads")
    if (source, target, kind) not in ROUTES:
        raise ValueError("Route is not explicitly admitted")
    payload_ref = envelope.get("payload_ref")
    if not isinstance(payload_ref, Mapping) or not _is_hex64(payload_ref.get("sha256")):
        raise ValueError("payload_ref.sha256 must be lowercase hex64")
    control = envelope.get("control")
    if not isinstance(control, Mapping):
        raise ValueError("control must be an object")
    if control.get("authority_delta") != 0:
        raise ValueError("authority_delta must remain zero")
    if control.get("mass_effect_budget_delta") != 0:
        raise ValueError("mass_effect_budget_delta must remain zero")
    if control.get("read_only_transfer") is not True:
        raise ValueError("transfer must be read-only")
    if control.get("external_effect_permitted") is not False:
        raise ValueError("external effects are not permitted")
    if control.get("delivery_claimed") is not False:
        raise ValueError("route cannot claim delivery")
    ttl = control.get("ttl_hops")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 8:
        raise ValueError("ttl_hops must be an integer in [1,8]")
    trace = envelope.get("trace")
    if not isinstance(trace, list) or len(trace) >= ttl:
        raise ValueError("invalid or exhausted trace")
    if any(hop not in HEADS for hop in trace):
        raise ValueError("trace contains an unknown head")


def build_skingpt_envelope(frame: Mapping[str, Any], *, envelope_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    sample = skin.build_sample(frame)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-1-skingpt-{frame['seq']}",
        "source_head": "SKINGPT",
        "target_head": "OBSERVER",
        "payload_kind": "TELEMETRY_SAMPLE",
        "payload_ref": {
            "sha256": sample["sample_sha256"],
            "locator": f"memory://skingpt/telemetry/{sample['source']['source_identity_sha256']}/{frame['seq']}",
        },
        "trace": [],
        "control": {
            "read_only_transfer": True,
            "external_effect_permitted": False,
            "delivery_claimed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "ttl_hops": 4,
        },
    }
    validate_envelope(envelope)
    return sample, envelope


def verify_skingpt_envelope(envelope: Mapping[str, Any], frame: Mapping[str, Any], sample: Mapping[str, Any]) -> bool:
    if not skin.verify_sample(frame, sample):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "SKINGPT"
        and envelope.get("target_head") == "OBSERVER"
        and envelope.get("payload_kind") == "TELEMETRY_SAMPLE"
        and envelope.get("payload_ref", {}).get("sha256") == sample.get("sample_sha256")
        and sample.get("authority_delta") == 0
        and sample.get("mass_effect_budget_delta") == 0
        and sample.get("claim_ceiling", {}).get("telemetry_sample_is_truth") is False
    )


def route_receipt(envelope: Mapping[str, Any]) -> dict[str, Any]:
    validate_envelope(envelope)
    return {
        "schema": ROUTE_RECEIPT_SCHEMA,
        "contract": CONTRACT,
        "status": "ROUTE_ADMITTED_READ_ONLY",
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": v1.sha256(dict(envelope)),
        "source_head": envelope["source_head"],
        "target_head": envelope["target_head"],
        "payload_kind": envelope["payload_kind"],
        "payload_sha256": envelope["payload_ref"]["sha256"],
        "routing": {
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "delivery_performed": False,
            "observation_signal_created_by_router": False,
            "external_effect_permitted": False,
        },
        "claim_ceiling": {
            "route_is_delivery": False,
            "telemetry_is_observation_signal": False,
            "telemetry_is_truth": False,
            "sensor_validation_established": False,
            "medical_or_safety_authority": False,
        },
    }


def habitat_snapshot() -> dict[str, Any]:
    return {
        "schema": "janus.demihead.habitat_snapshot.v2_1",
        "contract": CONTRACT,
        "parent_contract": v2.CONTRACT,
        "new_heads": ["SKINGPT"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "head_count": len(HEADS),
        "route_count": len(ROUTES),
        "source_repository": skin.SOURCE_REPOSITORY,
        "source_sha": skin.SOURCE_SHA,
        "source_schema_blob_sha": skin.SOURCE_SCHEMA_BLOB_SHA,
        "global_control": {
            "nexus_v2_rewritten": False,
            "read_only_coordination": True,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "raw_sensor_frame_is_observation_signal": False,
            "telemetry_sample_is_truth": False,
        },
    }
