from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


INPUT_SCHEMA = "janus.demihead.appeal_bundle.v1"
RESULT_SCHEMA = "janus.demihead.appeal_result.v1"

ALLOWED_GROUNDS = {
    "SOURCE_MISSING",
    "SOURCE_MISATTRIBUTED",
    "CORRECTION_MISSING",
    "LANGUAGE_SEMANTIC_DRIFT",
    "REVIEW_DISAGREEMENT",
    "PROVENANCE_MISMATCH",
    "OTHER_EXPLAINED",
}
ALLOWED_ACTIONS = {"INSPECT", "CORRECT_LINEAGE", "REVIEW", "NO_ACTION"}
ALLOWED_RESOLUTIONS = {"NO_CHANGE", "CORRECTION_LINKED", "NOTE_ADDED"}


class AppealError(ValueError):
    pass


def canonical_sha256(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_bundle(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)
    if bundle.get("schema") != INPUT_SCHEMA:
        raise AppealError("Unsupported appeal bundle schema")
    return bundle


def _invalid(bundle: dict[str, Any], failures: list[str], decision_sha: str | None) -> dict[str, Any]:
    return {
        "schema": RESULT_SCHEMA,
        "case_id": bundle.get("case_id", "UNSPECIFIED"),
        "status": "INVALID_APPEAL",
        "failures": sorted(set(failures)),
        "decision_receipt_sha256": decision_sha,
        "history": {
            "decision_receipt": bundle.get("decision_receipt"),
            "appeal": bundle.get("appeal"),
            "resolution": bundle.get("resolution"),
        },
        "resolution_effect": None,
        "human_reviewer_identity_proven_by_software": False,
        "invariants": _invariants(),
    }


def _invariants() -> dict[str, Any]:
    return {
        "appeal_is_admission_of_error": False,
        "appeal_request_is_outcome_override": False,
        "original_decision_rewritten": False,
        "history_deleted": False,
        "evidence_state_mutated_by_appeal_gate": False,
        "correction_applied_by_appeal_gate": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }


def evaluate_appeal(bundle: dict[str, Any]) -> dict[str, Any]:
    decision = bundle.get("decision_receipt")
    declared_sha = bundle.get("decision_receipt_sha256")
    appeal = bundle.get("appeal")
    resolution = bundle.get("resolution")
    failures: list[str] = []

    if not isinstance(decision, dict) or not decision:
        return _invalid(bundle, ["DECISION_RECEIPT_MISSING"], None)

    actual_sha = canonical_sha256(decision)
    if not isinstance(declared_sha, str) or declared_sha != actual_sha:
        failures.append("DECISION_RECEIPT_SHA256_MISMATCH")

    if not isinstance(appeal, dict):
        failures.append("APPEAL_OBJECT_MISSING")
        return _invalid(bundle, failures, actual_sha)

    appeal_id = appeal.get("appeal_id")
    ground = appeal.get("ground")
    requested_action = appeal.get("requested_action")
    statement = appeal.get("statement")

    if not isinstance(appeal_id, str) or not appeal_id.strip():
        failures.append("APPEAL_ID_MISSING")
    if ground not in ALLOWED_GROUNDS:
        failures.append("UNSUPPORTED_APPEAL_GROUND")
    if requested_action not in ALLOWED_ACTIONS:
        failures.append("UNSUPPORTED_REQUESTED_ACTION")
    if appeal.get("user_requested") is not True:
        failures.append("USER_REQUEST_NOT_CONFIRMED")
    if ground == "OTHER_EXPLAINED" and (not isinstance(statement, str) or not statement.strip()):
        failures.append("OTHER_EXPLAINED_REQUIRES_STATEMENT")

    resolution_effect: dict[str, Any] | None = None
    state = "APPEAL_RECORDED_NEEDS_HUMAN_REVIEW"

    if resolution is not None:
        if not isinstance(resolution, dict):
            failures.append("RESOLUTION_NOT_OBJECT")
        else:
            resolution_id = resolution.get("resolution_id")
            reviewer_id = resolution.get("reviewer_id")
            resolution_type = resolution.get("resolution_type")
            if not isinstance(resolution_id, str) or not resolution_id.strip():
                failures.append("RESOLUTION_ID_MISSING")
            if not isinstance(reviewer_id, str) or not reviewer_id.strip():
                failures.append("RESOLUTION_REVIEWER_ID_MISSING")
            if resolution.get("verifier_status") != "PASS":
                failures.append("RESOLUTION_VERIFIER_NOT_PASS")
            if resolution_type not in ALLOWED_RESOLUTIONS:
                failures.append("UNSUPPORTED_RESOLUTION_TYPE")
            elif resolution_type == "NO_CHANGE":
                state = "APPEAL_RESOLVED_NO_CHANGE"
                resolution_effect = {
                    "type": "NO_CHANGE",
                    "decision_rewritten": False,
                    "evidence_state_mutated": False,
                }
            elif resolution_type == "NOTE_ADDED":
                note = resolution.get("note")
                if not isinstance(note, str) or not note.strip():
                    failures.append("NOTE_ADDED_REQUIRES_NOTE")
                else:
                    state = "APPEAL_RESOLVED_NOTE_ADDED"
                    resolution_effect = {
                        "type": "NOTE_ADDED",
                        "note": note,
                        "decision_rewritten": False,
                        "evidence_state_mutated": False,
                    }
            elif resolution_type == "CORRECTION_LINKED":
                correction_id = resolution.get("correction_id")
                if not isinstance(correction_id, str) or not correction_id.strip():
                    failures.append("CORRECTION_LINKED_REQUIRES_CORRECTION_ID")
                else:
                    state = "APPEAL_RESOLVED_CORRECTION_LINKED"
                    resolution_effect = {
                        "type": "CORRECTION_LINKED",
                        "correction_id": correction_id,
                        "correction_applied": False,
                        "next_gate_owner": "KETO_CORRECTION_PROPAGATOR",
                        "decision_rewritten": False,
                        "evidence_state_mutated": False,
                    }

    if failures:
        return _invalid(bundle, failures, actual_sha)

    return {
        "schema": RESULT_SCHEMA,
        "case_id": bundle.get("case_id", "UNSPECIFIED"),
        "status": state,
        "failures": [],
        "appeal_id": appeal_id,
        "ground": ground,
        "requested_action": requested_action,
        "decision_receipt_sha256": actual_sha,
        "decision_binding_verified": True,
        "needs_human_review": resolution is None,
        "resolution_effect": resolution_effect,
        "history": {
            "decision_receipt": decision,
            "appeal": appeal,
            "resolution": resolution,
        },
        "human_reviewer_identity_proven_by_software": False,
        "invariants": _invariants(),
        "claim_ceiling": {
            "established": [
                "The appeal is bound to the exact submitted decision receipt by canonical SHA-256.",
                "The original decision, appeal and optional resolution are preserved together in the output history.",
                "A correction-linked resolution records only a correction reference and delegates application to the correction propagator.",
            ],
            "not_established": [
                "that filing the appeal proves the original decision was wrong",
                "human identity of a resolver",
                "truth of a correction",
                "automatic evidence-state mutation",
                "world-effect authority",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    decision = {
        "receipt_id": "decision-1",
        "evidence_state": "CONTESTED",
        "release_control": "SHOW_CONFLICT_AND_ALLOW_EXIT",
    }
    base = {
        "schema": INPUT_SCHEMA,
        "case_id": "SELF_TEST",
        "decision_receipt": decision,
        "decision_receipt_sha256": canonical_sha256(decision),
        "appeal": {
            "appeal_id": "appeal-1",
            "ground": "CORRECTION_MISSING",
            "requested_action": "CORRECT_LINEAGE",
            "statement": "Known correction is not linked.",
            "user_requested": True,
        },
        "resolution": None,
    }
    pending = evaluate_appeal(base)

    resolved_input = json.loads(json.dumps(base))
    resolved_input["resolution"] = {
        "resolution_id": "resolution-1",
        "reviewer_id": "human-reviewer-1",
        "verifier_status": "PASS",
        "resolution_type": "CORRECTION_LINKED",
        "correction_id": "corr-42",
    }
    resolved = evaluate_appeal(resolved_input)

    tampered = json.loads(json.dumps(base))
    tampered["decision_receipt"]["evidence_state"] = "SUPPORTED_BY_PRESENT_SOURCES"
    tampered_result = evaluate_appeal(tampered)

    checks = {
        "pending_needs_review": pending["status"] == "APPEAL_RECORDED_NEEDS_HUMAN_REVIEW",
        "pending_binding_verified": pending["decision_binding_verified"] is True,
        "correction_linked_resolves": resolved["status"] == "APPEAL_RESOLVED_CORRECTION_LINKED",
        "correction_not_applied_here": resolved["resolution_effect"]["correction_applied"] is False,
        "next_gate_is_correction_propagator": resolved["resolution_effect"]["next_gate_owner"] == "KETO_CORRECTION_PROPAGATOR",
        "tamper_fails": tampered_result["status"] == "INVALID_APPEAL",
        "original_decision_not_rewritten": resolved["invariants"]["original_decision_rewritten"] is False,
        "appeal_not_error_admission": resolved["invariants"]["appeal_is_admission_of_error"] is False,
        "authority_zero": resolved["invariants"]["authority_delta"] == 0,
        "mass_effect_zero": resolved["invariants"]["mass_effect_budget_delta"] == 0,
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
    parser = argparse.ArgumentParser(description="DemiHead append-only Human Appeal reference gate")
    parser.add_argument("bundle", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        _render(self_test(), args.output)
        return
    if args.bundle is None:
        parser.error("bundle is required unless --self-test is used")
    _render(evaluate_appeal(load_bundle(args.bundle)), args.output)


if __name__ == "__main__":
    main()
