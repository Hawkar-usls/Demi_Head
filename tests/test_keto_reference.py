from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from keto_reference import load_case, summarize_case  # noqa: E402


class KetoReferenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.fixture = load_case(ROOT / "examples" / "case_echo_collapse.json")
        self.result = summarize_case(self.fixture)

    def test_echo_presentations_collapse_to_roots(self) -> None:
        self.assertEqual(self.result["accounting"]["presentation_count"], 6)
        self.assertEqual(self.result["accounting"]["root_count"], 4)
        root_a = next(row for row in self.result["roots"] if row["root_id"] == "root-A")
        self.assertEqual(root_a["presentation_count"], 3)

    def test_stale_source_does_not_count_as_current_support(self) -> None:
        self.assertEqual(self.result["accounting"]["stale_presentation_count"], 1)
        self.assertNotIn("root-D", self.result["current_support_roots"])

    def test_support_and_contradiction_are_preserved(self) -> None:
        self.assertEqual(self.result["evidence_state"], "CONTESTED")
        self.assertIn("root-C", self.result["current_contradiction_roots"])
        self.assertTrue(self.result["current_support_roots"])

    def test_official_position_is_not_truth_label(self) -> None:
        self.assertIn("root-B", self.result["official_position_roots"])
        self.assertEqual(self.result["truth_claim"], "NOT_MADE")

    def test_authenticated_independence_is_counted_separately(self) -> None:
        self.assertEqual(self.result["authenticated_independent_roots"], ["root-C"])
        self.assertEqual(self.result["accounting"]["authenticated_independent_root_count"], 1)

    def test_mass_effect_budget_is_zero(self) -> None:
        self.assertEqual(self.result["mass_effect_budget"], 0)

    def test_result_is_json_serializable(self) -> None:
        json.dumps(self.result, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
