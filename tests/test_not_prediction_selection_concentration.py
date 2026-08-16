from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from not_prediction_selection_concentration import analyze  # noqa: E402


BASELINE = ROOT / "examples" / "not_prediction_atomic_baseline_minimal.json"
OVERLAY = ROOT / "examples" / "not_prediction_overlay_c030_c035.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class NotPredictionSelectionConcentrationTests(unittest.TestCase):
    def test_expanded_strict_total_is_27(self) -> None:
        result = analyze(load(BASELINE), load(OVERLAY))
        self.assertEqual(result["strict_root_count"], 27)

    def test_five_declared_selection_families(self) -> None:
        result = analyze(load(BASELINE), load(OVERLAY))
        self.assertEqual(result["selection_process_family_count"], 5)

    def test_clock_family_contains_twenty_roots(self) -> None:
        result = analyze(load(BASELINE), load(OVERLAY))
        clock = next(row for row in result["families"] if row["selection_process_root"] == "CLOCK_SALIENCE_AND_LOOKUP_PROCESS")
        self.assertEqual(clock["strict_root_count"], 20)
        self.assertAlmostEqual(clock["share_of_strict_roots"], 20 / 27)

    def test_top_two_families_cover_twenty_three_roots(self) -> None:
        result = analyze(load(BASELINE), load(OVERLAY))
        concentration = result["concentration"]
        self.assertEqual(concentration["top_two_family_root_count"], 23)
        self.assertAlmostEqual(concentration["top_two_family_share"], 23 / 27)

    def test_descriptive_metrics_do_not_claim_effective_sample_size(self) -> None:
        result = analyze(load(BASELINE), load(OVERLAY))
        self.assertEqual(result["claim_ceiling"], "DESCRIPTIVE_SELECTION_CONCENTRATION_ONLY_NOT_EFFECTIVE_SAMPLE_SIZE")
        self.assertEqual(result["independent_evidence_root_count"], "NOT_ESTIMATED")
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")

    def test_missing_selection_root_fails_closed(self) -> None:
        baseline = load(BASELINE)
        target = next(case for case in baseline["cases"] if case["case_id"] == "NP-003")
        target.pop("selection_process_root")
        with self.assertRaisesRegex(ValueError, "strict roots require selection_process_root"):
            analyze(baseline, load(OVERLAY))


if __name__ == "__main__":
    unittest.main()
