from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT = "JANUS_NEXUS_HABITAT_V1"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v1"
SNAPSHOT_SCHEMA = "janus.demihead.habitat_snapshot.v1"


@dataclass(frozen=True)
class HeadRule:
    role: str
    repository: str
    accepts: tuple[str, ...]
    emits: tuple[str, ...]


HEADS: dict[str, HeadRule] = {
    "PORTAL": HeadRule(
        role="TYPED_DESTINATION_ROUTER",
        repository="Hawkar-usls/Janus",
        accepts=("ROUTE_REQUEST",),
        emits=("ROUTE_RECEIPT",),
    ),
    "OBSERVER": HeadRule(
        role="READ_ONLY_ENVIRONMENT_OBSERVER",
        repository="Hawkar-usls/Demi_Head",
        accepts=("TELEMETRY_SAMPLE",),
        emits=("OBSERVATION_SIGNAL",),
    ),
    "HRAIN": HeadRule(
        role="STRUCTURAL_CONTEXT",
        repository="Hawkar-usls/Hrain",
        accepts=("CONTEXT_REQUEST",),
        emits=("HEMISPHERE_PACKET",),
    ),
    "INAIHR": HeadRule(
        role="ASSOCIATIVE_CONTEXT",
        repository="Hawkar-usls/iNaiHR",
        accepts=("CONTEXT_REQUEST",),
        emits=("HEMISPHERE_PACKET",),
    ),
    "BICAMERAL_BRIDGE": HeadRule(
        role="READ_ONLY_CONTEXT_BINDER",
        repository="Hawkar-usls/Demi_Head",
        accepts=("HEMISPHERE_PACKET",),
        emits=("BICAMERAL_RESULT",),
    ),
    "FUNDAMENTUM": HeadRule(
        role="WITNESS_LEDGER_TRUTH_GUARD",
        repository="Hawkar-usls/Janus-Fundamentum",
        accepts=("EVIDENCE_CANDIDATE", "BICAMERAL_RESULT"),
        emits=("EVIDENCE_RECEIPT", "HOLD_RECEIPT"),
    ),
    "GUARDIAN": HeadRule(
        role="BOUNDED_EVIDENCE_STATE",
        repository="Hawkar-usls/Demi_Head",
        accepts=("EVIDENCE_RECEIPT", "HOLD_RECEIPT", "OBSERVATION_SIGNAL"),
        emits=("GUARDIAN_RESULT",),
    ),
    "RELEASE_CONTROL": HeadRule(
        role="STOP_OR_CONTINUE_GATE",
        repository="Hawkar-usls/Demi_Head",
        accepts=("GUARDIAN_RESULT",),
        emits=("RELEASE_RECEIPT",),
    ),
    "REGISTRY": HeadRule(
        role="PROVENANCE_ARCHIVE",
        repository="Hawkar-usls/janus-meta-registry",
        accepts=(
            "ROUTE_RECEIPT",
            "OBSERVATION_SIGNAL",
            "BICAMERAL_RESULT",
            "EVIDENCE_RECEIPT",
            "HOLD_RECEIPT",
            "GUARDIAN_RESULT",
            "RELEASE_RECEIPT",
        ),
        emits=("REGISTRY_RECEIPT",),
    ),
}

# Explicitly admitted edges. A head cannot route merely because payload kinds happen to match.
ROUTES: frozenset[tuple[str, str, str]] = frozenset(
    {
        ("PORTAL", "REGISTRY", "ROUTE_RECEIPT"),
        ("OBSERVER", "GUARDIAN", "OBSERVATION_SIGNAL"),
        ("OBSERVER", "REGISTRY", "OBSERVATION_SIGNAL"),
        ("HRAIN", "BICAMERAL_BRIDGE", "HEMISPHERE_PACKET"),
        ("INAIHR", "BICAMERAL_BRIDGE", "HEMISPHERE_PACKET"),
        ("BICAMERAL_BRIDGE", "FUNDAMENTUM", "BICAMERAL_RESULT"),
        ("BICAMERAL_BRIDGE", "REGISTRY", "BICAMERAL_RESULT"),
        ("FUNDAMENTUM", "GUARDIAN", "EVIDENCE_RECEIPT"),
        ("FUNDAMENTUM", "GUARDIAN", "HOLD_RECEIPT"),
        ("FUNDAMENTUM", "REGISTRY", "EVIDENCE_RECEIPT"),
        ("FUNDAMENTUM", "REGISTRY", "HOLD_RECEIPT"),
        ("GUARDIAN", "RELEASE_CONTROL", "GUARDIAN_RESULT"),
        ("GUARDIAN", "REGISTRY", "GUARDIAN_RESULT"),
        ("RELEASE_CONTROL", "REGISTRY", "RELEASE_RECEIPT"),
    }
)


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_envelope(envelope: dict[str, Any]) -> None:
    if not isinstance(envelope, dict):
        raise ValueError("Nexus envelope must be a JSON object")
    if envelope.get("schema") != ENVELOPE_SCHEMA:
        raise ValueError("Unexpected Nexus envelope schema")
    if envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus contract mismatch")

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
    if not isinstance(payload_ref, dict):
        raise ValueError("payload_ref must be an object")
    digest = payload_ref.get("sha256")
    if not isinstance(digest, str) or len(digest) != 64:
        raise ValueError("payload_ref.sha256 must be a 64-character digest")
    if any(char not in "0123456789abcdef" for char in digest.lower()):
        raise ValueError("payload_ref.sha256 must be hexadecimal")

    control = envelope.get("control")
    if not isinstance(control, dict):
        raise ValueError("control must be an object")
    required_zero = ("authority_delta", "mass_effect_budget_delta")
    for field in required_zero:
        if control.get(field) != 0:
            raise ValueError(f"{field} must remain zero")
    if control.get("read_only_transfer") is not True:
        raise ValueError("Nexus transfer must be read-only")
    if control.get("external_effect_permitted") is not False:
        raise ValueError("Nexus envelope cannot authorize external effects")
    if control.get("direct_workspace_mutation") is not False:
        raise ValueError("Direct cross-head workspace mutation is forbidden")

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


