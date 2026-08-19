from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SOURCE_REPOSITORY = "Hawkar-usls/AIFC"
SOURCE_SHA = "221a523a1befd1423a8fd3165018336f7853b577"
README_BLOB_SHA = "11fcbbd01ac1a6e4e8ebfa5f838d096ef8988f30"
GRADES_BLOB_SHA = "0b8ff69112a4a037f09ff69bdc9511829a5cfd37"
SPEC_BLOB_SHA = "399ceacc0e97045eda61a270290c556e7ef0ce3e"
INPUT_SCHEMA = "janus.demihead.aifc_witness_package_summary.v1"
OUTPUT_SCHEMA = "janus.demihead.aifc_evidence_candidate.v1"

MANDATORY_GATES = (
    "CERTIFIED_TRIAL_CREATION",
    "GLOBAL_TRIAL_LEDGER",
    "EXACT_PRE_TARGET_FREEZE",
    "POST_FREEZE_TARGET_GENERATION",
    "PROOF_CARRYING_ENTROPY_PROFILE",
    "MACHINE_READABLE_CAUSAL_DAG",
    "MULTIPLICITY_ACCOUNTING",
    "ANYTIME_VALID_EVIDENCE",
    "EXTERNAL_FRESHNESS",
    "WITNESS_KEY_LIFECYCLE",
    "BYZANTINE_SAFE_QUORUM",
    "CANONICALIZATION",
    "FAIL_CLOSED_VERIFIER",
)
GATE_STATES = {"PASS", "FAIL", "MISSING", "UNKNOWN"}
GRADES = {
    "NOT_ADMITTED",
    "STRUCTURAL_MATCH_ONLY",
    "FORWARD_NULL_COMPATIBLE",
    "FORWARD_NULL_INCOMPATIBILITY_CANDIDATE",
    "EXTERNAL_REPLICATION_REQUIRED",
    "REPLICATED_FORWARD_NULL_INCOMPATIBILITY",
    "PHYSICAL_MECHANISM_UNRESOLVED",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _all_gates_pass(gates: Mapping[str, Any]) -> bool:
    return set(gates) == set(MANDATORY_GATES) and all(gates[name] == "PASS" for name in MANDATORY_GATES)


def verify_summary(summary: Mapping[str, Any]) -> bool:
    if not isinstance(summary, Mapping) or summary.get("schema") != INPUT_SCHEMA:
        return False
    if not isinstance(summary.get("package_id"), str) or not summary["package_id"].strip():
        return False
    if not _hex64(summary.get("package_sha256")):
        return False
    if summary.get("trial_state") != "TERMINAL":
        return False
    grade = summary.get("grade")
    if grade not in GRADES:
        return False
    gates = summary.get("mandatory_gates")
    if not isinstance(gates, Mapping) or set(gates) != set(MANDATORY_GATES):
        return False
    if any(gates[name] not in GATE_STATES for name in MANDATORY_GATES):
        return False
    for key in ("admitted", "statistical_threshold_crossed", "internal_adversarial_audit_pass", "mechanism_established", "physical_retrocausality_claimed"):
        if not isinstance(summary.get(key), bool):
            return False
    reps = summary.get("independent_replications")
    if not isinstance(reps, int) or isinstance(reps, bool) or reps < 0:
        return False
    if summary["physical_retrocausality_claimed"] is not False:
        return False
    if summary["mechanism_established"] is not False:
        return False

    all_pass = _all_gates_pass(gates)
    threshold = summary["statistical_threshold_crossed"]
    admitted = summary["admitted"]
    audit = summary["internal_adversarial_audit_pass"]

    if grade == "NOT_ADMITTED":
        return (not admitted) and (not all_pass)
    if grade == "STRUCTURAL_MATCH_ONLY":
        return (not admitted) and (not all_pass)
    if grade == "FORWARD_NULL_COMPATIBLE":
        return admitted and all_pass and not threshold
    if grade == "FORWARD_NULL_INCOMPATIBILITY_CANDIDATE":
        return admitted and all_pass and threshold
    if grade == "EXTERNAL_REPLICATION_REQUIRED":
        return admitted and all_pass and threshold and audit and reps < 2
    if grade == "REPLICATED_FORWARD_NULL_INCOMPATIBILITY":
        return admitted and all_pass and threshold and reps >= 2
    if grade == "PHYSICAL_MECHANISM_UNRESOLVED":
        return admitted and all_pass and threshold and reps >= 2 and not summary["mechanism_established"]
    return False


def build_candidate(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_summary(summary):
        raise ValueError("AIFC_WITNESS_PACKAGE_SUMMARY_INVALID")
    gates = dict(summary["mandatory_gates"])
    missing_or_nonpass = [name for name in MANDATORY_GATES if gates[name] != "PASS"]
    candidate: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_sha": SOURCE_SHA,
            "readme_blob_sha": README_BLOB_SHA,
            "evidence_grades_blob_sha": GRADES_BLOB_SHA,
            "spec_blob_sha": SPEC_BLOB_SHA,
            "spec_status": "DRAFT_NOT_YET_EXTERNAL_BENCH_FROZEN",
        },
        "package": {
            "package_id": summary["package_id"],
            "package_sha256": summary["package_sha256"],
            "trial_state": "TERMINAL",
            "summary_sha256": digest(dict(summary)),
        },
        "evidence": {
            "grade": summary["grade"],
            "admitted_by_aifc_summary": summary["admitted"],
            "statistical_threshold_crossed": summary["statistical_threshold_crossed"],
            "internal_adversarial_audit_pass": summary["internal_adversarial_audit_pass"],
            "independent_replications": summary["independent_replications"],
            "mandatory_gates": gates,
            "nonpass_gates": missing_or_nonpass,
        },
        "fundamentum_boundary": {
            "candidate_requires_independent_fundamentum_evaluation": True,
            "route_is_aifc_admission": False,
            "route_is_fundamentum_admission": False,
            "aifc_grade_is_world_truth": False,
        },
        "claim_ceiling": {
            "physical_retrocausality_established": False,
            "ftl_signalling_established": False,
            "closed_timelike_curves_established": False,
            "precognition_established": False,
            "physical_mechanism_established": False,
            "hash_or_signature_is_truth_of_content": False,
            "external_authority": False,
        },
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    candidate["candidate_sha256"] = digest(candidate)
    return candidate


def verify_candidate(summary: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if not isinstance(candidate, Mapping) or candidate.get("schema") != OUTPUT_SCHEMA:
        return False
    try:
        expected = build_candidate(summary)
    except ValueError:
        return False
    return dict(candidate) == expected
