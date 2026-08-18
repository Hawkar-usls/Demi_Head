from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

from goldprompt_intent_handoff import build_handoff, canonical_json_bytes, sha256, verify_anchor, verify_handoff

REQUEST_SCHEMA = "janus.demihead.cosmos_proof_request.v1"
RECEIPT_SCHEMA = "janus.demihead.cosmos_proof_receipt.v1"
PROVIDER_REPOSITORY = "Hawkar-usls/Janus-Cosmos"
PROVIDER_SHA = "c77f920d764229efb6932bc4ea522a4ec0342c64"
PROVIDER_FACE = "COSMOS_PROOF_PROVIDER"
CANONICAL_GATE = "S𓂸ḥ/2"
OPERATION = "VERIFY_CANONICAL_GATE"
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _write(payload: Mapping[str, Any], path: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if path is None:
        print(text, end="")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")


def build_request(intent_anchor: Mapping[str, Any], request_id: str) -> dict[str, Any]:
    if not verify_anchor(intent_anchor):
        raise ValueError("COSMOS_INTENT_ANCHOR_INVALID")
    payload = {
        "kind": "CANONICAL_GATE_SELF_TEST",
        "gate": CANONICAL_GATE,
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_sha": PROVIDER_SHA,
    }
    request: dict[str, Any] = {
        "schema": REQUEST_SCHEMA,
        "request_id": str(request_id),
        "operation": OPERATION,
        "intent_anchor": copy.deepcopy(dict(intent_anchor)),
        "intent_handoff": build_handoff(intent_anchor, PROVIDER_FACE, 2),
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_sha": PROVIDER_SHA,
        "canonical_gate": CANONICAL_GATE,
        "input_payload": payload,
        "input_sha256": sha256(payload),
    }
    request["request_sha256"] = _digest(request)
    return request


def verify_request(request: Mapping[str, Any]) -> bool:
    if not isinstance(request, Mapping) or request.get("schema") != REQUEST_SCHEMA:
        return False
    if request.get("operation") != OPERATION:
        return False
    if request.get("provider_repository") != PROVIDER_REPOSITORY or request.get("provider_sha") != PROVIDER_SHA:
        return False
    if request.get("canonical_gate") != CANONICAL_GATE:
        return False
    anchor = request.get("intent_anchor")
    handoff = request.get("intent_handoff")
    if not isinstance(anchor, Mapping) or not verify_anchor(anchor):
        return False
    if not isinstance(handoff, Mapping) or not verify_handoff(anchor, handoff, PROVIDER_FACE):
        return False
    payload = request.get("input_payload")
    if not isinstance(payload, Mapping):
        return False
    expected_payload = {
        "kind": "CANONICAL_GATE_SELF_TEST",
        "gate": CANONICAL_GATE,
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_sha": PROVIDER_SHA,
    }
    if dict(payload) != expected_payload or request.get("input_sha256") != sha256(expected_payload):
        return False
    claimed = request.get("request_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        return False
    replay = dict(request)
    replay.pop("request_sha256", None)
    return _digest(replay) == claimed


def verify_cosmos_result(result: Mapping[str, Any]) -> bool:
    if not isinstance(result, Mapping):
        return False
    claimed = result.get("integrity_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        return False
    replay = dict(result)
    replay.pop("integrity_sha256", None)
    if _digest(replay) != claimed:
        return False
    status = result.get("status")
    if not isinstance(status, str) or not status.startswith("PASS_KEEP_S_PHALLUS_H_GATE_2"):
        return False
    conformance = result.get("implementation_conformance")
    if not isinstance(conformance, Mapping) or conformance.get("P_VS_NP") != "OPEN":
        return False
    if conformance.get("new_posthoc_threshold_added") is not False:
        return False
    if conformance.get("frozen_contract_unchanged") is not True or conformance.get("frozen_fixture_corpus_unchanged") is not True:
        return False
    return True


def build_receipt(request: Mapping[str, Any], cosmos_result: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_request(request):
        raise ValueError("COSMOS_PROOF_REQUEST_INVALID")
    if not verify_cosmos_result(cosmos_result):
        raise ValueError("COSMOS_EXECUTION_RESULT_INVALID")
    anchor = request["intent_anchor"]
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "intent_id": anchor["intent_id"],
        "requested_operation": anchor["requested_operation"],
        "provider_repository": PROVIDER_REPOSITORY,
        "provider_sha": PROVIDER_SHA,
        "provider_role": "SPECIALIZED_PROOF_PROVIDER_NOT_TRUTH_ARBITER",
        "canonical_gate": CANONICAL_GATE,
        "input_sha256": request["input_sha256"],
        "cosmos_result_integrity_sha256": cosmos_result["integrity_sha256"],
        "cosmos_status": cosmos_result["status"],
        "execution_state": "EXECUTED_AND_REPLAY_VERIFIED",
        "evidence_state": "VERIFIED_EXECUTION_PASS_WITHIN_FROZEN_GATE_SCOPE",
        "definitive_claim_permitted": True,
        "P_VS_NP": "OPEN",
        "P_EQUALS_NP": "NOT_ESTABLISHED",
        "P_NOT_EQUALS_NP": "NOT_ESTABLISHED",
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "claim_ceiling": (
            "The exact Janus-Cosmos provider revision reproduced its frozen S𓂸ḥ/2 canonical gate result. "
            "This is evidence about that bound computation only; it does not establish P=NP, P!=NP, arbitrary-CNF tractability, "
            "world truth, user intent beyond the bound GoldPrompt anchor, or external-effect authority."
        ),
        "invariants": [
            "SAME_INTENT_REQUIRED_ACROSS_DEMIHEAD_AND_COSMOS",
            "COSMOS_PASS != WORLD_TRUTH",
            "COSMOS_PASS != P_EQUALS_NP",
            "COSMOS_PASS != AUTHORITY",
            "MODEL_OUTPUT != EXECUTION_RECEIPT",
            "PROVIDER_SHA_MUST_BE_EXACT",
            "INPUT_HASH_MUST_BE_BOUND",
            "P_VS_NP = OPEN",
        ],
    }
    receipt["receipt_sha256"] = _digest(receipt)
    return receipt


def verify_receipt(request: Mapping[str, Any], cosmos_result: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not verify_request(request) or not verify_cosmos_result(cosmos_result):
        return False
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    try:
        expected = build_receipt(request, cosmos_result)
    except ValueError:
        return False
    return dict(receipt) == expected


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--cosmos-result", type=Path, required=True)
    ap.add_argument("--output", type=Path)
    ap.add_argument("--verify-receipt", type=Path)
    args = ap.parse_args()

    request = json.loads(args.request.read_text(encoding="utf-8"))
    cosmos_result = json.loads(args.cosmos_result.read_text(encoding="utf-8"))
    if args.verify_receipt:
        receipt = json.loads(args.verify_receipt.read_text(encoding="utf-8"))
        ok = verify_receipt(request, cosmos_result, receipt)
        print(json.dumps({"verified": ok, "authority_delta": 0, "P_VS_NP": "OPEN"}, sort_keys=True))
        raise SystemExit(0 if ok else 1)
    receipt = build_receipt(request, cosmos_result)
    _write(receipt, args.output)


if __name__ == "__main__":
    main()
