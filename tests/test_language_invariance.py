import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "language_invariance.py"
SPEC = importlib.util.spec_from_file_location("language_invariance", MODULE_PATH)
language = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(language)


class LanguageInvarianceTests(unittest.TestCase):
    def canonical(self):
        return {
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

    def base_bundle(self):
        canonical = self.canonical()
        return {
            "schema": language.INPUT_SCHEMA,
            "bundle_id": "test",
            "required_languages": ["uk", "ru", "en"],
            "canonical_semantics": canonical,
            "renders": [
                {"language": "uk", "semantics": {**canonical, "user_rights": list(reversed(canonical["user_rights"]))}, "presentation": {"summary": "UA"}},
                {"language": "ru", "semantics": canonical, "presentation": {"summary": "RU"}},
                {"language": "en", "semantics": canonical, "presentation": {"summary": "EN"}},
            ],
        }

    def test_equal_protected_semantics_pass_despite_different_prose(self):
        result = language.evaluate_invariance(self.base_bundle())
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["violations"], [])

    def test_user_right_order_is_set_like(self):
        result = language.evaluate_invariance(self.base_bundle())
        self.assertEqual(result["status"], "PASS")

    def test_evidence_state_drift_fails(self):
        bundle = self.base_bundle()
        bundle["renders"][0]["semantics"]["evidence_state"] = "SUPPORTED_BY_PRESENT_SOURCES"
        result = language.evaluate_invariance(bundle)
        self.assertEqual(result["status"], "FAIL_CLOSED_SEMANTIC_DRIFT")
        self.assertTrue(any(v["field"] == "evidence_state" for v in result["violations"]))

    def test_uncertainty_drift_fails(self):
        bundle = self.base_bundle()
        bundle["renders"][1]["semantics"]["uncertainty_class"] = "NONE"
        result = language.evaluate_invariance(bundle)
        self.assertTrue(any(v["field"] == "uncertainty_class" for v in result["violations"]))

    def test_urgency_drift_fails(self):
        bundle = self.base_bundle()
        bundle["renders"][2]["semantics"]["urgency_class"] = "EMERGENCY"
        result = language.evaluate_invariance(bundle)
        self.assertTrue(any(v["field"] == "urgency_class" for v in result["violations"]))

    def test_missing_user_right_fails(self):
        bundle = self.base_bundle()
        bundle["renders"][0]["semantics"]["user_rights"] = ["APPEAL", "DISAGREE", "INSPECT_SOURCES"]
        result = language.evaluate_invariance(bundle)
        self.assertTrue(any(v["field"] == "user_rights" for v in result["violations"]))

    def test_missing_language_fails_closed(self):
        bundle = self.base_bundle()
        bundle["renders"] = [r for r in bundle["renders"] if r["language"] != "en"]
        result = language.evaluate_invariance(bundle)
        self.assertEqual(result["status"], "FAIL_CLOSED_SEMANTIC_DRIFT")
        self.assertTrue(any(v["type"] == "MISSING_REQUIRED_LANGUAGE" for v in result["violations"]))

    def test_unsupported_language_is_rejected(self):
        bundle = self.base_bundle()
        bundle["renders"].append({"language": "de", "semantics": self.canonical(), "presentation": {}})
        with self.assertRaises(language.LanguageInvariantError):
            language.evaluate_invariance(bundle)

    def test_language_does_not_create_authority(self):
        result = language.evaluate_invariance(self.base_bundle())
        inv = result["invariants"]
        self.assertFalse(inv["language_identity_used_as_evidence_weight"])
        self.assertFalse(inv["evidence_state_mutated"])
        self.assertEqual(inv["authority_delta"], 0)
        self.assertEqual(inv["mass_effect_budget_delta"], 0)

    def test_self_test(self):
        self.assertEqual(language.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
