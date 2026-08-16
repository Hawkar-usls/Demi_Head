from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class NotPredictionReauditCliContractTests(unittest.TestCase):
    def test_cli_emits_bounded_result(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "not_prediction_reaudit.py"),
                str(ROOT / "examples" / "not_prediction_reaudit_minimal.json"),
            ],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(proc.stdout)
        self.assertEqual(result["root_collapse"]["root_count"], 1)
        self.assertEqual(result["authoritative_total_preserved"], 29)
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")
        self.assertEqual(result["truth_claim"], "NOT_MADE")

    def test_forbidden_promotion_fixture_fails(self) -> None:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "not_prediction_reaudit.py"),
                str(ROOT / "examples" / "not_prediction_reaudit_forbidden_promotion.json"),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Forbidden silent promotion", proc.stderr)


if __name__ == "__main__":
    unittest.main()
