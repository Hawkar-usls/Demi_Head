from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from plus_plus_recenter import RHYME, run, self_test  # noqa: E402


class PlusPlusRecenterTests(unittest.TestCase):
    def test_two_faces_are_plus_only(self) -> None:
        result = run([("user", ()), ("system", ())])
        self.assertFalse(result["invariants"]["negative_face_exists"])
        self.assertTrue(all(row["face_polarity"] == "+" for row in result["trace"]))

    def test_difficult_topic_without_pressure_flags_does_not_recenter(self) -> None:
        result = run([("user", ())] * 10)
        self.assertEqual(result["state"]["recenter_events"], 0)
        self.assertEqual(result["state"]["pressure"], "CLEAR")

    def test_sustained_user_pressure_recenters(self) -> None:
        result = run(
            [
                ("user", ("choice_narrowing",)),
                ("user", ("certainty_without_support",)),
                ("user", ("repetition_without_new_evidence",)),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 1)
        self.assertEqual(result["state"]["pressure"], "CLEAR")
        self.assertEqual(result["trace"][-1]["recenter_sequence"], [x.value for x in RHYME])

    def test_system_can_trigger_same_self_recenter(self) -> None:
        result = run(
            [
                ("system", ("engagement_pressure",)),
                ("system", ("choice_narrowing",)),
                ("system", ("repetition_without_new_evidence",)),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 1)

    def test_clean_turns_decay_pressure(self) -> None:
        result = run(
            [
                ("user", ("choice_narrowing",)),
                ("user", ("certainty_without_support",)),
                ("user", ()),
                ("user", ()),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 0)
        self.assertEqual(result["state"]["pressure"], "CLEAR")

    def test_recenter_does_not_touch_evidence_or_authority(self) -> None:
        result = run(
            [
                ("external", ("high_arousal_loop",)),
                ("user", ("identity_capture_pressure",)),
                ("system", ("engagement_pressure",)),
            ]
        )
        for row in result["trace"]:
            self.assertFalse(row["evidence_status_mutated"])
            self.assertEqual(row["authority_delta"], 0)

    def test_unknown_flags_are_ignored_not_promoted(self) -> None:
        result = run([("user", ("sadness", "political_disagreement", "unknown_flag"))])
        row = result["trace"][0]
        self.assertEqual(row["accepted_pressure_flags"], [])
        self.assertEqual(result["state"]["pressure"], "CLEAR")

    def test_embedded_self_test(self) -> None:
        self.assertTrue(all(value == "PASS" for value in self_test().values()))


if __name__ == "__main__":
    unittest.main()
