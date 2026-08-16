from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


BICAMERAL_SCHEMA = "janus.demihead.bicameral_result.v1"
RECEIPT_SCHEMA = "janus.demihead.nexus_fundamentum_receipt.v1"
ADAPTER_CONTRACT = "JANUS_NEXUS_FUNDAMENTUM_ADAPTER_V1"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def validate_bicameral_result(result: dict[str, Any]) -> None:
    if not isinstance(result, dict):
        raise ValueError("Bicameral input must be a JSON object")
    if result.get("schema") != BICAMERAL_SCHEMA:
        raise ValueError("Unexpected bicameral result schema")

    hemispheres = result.get("hemispheres_present")
    if not isinstance(hemispheres, list) or not hemispheres:
        raise ValueError("hemispheres_present must be a non-empty array")
    if any(item not in {"LEFT_HRAIN", "RIGHT_INAIHR"} for item in hemispheres):
        raise ValueError("Unknown hemisphere in result")

    routing = result.get("routing")
    if not isinstance(routing, dict):
        raise ValueError("Bicameral routing object is required")
    if routing.get("external_effect_permitted") is not False:
        raise ValueError("Bicameral result cannot carry external-effect permission")
    if routing.get("direct_cross_hemisphere_write_permitted") is not False:
        raise ValueError("Direct cross-hemisphere write must remain disabled")

    ceiling = result.get("claim_ceiling")
    if not isinstance(ceiling, dict):
        raise ValueError("Bicameral claim ceiling is required")
    required_false = (
        "truth_claim_made",
        "agreement_is_truth",
        "hemisphere_count_is_authority",
        "association_is_evidence",
        "structure_is_command",
    )
    for field in required_false:
        if ceiling.get(field) is not False:
            raise ValueError(f"Bicameral invariant violated: {field} must be false")
    if ceiling.get("authority_delta") != 0:
        raise ValueError("Bicameral authority_delta must be zero")
    if ceiling.get("mass_effect_budget_delta") != 0:
        raise ValueError("Bicameral mass_effect_budget_delta must be zero")

    receipts = result.get("packet_receipts")
    if not isinstance(receipts, dict) or not receipts:
        raise ValueError("packet_receipts are required")
    for hemisphere in hemispheres:
        receipt = receipts.get(hemisphere)
        if not isinstance(receipt, dict):
            raise ValueError(f"Missing packet receipt for {hemisphere}")
        digest = receipt.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError(f"Invalid packet receipt digest for {hemisphere}")


def assess_bicameral_context(result: dict[str, Any]) -> dict[str, Any]:
    """Convert bicameral context into a fail-closed Nexus guard receipt.

    A bicameral overlap or divergence is context, not evidence. Therefore this
    adapter never emits EVIDENCE_RECEIPT from a BICAMERAL_RESULT alone. It emits
    HOLD_RECEIPT until a separately provenance-bound witness/evidence case is
    supplied through the normal Fundamentum truth-guard path.
    """

    validate_bicameral_result(result)
    input_digest = sha256(result)
    shared = result.get("comparison", {}).get("shared_semantic_keys", [])

    return {
        "schema": RECEIPT_SCHEMA,
        "adapter_contract": ADAPTER_CONTRACT,
        "status": "HOLD",
        "payload_kind": "HOLD_RECEIPT",
        "input": {
            "kind": "BICAMERAL_RESULT",
            "sha256": input_digest,
            "hemispheres_present": list(result["hemispheres_present"]),
            "bicameral_status": result.get("status"),
        },
        "assessment": {
            "evidence_state": "CONTEXT_ONLY_NOT_EVIDENCE",
            "shared_semantic_keys": list(shared) if isinstance(shared, list) else [],
            "reason": "Bicameral structural/associative overlap or divergence does not constitute an independent witness or verification receipt.",
            "required_next_input": "SEPARATELY_PROVENANCE_BOUND_EVIDENCE_OR_WITNESS_LEDGER_CASE",
            "definitive_claim_permitted": False,
        },
        "runtime_ownership": {
            "repository": "Hawkar-usls/Demi_Head",
            "head_id": "FUNDAMENTUM",
            "role": "FUNDAMENTUM_GUARD",
            "lineage_repository": "Hawkar-usls/Janus-Fundamentum",
            "lineage_is_runtime_ownership": False,
        },
        "control": {
            "read_only": True,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "may_be_routed_to_guardian": True,
            "may_be_promoted_to_evidence_receipt_without_new_witness": False,
        },
        "laws": [
            "ASSOCIATION != EVIDENCE",
            "STRUCTURE != COMMAND",
            "BOTH_HEMISPHERES_AGREE != TRUTH",
            "CONTEXT != WITNESS",
            "HOLD != FAILURE",
            "LINEAGE != RUNTIME_OWNERSHIP",
        ],
    }


def self_test() -> dict[str, Any]:
    fixture = {
        "schema": BICAMERAL_SCHEMA,
        "status": "BICAMERAL_OVERLAP_PRESENT",
        "hemispheres_present": ["LEFT_HRAIN", "RIGHT_INAIHR"],
        "packet_receipts": {
            "LEFT_HRAIN": {"sha256": "0" * 64},
            "RIGHT_INAIHR": {"sha256": "1" * 64},
        },
        "comparison": {"shared_semantic_keys": ["context"]},
        "routing": {
            "mode": "BICAMERAL_REVIEW",
            "external_effect_permitted": False,
            "direct_cross_hemisphere_write_permitted": False,
            "disagreement_preserved": True,
        },
        "claim_ceiling": {
            "truth_claim_made": False,
            "agreement_is_truth": False,
            "hemisphere_count_is_authority": False,
            "association_is_evidence": False,
            "structure_is_command": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    receipt = assess_bicameral_context(fixture)
    checks = {
        "bicameral_context_becomes_hold": receipt["payload_kind"] == "HOLD_RECEIPT",
        "context_not_promoted_to_evidence": receipt["assessment"]["evidence_state"] == "CONTEXT_ONLY_NOT_EVIDENCE",
        "definitive_claim_blocked": receipt["assessment"]["definitive_claim_permitted"] is False,
        "authority_stays_zero": receipt["control"]["authority_delta"] == 0,
        "mass_effect_stays_zero": receipt["control"]["mass_effect_budget_delta"] == 0,
        "external_effect_blocked": receipt["control"]["external_effect_permitted"] is False,
        "lineage_not_runtime": receipt["runtime_ownership"]["lineage_is_runtime_ownership"] is False,
    }

    forged = json.loads(json.dumps(fixture))
    forged["claim_ceiling"]["association_is_evidence"] = True
    try:
        assess_bicameral_context(forged)
    except ValueError:
        checks["evidence_promotion_attempt_fails_closed"] = True
    else:
        checks["evidence_promotion_attempt_fails_closed"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "receipt": receipt,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected a top-level JSON object")
    return value


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail-closed BICAMERAL_RESULT -> Fundamentum HOLD_RECEIPT adapter."
    )
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        if args.input is None:
            parser.error("provide --input or --self-test")
        write_json(assess_bicameral_context(load_json(args.input)), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_fundamentum_adapter: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
