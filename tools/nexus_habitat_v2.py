from __future__ import annotations

import copy
import json
from dataclasses import asdict
from typing import Any, Mapping

import cosmos_proof_adapter as cosmos
import nexus_habitat as v1

CONTRACT = "JANUS_NEXUS_HABITAT_V2"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2"

PROOF_REQUEST_KIND = "COSMOS_PROOF_REQUEST"
PROOF_RECEIPT_KIND = "COSMOS_PROOF_RECEIPT"

HEADS = dict(v1.HEADS)
HEADS.update(
    {
        "PROOF_BROKER": v1.HeadRule(
            role="INTENT_BOUND_SPECIALIZED_PROOF_ROUTER",
            repository="Hawkar-usls/Demi_Head",
            accepts=(PROOF_RECEIPT_KIND,),
            emits=(PROOF_REQUEST_KIND,),
        ),
        "COSMOS": v1.HeadRule(
            role="SPECIALIZED_PROOF_PROVIDER_NOT_TRUTH_ARBITER",
            repository=cosmos.PROVIDER_REPOSITORY,
            accepts=(PROOF_REQUEST_KIND,),
            emits=(PROOF_RECEIPT_KIND,),
        ),
    }
)

NEW_ROUTES = frozenset(
    {
        ("PROOF_BROKER", "COSMOS", PROOF_REQUEST_KIND),
        ("COSMOS", "PROOF_BROKER", PROOF_RECEIPT_KIND),
    }
)
ROUTES = frozenset(set(v1.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _head_descriptor(head_id: str) -> dict[str, Any]:
    rule = HEADS[head_id]
    descriptor = {
        "head_id": head_id,
        "role": rule.role,
        "repository": rule.repository,
    }
    if rule.lineage_repository is not None:
        descriptor["lineage_repository"] = rule.lineage_repository
        descriptor["lineage_is_runtime_ownership"] = False
    return descriptor


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2 envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise ValueError("Unexpected Nexus v2 envelope schema")
    if envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2 contract mismatch")

    envelope_id = envelope.get("envelope_id")
    if not isinstance(envelope_id, str) or not envelope_id.strip():
        raise ValueError("envelope_id must be a non-empty string")

    source = envelope.get("source_head")
    target = envelope.get("target_head")
    kind = envelope.get("payload_kind")
    if source not in HEADS or target not in HEADS:
        raise ValueError("Unknown source or target head")
    if not isinstance(kind, str) or not kind:
        raise ValueError("payload_kind must be a non-empty string")
    if kind not in HEADS[source].emits:
        raise ValueError(f"{source} is not admitted to emit {kind}")
    if kind not in HEADS[target].accepts:
        raise ValueError(f"{target} is not admitted to accept {kind}")
    if (source, target, kind) not in ROUTES:
        raise ValueError("Route is not explicitly admitted")

    payload_ref = envelope.get("payload_ref")
    if not isinstance(payload_ref, Mapping):
        raise ValueError("payload_ref must be an object")
    if not _is_hex64(payload_ref.get("sha256")):
        raise ValueError("payload_ref.sha256 must be lowercase hex64")

    control = envelope.get("control")
    if not isinstance(control, Mapping):
        raise ValueError("control must be an object")
    if control.get("authority_delta") != 0:
        raise ValueError("authority_delta must remain zero")
    if control.get("mass_effect_budget_delta") != 0:
        raise ValueError("mass_effect_budget_delta must remain zero")
    if control.get("read_only_transfer") is not True:
        raise ValueError("Nexus v2 transfer must be read-only")
    if control.get("external_effect_permitted") is not False:
        raise ValueError("Nexus v2 cannot authorize external effects")
    if control.get("direct_workspace_mutation") is not False:
        raise ValueError("Direct cross-head workspace mutation is forbidden")
    if control.get("delivery_claimed") is not False:
        raise ValueError("A route envelope cannot claim delivery")

    ttl = control.get("ttl_hops")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 8:
        raise ValueError("ttl_hops must be an integer in [1, 8]")
    trace = envelope.get("trace")
    if not isinstance(trace, list):
        raise ValueError("trace must be an array")
    if len(trace) >= ttl:
        raise ValueError("Envelope hop budget exhausted")
    for hop in trace:
        if hop not in HEADS:
            raise ValueError(f"Unknown trace head: {hop!r}")


def route_receipt(envelope: Mapping[str, Any]) -> dict[str, Any]:
    validate_envelope(envelope)
    source = str(envelope["source_head"])
    target = str(envelope["target_head"])
    return {
        "schema": ROUTE_RECEIPT_SCHEMA,
        "contract": CONTRACT,
        "status": "ROUTE_ADMITTED_READ_ONLY",
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": v1.sha256(dict(envelope)),
        "source_head": source,
        "target_head": target,
        "payload_kind": envelope["payload_kind"],
        "payload_sha256": envelope["payload_ref"]["sha256"],
        "source_descriptor": _head_descriptor(source),
        "target_descriptor": _head_descriptor(target),
        "routing": {
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "external_effect_permitted": False,
            "direct_workspace_mutation": False,
            "delivery_performed": False,
            "provider_execution_performed_by_router": False,
            "next_trace": [*envelope["trace"], source],
        },
        "claim_ceiling": {
            "route_is_delivery": False,
            "route_is_provider_execution": False,
            "route_is_truth": False,
            "route_is_authority": False,
            "P_VS_NP": "OPEN",
        },
    }


def _base_control(ttl_hops: int = 4) -> dict[str, Any]:
    return {
        "read_only_transfer": True,
        "direct_workspace_mutation": False,
        "external_effect_permitted": False,
        "delivery_claimed": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "ttl_hops": ttl_hops,
    }


def build_cosmos_request_envelope(request: Mapping[str, Any], *, envelope_id: str | None = None) -> dict[str, Any]:
    if not cosmos.verify_request(request):
        raise ValueError("COSMOS_PROOF_REQUEST_INVALID")
    return {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-request-{request['request_id']}",
        "source_head": "PROOF_BROKER",
        "target_head": "COSMOS",
        "payload_kind": PROOF_REQUEST_KIND,
        "payload_ref": {
            "sha256": request["request_sha256"],
            "locator": f"memory://cosmos-proof/request/{request['request_id']}",
        },
        "trace": [],
        "control": _base_control(),
    }


def verify_cosmos_request_envelope(envelope: Mapping[str, Any], request: Mapping[str, Any]) -> bool:
    if not cosmos.verify_request(request):
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "PROOF_BROKER"
        and envelope.get("target_head") == "COSMOS"
        and envelope.get("payload_kind") == PROOF_REQUEST_KIND
        and envelope.get("payload_ref", {}).get("sha256") == request.get("request_sha256")
        and request.get("provider_sha") == cosmos.PROVIDER_SHA
        and request.get("canonical_gate") == cosmos.CANONICAL_GATE
        and request.get("operation") == cosmos.OPERATION
    )


def build_cosmos_receipt_envelope(
    request: Mapping[str, Any],
    cosmos_result: Mapping[str, Any],
    receipt: Mapping[str, Any],
    *,
    envelope_id: str | None = None,
) -> dict[str, Any]:
    if not cosmos.verify_receipt(request, cosmos_result, receipt):
        raise ValueError("COSMOS_PROOF_RECEIPT_INVALID")
    if receipt.get("intent_id") != request.get("intent_anchor", {}).get("intent_id"):
        raise ValueError("COSMOS_PROOF_RECEIPT_INTENT_MISMATCH")
    return {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id or f"nexus-v2-receipt-{request['request_id']}",
        "source_head": "COSMOS",
        "target_head": "PROOF_BROKER",
        "payload_kind": PROOF_RECEIPT_KIND,
        "payload_ref": {
            "sha256": receipt["receipt_sha256"],
            "locator": f"memory://cosmos-proof/receipt/{request['request_id']}",
        },
        "trace": ["PROOF_BROKER"],
        "control": _base_control(),
    }


def verify_cosmos_receipt_envelope(
    envelope: Mapping[str, Any],
    request: Mapping[str, Any],
    cosmos_result: Mapping[str, Any],
    receipt: Mapping[str, Any],
) -> bool:
    if not cosmos.verify_receipt(request, cosmos_result, receipt):
        return False
    if receipt.get("intent_id") != request.get("intent_anchor", {}).get("intent_id"):
        return False
    if receipt.get("provider_sha") != cosmos.PROVIDER_SHA:
        return False
    if receipt.get("authority_delta") != 0 or receipt.get("mass_effect_budget_delta") != 0:
        return False
    if receipt.get("P_VS_NP") != "OPEN":
        return False
    try:
        validate_envelope(envelope)
    except ValueError:
        return False
    return (
        envelope.get("source_head") == "COSMOS"
        and envelope.get("target_head") == "PROOF_BROKER"
        and envelope.get("payload_kind") == PROOF_RECEIPT_KIND
        and envelope.get("payload_ref", {}).get("sha256") == receipt.get("receipt_sha256")
    )


def habitat_snapshot() -> dict[str, Any]:
    heads = []
    for head_id in sorted(HEADS):
        descriptor = _head_descriptor(head_id)
        descriptor.update({"availability": "UNKNOWN", "authority_delta": 0})
        heads.append(descriptor)
    return {
        "schema": "janus.demihead.habitat_snapshot.v2",
        "contract": CONTRACT,
        "parent_contract": v1.CONTRACT,
        "parent_heads": sorted(v1.HEADS),
        "parent_routes_sha256": v1.sha256(sorted([list(route) for route in v1.ROUTES])),
        "new_heads": ["PROOF_BROKER", "COSMOS"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "heads": heads,
        "route_count": len(ROUTES),
        "global_control": {
            "nexus_v1_rewritten": False,
            "read_only_coordination": True,
            "mass_effect_budget_delta": 0,
            "external_effect_authority": False,
            "provider_pass_is_truth": False,
            "P_VS_NP": "OPEN",
        },
    }


def describe_contract() -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "parent": v1.CONTRACT,
        "new_heads": {key: asdict(HEADS[key]) for key in ("PROOF_BROKER", "COSMOS")},
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "provider_sha": cosmos.PROVIDER_SHA,
        "canonical_gate": cosmos.CANONICAL_GATE,
        "operation": cosmos.OPERATION,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "P_VS_NP": "OPEN",
    }


if __name__ == "__main__":
    print(json.dumps(describe_contract(), ensure_ascii=False, indent=2, sort_keys=True))
