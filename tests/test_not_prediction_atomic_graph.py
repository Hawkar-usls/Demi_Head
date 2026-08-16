from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from not_prediction_atomic_graph import analyze  # noqa: E402


FIXTURE = ROOT / "examples" / "not_prediction_atomic_baseline_minimal.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class NotPredictionAtomicGraphTests(unittest.TestCase):
    def test_baseline_counts_are_frozen(self) -> None:
        result = analyze(load_fixture())
        counts = result["counting"]
        self.assertEqual(counts["semantic_case_family_count"], 29)
        self.assertEqual(counts["strict_phenomenon_session_root_count"], 24)
        self.assertEqual(counts["uncertain_phenomenology_root_count"], 3)
        self.assertEqual(counts["inclusive_phenomenology_root_count"], 27)

    def test_holy_clock_is_twelve_event_sessions(self) -> None:
        result = analyze(load_fixture())
        row = next(item for item in result["per_case"] if item["case_id"] == "NP-003")
        self.assertEqual(row["strict_phenomenon_session_count"], 12)
        self.assertEqual(row["selection_process_root"], "CLOCK_SALIENCE_AND_LOOKUP_PROCESS")

    def test_session_subevents_do_not_become_independent_roots(self) -> None:
        result = analyze(load_fixture())
        np019 = next(item for item in result["per_case"] if item["case_id"] == "NP-019")
        np028 = next(item for item in result["per_case"] if item["case_id"] == "NP-028")
        self.assertEqual(np019["strict_phenomenon_session_count"], 1)
        self.assertEqual(np019["subevent_count"], 23)
        self.assertEqual(np028["strict_phenomenon_session_count"], 0)
        self.assertEqual(np028["subevent_count"], 22)

    def test_direct_and_recursive_dependencies_are_hard_collapses(self) -> None:
        result = analyze(load_fixture())
        rows = {row["component_id"]: row for row in result["dependency_components"]}
        self.assertEqual(rows["DEP_GENESIS_013_014_PARENT"]["independence_effect"], "HARD_INDEPENDENCE_COLLAPSE")
        self.assertEqual(rows["DEP_EYE_WEDJAT_RECURSION"]["independence_effect"], "HARD_INDEPENDENCE_COLLAPSE")

    def test_shared_selection_and_ontology_are_soft_dependencies(self) -> None:
        result = analyze(load_fixture())
        rows = {row["component_id"]: row for row in result["dependency_components"]}
        self.assertEqual(rows["DEP_CLOCK_SELECTION"]["independence_effect"], "SOFT_NULL_MODEL_DEPENDENCY")
        self.assertEqual(rows["DEP_FUTURE_INFORMATION_STACK"]["independence_effect"], "SOFT_NULL_MODEL_DEPENDENCY")

    def test_no_extraordinary_claim_is_promoted(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["truth_claim"], "NOT_MADE")
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")
        self.assertEqual(result["prophecy_claim"], "NOT_PROMOTED")
        self.assertEqual(result["precognition_claim"], "NOT_PROMOTED")
        self.assertEqual(result["physical_retrocausality_claim"], "NOT_PROMOTED")

    def test_missing_baseline_case_fails_closed(self) -> None:
        document = load_fixture()
        document["cases"] = document["cases"][:-1]
        with self.assertRaisesRegex(ValueError, "NP-001..NP-029"):
            analyze(document)


if __name__ == "__main__":
    unittest.main()
