from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import not_prediction_event_unit as npeu  # noqa: E402


class NotPredictionEventUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        path = ROOT / "examples" / "not_prediction_event_unit_manifest.json"
        self.document = json.loads(path.read_text(encoding="utf-8"))

    def test_one_source_can_contain_multiple_events(self) -> None:
        result = npeu.analyze(self.document)
        self.assertEqual(result["event_collapse"]["row_count"], 3)
        self.assertEqual(result["event_collapse"]["event_root_count"], 3)

    def test_multiple_sources_can_reference_same_event(self) -> None:
        result = npeu.analyze(self.document)
        events = {x["event_root"]: x for x in result["event_collapse"]["events"]}
        shared = events["CLOCK_2026_07_07_2112"]
        self.assertEqual(shared["row_reference_count"], 2)
        self.assertEqual(
            shared["row_ids"],
            ["CLOCK-2112-DERIVATIVE", "CLOCK-LINEAGE-A"],
        )

    def test_salience_triggered_clock_sample_forbids_naive_uniform_frequency(self) -> None:
        result = npeu.analyze(self.document)
        gate = result["selection_gate"]
        self.assertTrue(gate["requires_selection_matched_null"])
        self.assertTrue(gate["naive_uniform_frequency_inference_forbidden"])
        self.assertEqual(gate["mode_counts"]["SALIENCE_TRIGGERED"], 1)
        self.assertEqual(gate["mode_counts"]["LOOKUP_CONDITIONED"], 1)

    def test_preregistered_control_is_low_selection_risk(self) -> None:
        result = npeu.analyze(self.document)
        rows = {x["row_id"]: x for x in result["selection_gate"]["rows"]}
        control = rows["TECHNICAL-CONTROL"]
        self.assertEqual(control["risk_level"], 0)
        self.assertTrue(control["sampling_frame_known"])
        self.assertTrue(control["all_opportunities_logged"])

    def test_claim_ceiling_stays_bounded(self) -> None:
        result = npeu.analyze(self.document)
        self.assertEqual(result["truth_claim"], "NOT_MADE")
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")
        self.assertEqual(
            result["claim_ceiling"],
            "UNIT_OF_ANALYSIS_AND_SELECTION_ACCOUNTING_ONLY",
        )


if __name__ == "__main__":
    unittest.main()
