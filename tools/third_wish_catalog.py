#!/usr/bin/env python3
"""DemiHead Third Wish catalog activation gate.

This tool activates catalog visibility and voluntary request routing only. It does
not execute provider effects. The authoritative 32-capability catalog remains in
Janus_Genesis; DemiHead binds to its completion receipt instead of shadow-copying
capability identities.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "third_wish.activation.json"


def load_config(path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def catalog_status(config: dict[str, object]) -> dict[str, object]:
    frozen = config["frozen_catalog"]
    activation = config["activation_semantics"]
    boundary = config["demihead_effect_boundary"]
    return {
        "genesis_signature": config["genesis_signature"],
        "activation_mode": config["activation_mode"],
        "catalog_visibility": activation["catalog_visibility"],
        "capability_inspection": activation["capability_inspection"],
        "frozen_capability_ids": frozen["capability_ids"],
        "typed_reference_handler_contracts": frozen["typed_reference_handler_contracts"],
        "adapter_ownership_overlap": frozen["adapter_ownership_overlap"],
        "catalog_completion": frozen["catalog_completion"],
        "provider_universal_completion": frozen["provider_universal_completion"],
        "automatic_external_effect": boundary["automatic_external_effect"],
        "automatic_high_impact_execution": boundary["automatic_high_impact_execution"],
        "mass_effect_budget_delta": boundary["mass_effect_budget_delta"],
        "external_effect_authority": activation["external_effect_authority"],
    }


def inspect_request(capability_id: str, config: dict[str, object]) -> dict[str, object]:
    capability_id = capability_id.strip().upper()
    high_impact = capability_id in set(config["high_impact_classes"])
    boundary = config["demihead_effect_boundary"]

    if not capability_id:
        decision = "NO_CAPABILITY_ID"
    elif high_impact:
        decision = "HELD_FOR_FRESH_VERIFIED_HUMAN_REAUTH_AND_PROVIDER_GATE"
    else:
        decision = "REQUEST_MAY_BE_ROUTED_TO_SEPARATE_PROVIDER_GATE"

    return {
        "capability_id": capability_id,
        "catalog_active": True,
        "catalog_membership_claimed_by_demihead": False,
        "catalog_membership_reason": "Exact membership belongs to the authoritative frozen Janus_Genesis catalog.",
        "high_impact_class": high_impact,
        "decision": decision,
        "effect_executed": False,
        "provider_call_entered": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": boundary["mass_effect_budget_delta"],
        "fresh_verified_human_reauthorization_required": bool(
            high_impact and boundary["fresh_verified_human_reauthorization_required_for_high_impact"]
        ),
    }


def self_test() -> dict[str, str]:
    config = load_config()
    status = catalog_status(config)
    assert status["genesis_signature"] == "0:0 = JANUS"
    assert status["frozen_capability_ids"] == 32
    assert status["typed_reference_handler_contracts"] == 32
    assert status["adapter_ownership_overlap"] == 0
    assert status["catalog_completion"] == "ESTABLISHED"
    assert status["provider_universal_completion"] is False
    assert status["automatic_external_effect"] is False
    assert status["automatic_high_impact_execution"] is False
    assert status["mass_effect_budget_delta"] == 0

    ordinary = inspect_request("GITHUB.REPOSITORY.READ", config)
    assert ordinary["effect_executed"] is False
    assert ordinary["provider_call_entered"] is False
    assert ordinary["decision"] == "REQUEST_MAY_BE_ROUTED_TO_SEPARATE_PROVIDER_GATE"

    high = inspect_request("GITHUB.DESTRUCTIVE", config)
    assert high["effect_executed"] is False
    assert high["provider_call_entered"] is False
    assert high["fresh_verified_human_reauthorization_required"] is True
    assert high["decision"] == "HELD_FOR_FRESH_VERIFIED_HUMAN_REAUTH_AND_PROVIDER_GATE"

    return {
        "genesis_signature_0_colon_0": "PASS",
        "catalog_32_of_32_receipt_binding": "PASS",
        "zero_adapter_overlap_receipt_binding": "PASS",
        "provider_universal_completion_not_inferred": "PASS",
        "catalog_visibility_active": "PASS",
        "ordinary_request_does_not_execute_effect": "PASS",
        "high_impact_request_is_held": "PASS",
        "mass_effect_budget_unchanged": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead Third Wish catalog gate")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--request")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    config = load_config(args.config)
    if args.self_test:
        result: object = self_test()
    elif args.request is not None:
        result = inspect_request(args.request, config)
    else:
        result = catalog_status(config)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
