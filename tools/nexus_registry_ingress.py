from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


RELEASE_SCHEMA = "janus.demihead.nexus_release_receipt.v1"
OBSERVATION_SCHEMA = "janus.demihead.observation_signal.v1"
BICAMERAL_SCHEMA = "janus.demihead.bicameral_result.v1"
FUNDAMENTUM_SCHEMA = "janus.demihead.nexus_fundamentum_receipt.v1"
GUARDIAN_SCHEMA = "janus.demihead.nexus_guardian_result.v1"
REGISTRY_SCHEMA = "janus.demihead.nexus_registry_receipt.v1"
CONTRACT = "JANUS_NEXUS_REGISTRY_INGRESS_V1"

KIND_TO_SCHEMA = {
    "RELEASE_RECEIPT": RELEASE_SCHEMA,
    "OBSERVATION_SIGNAL": OBSERVATION_SCHEMA,
    "BICAMERAL_RESULT": BICAMERAL_SCHEMA,
    "HOLD_RECEIPT": FUNDAMENTUM_SCHEMA,
    "GUARDIAN_RESULT": GUARDIAN_SCHEMA,
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _reject_effect_authority(payload: dict[str, Any]) -> None:
    control = payload.get("control")
    if isinstance(control, dict):
        if control.get("authority_delta", 0) != 0:
            raise ValueError("Registry ingress refuses non-zero authority_delta")
        if control.get("mass_effect_budget_delta", 0) != 0:
            raise ValueError("Registry ingress refuses non-zero mass_effect_budget_delta")
        for field in (
            "external_effect_permitted",
            "automatic_external_effect_permitted",
        ):
            if field in control and control[field] is not False:
                raise ValueError(f"Registry ingress refuses {field}=true")


def ingest(payload_kind: str, payload: dict[str, Any]) -> dict[str, Any]:
    expected_schema = KIND_TO_SCHEMA.get(payload_kind)
    if expected_schema is None:
        raise ValueError("Unsupported Registry payload kind")
    if not isinstance(payload, dict) or payload.get("schema") != expected_schema:
        raise ValueError(f"{payload_kind} schema mismatch")
    _reject_effect_authority(payload)

    digest = sha256(payload)
    return {
        "schema": REGISTRY_SCHEMA,
        "contract": CONTRACT,
        "status": "LOCAL_PROVENANCE_RECEIPT_READY",
        "input": {
            "payload_kind": payload_kind,
            "sha256": digest,
            "schema": expected_schema,
        },
        "archive_candidate": {
            "content_address": f"sha256:{digest}",
            "preserve_input_unchanged": True,
            "append_only_recommended": True,
            "correction_by_descendant_record": True,
        },
        "effect_boundary": {
            "meta_registry_write_performed": False,
            "git_commit_performed": False,
            "network_delivery_performed": False,
            "external_publication_performed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "receipt_proves_payload_hash_binding": True,
            "receipt_proves_payload_truth": False,
            "receipt_proves_delivery": False,
            "receipt_is_archive_commit": False,
        },
        "laws": [
            "HASH != TRUTH",
            "REGISTRY_RECEIPT != GIT_COMMIT",
            "ARCHIVE_CANDIDATE != PUBLICATION",
            "CORRECTION != DELETION",
        ],
    }


def self_test() -> dict[str, Any]:
    release = {
        "schema": RELEASE_SCHEMA,
        "status": "WAIT_FOR_NEW_EVIDENCE",
        "control": {
            "return_control_to_human": True,
            "automatic_retry_permitted": False,
            "automatic_external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    receipt = ingest("RELEASE_RECEIPT", release)
    checks = {
        "local_receipt_ready": receipt["status"] == "LOCAL_PROVENANCE_RECEIPT_READY",
        "hash_binding_true": receipt["claim_ceiling"]["receipt_proves_payload_hash_binding"] is True,
        "truth_not_claimed": receipt["claim_ceiling"]["receipt_proves_payload_truth"] is False,
        "delivery_not_claimed": receipt["claim_ceiling"]["receipt_proves_delivery"] is False,
        "git_write_not_claimed": receipt["effect_boundary"]["git_commit_performed"] is False,
        "publication_not_claimed": receipt["effect_boundary"]["external_publication_performed"] is False,
    }

    forged = json.loads(json.dumps(release))
    forged["control"]["automatic_external_effect_permitted"] = True
    try:
        ingest("RELEASE_RECEIPT", forged)
    except ValueError:
        checks["effect_escalation_fails_closed"] = True
    else:
        checks["effect_escalation_fails_closed"] = False

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
    parser = argparse.ArgumentParser(description="Create local provenance-only Nexus Registry receipts.")
    parser.add_argument("--kind", choices=sorted(KIND_TO_SCHEMA))
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        if args.input is None or args.kind is None:
            parser.error("provide --kind and --input, or --self-test")
        write_json(ingest(args.kind, load_json(args.input)), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_registry_ingress: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
