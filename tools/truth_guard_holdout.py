from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from epistemic_execution_gate import assess_case
from fundamentum_truth_guard import assess_commit_case, assess_language_bundle, propagate_corrections
from reviewer_appeal_gate import (
    REVIEW_BUNDLE_SCHEMA,
    assess_review_bundle,
    freeze_appeal,
    validate_appeal_package,
)


CORPUS_SCHEMA = "janus.demihead.truth_guard_adversarial_holdout.v1"
RESULT_SCHEMA = "janus.demihead.truth_guard_adversarial_holdout_result.v1"


def canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def load_frozen_corpus(path: Path) -> dict[str, Any]:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(corpus, dict):
        raise ValueError("HOLDOUT_CORPUS_NOT_OBJECT")
    freeze_payload = corpus.get("freeze_payload")
    if not isinstance(freeze_payload, dict):
        raise ValueError("HOLDOUT_FREEZE_PAYLOAD_MISSING")
    if freeze_payload.get("schema") != CORPUS_SCHEMA:
        raise ValueError("HOLDOUT_SCHEMA_MISMATCH")
    expected = str(corpus.get("freeze_sha256", ""))
    actual = sha256_json(freeze_payload)
    if actual != expected:
        raise ValueError(f"HOLDOUT_FREEZE_SHA256_MISMATCH expected={expected} actual={actual}")
    if freeze_payload.get("frozen_before_first_execution") is not True:
        raise ValueError("HOLDOUT_NOT_DECLARED_FROZEN_BEFORE_EXECUTION")
    cases = freeze_payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("HOLDOUT_CASES_MISSING")
    if freeze_payload.get("case_count") != len(cases):
        raise ValueError("HOLDOUT_CASE_COUNT_MISMATCH")
    if freeze_payload.get("required_pass_count") != len(cases):
        raise ValueError("HOLDOUT_REQUIRED_PASS_COUNT_MISMATCH")
    ids = [str(case.get("case_id", "")) for case in cases]
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("HOLDOUT_CASE_IDS_MUST_BE_NONEMPTY_AND_UNIQUE")
    return corpus


def _path_get(value: Any, path: str) -> Any:
    current = value
    for part in path.split("."):
        if isinstance(current, list):
            current = current[int(part)]
        elif isinstance(current, dict):
            current = current[part]
        else:
            raise KeyError(path)
    return current


def _build_review_result(payload: dict[str, Any]) -> dict[str, Any]:
    package = freeze_appeal(payload["original_decision"], payload["appeal_request"])
    attestations: list[dict[str, Any]] = []
    for row in payload.get("reviews", []):
        attestation = {
            "reviewer_id": row["reviewer_id"],
            "independence_root_id": row["independence_root_id"],
            "verdict": row["verdict"],
            "appeal_id": package["appeal_id"],
            "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
            "original_decision_digest_sha256": package["original_decision_digest_sha256"],
            "independent_submission": row.get("independent_submission", True),
            "saw_other_verdicts_before_submission": row.get("saw_other_verdicts_before_submission", False),
            "package_bound": row.get("package_bound", True),
            "evidence_root_ids": row.get("evidence_root_ids", [f"holdout:{row['independence_root_id']}"]),
        }
        for key, value in row.items():
            if key not in attestation:
                attestation[key] = value
        attestations.append(attestation)

    bundle = {
        "schema": REVIEW_BUNDLE_SCHEMA,
        "appeal_id": package["appeal_id"],
        "appeal_package_digest_sha256": package["appeal_package_digest_sha256"],
        "attestations": attestations,
    }
    bundle.update(payload.get("bundle_overrides", {}))
    return assess_review_bundle(package, bundle)


