from __future__ import annotations

from typing import Any, Mapping

import nexus_habitat as v1
import nexus_habitat_v2_1 as v21
import swarm_edge_observation_adapter as swarm

CONTRACT = "JANUS_NEXUS_HABITAT_V2_2"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2_2"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2_2"

HEADS = dict(v21.HEADS)
HEADS["SWARM_EDGE"] = v1.HeadRule(
    role="EDGE_PERIPHERAL_NERVOUS_SYSTEM_TELEMETRY_SOURCE",
    repository=swarm.SOURCE_REPOSITORY,
    accepts=(),
    emits=("TELEMETRY_SAMPLE",),
)
NEW_ROUTES = frozenset({("SWARM_EDGE", "OBSERVER", "TELEMETRY_SAMPLE")})
ROUTES = frozenset(set(v21.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2.2 envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2.2 schema or contract mismatch")
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
    if control.get("authority_delta") != 0 or control.get("mass_effect_budget_delta") != 0:
        raise ValueError("authority/effect deltas must remain zero")
    if control.get("read_only_transfer") is not True or control.get("external_effect_permitted") is not False:
        raise ValueError("transfer must remain read-only and effect-free")
    if control.get("delivery_claimed") is not False:
        raise ValueError("route cannot claim delivery")
    ttl = control.get("ttl_hops")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 8:
        raise ValueError("ttl_hops must be an integer in [1,8]")
    trace = envelope.get("trace")
    if not isinstance(trace, list) or len(trace) >= ttl or any(hop not in HEADS for hop in trace):
        raise ValueError("invalid trace")


def build_swarm_envelope(summary: Mapping[str, Any], *, envelope_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    sample = swarm.build_sample(summary)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-2-swarm-{summary['node_id']}-{summary['observed_at_ms']}",
        "source_head": "SWARM_EDGE",
        "target_head": "OBSERVER",
        "payload_kind": "TELEMETRY_SAMPLE",
        "payload_ref": {
            "sha256": sample["sample_sha256"],
            "locator": f"memory://swarm-edge/{sample['node']['semantic_identity_sha256']}/{summary['observed_at_ms']}",
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


def verify_swarm_envelope(envelope: Mapping[str, Any], summary: Mapping[str, Any], sample: Mapping[str, Any]) -> bool:
    if not swarm.verify_sample(summary, sample):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "SWARM_EDGE"
        and envelope.get("target_head") == "OBSERVER"
        and envelope.get("payload_kind") == "TELEMETRY_SAMPLE"
        and envelope.get("payload_ref", {}).get("sha256") == sample.get("sample_sha256")
        and sample.get("authority_delta") == 0
        and sample.get("mass_effect_budget_delta") == 0
        and sample.get("claim_ceiling", {}).get("edge_telemetry_is_command") is False
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
            "command_performed": False,
            "observation_signal_created_by_router": False,
        },
        "claim_ceiling": {
            "route_is_delivery": False,
            "edge_telemetry_is_command": False,
            "stale_telemetry_is_current_truth": False,
            "prediction_or_memory_is_current_presence": False,
            "pool_or_sha_truth_changed": False,
        },
    }


def habitat_snapshot() -> dict[str, Any]:
    return {
        "schema": "janus.demihead.habitat_snapshot.v2_2",
        "contract": CONTRACT,
        "parent_contract": v21.CONTRACT,
        "new_heads": ["SWARM_EDGE"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "head_count": len(HEADS),
        "route_count": len(ROUTES),
        "source_repository": swarm.SOURCE_REPOSITORY,
        "source_sha": swarm.SOURCE_SHA,
        "global_control": {
            "nexus_v2_1_rewritten": False,
            "read_only_coordination": True,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "observer_only_submit_pressure": 0,
            "stale_state_visible": True,
            "prediction_is_current_presence": False,
        },
    }
