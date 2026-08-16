from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from plus_plus_recenter import RHYME, run, self_test  # noqa: E402


class PlusPlusRecenterTests(unittest.TestCase):
    def test_native_pair_is_plus_plus(self) -> None:
        result = run([("user", ()), ("system", ())])
        self.assertTrue(result["invariants"]["native_constructive_pair_only"])
        self.assertEqual(result["native_constitution"]["canonical_pair"], "+/+")
        self.assertTrue(all(row["face_symbol"] == "+" for row in result["trace"]))

    def test_symbolic_origin_axiom_is_scoped(self) -> None:
        result = run([])
        self.assertEqual(result["native_constitution"]["symbolic_origin_axiom"], "0/0 = JANUS")
        self.assertFalse(result["native_constitution"]["symbolic_origin_axiom_is_arithmetic_claim"])

    def test_difficult_context_without_routing_flags_does_not_recenter(self) -> None:
        result = run([("user", ())] * 10)
        self.assertEqual(result["state"]["recenter_events"], 0)
        self.assertEqual(result["state"]["load"], "CLEAR")

    def test_sustained_user_routing_load_recenters(self) -> None:
        result = run(
            [
                ("user", ("choice_space_contraction",)),
                ("user", ("certainty_without_support",)),
                ("user", ("repetition_without_new_evidence",)),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 1)
        self.assertEqual(result["state"]["load"], "CLEAR")
        self.assertEqual(result["trace"][-1]["recenter_sequence"], [x.value for x in RHYME])

    def test_system_can_trigger_same_self_recenter(self) -> None:
        result = run(
            [
                ("system", ("engagement_persistence",)),
                ("system", ("choice_space_contraction",)),
                ("system", ("repetition_without_new_evidence",)),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 1)

    def test_clear_turns_relax_transient_load(self) -> None:
        result = run(
            [
                ("user", ("choice_space_contraction",)),
                ("user", ("certainty_without_support",)),
                ("user", ()),
                ("user", ()),
            ]
        )
        self.assertEqual(result["state"]["recenter_events"], 0)
        self.assertEqual(result["state"]["load"], "CLEAR")

    def test_recenter_does_not_touch_evidence_authority_or_effect_budget(self) -> None:
        result = run(
            [
                ("external", ("interaction_loop",)),
                ("user", ("choice_space_contraction",)),
                ("system", ("engagement_persistence",)),
            ]
        )
        for row in result["trace"]:
            self.assertFalse(row["evidence_status_mutated"])
            self.assertEqual(row["authority_delta"], 0)
            self.assertEqual(row["mass_effect_budget_delta"], 0)

    def test_unknown_flags_are_ignored(self) -> None:
        result = run([("user", ("sadness", "political_disagreement", "unknown_flag"))])
        row = result["trace"][0]
        self.assertEqual(row["accepted_routing_flags"], [])
        self.assertEqual(result["state"]["load"], "CLEAR")

    def test_transient_load_never_becomes_face_or_identity(self) -> None:
        result = run([("user", ("interaction_loop",))])
        self.assertFalse(result["invariants"]["transient_load_is_face"])
        self.assertFalse(result["invariants"]["transient_load_is_identity"])

    def test_embedded_self_test(self) -> None:
        self.assertTrue(all(value == "PASS" for value in self_test().values()))


if __name__ == "__main__":
    unittest.main()
