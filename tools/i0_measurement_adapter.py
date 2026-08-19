from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SOURCE_REPOSITORY = "Hawkar-usls/janus-io-public"
SOURCE_SHA = "7d02fb08fa9defd71297f8c5c4c9ac9d6be76316"
PROJECT_STATUS_BLOB_SHA = "df92b16ab1cc62183de1d667576e57c82c10dc3c"
PROOF_OF_OBSERVATION_BLOB_SHA = "f7fcd76c376b17b4b001094355e17e517b7cb84c"
ENGINEERING_CAPABILITIES_BLOB_SHA = "e60d5ffe8aae8de0a9d946460244a22f16e29112"
INPUT_SCHEMA = "janus.demihead.i0_measurement_summary.v1"
RECEIPT_SCHEMA = "janus.demihead.i0_measurement_receipt.v1"
EVIDENCE_SCHEMA = "janus.demihead.i0_measurement_evidence_candidate.v1"

STATUSES = {
    "NOT_EVALUATED",
    "INSUFFICIENT_DATA",
    "BLOCKED",
    "OBSERVATION_ONLY",
    "EXPLORATORY_ONLY",
    "CANDIDATE",
    "CONFIRMED",
    "REVOKED_BY_NEW_EVIDENCE",
}
MEASUREMENT_STATES = {"OBSERVED", "UNKNOWN", "STALE", "CONTAMINATED"}
FORBIDDEN_CLAIMS = (
    "sha256_predictability_or_weakness_established",
    "increased_proof_probability_established",
    "mining_advantage_or_profitability_established",
    "wall_energy_savings_established",
    "extended_hardware_lifetime_established",
    "source_truth_from_hash_chain_established",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _verify_measurement_map(values: Any) -> bool:
    if not isinstance(values, Mapping):
        return False
    for name, item in values.items():
        if not isinstance(name, str) or not name or not isinstance(item, Mapping):
            return False
        state = item.get("state")
        if state not in MEASUREMENT_STATES:
            return False
        current = item.get("current")
        if not isinstance(current, bool):
            return False
        value = item.get("value")
        unit = item.get("unit")
        if state == "OBSERVED":
            if not current or not _number(value) or not isinstance(unit, str) or not unit:
                return False
        elif state == "UNKNOWN":
            if current or value is not None:
                return False
        elif state in {"STALE", "CONTAMINATED"}:
            if current:
                return False
            if value is not None and not _number(value):
                return False
        if unit is not None and not isinstance(unit, str):
            return False
    return True


def verify_summary(summary: Mapping[str, Any]) -> bool:
    if not isinstance(summary, Mapping) or summary.get("schema") != INPUT_SCHEMA:
        return False
    if not isinstance(summary.get("measurement_id"), str) or not summary["measurement_id"].strip():
        return False
    if not _hex64(summary.get("source_bundle_sha256")):
        return False
    status = summary.get("status")
    if status not in STATUSES:
        return False
    for key in ("integrity_valid", "comparability_valid", "holdout_replication", "overlapping_views_counted_as_independent"):
        if not isinstance(summary.get(key), bool):
            return False
    if summary["overlapping_views_counted_as_independent"] is not False:
        return False
    reps = summary.get("independent_replications")
    if not isinstance(reps, int) or isinstance(reps, bool) or reps < 0:
        return False

    exposure = summary.get("exposure")
    if not isinstance(exposure, Mapping) or not isinstance(exposure.get("known"), bool):
        return False
    checked = exposure.get("checked_hashes")
    if exposure["known"]:
        if not isinstance(checked, int) or isinstance(checked, bool) or checked < 0:
            return False
    elif checked is not None:
        return False

    if not _verify_measurement_map(summary.get("facts")):
        return False
    if not _verify_measurement_map(summary.get("derived_metrics")):
        return False

    claims = summary.get("claim_flags")
    if not isinstance(claims, Mapping) or set(claims) != set(FORBIDDEN_CLAIMS):
        return False
    if any(claims[name] is not False for name in FORBIDDEN_CLAIMS):
        return False

    if status == "CONFIRMED":
        if not summary["integrity_valid"] or not summary["comparability_valid"] or not summary["holdout_replication"]:
            return False
        if reps < 1:
            return False
        if any(item.get("state") == "CONTAMINATED" for group in (summary["facts"], summary["derived_metrics"]) for item in group.values()):
            return False
    return True


def build_receipt(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_summary(summary):
        raise ValueError("I0_MEASUREMENT_SUMMARY_INVALID")
    facts = {name: dict(item) for name, item in summary["facts"].items()}
    derived = {name: dict(item) for name, item in summary["derived_metrics"].items()}
    unknown = sorted(
        [f"facts.{name}" for name, item in facts.items() if item["state"] == "UNKNOWN"]
        + [f"derived_metrics.{name}" for name, item in derived.items() if item["state"] == "UNKNOWN"]
    )
    stale = sorted(
        [f"facts.{name}" for name, item in facts.items() if item["state"] == "STALE"]
        + [f"derived_metrics.{name}" for name, item in derived.items() if item["state"] == "STALE"]
    )
    contaminated = sorted(
        [f"facts.{name}" for name, item in facts.items() if item["state"] == "CONTAMINATED"]
        + [f"derived_metrics.{name}" for name, item in derived.items() if item["state"] == "CONTAMINATED"]
    )
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_sha": SOURCE_SHA,
            "project_status_blob_sha": PROJECT_STATUS_BLOB_SHA,
            "proof_of_observation_blob_sha": PROOF_OF_OBSERVATION_BLOB_SHA,
            "engineering_capabilities_blob_sha": ENGINEERING_CAPABILITIES_BLOB_SHA,
            "source_bundle_sha256": summary["source_bundle_sha256"],
            "summary_sha256": digest(dict(summary)),
        },
        "measurement_id": summary["measurement_id"],
        "status": summary["status"],
        "facts": facts,
        "derived_metrics": derived,
        "exposure": dict(summary["exposure"]),
        "evidence_controls": {
            "integrity_valid": summary["integrity_valid"],
            "comparability_valid": summary["comparability_valid"],
            "holdout_replication": summary["holdout_replication"],
            "independent_replications": summary["independent_replications"],
            "overlapping_views_counted_as_independent": False,
            "unknown_fields": unknown,
            "stale_fields": stale,
            "contaminated_fields": contaminated,
        },
        "proof_of_observation_boundary": {
            "facts_and_derived_metrics_separate": True,
            "missing_data_zero_filled": False,
            "hash_chain_integrity_is_source_truth": False,
            "measurement_receipt_is_claim_admission": False,
            "negative_and_inconclusive_outcomes_preserved": True,
        },
        "claim_ceiling": {
            "sha256_predictability_or_weakness_established": False,
            "increased_proof_probability_established": False,
            "mining_advantage_or_profitability_established": False,
            "wall_energy_savings_established": False,
            "extended_hardware_lifetime_established": False,
            "production_readiness_established": False,
            "source_truth_from_integrity_established": False,
        },
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    receipt["receipt_sha256"] = digest(receipt)
    return receipt


def verify_receipt(summary: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    try:
        expected = build_receipt(summary)
    except ValueError:
        return False
    return dict(receipt) == expected


def build_evidence_candidate(receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("I0_MEASUREMENT_RECEIPT_INVALID")
    claimed = receipt.get("receipt_sha256")
    if not _hex64(claimed):
        raise ValueError("I0_MEASUREMENT_RECEIPT_HASH_INVALID")
    replay = dict(receipt)
    replay.pop("receipt_sha256", None)
    if digest(replay) != claimed:
        raise ValueError("I0_MEASUREMENT_RECEIPT_REPLAY_FAIL")
    if receipt.get("authority_delta") != 0 or receipt.get("mass_effect_budget_delta") != 0:
        raise ValueError("I0_MEASUREMENT_RECEIPT_AUTHORITY_ESCALATION")
    ceiling = receipt.get("claim_ceiling")
    if not isinstance(ceiling, Mapping) or any(ceiling.get(name) is not False for name in (
        "sha256_predictability_or_weakness_established",
        "increased_proof_probability_established",
        "mining_advantage_or_profitability_established",
        "wall_energy_savings_established",
        "extended_hardware_lifetime_established",
        "source_truth_from_integrity_established",
    )):
        raise ValueError("I0_MEASUREMENT_RECEIPT_CLAIM_PROMOTION")
    candidate: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "source_measurement_receipt_sha256": claimed,
        "measurement_id": receipt["measurement_id"],
        "measurement_status": receipt["status"],
        "evidence_controls": dict(receipt["evidence_controls"]),
        "projection": {
            "measurement_values_rewritten": False,
            "unknown_fields_preserved": list(receipt["evidence_controls"]["unknown_fields"]),
            "stale_fields_preserved": list(receipt["evidence_controls"]["stale_fields"]),
            "contaminated_fields_preserved": list(receipt["evidence_controls"]["contaminated_fields"]),
            "fundamentum_evaluation_required": True,
            "projection_is_claim_promotion": False,
            "projection_is_evidence_admission": False,
        },
        "claim_ceiling": dict(receipt["claim_ceiling"]),
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    candidate["candidate_sha256"] = digest(candidate)
    return candidate


def verify_evidence_candidate(receipt: Mapping[str, Any], candidate: Mapping[str, Any]) -> bool:
    if not isinstance(candidate, Mapping) or candidate.get("schema") != EVIDENCE_SCHEMA:
        return False
    try:
        expected = build_evidence_candidate(receipt)
    except ValueError:
        return False
    return dict(candidate) == expected
