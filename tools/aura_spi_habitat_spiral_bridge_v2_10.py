from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REQUEST_SCHEMA = "janus.aura_spi.spiral_event.v1"
AURA_SCHEMA = "janus.aura_spi.aura_reflection.v1"
SPI_SCHEMA = "janus.aura_spi.semantic_synthesis.v1"
ARBITRATION_SCHEMA = "janus.aura_spi.demihead_arbitration.v1"
VERIFIED_RETURN_SCHEMA = "janus.aura_spi.verified_return.v1"
CONTRACT_ID = "NEXUS_V2_10_AURA_SPI_HABITAT_SPIRAL_FROZEN_CONTRACT"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}:JSON_OBJECT_REQUIRED")
    return value


def _require_common(packet: dict[str, Any], schema: str, request: dict[str, Any]) -> None:
    if packet.get("schema") != schema:
        raise ValueError(f"SCHEMA_REQUIRED:{schema}")
    if packet.get("session_id") != request.get("session_id"):
        raise ValueError("SESSION_SPLIT_REJECT")
    if packet.get("generation") != request.get("generation"):
        raise ValueError("GENERATION_SPLIT_REJECT")
    if packet.get("intent_id") != request.get("intent_id"):
        raise ValueError("INTENT_SPLIT_REJECT")


def validate_request(request: dict[str, Any]) -> None:
    if request.get("schema") != REQUEST_SCHEMA:
        raise ValueError("REQUEST_SCHEMA_REJECT")
    intent = request.get("intent_id")
    if not isinstance(intent, str) or HEX64.fullmatch(intent) is None:
        raise ValueError("INTENT_ID_LOWERCASE_HEX64_REQUIRED")
    if not isinstance(request.get("session_id"), str) or not request["session_id"]:
        raise ValueError("SESSION_ID_REQUIRED")
    if not isinstance(request.get("generation"), int) or request["generation"] < 1:
        raise ValueError("GENERATION_REQUIRED")
    if not str(request.get("trigger_text", "")).strip():
        raise ValueError("FRESH_TRIGGER_REQUIRED")


def validate_aura(aura: dict[str, Any], request: dict[str, Any]) -> None:
    _require_common(aura, AURA_SCHEMA, request)
    if aura.get("predictive_label_authority") is not False:
        raise ValueError("AURA_AS_PREDICTIVE_LABEL_REJECT")
    if aura.get("scientific_evidence_authority") is not False:
        raise ValueError("AURA_AS_EVIDENCE_AUTHORITY_REJECT")
    if aura.get("may_train_predictive_head") is not False:
        raise ValueError("AURA_PREDICTIVE_TRAINING_REJECT")
    if aura.get("may_replace_primary_intent") is not False:
        raise ValueError("AURA_INTENT_REPLACEMENT_REJECT")


def validate_spi(spi: dict[str, Any], request: dict[str, Any]) -> None:
    _require_common(spi, SPI_SCHEMA, request)
    if spi.get("semantic_similarity_is_evidence") is not False:
        raise ValueError("SEMANTIC_SIMILARITY_AS_EVIDENCE_REJECT")
    if spi.get("prediction_is_truth") is not False:
        raise ValueError("PREDICTION_AS_TRUTH_REJECT")
    if spi.get("aura_is_predictive_label") is not False:
        raise ValueError("SPI_AURA_LABEL_PROMOTION_REJECT")
    refs = spi.get("retrieval_refs")
    if not isinstance(refs, list):
        raise ValueError("SPI_RETRIEVAL_REFS_REQUIRED")


def arbitrate(
    *,
    request: dict[str, Any],
    aura: dict[str, Any],
    spi: dict[str, Any],
    decision: str,
    intent_authority: str,
) -> dict[str, Any]:
    validate_request(request)
    validate_aura(aura, request)
    validate_spi(spi, request)
    decision = decision.upper()
    if decision not in {"PASS", "HOLD", "REJECT"}:
        raise ValueError("DEMIHEAD_DECISION_INVALID")
    verified_eligible = decision == "PASS" and intent_authority == "DEMIHEAD_GOLDPROMPT_VERIFIED"
    core = {
        "schema": ARBITRATION_SCHEMA,
        "contract_id": CONTRACT_ID,
        "session_id": request["session_id"],
        "generation": request["generation"],
        "intent_id": request["intent_id"],
        "decision": decision,
        "intent_authority": intent_authority,
        "bindings": {
            "request_sha256": sha256(request),
            "aura_sha256": sha256(aura),
            "spi_sha256": sha256(spi),
        },
        "verified_return_eligible": verified_eligible,
        "external_effect_authorized": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "claim_ceiling": {
            "arbitration_is_world_truth": False,
            "aura_is_evidence": False,
            "semantic_similarity_is_evidence": False,
            "pass_is_predictive_training_label": False,
        },
    }
    core["arbitration_sha256"] = sha256(core)
    if verified_eligible:
        core["verified_return"] = {
            "schema": VERIFIED_RETURN_SCHEMA,
            "session_id": request["session_id"],
            "generation": request["generation"],
            "intent_id": request["intent_id"],
            "state_advance": "ORIGIN_PRIME_(n+1)",
            "return_is_reset": False,
            "world_truth": False,
            "predictive_training_label": False,
        }
    return core


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead Nexus v2.10 Aura-SPI Habitat spiral arbiter")
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--aura", type=Path, required=True)
    parser.add_argument("--spi", type=Path, required=True)
    parser.add_argument("--decision", choices=["PASS", "HOLD", "REJECT"], default="HOLD")
    parser.add_argument("--intent-authority", choices=["LOCAL_PREVIEW", "DEMIHEAD_GOLDPROMPT_VERIFIED"], default="LOCAL_PREVIEW")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        result = arbitrate(
            request=load(args.request),
            aura=load(args.aura),
            spi=load(args.spi),
            decision=args.decision,
            intent_authority=args.intent_authority,
        )
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    except Exception as exc:
        sys.stderr.write(f"aura_spi_habitat_spiral_bridge_v2_10: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
