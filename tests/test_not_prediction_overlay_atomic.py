from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from not_prediction_overlay_atomic import analyze  # noqa: E402


FIXTURE = ROOT / "examples" / "not_prediction_overlay_c030_c035.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class NotPredictionOverlayAtomicTests(unittest.TestCase):
    def test_overlay_delta_is_three_strict_one_uncertain(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["overlay_delta"]["new_strict_roots"], 3)
        self.assertEqual(result["overlay_delta"]["new_uncertain_roots"], 1)
        self.assertEqual(result["overlay_delta"]["absorbed_baseline_candidates"], 1)
        self.assertEqual(result["overlay_delta"]["reference_only_candidates"], 1)

    def test_expanded_accounting_is_27_strict_31_inclusive(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["expanded_accounting"]["strict_phenomenon_session_roots"], 27)
        self.assertEqual(result["expanded_accounting"]["uncertain_phenomenology_roots"], 4)
        self.assertEqual(result["expanded_accounting"]["inclusive_phenomenology_roots"], 31)

    def test_0303_is_absorbed_into_baseline(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["absorbed_candidates"], ["NP-C032"])
        row = next(item for item in result["candidates"] if item["candidate_id"] == "NP-C032")
        self.assertEqual(row["baseline_root"], "CLOCK_2026_07_08_0303")

    def test_aura_kem_is_reference_only(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["reference_only_candidates"], ["NP-C035"])

    def test_claims_remain_bounded(self) -> None:
        result = analyze(load_fixture())
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")
        self.assertEqual(result["truth_claim"], "NOT_MADE")

    def test_missing_candidate_fails_closed(self) -> None:
        document = load_fixture()
        document["candidates"] = document["candidates"][:-1]
        with self.assertRaisesRegex(ValueError, "NP-C030..NP-C035"):
            analyze(document)


if __name__ == "__main__":
    unittest.main()
