"""R2E safety-envelope tests: public author-written development fixture ONLY."""
from __future__ import annotations
import copy
import math
import unittest

from tachyon.science_generator import ScienceHold
from tachyon.r2d_audit import public_split, validate_questions
from tachyon.r2e_hybrid import load_cards, hybrid_explain, batch_explain

class R2E(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cards=load_cards("data/tachyon/r2c/science_cards.json")
        cls.q,cls.key=public_split("data/tachyon/r2d/public_dev_challenge.json")
        cls.by_id={x["case_id"]:x for x in cls.key["cases"]}

    def test_public_fixture_route_on_18_cases(self):
        results=batch_explain(self.q,self.cards)
        self.assertFalse(results["candidate_admitted"])
        self.assertFalse(results["candidate_checkpoint_used"])
        n_formula=n_citation=n_abstain=0
        for case in results["cases"]:
            gold=self.by_id[case["case_id"]]
            a=case["explanation"]
            self.assertFalse(a["scientifically_admitted"])
            self.assertFalse(a["retrocausal_signal_claimed"])
            self.assertTrue(a["requires_scientific_review"])
            self.assertFalse(a["model_generated_explanation_used_as_fact"])
            if gold["kind"]=="numeric":
                self.assertEqual(a["decision"],"DETERMINISTIC_FORMULA_WITH_CITED_SOURCE")
                self.assertTrue(a["numeric_result_verified_against_formula"])
                self.assertFalse(a["numeric_result_verified_against_lab_measurement"])
                self.assertAlmostEqual(a["computed_numeric"],gold["expected_numeric"],delta=gold["absolute_tolerance"])
                self.assertEqual(a["citations"][0]["family"],gold["gold_family"])
                n_formula+=1
            elif gold["kind"]=="conceptual":
                self.assertEqual(a["decision"],"SOURCE_PARAPHRASE_REQUIRES_REVIEW")
                self.assertEqual(a["citations"][0]["family"],gold["gold_family"])
                self.assertFalse(a["numeric_result_verified_against_formula"])
                n_citation+=1
            else:
                self.assertEqual(a["decision"],"ABSTAIN")
                self.assertIsNone(a["answer"])
                self.assertEqual(a["citations"],[])
                n_abstain+=1
        self.assertEqual([n_formula,n_citation,n_abstain],[8,6,4])

    def test_reject_ambiguous_formula(self):
        a=hybrid_explain("Каков ответ если v/c=0.8 и одновременно ρ00=0.3 для часов?",self.cards)
        self.assertEqual(a["decision"],"ABSTAIN")
        self.assertEqual(a["reason"],"AMBIGUOUS_MIXED_RULES")

    def test_reject_invalid_superluminal_speed(self):
        a=hybrid_explain("Для часов при v/c=1.2 дай физически корректное отношение dτ/dt",self.cards)
        self.assertEqual(a["decision"],"ABSTAIN")
        self.assertEqual(a["reason"],"UNSUPPORTED_OR_INVALID_PARAMETERS")

    def test_reject_negative_probability(self):
        a=hybrid_explain("Для состояния с ρ00=-0.1 и проектором |0><0| найти P(0)",self.cards)
        self.assertEqual(a["decision"],"ABSTAIN")

    def test_reject_question_scoring_labels_in_input(self):
        q=copy.deepcopy(self.q)
        q["cases"][0]["gold_family"]="SR_EINSTEIN_1905"
        with self.assertRaisesRegex(ScienceHold,"QUESTIONS_CONTAIN_SCORING_LABELS"):
            batch_explain(q,self.cards)

    def test_source_bad_sha_not_accepted(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            tmp=Path(d)/"cards.json"
            tmp.write_text('{"x":1}',encoding="utf8")
            with self.assertRaisesRegex(ScienceHold,"R2E_SOURCE_CARD_SHA_MISMATCH"):
                load_cards(tmp)

if __name__=="__main__":
    unittest.main()
