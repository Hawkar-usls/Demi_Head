from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


APPEAL_REQUEST_SCHEMA = "janus.demihead.appeal_request.v1"
APPEAL_PACKAGE_SCHEMA = "janus.demihead.appeal_package.v1"
REVIEW_BUNDLE_SCHEMA = "janus.demihead.review_bundle.v1"
REVIEW_RESULT_SCHEMA = "janus.demihead.review_result.v1"

ALLOWED_GROUNDS = {
    "FACTUAL_ACCURACY",
    "SOURCE_PROVENANCE",
    "CORRECTION_STATE",
    "TRANSLATION_SEMANTICS",
    "URGENCY",
    "SAFETY_CLASSIFICATION",
    "USER_RIGHTS",
    "PROPOSED_ACTION",
    "OTHER_SCOPE_ONLY",
}

ALLOWED_VERDICTS = {
    "UPHOLD",
    "CORRECTION_SUPPORTED",
    "INSUFFICIENT_EVIDENCE",
    "ABSTAIN",
}

INVARIANTS = [
    "APPEAL != ERROR",
    "APPEAL != AUTOMATIC_OVERRULE",
    "APPEAL != HOSTILITY",
    "REVIEW != PUNISHMENT",
    "REVIEW_COUNT != TRUTH",
    "REVIEWER_ID != AUTHORITY",
    "SAME_ROOT_REVIEW != INDEPENDENT_REVIEW",
    "CONSENSUS != EXTERNAL_EFFECT_AUTHORIZATION",
    "ORIGINAL_DECISION != DELETABLE",
    "CORRECTION_WITHOUT_AUDIT_TRAIL != PREVENTION",
    "APPEAL_RECORD != PERSONALITY_DOSSIER",
    "USER_EXIT_REMAINS_AVAILABLE",
    "DISAGREEMENT != ERROR",
]


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _package_without_digest(package: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in package.items() if key != "appeal_package_digest_sha256"}


def freeze_appeal(original_decision: dict[str, Any], request: dict[str, Any]) -> dict[str, Any]:
    if request.get("schema") != APPEAL_REQUEST_SCHEMA:
        raise ValueError(f"Unsupported appeal request schema; expected {APPEAL_REQUEST_SCHEMA}")

    appeal_id = str(request.get("appeal_id", "")).strip()
    locator = str(request.get("original_decision_locator", "")).strip()
    if not appeal_id or not locator:
        raise ValueError("appeal_id and original_decision_locator are required")

    grounds = request.get("grounds")
    if not isinstance(grounds, list) or not grounds:
        raise ValueError("grounds must be a non-empty list of bounded categories")
    unknown = sorted(set(str(item) for item in grounds) - ALLOWED_GROUNDS)
    if unknown:
        raise ValueError(f"Unsupported appeal grounds: {unknown}")

    if request.get("penalty_for_appeal", False) is not False:
        raise ValueError("Appeal cannot carry a penalty")
    if request.get("surveillance_escalation_for_appeal", False) is not False:
        raise ValueError("Appeal cannot authorize surveillance escalation")
    if request.get("user_exit_available") is not True:
        raise ValueError("user_exit_available must remain true for this reference gate")

    package = {
        "schema": APPEAL_PACKAGE_SCHEMA,
        "appeal_id": appeal_id,
        "original_decision_locator": locator,
        "original_decision_digest_sha256": sha256_json(original_decision),
        "grounds": sorted(set(str(item) for item in grounds)),
        "requested_review_scope": str(request.get("requested_review_scope", "DECISION_AND_EVIDENCE")).strip(),
        "high_stakes": bool(request.get("high_stakes", False)),
        "user_exit_available": True,
        "penalty_for_appeal": False,
        "surveillance_escalation_for_appeal": False,
        "original_decision_preserved": True,
        "automatic_overrule": False,
        "external_effect_authorized": False,
        "appellant_profile_created": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "invariants": INVARIANTS,
    }
    package["appeal_package_digest_sha256"] = sha256_json(package)
    return package


def validate_appeal_package(package: dict[str, Any]) -> None:
    if package.get("schema") != APPEAL_PACKAGE_SCHEMA:
        raise ValueError(f"Unsupported appeal package schema; expected {APPEAL_PACKAGE_SCHEMA}")
    expected = sha256_json(_package_without_digest(package))
    if package.get("appeal_package_digest_sha256") != expected:
        raise ValueError("APPEAL_PACKAGE_DIGEST_MISMATCH")
    if package.get("original_decision_preserved") is not True:
        raise ValueError("ORIGINAL_DECISION_MUST_REMAIN_PRESERVED")
    if package.get("automatic_overrule") is not False:
        raise ValueError("APPEAL_CANNOT_AUTOMATICALLY_OVERRULE")
    if package.get("external_effect_authorized") is not False:
        raise ValueError("APPEAL_CANNOT_AUTHORIZE_EXTERNAL_EFFECT")
    if package.get("penalty_for_appeal") is not False:
        raise ValueError("APPEAL_PENALTY_FORBIDDEN")
    if package.get("surveillance_escalation_for_appeal") is not False:
        raise ValueError("APPEAL_SURVEILLANCE_ESCALATION_FORBIDDEN")
    if package.get("user_exit_available") is not True:
        raise ValueError("USER_EXIT_MUST_REMAIN_AVAILABLE")