def execute_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = case.get("kind")
    payload = case.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("CASE_PAYLOAD_NOT_OBJECT")

    if kind == "epistemic":
        return assess_case(payload)
    if kind == "commit":
        return assess_commit_case(payload)
    if kind == "language":
        return assess_language_bundle(payload)
    if kind == "correction":
        return propagate_corrections(payload)
    if kind == "review":
        return _build_review_result(payload)
    if kind == "appeal_freeze_invalid":
        return freeze_appeal(payload["original_decision"], payload["appeal_request"])
    if kind == "appeal_tamper":
        package = freeze_appeal(payload["original_decision"], payload["appeal_request"])
        mutation = payload.get("mutation", {})
        package[str(mutation["field"])] = mutation.get("value")
        validate_appeal_package(package)
        return package
    raise ValueError(f"UNKNOWN_HOLDOUT_CASE_KIND:{kind}")


def compare_expected(result: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for field, wanted in expected.get("top_level", {}).items():
        observed = result.get(field)
        if observed != wanted:
            errors.append(f"top_level.{field}: expected {wanted!r}, observed {observed!r}")
    for path, wanted in expected.get("path_equals", {}).items():
        try:
            observed = _path_get(result, path)
        except Exception as exc:
            errors.append(f"{path}: missing ({type(exc).__name__})")
            continue
        if observed != wanted:
            errors.append(f"{path}: expected {wanted!r}, observed {observed!r}")
    for path, wanted_len in expected.get("path_length", {}).items():
        try:
            observed = _path_get(result, path)
        except Exception as exc:
            errors.append(f"{path}: missing ({type(exc).__name__})")
            continue
        try:
            observed_len = len(observed)
        except TypeError:
            errors.append(f"{path}: object has no length")
            continue
        if observed_len != wanted_len:
            errors.append(f"len({path}): expected {wanted_len}, observed {observed_len}")
    return errors


def run_holdout(corpus: dict[str, Any]) -> dict[str, Any]:
    freeze_payload = corpus["freeze_payload"]
    rows: list[dict[str, Any]] = []
    passed = 0

    for case in freeze_payload["cases"]:
        case_id = case["case_id"]
        expected_error = case.get("expected_error_contains")
        try:
            result = execute_case(case)
        except Exception as exc:
            if expected_error and expected_error in str(exc):
                passed += 1
                rows.append(
                    {
                        "case_id": case_id,
                        "status": "PASS",
                        "expected_error_observed": type(exc).__name__,
                        "error_text": str(exc),
                    }
                )
            else:
                rows.append(
                    {
                        "case_id": case_id,
                        "status": "FAIL",
                        "unexpected_exception": type(exc).__name__,
                        "error_text": str(exc),
                    }
                )
            continue

        if expected_error:
            rows.append(
                {
                    "case_id": case_id,
                    "status": "FAIL",
                    "reason": f"Expected error containing {expected_error!r}, but case returned normally.",
                    "observed_result": result,
                }
            )
            continue

        errors = compare_expected(result, case.get("expected", {}))
        if errors:
            rows.append(
                {
                    "case_id": case_id,
                    "status": "FAIL",
                    "comparison_errors": errors,
                    "observed_result": result,
                }
            )
        else:
            passed += 1
            rows.append(
                {
                    "case_id": case_id,
                    "status": "PASS",
                    "observed_summary": {
                        key: result[key]
                        for key in (
                            "evidence_state",
                            "commit_state",
                            "status",
                            "independent_root_count",
                            "external_effect_authorized",
                            "automatic_overrule",
                        )
                        if key in result
                    },
                }
            )

    total = len(rows)
    required = freeze_payload["required_pass_count"]
    overall = "PASS" if passed == required == total else "FAIL"
    return {
        "schema": RESULT_SCHEMA,
        "corpus_id": freeze_payload["corpus_id"],
        "freeze_sha256": corpus["freeze_sha256"],
        "freeze_verified_before_execution": True,
        "status": overall,
        "passed": passed,
        "total": total,
        "required_pass_count": required,
        "cases": rows,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "independent_external_validation": False,
        "real_world_reviewer_independence_established": False,
        "universal_truthfulness_established": False,
        "production_readiness_established": False,
        "claim_ceiling": freeze_payload["claim_ceiling"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen JANUS DemiHead truth-guard adversarial holdout")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=Path("holdout/truth_guard_v1/frozen_corpus.json"),
    )
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    corpus = load_frozen_corpus(args.corpus)
    result = run_holdout(corpus)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(text, end="")
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
