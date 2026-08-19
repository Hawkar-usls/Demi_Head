from __future__ import annotations

from typing import Any, Mapping

import i0_measurement_adapter as i0
import nexus_habitat as v1
import nexus_habitat_v2_3 as v23

CONTRACT = "JANUS_NEXUS_HABITAT_V2_4"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2_4"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2_4"

HEADS = dict(v23.HEADS)
HEADS.update(
    {
        "I0_MEASUREMENT": v1.HeadRule(
            role="CONTROLLED_MEASUREMENT_AND_PROOF_OF_OBSERVATION_SOURCE",
            repository=i0.SOURCE_REPOSITORY,
            accepts=(),
            emits=("MEASUREMENT_RECEIPT",),
        ),
        "MEASUREMENT_BROKER": v1.HeadRule(
            role="MEASUREMENT_TO_EVIDENCE_PROJECTION_WITHOUT_PROMOTION",
            repository="Hawkar-usls/Demi_Head",
            accepts=("MEASUREMENT_RECEIPT",),
            emits=("EVIDENCE_CANDIDATE",),
        ),
    }
)
NEW_ROUTES = frozenset(
    {
        ("I0_MEASUREMENT", "MEASUREMENT_BROKER", "MEASUREMENT_RECEIPT"),
        ("MEASUREMENT_BROKER", "FUNDAMENTUM", "EVIDENCE_CANDIDATE"),
    }
)
ROUTES = frozenset(set(v23.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2.4 envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2.4 schema or contract mismatch")
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
    if control.get("admission_claimed") is not False:
        raise ValueError("route cannot claim evidence admission")
    ttl = control.get("ttl_hops")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 8:
        raise ValueError("ttl_hops must be an integer in [1,8]")
    trace = envelope.get("trace")
    if not isinstance(trace, list) or len(trace) >= ttl or any(hop not in HEADS for hop in trace):
        raise ValueError("invalid trace")


def _control() -> dict[str, Any]:
    return {
        "read_only_transfer": True,
        "external_effect_permitted": False,
        "delivery_claimed": False,
        "admission_claimed": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "ttl_hops": 5,
    }


def build_measurement_route(summary: Mapping[str, Any], *, envelope_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    receipt = i0.build_receipt(summary)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-4-i0-{summary['measurement_id']}",
        "source_head": "I0_MEASUREMENT",
        "target_head": "MEASUREMENT_BROKER",
        "payload_kind": "MEASUREMENT_RECEIPT",
        "payload_ref": {
            "sha256": receipt["receipt_sha256"],
            "locator": f"memory://i0-measurement/{summary['measurement_id']}",
        },
        "trace": [],
        "control": _control(),
    }
    validate_envelope(envelope)
    return receipt, envelope


def build_evidence_route(receipt: Mapping[str, Any], *, envelope_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = i0.build_evidence_candidate(receipt)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-4-evidence-{receipt['measurement_id']}",
        "source_head": "MEASUREMENT_BROKER",
        "target_head": "FUNDAMENTUM",
        "payload_kind": "EVIDENCE_CANDIDATE",
        "payload_ref": {
            "sha256": candidate["candidate_sha256"],
            "locator": f"memory://i0-evidence/{receipt['measurement_id']}",
        },
        "trace": ["I0_MEASUREMENT"],
        "control": _control(),
    }
    validate_envelope(envelope)
    return candidate, envelope


def verify_measurement_route(envelope: Mapping[str, Any], summary: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not i0.verify_receipt(summary, receipt):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "I0_MEASUREMENT"
        and envelope.get("target_head") == "MEASUREMENT_BROKER"
        and envelope.get("payload_kind") == "MEASUREMENT_RECEIPT"
        and envelope.get("payload_ref", {}).get("sha256") == receipt.get("receipt_sha256")
        and receipt.get("authority_delta") == 0
        and receipt.get("mass_effect_budget_delta") == 0
    )


def verify_evidence_route(envelope: Mapping[str, Any], receipt: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if not i0.verify_evidence_candidate(receipt, candidate):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "MEASUREMENT_BROKER"
        and envelope.get("target_head") == "FUNDAMENTUM"
        and envelope.get("payload_kind") == "EVIDENCE_CANDIDATE"
        and envelope.get("payload_ref", {}).get("sha256") == candidate.get("candidate_sha256")
        and candidate.get("projection", {}).get("projection_is_evidence_admission") is False
        and candidate.get("projection", {}).get("projection_is_claim_promotion") is False
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
            "claim_promotion_performed": False,
            "evidence_admission_performed": False,
            "fundamentum_evaluation_performed_by_router": False,
        },
        "claim_ceiling": {
            "measurement_receipt_is_truth": False,
            "evidence_projection_is_admission": False,
            "sha256_predictability_established": False,
            "mining_advantage_established": False,
            "energy_savings_established": False,
            "hardware_lifetime_extension_established": False,
            "external_authority": False,
        },
    }


def habitat_snapshot() -> dict[str, Any]:
    return {
        "schema": "janus.demihead.habitat_snapshot.v2_4",
        "contract": CONTRACT,
        "parent_contract": v23.CONTRACT,
        "new_heads": ["I0_MEASUREMENT", "MEASUREMENT_BROKER"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "head_count": len(HEADS),
        "route_count": len(ROUTES),
        "source_repository": i0.SOURCE_REPOSITORY,
        "source_sha": i0.SOURCE_SHA,
        "global_control": {
            "nexus_v2_3_rewritten": False,
            "measurement_is_inference": False,
            "integrity_is_truth": False,
            "missing_is_zero": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
