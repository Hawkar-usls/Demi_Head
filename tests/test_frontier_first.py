from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("frontier_first", ROOT / "tools" / "frontier_first.py")
assert SPEC and SPEC.loader
frontier_first = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(frontier_first)


class FrontierFirstTests(unittest.TestCase):
    def test_no_prior_work_starts_from_first_principles(self) -> None:
        r = frontier_first.evaluate(internal_hits=0, external_hits=0, verified_frontiers=0, open_gaps=0)
        self.assertEqual(r["state"], "NO_RELEVANT_PRIOR_WORK_FOUND")
        self.assertFalse(r["claim_ceiling"]["novelty_established"])

    def test_unverified_prior_work_is_not_frontier(self) -> None:
        r = frontier_first.evaluate(internal_hits=2, external_hits=5, verified_frontiers=0, open_gaps=3)
        self.assertEqual(r["state"], "PRIOR_WORK_FOUND_UNVERIFIED")
        self.assertIn("VERIFY", r["next_action"])

    def test_verified_frontier_with_gaps_continues_from_frontier(self) -> None:
        r = frontier_first.evaluate(internal_hits=1, external_hits=4, verified_frontiers=2, open_gaps=3)
        self.assertEqual(r["state"], "VERIFIED_FRONTIER_FOUND")
        self.assertIn("ATTACK_OPEN_GAPS", r["next_action"])
        self.assertEqual(r["claim_ceiling"]["authority_delta"], 0)

    def test_solved_work_is_not_rebuilt(self) -> None:
        r = frontier_first.evaluate(internal_hits=1, external_hits=1, verified_frontiers=1, open_gaps=0)
        self.assertEqual(r["state"], "FRONTIER_REUSED")
        self.assertIn("DO_NOT_REBUILD", r["next_action"])


if __name__ == "__main__":
    unittest.main()
