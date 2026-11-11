"""R2C fail-closed regression tests: no secret data and no automatic physics claims."""
from __future__ import annotations
import copy
import json
import os
from pathlib import Path
import unittest

from tachyon.science_generator import ScienceHold, HOLDOUT_DOIS, HOLDOUT_FAMILIES
from tachyon.r2c_grounded import (
    EXPECTED, new_source_rows, full_training_rows, retrieve, review_gate, explain,
    _terms,
)

CARDS = Path("data/tachyon/r2c/science_cards.json")
VIDEO = Path(os.environ.get("TACHYON_R2B_VIDEO_CORPUS", "artifacts/tachyon-r2c/video-corpus.json"))
PAPERS = Path("data/tachyon/r2b/primary_papers_train.json")

class R2C(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards, _, cls.rows = new_source_rows(CARDS)

    def _tamper(self, payload):
        dest = Path("artifacts/tachyon-r2c/test-malicious.json")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf8")
        return dest

    def test_six_primary_source_families(self):
        self.assertEqual(len(self.cards["sources"]), 6)
        self.assertEqual({s["family"]: s["doi"] for s in self.cards["sources"]}, EXPECTED)
        self.assertEqual(len(self.rows), 12)

    def test_clock_holdout_stays_absent_from_all_new_sources(self):
        self.assertTrue(set(s["doi"] for s in self.cards["sources"]).isdisjoint(HOLDOUT_DOIS))
        self.assertTrue({r["family"] for r in self.rows}.isdisjoint(HOLDOUT_FAMILIES))
        self.assertFalse(self.cards["policy"]["clock_lab_measurements_used"])

    def test_full_training_36_pairs_if_video_built(self):
        if not VIDEO.exists():
            self.skipTest("R2A pinned video corpus built by the dedicated workflow")
        rows, hashes, _ = full_training_rows(VIDEO, PAPERS, CARDS)
        self.assertEqual(len(rows), 36)
        self.assertEqual(len({r["family"] for r in rows}), 13)
        self.assertEqual(len(hashes), 3)

    def test_attempt_to_add_clock_source_is_rejected(self):
        bad = copy.deepcopy(self.cards)
        bad["sources"][0]["doi"] = "10.1126/science.1192720"
        with self.assertRaisesRegex(ScienceHold, "R2C_SOURCE_ALLOWLIST"):
            new_source_rows(self._tamper(bad))

    def test_attempt_to_admit_measurements_is_rejected(self):
        bad = copy.deepcopy(self.cards)
        bad["policy"]["clock_lab_measurements_used"] = True
        with self.assertRaisesRegex(ScienceHold, "R2C_SOURCE_POLICY_LEAK"):
            new_source_rows(self._tamper(bad))

    def test_doi_metadata_tamper_is_rejected(self):
        bad = copy.deepcopy(self.cards)
        bad["sources"][0]["url"] = "https://wrong.example/paper"
        with self.assertRaisesRegex(ScienceHold, "R2C_DOI_URL"):
            new_source_rows(self._tamper(bad))

    def test_unreviewed_source_authority_escalation_is_rejected(self):
        bad = copy.deepcopy(self.cards)
        bad["sources"][0]["provenance_status"] = "INDEPENDENT_PHYSICAL_PROOF"
        with self.assertRaisesRegex(ScienceHold, "R2C_PROVENANCE"):
            new_source_rows(self._tamper(bad))

    def test_retrieval_is_pinned_to_real_doi(self):
        q = self.cards["sources"][0]["questions"][0]
        results = retrieve(q, self.cards)
        self.assertTrue(results)
        self.assertEqual(results[0]["family"], "SR_EINSTEIN_1905")
        self.assertEqual(results[0]["doi"], EXPECTED["SR_EINSTEIN_1905"])

    def test_out_of_scope_question_abstains(self):
        results = retrieve("Как посадить яблоню на Марсе сегодня?", self.cards)
        self.assertEqual(results, [])
        gate = review_gate("Как посадить яблоню на Марсе сегодня?", results)
        self.assertEqual(gate["decision"], "ABSTAIN")

    def test_citation_is_not_equated_with_independent_truth(self):
        question = self.cards["sources"][2]["questions"][1]
        result = explain(question, self.cards)
        self.assertTrue(result["sources"])
        self.assertTrue(result["gate"]["review_required"])
        self.assertFalse(result["gate"]["claim_proven"])
        self.assertFalse(result["claim_of_retrocausal_signal"])
        self.assertIsNone(result["neural_unverified_draft"])

    def test_no_clock_or_secret_input_to_train_api(self):
        from inspect import signature
        from tachyon.r2c_grounded import train
        params = signature(train).parameters
        for forbidden in ("holdout","clock_measurements","blind_answers","evaluator_secret"):
            self.assertNotIn(forbidden, params)

    def test_lexical_engine_has_no_static_truth_claim(self):
        self.assertNotIn("гарантированно", _terms("гарантированно верно"))
        # A source match is still marked as review-required.
        q = self.cards["sources"][1]["questions"][0]
        result = explain(q, self.cards)
        self.assertFalse(result["gate"]["claim_proven"])

if __name__ == "__main__":
    unittest.main()