def route_receipt(envelope: dict[str, Any]) -> dict[str, Any]:
    validate_envelope(envelope)
    source = envelope["source_head"]
    target = envelope["target_head"]
    return {
        "schema": "janus.demihead.nexus_route_receipt.v1",
        "contract": CONTRACT,
        "status": "ROUTE_ADMITTED_READ_ONLY",
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": sha256(envelope),
        "source_head": source,
        "target_head": target,
        "payload_kind": envelope["payload_kind"],
        "source_repository": HEADS[source].repository,
        "target_repository": HEADS[target].repository,
        "routing": {
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "external_effect_permitted": False,
            "direct_workspace_mutation": False,
            "next_trace": [*envelope["trace"], source],
        },
        "claim_ceiling": {
            "delivery_performed": False,
            "provider_realization_established": False,
            "target_acceptance_established": False,
            "truth_claim_made": False,
            "route_is_authority": False,
        },
    }


def habitat_snapshot(availability: dict[str, str] | None = None) -> dict[str, Any]:
    availability = availability or {}
    heads = []
    for head_id, rule in sorted(HEADS.items()):
        state = availability.get(head_id, "UNKNOWN")
        if state not in {"READY", "DEGRADED", "HOLD", "OFFLINE", "UNKNOWN"}:
            raise ValueError(f"Invalid availability state for {head_id}: {state}")
        heads.append(
            {
                "head_id": head_id,
                "role": rule.role,
                "repository": rule.repository,
                "availability": state,
                "authority_delta": 0,
            }
        )
    return {
        "schema": SNAPSHOT_SCHEMA,
        "contract": CONTRACT,
        "heads": heads,
        "route_count": len(ROUTES),
        "global_control": {
            "read_only_coordination": True,
            "mass_effect_budget_delta": 0,
            "external_effect_authority": False,
            "missing_head_means_success": False,
            "degraded_head_may_be_silently_replaced": False,
        },
    }


def _example_envelope() -> dict[str, Any]:
    payload = {"example": "bounded evidence receipt"}
    return {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": "selftest-fundamentum-guardian-001",
        "source_head": "FUNDAMENTUM",
        "target_head": "GUARDIAN",
        "payload_kind": "EVIDENCE_RECEIPT",
        "payload_ref": {
            "sha256": sha256(payload),
            "locator": "memory://selftest/evidence-receipt",
        },
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


def self_test() -> dict[str, Any]:
    envelope = _example_envelope()
    receipt = route_receipt(envelope)
    checks: dict[str, bool] = {
        "admitted_route_yields_receipt": receipt["status"] == "ROUTE_ADMITTED_READ_ONLY",
        "route_does_not_deliver": receipt["claim_ceiling"]["delivery_performed"] is False,
        "route_does_not_grant_authority": receipt["routing"]["authority_delta"] == 0,
        "route_does_not_grant_mass_effect": receipt["routing"]["mass_effect_budget_delta"] == 0,
        "route_does_not_authorize_external_effect": receipt["routing"]["external_effect_permitted"] is False,
        "habitat_lists_all_heads": len(habitat_snapshot()["heads"]) == len(HEADS),
    }

    bad_route = json.loads(json.dumps(envelope))
    bad_route["target_head"] = "PORTAL"
    try:
        route_receipt(bad_route)
    except ValueError:
        checks["unadmitted_route_fails_closed"] = True
    else:
        checks["unadmitted_route_fails_closed"] = False

    authority_escalation = json.loads(json.dumps(envelope))
    authority_escalation["control"]["authority_delta"] = 1
    try:
        route_receipt(authority_escalation)
    except ValueError:
        checks["authority_escalation_fails_closed"] = True
    else:
        checks["authority_escalation_fails_closed"] = False

    exhausted = json.loads(json.dumps(envelope))
    exhausted["control"]["ttl_hops"] = 2
    exhausted["trace"] = ["HRAIN", "BICAMERAL_BRIDGE"]
    try:
        route_receipt(exhausted)
    except ValueError:
        checks["hop_exhaustion_fails_closed"] = True
    else:
        checks["hop_exhaustion_fails_closed"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "receipt": receipt,
        "habitat": habitat_snapshot(
            {
                "PORTAL": "READY",
                "OBSERVER": "DEGRADED",
                "HRAIN": "READY",
                "INAIHR": "READY",
                "BICAMERAL_BRIDGE": "READY",
                "FUNDAMENTUM": "READY",
                "GUARDIAN": "READY",
                "RELEASE_CONTROL": "READY",
                "REGISTRY": "READY",
            }
        ),
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected top-level JSON object")
    return value


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate fail-closed JANUS Nexus Habitat coordination envelopes."
    )
    parser.add_argument("--envelope", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        if args.snapshot:
            write_json(habitat_snapshot(), args.output)
            return 0
        if args.envelope is None:
            parser.error("provide --envelope, --snapshot, or --self-test")
        write_json(route_receipt(load_json(args.envelope)), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_habitat: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