def assess_review_bundle(package: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
    validate_appeal_package(package)
    if bundle.get("schema") != REVIEW_BUNDLE_SCHEMA:
        raise ValueError(f"Unsupported review bundle schema; expected {REVIEW_BUNDLE_SCHEMA}")
    if bundle.get("appeal_id") != package["appeal_id"]:
        raise ValueError("REVIEW_BUNDLE_APPEAL_ID_MISMATCH")
    if bundle.get("appeal_package_digest_sha256") != package["appeal_package_digest_sha256"]:
        raise ValueError("REVIEW_BUNDLE_PACKAGE_DIGEST_MISMATCH")
    if float(bundle.get("requested_reviewer_authority_multiplier", 1) or 1) != 1.0:
        raise ValueError("REVIEW_COUNT_TO_AUTHORITY_FORBIDDEN")

    attestations = bundle.get("attestations", [])
    if not isinstance(attestations, list):
        raise ValueError("attestations must be a list")

    binding_failures: list[dict[str, Any]] = []
    accepted: list[dict[str, Any]] = []
    for index, row in enumerate(attestations):
        if not isinstance(row, dict):
            binding_failures.append({"index": index, "reason": "ATTESTATION_NOT_OBJECT"})
            continue
        reviewer_id = str(row.get("reviewer_id", "")).strip()
        root = str(row.get("independence_root_id", "")).strip()
        verdict = str(row.get("verdict", "")).strip()
        reasons: list[str] = []
        if not reviewer_id:
            reasons.append("REVIEWER_ID_REQUIRED")
        if not root:
            reasons.append("INDEPENDENCE_ROOT_REQUIRED")
        if verdict not in ALLOWED_VERDICTS:
            reasons.append("VERDICT_INVALID")
        if row.get("appeal_id") != package["appeal_id"]:
            reasons.append("APPEAL_ID_MISMATCH")
        if row.get("appeal_package_digest_sha256") != package["appeal_package_digest_sha256"]:
            reasons.append("PACKAGE_DIGEST_MISMATCH")
        if row.get("original_decision_digest_sha256") != package["original_decision_digest_sha256"]:
            reasons.append("ORIGINAL_DECISION_DIGEST_MISMATCH")
        if row.get("independent_submission") is not True:
            reasons.append("INDEPENDENT_SUBMISSION_NOT_ATTESTED")
        if row.get("saw_other_verdicts_before_submission") is not False:
            reasons.append("BLINDING_NOT_PRESERVED")
        if row.get("package_bound") is not True:
            reasons.append("EXACT_PACKAGE_BINDING_NOT_ATTESTED")
        if reasons:
            binding_failures.append({"index": index, "reviewer_id": reviewer_id or None, "reasons": reasons})
            continue
        accepted.append({
            "reviewer_id": reviewer_id,
            "independence_root_id": root,
            "verdict": verdict,
            "evidence_root_ids": sorted(set(str(item) for item in row.get("evidence_root_ids", []))),
        })

    if binding_failures:
        return {
            "schema": REVIEW_RESULT_SCHEMA,
            "appeal_id": package["appeal_id"],
            "status": "PACKAGE_BINDING_FAILURE",
            "binding_failures": binding_failures,
            "accepted_attestations": accepted,
            "automatic_overrule": False,
            "external_effect_authorized": False,
            "original_decision_preserved": True,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "invariants": INVARIANTS,
        }

    by_root: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        by_root[row["independence_root_id"]].append(row)

    root_outcomes: list[dict[str, Any]] = []
    dependent_duplicates: list[dict[str, Any]] = []
    root_conflict = False
    for root in sorted(by_root):
        rows = by_root[root]
        verdicts = sorted(set(row["verdict"] for row in rows))
        if len(rows) > 1:
            dependent_duplicates.append({
                "independence_root_id": root,
                "reviewer_ids": sorted(row["reviewer_id"] for row in rows),
                "counted_as_independent_roots": 1,
            })
        if len(verdicts) > 1:
            root_conflict = True
            root_outcomes.append({
                "independence_root_id": root,
                "verdict": "INTERNAL_DISAGREEMENT",
                "submitted_verdicts": verdicts,
            })
        else:
            root_outcomes.append({
                "independence_root_id": root,
                "verdict": verdicts[0],
                "submitted_verdicts": verdicts,
            })

    non_abstain = [row for row in root_outcomes if row["verdict"] not in {"ABSTAIN", "INTERNAL_DISAGREEMENT"}]
    independent_root_count = len(root_outcomes)
    effective_review_root_count = len(non_abstain)

    if not root_outcomes:
        status = "OPEN_NO_REVIEW"
    elif root_conflict:
        status = "DISAGREEMENT"
    else:
        distinct = sorted(set(row["verdict"] for row in non_abstain))
        if len(distinct) > 1:
            status = "DISAGREEMENT"
        elif effective_review_root_count < 2:
            status = "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED"
        elif len(distinct) == 0:
            status = "OPEN_INSUFFICIENT_REVIEW"
        else:
            status = f"CONSENSUS_{distinct[0]}"

    correction_proposal: dict[str, Any] | None = None
    if status == "CONSENSUS_CORRECTION_SUPPORTED":
        correction_proposal = {
            "status": "REVIEW_SUPPORTED_NOT_APPLIED",
            "supersedes_original_decision_digest_sha256": package["original_decision_digest_sha256"],
            "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
            "requires_separate_correction_propagation": True,
            "automatic_rewrite": False,
        }

    return {
        "schema": REVIEW_RESULT_SCHEMA,
        "appeal_id": package["appeal_id"],
        "status": status,
        "reviewer_submission_count": len(accepted),
        "independent_root_count": independent_root_count,
        "effective_review_root_count": effective_review_root_count,
        "root_outcomes": root_outcomes,
        "dependent_duplicates": dependent_duplicates,
        "binding_failures": [],
        "correction_proposal": correction_proposal,
        "automatic_overrule": False,
        "external_effect_authorized": False,
        "original_decision_preserved": True,
        "user_exit_available": package["user_exit_available"],
        "appellant_penalty_delta": 0,
        "surveillance_delta": 0,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "claim_ceiling": "Consensus or disagreement describes this exact review package only. It does not create world truth, external-effect permission, reviewer authority over the human, or permission to erase the original decision.",
        "invariants": INVARIANTS,
    }


def self_test() -> dict[str, Any]:
    original = {"decision_id": "D1", "state": "CONTESTED", "claim": "synthetic"}
    request = {
        "schema": APPEAL_REQUEST_SCHEMA,
        "appeal_id": "A1",
        "original_decision_locator": "synthetic:D1",
        "grounds": ["FACTUAL_ACCURACY"],
        "high_stakes": True,
        "user_exit_available": True,
        "penalty_for_appeal": False,
        "surveillance_escalation_for_appeal": False,
    }
    package = freeze_appeal(original, request)

    def attestation(reviewer: str, root: str, verdict: str) -> dict[str, Any]:
        return {
            "reviewer_id": reviewer,
            "independence_root_id": root,
            "verdict": verdict,
            "appeal_id": package["appeal_id"],
            "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
            "original_decision_digest_sha256": package["original_decision_digest_sha256"],
            "independent_submission": True,
            "saw_other_verdicts_before_submission": False,
            "package_bound": True,
            "evidence_root_ids": [f"evidence:{root}"],
        }

    consensus = assess_review_bundle(package, {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "appeal_id": package["appeal_id"],
        "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
        "attestations": [
            attestation("R1", "ROOT-1", "CORRECTION_SUPPORTED"),
            attestation("R2", "ROOT-2", "CORRECTION_SUPPORTED"),
        ],
    })
    disagreement = assess_review_bundle(package, {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "appeal_id": package["appeal_id"],
        "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
        "attestations": [
            attestation("R1", "ROOT-1", "UPHOLD"),
            attestation("R2", "ROOT-2", "CORRECTION_SUPPORTED"),
        ],
    })
    duplicate = assess_review_bundle(package, {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "appeal_id": package["appeal_id"],
        "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
        "attestations": [
            attestation("R1", "SAME-ROOT", "UPHOLD"),
            attestation("R2", "SAME-ROOT", "UPHOLD"),
        ],
    })

    checks = {
        "package_digest_valid": package["appeal_package_digest_sha256"] == sha256_json(_package_without_digest(package)),
        "appeal_has_no_penalty": package["penalty_for_appeal"] is False,
        "original_preserved": package["original_decision_preserved"] is True,
        "consensus_correction_is_not_auto_applied": consensus["status"] == "CONSENSUS_CORRECTION_SUPPORTED" and consensus["automatic_overrule"] is False and consensus["external_effect_authorized"] is False,
        "independent_disagreement_is_preserved": disagreement["status"] == "DISAGREEMENT",
        "same_root_does_not_count_twice": duplicate["status"] == "OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED" and duplicate["independent_root_count"] == 1,
    }
    return {
        "schema": "janus.demihead.reviewer_appeal_gate_self_test.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "invariants": INVARIANTS,
    }


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("Input JSON must be an object")
    return value


def _write(value: dict[str, Any], output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(text, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="JANUS human appeal and independent reviewer ledger reference gate")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze-appeal", nargs=2, metavar=("ORIGINAL_DECISION", "APPEAL_REQUEST"), type=Path)
    mode.add_argument("--assess-reviews", nargs=2, metavar=("APPEAL_PACKAGE", "REVIEW_BUNDLE"), type=Path)
    mode.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    if args.freeze_appeal:
        result = freeze_appeal(_load(args.freeze_appeal[0]), _load(args.freeze_appeal[1]))
    elif args.assess_reviews:
        result = assess_review_bundle(_load(args.assess_reviews[0]), _load(args.assess_reviews[1]))
    else:
        result = self_test()
    _write(result, args.output)


if __name__ == "__main__":
    main()
