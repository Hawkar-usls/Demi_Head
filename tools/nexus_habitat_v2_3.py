from __future__ import annotations

from typing import Any, Mapping

import aifc_witness_adapter as aifc
import nexus_habitat as v1
import nexus_habitat_v2_2 as v22

CONTRACT = "JANUS_NEXUS_HABITAT_V2_3"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2_3"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2_3"

HEADS = dict(v22.HEADS)
HEADS["AIFC_WITNESS"] = v1.HeadRule(
    role="INDEPENDENT_WITNESS_AND_EVIDENCE_PROTOCOL",
    repository=aifc.SOURCE_REPOSITORY,
    accepts=(),
    emits=("EVIDENCE_CANDIDATE",),
)
NEW_ROUTES = frozenset({("AIFC_WITNESS", "FUNDAMENTUM", "EVIDENCE_CANDIDATE")})
ROUTES = frozenset(set(v22.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2.3 envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2.3 schema or contract mismatch")
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


def build_aifc_envelope(summary: Mapping[str, Any], *, envelope_id: str | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate = aifc.build_candidate(summary)
    envelope = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-3-aifc-{summary['package_id']}",
        "source_head": "AIFC_WITNESS",
        "target_head": "FUNDAMENTUM",
        "payload_kind": "EVIDENCE_CANDIDATE",
        "payload_ref": {
            "sha256": candidate["candidate_sha256"],
            "locator": f"memory://aifc-witness/{summary['package_id']}",
        },
        "trace": [],
        "control": {
            "read_only_transfer": True,
            "external_effect_permitted": False,
            "delivery_claimed": False,
            "admission_claimed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "ttl_hops": 4,
        },
    }
    validate_envelope(envelope)
    return candidate, envelope


def verify_aifc_envelope(envelope: Mapping[str, Any], summary: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if not aifc.verify_candidate(summary, candidate):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "AIFC_WITNESS"
        and envelope.get("target_head") == "FUNDAMENTUM"
        and envelope.get("payload_kind") == "EVIDENCE_CANDIDATE"
        and envelope.get("payload_ref", {}).get("sha256") == candidate.get("candidate_sha256")
        and candidate.get("authority_delta") == 0
        and candidate.get("mass_effect_budget_delta") == 0
        and candidate.get("fundamentum_boundary", {}).get("route_is_fundamentum_admission") is False
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
            "fundamentum_evaluation_performed_by_router": False,
            "evidence_admission_performed": False,
        },
        "claim_ceiling": {
            "route_is_evidence_admission": False,
            "aifc_grade_is_world_truth": False,
            "physical_retrocausality_established": False,
            "physical_mechanism_established": False,
            "external_authority": False,
        },
    }


def habitat_snapshot() -> dict[str, Any]:
    return {
        "schema": "janus.demihead.habitat_snapshot.v2_3",
        "contract": CONTRACT,
        "parent_contract": v22.CONTRACT,
        "new_heads": ["AIFC_WITNESS"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "head_count": len(HEADS),
        "route_count": len(ROUTES),
        "source_repository": aifc.SOURCE_REPOSITORY,
        "source_sha": aifc.SOURCE_SHA,
        "global_control": {
            "nexus_v2_2_rewritten": False,
            "read_only_coordination": True,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "evidence_candidate_is_admission": False,
            "grade_is_truth": False,
        },
    }
