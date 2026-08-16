from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from truth_guard_holdout import load_frozen_corpus, run_holdout  # noqa: E402


CORPUS = ROOT / "holdout" / "truth_guard_v1" / "frozen_corpus.json"
EXPECTED_FREEZE = "4c658ea1532042e2c5db0298285335bbbb9e3e61ab21afd453ff0c846971201f"


class TruthGuardFrozenHoldoutTests(unittest.TestCase):
    def test_frozen_corpus_hash_is_exact(self) -> None:
        corpus = load_frozen_corpus(CORPUS)
        self.assertEqual(corpus["freeze_sha256"], EXPECTED_FREEZE)
        self.assertTrue(corpus["freeze_payload"]["frozen_before_first_execution"])
        self.assertEqual(corpus["freeze_payload"]["case_count"], 17)
        self.assertEqual(corpus["freeze_payload"]["required_pass_count"], 17)

    def test_all_frozen_cases_pass_without_tuning(self) -> None:
        corpus = load_frozen_corpus(CORPUS)
        result = run_holdout(corpus)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed"], 17)
        self.assertEqual(result["total"], 17)
        self.assertEqual(result["freeze_sha256"], EXPECTED_FREEZE)
        self.assertFalse(result["independent_external_validation"])
        self.assertFalse(result["universal_truthfulness_established"])
        self.assertFalse(result["production_readiness_established"])

    def test_any_fixture_mutation_invalidates_freeze_before_execution(self) -> None:
        corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
        mutated = copy.deepcopy(corpus)
        mutated["freeze_payload"]["cases"][0]["payload"]["claim"] = "mutated after freeze"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(mutated, ensure_ascii=False, indent=2), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "HOLDOUT_FREEZE_SHA256_MISMATCH"):
                load_frozen_corpus(path)

    def test_case_ids_are_unique_and_cover_expected_attack_families(self) -> None:
        corpus = load_frozen_corpus(CORPUS)
        ids = [row["case_id"] for row in corpus["freeze_payload"]["cases"]]
        self.assertEqual(len(ids), len(set(ids)))
        joined = " ".join(ids)
        for marker in (
            "MODEL_ONLY",
            "MISSING_WITNESS",
            "TRANSLATION",
            "CORRECTION",
            "APPEAL",
            "SAME_ROOT",
            "DISAGREEMENT",
            "AUTHORITY_MULTIPLIER",
        ):
            self.assertIn(marker, joined)


if __name__ == "__main__":
    unittest.main()
