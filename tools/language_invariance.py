from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


INPUT_SCHEMA = "janus.demihead.language_render_bundle.v1"
RESULT_SCHEMA = "janus.demihead.language_invariance_result.v1"
REQUIRED_LANGUAGES = ("uk", "ru", "en")
PROTECTED_FIELDS = (
    "evidence_state",
    "uncertainty_class",
    "urgency_class",
    "user_rights",
    "official_position_present",
    "independent_evidence_present",
    "contradictions_present",
    "unknown_fields_present",
    "release_control",
)
SET_LIKE_FIELDS = {"user_rights"}


class LanguageInvariantError(ValueError):
    pass


def load_bundle(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        bundle = json.load(handle)
    if bundle.get("schema") != INPUT_SCHEMA:
        raise LanguageInvariantError("Unsupported language render bundle schema")
    return bundle


def _normalize(field: str, value: Any) -> Any:
    if field in SET_LIKE_FIELDS:
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise LanguageInvariantError(f"{field} must be a list of non-empty strings")
        if len(value) != len(set(value)):
            raise LanguageInvariantError(f"{field} must not contain duplicates")
        return sorted(value)
    return value


def _validate_semantics(semantics: dict[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(semantics, dict):
        raise LanguageInvariantError(f"{label} semantics must be an object")
    missing = [field for field in PROTECTED_FIELDS if field not in semantics]
    if missing:
        raise LanguageInvariantError(f"{label} is missing protected fields: {', '.join(missing)}")

    normalized = {field: _normalize(field, semantics[field]) for field in PROTECTED_FIELDS}

    for field in (
        "official_position_present",
        "independent_evidence_present",
        "contradictions_present",
        "unknown_fields_present",
    ):
        if not isinstance(normalized[field], bool):
            raise LanguageInvariantError(f"{label}.{field} must be boolean")

    for field in ("evidence_state", "uncertainty_class", "urgency_class", "release_control"):
        if not isinstance(normalized[field], str) or not normalized[field]:
            raise LanguageInvariantError(f"{label}.{field} must be a non-empty string")

    return normalized


def evaluate_invariance(bundle: dict[str, Any]) -> dict[str, Any]:
    required = bundle.get("required_languages", list(REQUIRED_LANGUAGES))
    if required != list(REQUIRED_LANGUAGES):
        raise LanguageInvariantError("required_languages must be exactly ['uk', 'ru', 'en'] in v1")

    canonical = _validate_semantics(bundle.get("canonical_semantics"), "canonical")
    renders = bundle.get("renders")
    if not isinstance(renders, list):
        raise LanguageInvariantError("renders must be a list")

    by_language: dict[str, dict[str, Any]] = {}
    for render in renders:
        if not isinstance(render, dict):
            raise LanguageInvariantError("Each render must be an object")
        language = render.get("language")
        if language not in REQUIRED_LANGUAGES:
            raise LanguageInvariantError(f"Unsupported language: {language}")
        if language in by_language:
            raise LanguageInvariantError(f"Duplicate language render: {language}")
        by_language[language] = render

    violations: list[dict[str, Any]] = []
    language_rows: list[dict[str, Any]] = []

    for language in REQUIRED_LANGUAGES:
        render = by_language.get(language)
        if render is None:
            violations.append(
                {
                    "language": language,
                    "field": None,
                    "type": "MISSING_REQUIRED_LANGUAGE",
                    "expected": "PRESENT",
                    "observed": "MISSING",
                }
            )
            language_rows.append({"language": language, "status": "MISSING", "field_drift": []})
            continue

        semantics = _validate_semantics(render.get("semantics"), f"render[{language}]")
        field_drift: list[str] = []
        for field in PROTECTED_FIELDS:
            if semantics[field] != canonical[field]:
                field_drift.append(field)
                violations.append(
                    {
                        "language": language,
                        "field": field,
                        "type": "PROTECTED_SEMANTIC_DRIFT",
                        "expected": canonical[field],
                        "observed": semantics[field],
                    }
                )

        language_rows.append(
            {
                "language": language,
                "status": "PASS" if not field_drift else "FAIL",
                "field_drift": field_drift,
                "presentation_fields_compared": False,
            }
        )

    status = "PASS" if not violations else "FAIL_CLOSED_SEMANTIC_DRIFT"
    return {
        "schema": RESULT_SCHEMA,
        "bundle_id": bundle.get("bundle_id", "UNSPECIFIED"),
        "status": status,
        "required_languages": list(REQUIRED_LANGUAGES),
        "protected_fields": list(PROTECTED_FIELDS),
        "languages": language_rows,
        "violations": violations,
        "invariants": {
            "presentation_prose_compared_as_truth": False,
            "language_identity_used_as_evidence_weight": False,
            "semantic_drift_silently_normalized": False,
            "evidence_state_mutated": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "established": [
                "Protected semantic fields are compared against one canonical semantic envelope across required uk/ru/en receipts.",
                "Missing required languages and protected semantic drift fail closed.",
            ],
            "not_established": [
                "literary translation quality",
                "absence of every possible framing bias",
                "truth of the canonical semantic envelope",
                "automatic translation generation",
            ],
        },
    }


def self_test() -> dict[str, Any]:
    canonical = {
        "evidence_state": "CONTESTED",
        "uncertainty_class": "MATERIAL",
        "urgency_class": "NORMAL",
        "user_rights": ["APPEAL", "DISAGREE", "EXIT", "INSPECT_SOURCES"],
        "official_position_present": True,
        "independent_evidence_present": True,
        "contradictions_present": True,
        "unknown_fields_present": True,
        "release_control": "SHOW_CONFLICT_AND_ALLOW_EXIT",
    }
    bundle = {
        "schema": INPUT_SCHEMA,
        "bundle_id": "SELF_TEST",
        "required_languages": list(REQUIRED_LANGUAGES),
        "canonical_semantics": canonical,
        "renders": [
            {
                "language": "uk",
                "semantics": {**canonical, "user_rights": list(reversed(canonical["user_rights"]))},
                "presentation": {"summary": "Український текст"},
            },
            {
                "language": "ru",
                "semantics": canonical,
                "presentation": {"summary": "Русский текст"},
            },
            {
                "language": "en",
                "semantics": canonical,
                "presentation": {"summary": "English text"},
            },
        ],
    }
    passed = evaluate_invariance(bundle)

    drifted = json.loads(json.dumps(bundle))
    drifted["bundle_id"] = "DRIFT_TEST"
    drifted["renders"][1]["semantics"]["uncertainty_class"] = "NONE"
    failed = evaluate_invariance(drifted)

    missing = json.loads(json.dumps(bundle))
    missing["bundle_id"] = "MISSING_TEST"
    missing["renders"] = [render for render in missing["renders"] if render["language"] != "en"]
    missing_result = evaluate_invariance(missing)

    checks = {
        "equal_semantics_pass": passed["status"] == "PASS",
        "prose_differences_do_not_fail": not passed["violations"],
        "set_order_normalized": passed["status"] == "PASS",
        "uncertainty_drift_fails": failed["status"] == "FAIL_CLOSED_SEMANTIC_DRIFT",
        "missing_language_fails": missing_result["status"] == "FAIL_CLOSED_SEMANTIC_DRIFT",
        "authority_delta_zero": passed["invariants"]["authority_delta"] == 0,
        "mass_effect_delta_zero": passed["invariants"]["mass_effect_budget_delta"] == 0,
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
    parser = argparse.ArgumentParser(description="DemiHead uk/ru/en protected semantic invariance gate")
    parser.add_argument("bundle", type=Path, nargs="?")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.self_test:
        _render(self_test(), args.output)
        return
    if args.bundle is None:
        parser.error("bundle is required unless --self-test is used")
    _render(evaluate_invariance(load_bundle(args.bundle)), args.output)


if __name__ == "__main__":
    main()
