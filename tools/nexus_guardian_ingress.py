from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


HOLD_SCHEMA = "janus.demihead.nexus_fundamentum_receipt.v1"
OBSERVATION_SCHEMA = "janus.demihead.observation_signal.v1"
GUARDIAN_SCHEMA = "janus.demihead.nexus_guardian_result.v1"
RELEASE_SCHEMA = "janus.demihead.nexus_release_receipt.v1"
CONTRACT = "JANUS_NEXUS_GUARDIAN_INGRESS_V1"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_zero_control(control: dict[str, Any]) -> None:
    if control.get("authority_delta") != 0:
        raise ValueError("authority_delta must remain zero")
    if control.get("mass_effect_budget_delta") != 0:
        raise ValueError("mass_effect_budget_delta must remain zero")
    if control.get("external_effect_permitted") is not False:
        raise ValueError("external_effect_permitted must be false")


def validate_hold_receipt(payload: dict[str, Any]) -> None:
    if payload.get("schema") != HOLD_SCHEMA:
        raise ValueError("Unexpected HOLD receipt schema")
    if payload.get("status") != "HOLD" or payload.get("payload_kind") != "HOLD_RECEIPT":
        raise ValueError("Fundamentum receipt must explicitly remain HOLD_RECEIPT")
    assessment = payload.get("assessment")
    if not isinstance(assessment, dict):
        raise ValueError("HOLD receipt assessment is required")
    if assessment.get("definitive_claim_permitted") is not False:
        raise ValueError("HOLD receipt cannot permit a definitive claim")
    control = payload.get("control")
    if not isinstance(control, dict):
        raise ValueError("HOLD receipt control is required")
    _require_zero_control(control)
    if control.get("may_be_promoted_to_evidence_receipt_without_new_witness") is not False:
        raise ValueError("HOLD receipt cannot self-promote to evidence")


def validate_observation(payload: dict[str, Any]) -> None:
    if payload.get("schema") != OBSERVATION_SCHEMA:
        raise ValueError("Unexpected observation schema")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ValueError("Observation source is required")
    if source.get("raw_identifiers_included") is not False:
        raise ValueError("Nexus observation cannot include raw identifiers")
    if source.get("raw_syslog_included") is not False:
        raise ValueError("Nexus observation cannot include raw syslog")
    quality = payload.get("quality")
    if not isinstance(quality, dict):
        raise ValueError("Observation quality is required")
    if quality.get("quantum_randomness_claim") is not False:
        raise ValueError("Observation cannot claim quantum randomness")
    control = payload.get("control")
    if not isinstance(control, dict):
        raise ValueError("Observation control is required")
    if control.get("authority_delta") != 0 or control.get("mass_effect_budget_delta") != 0:
        raise ValueError("Observation cannot increase authority or mass-effect budget")
    if control.get("direct_model_temperature_control") is not False:
        raise ValueError("Observation cannot directly control model temperature")
    if control.get("cryptographic_entropy_source") is not False:
        raise ValueError("Observation cannot claim cryptographic entropy")


