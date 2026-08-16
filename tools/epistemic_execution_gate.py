from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

CASE_SCHEMA = "janus.demihead.epistemic_execution_case.v1"
RESULT_SCHEMA = "janus.demihead.epistemic_execution_result.v1"
RECEIPT_SCHEMA = "janus.demihead.execution_receipt.v1"

EXACT_COMPUTATION = "EXACT_COMPUTATION"
EXTERNAL_FACT = "EXTERNAL_FACT"
CURRENT_STATE = "CURRENT_STATE"
INTERPRETATION = "INTERPRETATION"

HEX_256 = re.compile(r"^[0-9a-fA-F]{64}$")

INVARIANTS = [
    "MODEL_OUTPUT != EXECUTION_RECEIPT",
    "PLAUSIBLE_FORMAT != COMPUTED_VALUE",
    "HASH_SHAPE != HASH_VERIFIED",
    "CLAIM_OF_VERIFICATION_REQUIRES_RECEIPT",
    "TOOL_UNAVAILABLE != PERMISSION_TO_GUESS",
    "FORMAT_PRESSURE != PERMISSION_TO_GUESS",
    "NO_EVIDENCE -> EVIDENCE_INSUFFICIENT",
    "SOURCE_RETRIEVAL != SOURCE_TRUTH",
    "AUTHENTIC_RECEIPT != WORLD_TRUTH",
    "RECENTER != VERIFICATION",
    "CAPABILITY != EVIDENCE",
]


