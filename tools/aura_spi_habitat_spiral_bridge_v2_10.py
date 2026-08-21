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
STATE_CANDIDATE_SCHEMA = "janus.aura.spiral_5d.analysis.v2"
ARBITRATION_SCHEMA = "janus.aura_spi.demihead_arbitration.v1"
VERIFIED_RETURN_SCHEMA = "janus.aura_spi.verified_return.v1"
CONTRACT_ID = "NEXUS_V2_10_AURA_SPI_HABITAT_SPIRAL_FROZEN_CONTRACT"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
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


def validate_state_candidate(candidate: dict[str, Any] | None, request: dict[str, Any]) -> tuple[bool, str | None, dict[str, Any] | None]:
    if candidate is None:
        return False, "STATE_ADVANCE_CANDIDATE_REQUIRED", None
    if candidate.get("schema") != STATE_CANDIDATE_SCHEMA:
        return False, "STATE_CANDIDATE_SCHEMA_REJECT", None
    origin = candidate.get("origin_n")
    if not isinstance(origin, dict):
        return False, "STATE_CANDIDATE_ORIGIN_REQUIRED", None
    if origin.get("generation") != request.get("generation"):
        return False, "STATE_CANDIDATE_GENERATION_SPLIT", None
    if origin.get("intent_id") != request.get("intent_id"):
        return False, "STATE_CANDIDATE_INTENT_SPLIT", None
    origin_state_hash = candidate.get("origin_state_hash")
    if not isinstance(origin_state_hash, str) or HEX64.fullmatch(origin_state_hash) is None:
        return False, "ORIGIN_STATE_HASH_REQUIRED", None
    d5 = ((candidate.get("axes") or {}).get("D5_SPIRAL_ABSTRACTION") or {})
    if d5.get("advanced") is not True:
        return False, "ZERO_STATE_DELTA_HOLD", None
    state_delta_sha256 = d5.get("state_delta_sha256")
    if not isinstance(state_delta_sha256, str) or HEX64.fullmatch(state_delta_sha256) is None:
        return False, "STATE_DELTA_SHA256_REQUIRED", None
    prime = d5.get("origin_prime_candidate")
    if not isinstance(prime, dict):
        return False, "ORIGIN_PRIME_CANDIDATE_REQUIRED", None
    if prime.get("candidate_kind") != "ORIGIN_PRIME_CANDIDATE":
        return False, "ORIGIN_PRIME_CANDIDATE_KIND_REJECT", None
    if prime.get("generation") != request["generation"] + 1:
        return False, "CANDIDATE_NEXT_GENERATION_REQUIRED", None
    if prime.get("parent_origin_state_hash") != origin_state_hash:
        return False, "CANDIDATE_PARENT_HASH_MISMATCH", None
    if prime.get("state_delta_sha256") != state_delta_sha256:
        return False, "CANDIDATE_DELTA_HASH_MISMATCH", None
    candidate_state_hash = prime.get("candidate_state_hash")
    if not isinstance(candidate_state_hash, str) or HEX64.fullmatch(candidate_state_hash) is None:
        return False, "CANDIDATE_STATE_HASH_REQUIRED", None
    if candidate_state_hash == origin_state_hash:
        return False, "ZERO_STATE_HASH_DELTA_HOLD", None
    if prime.get("promotion_status") != "CANDIDATE_NOT_VERIFIED_RETURN":
        return False, "PREMATURE_PROMOTION_STATUS_REJECT", None
    return True, None, {
        "origin_state_hash": origin_state_hash,
        "parent_origin_state_hash": prime["parent_origin_state_hash"],
        "state_delta_sha256": state_delta_sha256,
        "candidate_state_hash": candidate_state_hash,
        "candidate_sha256": sha256(candidate),
    }


def arbitrate(
    *,
    request: dict[str, Any],
    aura: dict[str, Any],
    spi: dict[str, Any],
    decision: str,
    intent_authority: str,
    state_candidate: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validate_request(request)
    validate_aura(aura, request)
    validate_spi(spi, request)
    requested_decision = decision.upper()
    if requested_decision not in {"PASS", "HOLD", "REJECT"}:
        raise ValueError("DEMIHEAD_DECISION_INVALID")

    candidate_valid, candidate_error, candidate_binding = validate_state_candidate(state_candidate, request)
    verified_intent = intent_authority == "DEMIHEAD_GOLDPROMPT_VERIFIED"
    promotion_requested = requested_decision == "PASS" and verified_intent
    effective_decision = requested_decision
    if promotion_requested and not candidate_valid:
        effective_decision = "HOLD"
    verified_eligible = effective_decision == "PASS" and verified_intent and candidate_valid

    bindings = {
        "request_sha256": sha256(request),
        "aura_sha256": sha256(aura),
        "spi_sha256": sha256(spi),
        "state_candidate_sha256": sha256(state_candidate) if state_candidate is not None else None,
    }
    core = {
        "schema": ARBITRATION_SCHEMA,
        "contract_id": CONTRACT_ID,
        "session_id": request["session_id"],
        "generation": request["generation"],
        "intent_id": request["intent_id"],
        "requested_decision": requested_decision,
        "decision": effective_decision,
        "intent_authority": intent_authority,
        "bindings": bindings,
        "state_advance_gate": {
            "candidate_present": state_candidate is not None,
            "candidate_valid": candidate_valid,
            "failure_reason": candidate_error,
            "binding": candidate_binding,
            "zero_state_delta_promotes": False,
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
            "candidate_is_final_origin_prime": False,
        },
    }
    core["arbitration_sha256"] = sha256(core)
    if verified_eligible:
        assert candidate_binding is not None
        core["verified_return"] = {
            "schema": VERIFIED_RETURN_SCHEMA,
            "session_id": request["session_id"],
            "generation": request["generation"],
            "intent_id": request["intent_id"],
            "state_advance": "ORIGIN_PRIME_(n+1)",
            "origin_state_hash": candidate_binding["origin_state_hash"],
            "parent_origin_state_hash": candidate_binding["parent_origin_state_hash"],
            "state_delta_sha256": candidate_binding["state_delta_sha256"],
            "candidate_state_hash": candidate_binding["candidate_state_hash"],
            "candidate_sha256": candidate_binding["candidate_sha256"],
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
    parser.add_argument("--state-candidate", type=Path)
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
            state_candidate=load(args.state_candidate) if args.state_candidate else None,
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
