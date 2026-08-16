from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


INPUT_SCHEMA = "janus.demihead.reviewer_collection.v1"
RESULT_SCHEMA = "janus.demihead.reviewer_consensus_result.v1"
VALID_VERIFIER_STATUS = "PASS"


class ReviewerCollectionError(ValueError):
    pass


def load_collection(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        collection = json.load(handle)
    if collection.get("schema") != INPUT_SCHEMA:
        raise ReviewerCollectionError("Unsupported reviewer collection schema")
    return collection


def _validate_policy(collection: dict[str, Any]) -> tuple[str, int, list[str]]:
    package_id = collection.get("frozen_package_id")
    if not isinstance(package_id, str) or not package_id:
        raise ReviewerCollectionError("frozen_package_id must be a non-empty string")

    required = collection.get("required_reviewers", 2)
    if not isinstance(required, int) or isinstance(required, bool) or required < 2:
        raise ReviewerCollectionError("required_reviewers must be an integer >= 2")

    review_fields = collection.get("review_fields")
    if not isinstance(review_fields, list) or not review_fields:
        raise ReviewerCollectionError("review_fields must be a non-empty list")
    if not all(isinstance(field, str) and field for field in review_fields):
        raise ReviewerCollectionError("review_fields must contain non-empty strings")
    if len(review_fields) != len(set(review_fields)):
        raise ReviewerCollectionError("review_fields must be unique")
    return package_id, required, review_fields


def _validate_bundle(
    bundle: Any,
    *,
    package_id: str,
    review_fields: list[str],
    index: int,
) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    if not isinstance(bundle, dict):
        return {}, [f"REVIEW_{index}:BUNDLE_NOT_OBJECT"]

    reviewer_id = bundle.get("reviewer_id")
    attestation_id = bundle.get("attestation_id")
    bundle_package = bundle.get("frozen_package_id")
    verifier_status = bundle.get("verifier_status")
    labels = bundle.get("labels")

    if not isinstance(reviewer_id, str) or not reviewer_id.strip():
        failures.append(f"REVIEW_{index}:REVIEWER_ID_MISSING")
    if not isinstance(attestation_id, str) or not attestation_id.strip():
        failures.append(f"REVIEW_{index}:ATTESTATION_ID_MISSING")
    if bundle_package != package_id:
        failures.append(f"REVIEW_{index}:FROZEN_PACKAGE_MISMATCH")
    if verifier_status != VALID_VERIFIER_STATUS:
        failures.append(f"REVIEW_{index}:VERIFIER_NOT_PASS")
    if bundle.get("declared_independent") is not True:
        failures.append(f"REVIEW_{index}:DECLARED_INDEPENDENCE_NOT_CONFIRMED")
    if bundle.get("labels_frozen_before_model_reveal") is not True:
        failures.append(f"REVIEW_{index}:LABEL_FREEZE_NOT_CONFIRMED")
    if not isinstance(labels, dict):
        failures.append(f"REVIEW_{index}:LABELS_MISSING")
        labels = {}

    missing_fields = [field for field in review_fields if field not in labels]
    if missing_fields:
        failures.append(
            f"REVIEW_{index}:MISSING_REVIEW_FIELDS:" + ",".join(sorted(missing_fields))
        )
    unexpected_fields = sorted(set(labels) - set(review_fields))
    if unexpected_fields:
        failures.append(
            f"REVIEW_{index}:UNDECLARED_REVIEW_FIELDS:" + ",".join(unexpected_fields)
        )

    normalized = {
        "reviewer_id": reviewer_id.strip() if isinstance(reviewer_id, str) else None,
        "attestation_id": attestation_id.strip() if isinstance(attestation_id, str) else None,
        "frozen_package_id": bundle_package,
        "verifier_status": verifier_status,
        "declared_independent": bundle.get("declared_independent"),
        "labels_frozen_before_model_reveal": bundle.get("labels_frozen_before_model_reveal"),
        "labels": {field: labels.get(field) for field in review_fields},
    }
    return normalized, failures


def evaluate_collection(collection: dict[str, Any]) -> dict[str, Any]:
    package_id, required, review_fields = _validate_policy(collection)
    reviewers = collection.get("reviewers", [])
    if not isinstance(reviewers, list):
        raise ReviewerCollectionError("reviewers must be a list")

    receipts: list[dict[str, Any]] = []
    failures: list[str] = []
    normalized_reviewers: list[dict[str, Any]] = []

    for index, bundle in enumerate(reviewers):
        normalized, bundle_failures = _validate_bundle(
            bundle, package_id=package_id, review_fields=review_fields, index=index
        )
        receipts.append(
            {
                "bundle_index": index,
                "reviewer_id": normalized.get("reviewer_id"),
                "attestation_id": normalized.get("attestation_id"),
                "admissible": not bundle_failures,
                "failures": bundle_failures,
            }
        )
        failures.extend(bundle_failures)
        normalized_reviewers.append(normalized)

    valid = [
        reviewer
        for reviewer, receipt in zip(normalized_reviewers, receipts)
        if receipt["admissible"]
    ]
    reviewer_ids = [reviewer["reviewer_id"] for reviewer in valid]
    attestation_ids = [reviewer["attestation_id"] for reviewer in valid]

    if len(reviewer_ids) != len(set(reviewer_ids)):
        failures.append("REVIEWER_IDS_NOT_DISTINCT")
    if len(attestation_ids) != len(set(attestation_ids)):
        failures.append("ATTESTATION_IDS_NOT_DISTINCT")

    failures = sorted(set(failures))
    if failures:
        collection_state = "INVALID_COLLECTION"
        status = "FAIL"
        ready = False
    elif len(valid) == 0:
        collection_state = "WAITING_FOR_FIRST_REVIEWER"
        status = "PASS"
        ready = False
    elif len(valid) < required:
        collection_state = "WAITING_FOR_SECOND_REVIEWER"
        status = "PASS"
        ready = False
    else:
        collection_state = "READY_FOR_CONSENSUS"
        status = "PASS"
        ready = True

    consensus: dict[str, Any] | None = None
    disagreement_fields: list[str] = []
    if ready:
        field_results: dict[str, Any] = {}
        for field in review_fields:
            values = [reviewer["labels"][field] for reviewer in valid]
            first = values[0]
            if all(value == first for value in values[1:]):
                field_results[field] = first
            else:
                field_results[field] = "DISAGREEMENT"
                disagreement_fields.append(field)
        consensus = {
            "rule": "EXACT_UNANIMITY_PER_FIELD",
            "fields": field_results,
            "disagreement_fields": disagreement_fields,
            "unanimous_field_count": len(review_fields) - len(disagreement_fields),
            "disagreement_field_count": len(disagreement_fields),
            "majority_vote_used": False,
            "model_fill_used": False,
            "adjudication_used": False,
        }

    return {
        "schema": RESULT_SCHEMA,
        "case_id": collection.get("case_id", "UNSPECIFIED"),
        "frozen_package_id": package_id,
        "status": status,
        "collection_state": collection_state,
        "required_reviewers": required,
        "submitted_reviewer_count": len(reviewers),
        "admissible_reviewer_count": len(valid),
        "bundle_receipts": receipts,
        "failures": failures,
        "consensus_admission_ready": ready,
        "consensus": consensus,
        "reviewer_ids": reviewer_ids,
        "attestation_ids": attestation_ids,
        "human_independence_proven_by_software": False,
        "personhood_proven_by_software": False,
        "off_channel_non_collusion_proven_by_software": False,
        "reviewer_competence_truth_proven_by_software": False,
        "invariants": {
            "waiting_is_failure": False,
            "reviewer_count_is_truth_weight": False,
            "unanimity_is_objective_truth": False,
            "disagreement_is_error": False,
            "majority_can_override_disagreement": False,
            "model_can_fill_disagreement": False,
            "evidence_state_mutated_by_gate": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "established": [
                "The submitted artifact collection is classified under explicit readiness rules.",
                "When ready, declared review fields are combined by exact unanimity and any non-unanimity is preserved as DISAGREEMENT.",
            ],
            "not_established": [
                "human independence",
                "personhood",
                "reviewer competence truthfulness",
                "absence of collusion",
                "objective truth from unanimity",
                "real-world evidence from synthetic fixtures",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    base = {
        "schema": INPUT_SCHEMA,
        "case_id": "SELF_TEST",
        "frozen_package_id": "pkg-1",
        "required_reviewers": 2,
        "review_fields": ["evidence_state", "uncertainty_class"],
        "reviewers": [],
    }
    zero = evaluate_collection(base)

    one_input = json.loads(json.dumps(base))
    one_input["reviewers"] = [
        {
            "reviewer_id": "R1",
            "attestation_id": "A1",
            "frozen_package_id": "pkg-1",
            "verifier_status": "PASS",
            "declared_independent": True,
            "labels_frozen_before_model_reveal": True,
            "labels": {"evidence_state": "CONTESTED", "uncertainty_class": "MATERIAL"},
        }
    ]
    one = evaluate_collection(one_input)

    two_input = json.loads(json.dumps(one_input))
    two_input["reviewers"].append(
        {
            "reviewer_id": "R2",
            "attestation_id": "A2",
            "frozen_package_id": "pkg-1",
            "verifier_status": "PASS",
            "declared_independent": True,
            "labels_frozen_before_model_reveal": True,
            "labels": {"evidence_state": "CONTESTED", "uncertainty_class": "LOW"},
        }
    )
    two = evaluate_collection(two_input)

    checks = {
        "zero_waits_for_first": zero["collection_state"] == "WAITING_FOR_FIRST_REVIEWER",
        "one_waits_for_second": one["collection_state"] == "WAITING_FOR_SECOND_REVIEWER",
        "two_ready": two["collection_state"] == "READY_FOR_CONSENSUS",
        "unanimous_field_preserved": two["consensus"]["fields"]["evidence_state"] == "CONTESTED",
        "drift_becomes_disagreement": two["consensus"]["fields"]["uncertainty_class"] == "DISAGREEMENT",
        "no_majority_override": two["consensus"]["majority_vote_used"] is False,
        "independence_not_proven": two["human_independence_proven_by_software"] is False,
        "authority_zero": two["invariants"]["authority_delta"] == 0,
        "mass_effect_zero": two["invariants"]["mass_effect_budget_delta"] == 0,
    }
    if not all(checks.values()):
        raise AssertionError(checks)
    return {"self_test": "PASS", "checks": checks}


def _render(payload: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


def main() -> None:
    parser = argparse.ArgumentParser(description="DemiHead fail-closed reviewer collection and disagreement gate")
    parser.add_argument("collection", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        _render(self_test(), args.output)
        return
    if args.collection is None:
        parser.error("collection is required unless --self-test is used")
    _render(evaluate_collection(load_collection(args.collection)), args.output)


if __name__ == "__main__":
    main()