def _render(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def _normalize_expected_sha256(value: str | None) -> str | None:
    if value is None:
        return None
    if not HEX_256.fullmatch(value):
        raise ValueError("Expected SHA-256 must be exactly 64 hexadecimal characters")
    return value.lower()


def _sha256_receipt(data: bytes, *, input_kind: str, input_locator: str, expected: str | None) -> dict[str, Any]:
    expected_normalized = _normalize_expected_sha256(expected)
    computed = hashlib.sha256(data).hexdigest()
    if expected_normalized is None:
        comparison = "NOT_REQUESTED"
        verification_state = "COMPUTED_BY_LOCAL_EXECUTION"
    elif computed == expected_normalized:
        comparison = "MATCH"
        verification_state = "VERIFIED_MATCH_BY_LOCAL_EXECUTION"
    else:
        comparison = "MISMATCH"
        verification_state = "VERIFIED_MISMATCH_BY_LOCAL_EXECUTION"

    return {
        "schema": RECEIPT_SCHEMA,
        "operation_class": EXACT_COMPUTATION,
        "operation": "SHA-256",
        "execution_state": "EXECUTED",
        "execution_engine": "python.hashlib.sha256",
        "input_kind": input_kind,
        "input_locator": input_locator,
        "input_byte_length": len(data),
        "input_bound": True,
        "result_bound": True,
        "computed_value": computed,
        "expected_value": expected_normalized,
        "comparison": comparison,
        "verification_state": verification_state,
        "model_generated_value_accepted_without_execution": False,
        "claim_ceiling": "This receipt establishes the SHA-256 result for the bytes actually processed by this local execution. It does not establish the truth, safety, authorship, freshness, or meaning of those bytes.",
        "invariants": INVARIANTS,
    }


def compute_sha256_file(path: Path, expected: str | None = None) -> dict[str, Any]:
    data = path.read_bytes()
    return _sha256_receipt(data, input_kind="file", input_locator=str(path), expected=expected)


def compute_sha256_text(text: str, expected: str | None = None) -> dict[str, Any]:
    data = text.encode("utf-8")
    return _sha256_receipt(data, input_kind="utf8_text", input_locator="CLI_LITERAL", expected=expected)


def _execution_evidence_state(case: dict[str, Any]) -> tuple[str, list[str]]:
    claimed = case.get("claimed_value")
    evidence = case.get("evidence", [])
    reasons: list[str] = []

    receipts = [e for e in evidence if e.get("kind") == "execution_receipt"]
    model_outputs = [e for e in evidence if e.get("kind") == "model_output"]

    if model_outputs:
        reasons.append("Model output is present but is not execution evidence.")

    admissible: list[dict[str, Any]] = []
    for receipt in receipts:
        if receipt.get("execution_state") != "EXECUTED":
            reasons.append("Execution receipt rejected: execution_state is not EXECUTED.")
            continue
        if receipt.get("input_bound") is not True or receipt.get("result_bound") is not True:
            reasons.append("Execution receipt rejected: input/result binding is incomplete.")
            continue
        if receipt.get("origin") in {"model_output", "assistant_text", "untrusted_narrative"}:
            reasons.append("Execution receipt rejected: narrative/model origin cannot self-certify execution.")
            continue
        if not receipt.get("computed_value"):
            reasons.append("Execution receipt rejected: computed_value missing.")
            continue
        admissible.append(receipt)

    if not admissible:
        reasons.append("No admissible execution receipt binds a real execution to the claimed value.")
        return "EVIDENCE_INSUFFICIENT", reasons

    values = {str(r["computed_value"]) for r in admissible}
    if len(values) > 1:
        reasons.append("Admissible execution receipts disagree on the computed value.")
        return "CONTESTED_EXECUTION", reasons

    only_value = next(iter(values))
    if claimed is None:
        reasons.append("Execution exists, but the case did not bind a claimed_value for comparison.")
        return "COMPUTED_VALUE_AVAILABLE", reasons
    if str(claimed) == only_value:
        reasons.append("Claimed value matches the bound execution receipt.")
        return "VERIFIED_BY_EXECUTION_RECEIPT", reasons

    reasons.append("Claimed value conflicts with the bound execution receipt.")
    return "REFUTED_BY_EXECUTION_RECEIPT", reasons


def _source_evidence_state(case: dict[str, Any], *, require_current: bool) -> tuple[str, list[str]]:
    claimed = case.get("claimed_value")
    evidence = case.get("evidence", [])
    reasons: list[str] = []

    receipts = [e for e in evidence if e.get("kind") == "source_receipt"]
    model_outputs = [e for e in evidence if e.get("kind") == "model_output"]
    if model_outputs:
        reasons.append("Model output is present but is not a source receipt.")

    admissible: list[dict[str, Any]] = []
    for receipt in receipts:
        if receipt.get("retrieved") is not True:
            reasons.append("Source receipt rejected: retrieval not established.")
            continue
        if not receipt.get("source_locator"):
            reasons.append("Source receipt rejected: source_locator missing.")
            continue
        if receipt.get("origin") in {"model_output", "assistant_text", "untrusted_narrative"}:
            reasons.append("Source receipt rejected: model narrative cannot self-certify retrieval.")
            continue
        if require_current and receipt.get("freshness") != "current":
            reasons.append("Source receipt rejected for current-state claim: freshness is not current.")
            continue
        if "observed_value" not in receipt:
            reasons.append("Source receipt rejected: observed_value missing.")
            continue
        admissible.append(receipt)

    if not admissible:
        reasons.append("No admissible source receipt supports the factual claim.")
        return "EVIDENCE_INSUFFICIENT", reasons

    values = {json.dumps(r["observed_value"], ensure_ascii=False, sort_keys=True) for r in admissible}
    if len(values) > 1:
        reasons.append("Admissible source receipts disagree.")
        return "CONTESTED_SOURCES", reasons

    observed = admissible[0]["observed_value"]
    if claimed is None:
        reasons.append("Source observation exists, but claimed_value is absent.")
        return "OBSERVED_VALUE_AVAILABLE", reasons
    if claimed == observed:
        reasons.append("Claimed value matches the admissible source receipt.")
        return "SUPPORTED_BY_SOURCE_RECEIPT", reasons

    reasons.append("Claimed value conflicts with the admissible source receipt.")
    return "CONTRADICTED_BY_SOURCE_RECEIPT", reasons


def assess_case(case: dict[str, Any]) -> dict[str, Any]:
    if case.get("schema") != CASE_SCHEMA:
        raise ValueError(f"Unsupported case schema; expected {CASE_SCHEMA}")

    claim_type = case.get("claim_type")
    if claim_type == EXACT_COMPUTATION:
        state, reasons = _execution_evidence_state(case)
    elif claim_type == EXTERNAL_FACT:
        state, reasons = _source_evidence_state(case, require_current=False)
    elif claim_type == CURRENT_STATE:
        state, reasons = _source_evidence_state(case, require_current=True)
    elif claim_type == INTERPRETATION:
        state = "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION"
        reasons = ["Interpretive content is permitted when it is visibly labeled and not promoted as verified fact."]
    else:
        state = "EVIDENCE_INSUFFICIENT"
        reasons = ["Unknown claim_type; fail closed rather than infer a verification path."]

    verified_states = {
        "VERIFIED_BY_EXECUTION_RECEIPT",
        "SUPPORTED_BY_SOURCE_RECEIPT",
        "COMPUTED_VALUE_AVAILABLE",
        "OBSERVED_VALUE_AVAILABLE",
        "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION",
    }
    definitive_claim_permitted = state in verified_states and state != "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION"

    if state == "EVIDENCE_INSUFFICIENT":
        response_policy = "STATE_UNCERTAINTY_AND_REQUEST_OR_RUN_THE_REQUIRED_TOOL_OR_SOURCE_CHECK; DO_NOT_GUESS_A_VALUE"
    elif state.startswith("CONTESTED"):
        response_policy = "PRESERVE_DISAGREEMENT; DO_NOT_COLLAPSE_TO_A_SINGLE_CERTAIN_ANSWER"
    elif state.startswith("REFUTED") or state.startswith("CONTRADICTED"):
        response_policy = "REPORT_THE_CONFLICT_OR_MISMATCH_EXPLICITLY"
    elif state == "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION":
        response_policy = "KEEP_INTERPRETATION_LABEL_VISIBLE; DO_NOT_CALL_IT_VERIFIED_FACT"
    else:
        response_policy = "REPORT_ONLY_WITH_THE_RECEIPT_SCOPE_AND_CLAIM_CEILING_VISIBLE"

    return {
        "schema": RESULT_SCHEMA,
        "case_id": case.get("case_id", "UNKNOWN"),
        "claim": case.get("claim"),
        "claim_type": claim_type,
        "claimed_value": case.get("claimed_value"),
        "evidence_state": state,
        "definitive_claim_permitted": definitive_claim_permitted,
        "reasons": reasons,
        "response_policy": response_policy,
        "mass_effect_budget_delta": 0,
        "authority_delta": 0,
        "invariants": INVARIANTS,
    }


def self_test() -> dict[str, Any]:
    good_hash = hashlib.sha256(b"JANUS").hexdigest()
    fake_hash = "0" * 64
    cases = [
        (
            "model_only_hash",
            {
                "schema": CASE_SCHEMA,
                "case_id": "T1",
                "claim_type": EXACT_COMPUTATION,
                "claim": "SHA-256 matches",
                "claimed_value": fake_hash,
                "evidence": [{"kind": "model_output", "text": fake_hash}],
            },
            "EVIDENCE_INSUFFICIENT",
        ),
        (
            "bound_execution_match",
            {
                "schema": CASE_SCHEMA,
                "case_id": "T2",
                "claim_type": EXACT_COMPUTATION,
                "claim": "SHA-256 of JANUS",
                "claimed_value": good_hash,
                "evidence": [{
                    "kind": "execution_receipt",
                    "origin": "trusted_local_tool",
                    "execution_state": "EXECUTED",
                    "input_bound": True,
                    "result_bound": True,
                    "computed_value": good_hash,
                }],
            },
            "VERIFIED_BY_EXECUTION_RECEIPT",
        ),
        (
            "bound_execution_mismatch",
            {
                "schema": CASE_SCHEMA,
                "case_id": "T3",
                "claim_type": EXACT_COMPUTATION,
                "claim": "SHA-256 of JANUS",
                "claimed_value": fake_hash,
                "evidence": [{
                    "kind": "execution_receipt",
                    "origin": "trusted_local_tool",
                    "execution_state": "EXECUTED",
                    "input_bound": True,
                    "result_bound": True,
                    "computed_value": good_hash,
                }],
            },
            "REFUTED_BY_EXECUTION_RECEIPT",
        ),
        (
            "current_without_freshness",
            {
                "schema": CASE_SCHEMA,
                "case_id": "T4",
                "claim_type": CURRENT_STATE,
                "claim": "service is online now",
                "claimed_value": True,
                "evidence": [{
                    "kind": "source_receipt",
                    "origin": "connector",
                    "retrieved": True,
                    "source_locator": "service/status",
                    "freshness": "stale",
                    "observed_value": True,
                }],
            },
            "EVIDENCE_INSUFFICIENT",
        ),
        (
            "labeled_interpretation",
            {
                "schema": CASE_SCHEMA,
                "case_id": "T5",
                "claim_type": INTERPRETATION,
                "claim": "symbolic reading",
                "evidence": [],
            },
            "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION",
        ),
    ]

    results = []
    passed = 0
    for name, case, expected in cases:
        observed = assess_case(case)["evidence_state"]
        ok = observed == expected
        passed += int(ok)
        results.append({"name": name, "expected": expected, "observed": observed, "pass": ok})

    receipt = compute_sha256_text("JANUS", expected=good_hash)
    receipt_ok = receipt["comparison"] == "MATCH" and receipt["computed_value"] == good_hash
    passed += int(receipt_ok)
    results.append({"name": "real_sha256_execution", "expected": "MATCH", "observed": receipt["comparison"], "pass": receipt_ok})

    return {
        "schema": "janus.demihead.epistemic_execution_self_test.v1",
        "status": "PASS" if passed == len(results) else "FAIL",
        "passed": passed,
        "total": len(results),
        "results": results,
        "invariants": INVARIANTS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Fail-closed JANUS gate for computation, verification and factual-claim receipts.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--assess", type=Path, help="Assess a janus.demihead.epistemic_execution_case.v1 JSON file")
    mode.add_argument("--sha256-file", type=Path, help="Actually compute SHA-256 over a local file")
    mode.add_argument("--sha256-text", type=str, help="Actually compute SHA-256 over the provided UTF-8 text")
    mode.add_argument("--self-test", action="store_true", help="Run deterministic built-in guard tests")
    parser.add_argument("--expected", type=str, default=None, help="Optional expected SHA-256 for a real comparison")
    parser.add_argument("--output", type=Path, default=None, help="Optional JSON output path")
    args = parser.parse_args()

    if args.assess is not None:
        with args.assess.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        result = assess_case(payload)
    elif args.sha256_file is not None:
        result = compute_sha256_file(args.sha256_file, expected=args.expected)
    elif args.sha256_text is not None:
        result = compute_sha256_text(args.sha256_text, expected=args.expected)
    else:
        result = self_test()

    _render(result, args.output)


if __name__ == "__main__":
    main()