def guardian_ingest(payload_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload_kind == "HOLD_RECEIPT":
        validate_hold_receipt(payload)
        assessment = payload["assessment"]
        status = "HOLD_PRESERVED"
        evidence_state = str(assessment.get("evidence_state", "UNKNOWN"))
        next_requirement = str(assessment.get("required_next_input", "NEW_VERIFIED_EVIDENCE"))
        human_review_required = True
    elif payload_kind == "OBSERVATION_SIGNAL":
        validate_observation(payload)
        status = "OBSERVATION_ACCEPTED_ADVISORY"
        evidence_state = "OBSERVATION_ONLY_NOT_TRUTH"
        next_requirement = "NONE_AUTOMATIC"
        human_review_required = False
    else:
        raise ValueError("Guardian ingress accepts only HOLD_RECEIPT or OBSERVATION_SIGNAL")

    return {
        "schema": GUARDIAN_SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "input": {
            "payload_kind": payload_kind,
            "sha256": sha256(payload),
        },
        "bounded_result": {
            "evidence_state": evidence_state,
            "next_requirement": next_requirement,
            "human_review_required": human_review_required,
            "definitive_claim_permitted": False,
            "automatic_escalation_permitted": False,
        },
        "control": {
            "read_only": True,
            "external_effect_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "release_control_required": True,
        },
        "claim_ceiling": {
            "guardian_result_is_truth": False,
            "guardian_result_is_command": False,
            "hold_is_failure": False,
            "observation_is_evidence": False,
        },
    }


def release_control(guardian_result: dict[str, Any]) -> dict[str, Any]:
    if guardian_result.get("schema") != GUARDIAN_SCHEMA:
        raise ValueError("Unexpected Guardian result schema")
    control = guardian_result.get("control")
    if not isinstance(control, dict):
        raise ValueError("Guardian control is required")
    _require_zero_control(control)
    if control.get("automatic_retry_permitted") is not False:
        raise ValueError("Automatic retry must remain disabled")

    status = guardian_result.get("status")
    if status == "HOLD_PRESERVED":
        release_state = "WAIT_FOR_NEW_EVIDENCE"
        return_control_to_human = True
    elif status == "OBSERVATION_ACCEPTED_ADVISORY":
        release_state = "RELEASE_TO_HUMAN"
        return_control_to_human = True
    else:
        raise ValueError("Unsupported Guardian result status")

    return {
        "schema": RELEASE_SCHEMA,
        "contract": CONTRACT,
        "status": release_state,
        "guardian_result_sha256": sha256(guardian_result),
        "control": {
            "return_control_to_human": return_control_to_human,
            "automatic_retry_permitted": False,
            "automatic_external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "laws": [
            "HOLD != FAILURE",
            "AMBIGUOUS_EFFECT != RETRY_PERMISSION",
            "GUARDIAN_RESULT != COMMAND",
            "RELEASE_CONTROL_RETURNS_AGENCY",
        ],
    }


def self_test() -> dict[str, Any]:
    hold = {
        "schema": HOLD_SCHEMA,
        "status": "HOLD",
        "payload_kind": "HOLD_RECEIPT",
        "assessment": {
            "evidence_state": "CONTEXT_ONLY_NOT_EVIDENCE",
            "required_next_input": "NEW_VERIFIED_EVIDENCE",
            "definitive_claim_permitted": False,
        },
        "control": {
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "may_be_promoted_to_evidence_receipt_without_new_witness": False,
        },
    }
    guardian = guardian_ingest("HOLD_RECEIPT", hold)
    release = release_control(guardian)
    checks = {
        "hold_preserved": guardian["status"] == "HOLD_PRESERVED",
        "definitive_claim_blocked": guardian["bounded_result"]["definitive_claim_permitted"] is False,
        "automatic_escalation_blocked": guardian["bounded_result"]["automatic_escalation_permitted"] is False,
        "automatic_retry_blocked": guardian["control"]["automatic_retry_permitted"] is False,
        "release_waits_for_new_evidence": release["status"] == "WAIT_FOR_NEW_EVIDENCE",
        "release_returns_control": release["control"]["return_control_to_human"] is True,
        "external_effect_blocked": release["control"]["automatic_external_effect_permitted"] is False,
    }

    forged = json.loads(json.dumps(hold))
    forged["assessment"]["definitive_claim_permitted"] = True
    try:
        guardian_ingest("HOLD_RECEIPT", forged)
    except ValueError:
        checks["forged_hold_upgrade_fails_closed"] = True
    else:
        checks["forged_hold_upgrade_fails_closed"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "guardian": guardian,
        "release": release,
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
    parser = argparse.ArgumentParser(description="Bounded Guardian ingress and Release Control for Nexus Habitat.")
    parser.add_argument("--kind", choices=["HOLD_RECEIPT", "OBSERVATION_SIGNAL"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--release-input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        if args.release_input is not None:
            write_json(release_control(load_json(args.release_input)), args.output)
            return 0
        if args.input is None or args.kind is None:
            parser.error("provide --kind and --input, --release-input, or --self-test")
        write_json(guardian_ingest(args.kind, load_json(args.input)), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_guardian_ingress: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
