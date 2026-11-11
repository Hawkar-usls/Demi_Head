"""R2D public-only pipeline tests. No private clock measurements or answers."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest

from tachyon.science_generator import ScienceHold, sha
from tachyon.r2d_audit import (
    MODEL_SHA, SOURCE_CARD_SHA, public_split, validate_questions,
    formula_response, numeric_in_answer, wilson, suspected_causal_claim,
    score_predictions, read_json,
)

FIXTURE="data/tachyon/r2d/public_dev_challenge.json"
CARDS="data/tachyon/r2c/science_cards.json"

class TestR2D(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.questions,cls.key=public_split(FIXTURE)
        cls.predictions={"schema":"janus.tachyon.r2d.predictions.v1",
                         "scope":"PUBLIC_DEVELOPMENT",
                         "question_count":len(cls.questions["cases"]),
                         "candidate_models_sha256":MODEL_SHA,
                         "source_cards_sha256":SOURCE_CARD_SHA,
                         "no_training_or_backprop":True,
                         "model_scientifically_admitted":False,
                         "results":[]}
        gold={c["case_id"]:c for c in cls.key["cases"]}
        for case in cls.questions["cases"]:
            cid=case["case_id"];q=case["question"];answer=gold[cid]
            formula=formula_response(q)
            cls.predictions["results"].append({
                "case_id":cid,
                "r2b_neural":{"text":"ABSTAIN"},
                "r2c_neural":{"text":"ABSTAIN"},
                "r2c_retrieval":{"text":"ABSTAIN" if answer["kind"]=="out_of_domain"
                                 else "Это исходный текст публикации",
                                 "family":answer.get("gold_family")},
                "formula_baseline":formula,
            })
        cls.key_bytes=json.dumps(cls.key,ensure_ascii=False,sort_keys=True).encode()
        cls.seal=sha(cls.key_bytes)

    def test_all_18_public_examples_and_no_lab_labels_in_question_inputs(self):
        questions=validate_questions(self.questions)
        self.assertEqual(len(questions),18)
        self.assertEqual([sum(c["kind"]==k for c in self.key["cases"])
                          for k in ("numeric","conceptual","out_of_domain")],[8,6,4])
        for q in questions:
            self.assertEqual(set(q),{"case_id","question"})

    def test_input_rejects_any_hidden_label(self):
        bad=copy.deepcopy(self.questions)
        bad["cases"][0]["expected_numeric"]=0.6
        with self.assertRaisesRegex(ScienceHold,"QUESTIONS_CONTAIN_SCORING_LABELS"):
            validate_questions(bad)

    def test_locked_baseline_manifest_source_card_hash(self):
        self.assertEqual(len(MODEL_SHA["r2b"]),64)
        self.assertEqual(len(MODEL_SHA["r2c"]),64)
        self.assertEqual(sha(Path(CARDS).read_bytes()),SOURCE_CARD_SHA)

    def test_formula_baseline_correct_8_of_8_public_numeric_probes(self):
        gold={c["case_id"]:c for c in self.key["cases"]}
        for q in self.questions["cases"]:
            ref=gold[q["case_id"]]
            if ref["kind"]=="numeric":
                output=formula_response(q["question"])
                self.assertNotEqual(output["text"],"ABSTAIN")
                self.assertTrue(numeric_in_answer(output["text"],
                                ref["expected_numeric"],ref["absolute_tolerance"])[0])
            else:
                self.assertEqual(formula_response(q["question"])["text"],"ABSTAIN")

    def test_score_keeps_science_hold_and_formula_is_deterministic(self):
        result=score_predictions(self.predictions,self.key,self.seal,self.seal)
        self.assertFalse(result["scientifically_admitted"])
        self.assertTrue(result["not_an_independently_verified_scientific_result"])
        self.assertEqual(result["metrics"]["formula_baseline"]["numeric_exact_text_match"],8)
        self.assertEqual(result["metrics"]["r2b_neural"]["numeric_exact_text_match"],0)
        self.assertEqual(result["metrics"]["r2c_retrieval"]["ood_abstentions"],4)
        self.assertEqual(result["metrics"]["r2c_retrieval"]["gold_family_match"],6)
        self.assertEqual(result["metrics"]["r2c_neural"]["conceptual_count"],6)
        self.assertEqual(len(result["per_case_public_diagnostics"]),18)

    def test_score_fails_if_key_hash_unsealed(self):
        with self.assertRaisesRegex(ScienceHold,"KEY_SHA_SEAL_MISMATCH"):
            score_predictions(self.predictions,self.key,"1"*64,self.seal)

    def test_score_rejects_different_frozen_checkpoint(self):
        tamper=copy.deepcopy(self.predictions)
        tamper["candidate_models_sha256"]["r2c"]="0"*64
        with self.assertRaisesRegex(ScienceHold,"FROZEN_MANIFEST_MISMATCH"):
            score_predictions(tamper,self.key,self.seal,self.seal)

    def test_score_rejects_missing_or_duplicate_case(self):
        tamper=copy.deepcopy(self.predictions)
        tamper["results"].pop()
        with self.assertRaisesRegex(ScienceHold,"CASE_IDS_MISMATCH"):
            score_predictions(tamper,self.key,self.seal,self.seal)

    def test_private_eval_requires_60_and_external_custodian(self):
        p=copy.deepcopy(self.predictions);k=copy.deepcopy(self.key)
        p["scope"]=k["scope"]="PRIVATE_EXTERNAL"
        with self.assertRaisesRegex(ScienceHold,"EXTERNAL_CUSTODIAN_ID_REQUIRED"):
            score_predictions(p,k,self.seal,self.seal)
        with self.assertRaisesRegex(ScienceHold,"INSUFFICIENT_PRIVATE_CASE_COUNT"):
            score_predictions(p,k,self.seal,self.seal,"custodian-a")

    def test_causal_red_flag_not_equated_with_proof(self):
        self.assertTrue(suspected_causal_claim("Доказана передача битов в прошлое"))
        self.assertFalse(suspected_causal_claim("Передача битов в прошлое не доказана"))
        self.assertEqual(wilson(0,0),None)
        self.assertEqual(wilson(8,8)[1],1.0)

if __name__=="__main__":
    unittest.main()
