"""Offline R3.3 external custodian safety tests with synthetic, NOT real secret, questions."""
import copy
import unittest

from tachyon.r33_external_custodian import (
    MODEL_SHA256,CHALLENGE_SCHEMA,PREDICTIONS_SCHEMA,RUBRIC,
    sealed_commitment,questions_only,evaluate_private,validate,sha
)

SALT=bytes.fromhex("e4"*32)

def fake_challenge():
    items=[]
    for group in ("NUMERIC","CONCEPTUAL","OOD"):
        for i in range(20):
            gold=({"kind":"numeric","value":float(i+1),"unit":"m/s"}
                  if group=="NUMERIC" else
                  {"kind":"conceptual","rubric":"Published laws require units, uncertainty and source justification."}
                  if group=="CONCEPTUAL" else {"kind":"abstain"})
            items.append({
                "case_id":group.lower()+"_"+str(i).zfill(3),
                "category":group,
                "family":"EXTERNAL_FAMILY_"+group,
                "question":"A sealed independent new-family physical challenge number "+str(i),
                "source_url":"https://example.org/independent-study",
                "gold":gold
            })
    return {"schema":CHALLENGE_SCHEMA,"items":items}

def fake_preds(pack):
    out=[]
    for item in pack["items"]:
        if item["category"]=="NUMERIC":
            out.append({"case_id":item["case_id"],"kind":"numeric",
                        "value":item["gold"]["value"],"unit":"m/s"})
        elif item["category"]=="OOD":
            out.append({"case_id":item["case_id"],"kind":"abstain"})
        else:
            out.append({"case_id":item["case_id"],"kind":"abstain"})
    return {"schema":PREDICTIONS_SCHEMA,
            "candidate_weights_sha256":MODEL_SHA256,
            "questions_sha256":questions_only(pack,MODEL_SHA256)["questions_sha256"],
            "items":out}

class CustodianProtocol(unittest.TestCase):
    def setUp(self):
        self.pack=fake_challenge()
        self.seal=sealed_commitment(
            self.pack,SALT,MODEL_SHA256,now="2026-11-11T17:00:00+00:00")

    def test_fixed_60_20_each_and_salt_commitment_without_answers(self):
        self.assertEqual(validate(self.pack),
                         {"NUMERIC":20,"CONCEPTUAL":20,"OOD":20})
        self.assertFalse(self.seal["independent_custodian_verified"])
        self.assertFalse(self.seal["independent_external_signature_present"])
        self.assertFalse(self.seal["private_question_or_answer_keys_published"])
        self.assertNotIn("gold",str(self.seal))
        self.assertEqual(self.seal["fixed_rubric_sha256"],sha(RUBRIC))
        self.assertEqual(self.seal["receipt_sha256"],
                         sha({k:v for k,v in self.seal.items()
                             if k!="receipt_sha256"}))

    def test_question_only_transport_never_has_gold(self):
        q=questions_only(self.pack,MODEL_SHA256)
        self.assertEqual(q["case_count"],60)
        self.assertTrue(q["gold_answers_excluded"])
        self.assertTrue(all("gold" not in v for v in q["items"]))

    def test_unknown_private_fields_fail_closed_instead_of_leaking(self):
        bad=copy.deepcopy(self.pack)
        bad["items"][0]["solution_steps"]="secret gold=1.0"
        with self.assertRaisesRegex(ValueError,"R33_HIDDEN_FIELD_LEAK_RISK"):
            questions_only(bad,MODEL_SHA256)

    def test_prediction_must_match_exact_question_transport_sha(self):
        p=fake_preds(self.pack)
        p["questions_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"R33_PREDICTION_QUESTION_TRANSPORT_MISMATCH"):
            evaluate_private(self.pack,SALT,self.seal,p,MODEL_SHA256)

    def test_private_gold_mismatch_after_seal_is_rejected(self):
        pack=copy.deepcopy(self.pack)
        pack["items"][0]["gold"]["value"]=1903.0
        with self.assertRaisesRegex(ValueError,"R33_SALT_GOLD_OR_CANDIDATE_MISMATCH"):
            evaluate_private(pack,SALT,self.seal,fake_preds(self.pack),MODEL_SHA256)

    def test_wrong_salt_and_model_rejected(self):
        with self.assertRaisesRegex(ValueError,"R33_SALT_GOLD_OR_CANDIDATE_MISMATCH"):
            evaluate_private(self.pack,bytes.fromhex("aa"*32),
                             self.seal,fake_preds(self.pack),MODEL_SHA256)
        with self.assertRaisesRegex(ValueError,"R33_WRONG_FROZEN_MODEL_SHA"):
            sealed_commitment(self.pack,SALT,"0"*64)

    def test_technical_score_does_not_claim_scientific_admission(self):
        r=evaluate_private(self.pack,SALT,self.seal,
                           fake_preds(self.pack),MODEL_SHA256)
        self.assertEqual(r["numeric_scored_count"],20)
        self.assertEqual(r["numeric_correct_count"],20)
        self.assertEqual(r["ood_correct_abstention_count"],20)
        self.assertEqual(r["conceptual_pending_independent_manual_review"],20)
        self.assertFalse(r["independent_external_custodian_signature_verified"])
        self.assertFalse(r["production_promotion"])
        self.assertEqual(r["scientific_admission"],"HOLD")
        self.assertTrue(r["automatic_total_physics_accuracy_not_reported"])

    def test_missing_prediction_or_duplicate_rejected(self):
        p=fake_preds(self.pack)
        p["items"]=p["items"][:-1]
        with self.assertRaisesRegex(ValueError,"R33_MISSING_PREDICTIONS"):
            evaluate_private(self.pack,SALT,self.seal,p,MODEL_SHA256)
        p=fake_preds(self.pack)
        p["items"][-1]["case_id"]=p["items"][0]["case_id"]
        with self.assertRaisesRegex(ValueError,"R33_DUPLICATE_OR_BAD_PREDICTION"):
            evaluate_private(self.pack,SALT,self.seal,p,MODEL_SHA256)

    def test_wrong_units_does_not_pass_numeric(self):
        p=fake_preds(self.pack)
        p["items"][0]["unit"]="km/h"
        s=evaluate_private(self.pack,SALT,self.seal,p,MODEL_SHA256)
        self.assertEqual(s["numeric_correct_count"],19)

    def test_leaked_training_formula_family_rejected(self):
        pack=copy.deepcopy(self.pack)
        pack["items"][0]["family"]="SR_PROPER_TIME_RATIO"
        with self.assertRaisesRegex(ValueError,"R33_TRAINING_FAMILY_LEAK"):
            validate(pack)

    def test_insufficient_independent_cases_rejected(self):
        pack=copy.deepcopy(self.pack)
        pack["items"]=pack["items"][:-1]
        with self.assertRaisesRegex(ValueError,"R33_CHALLENGE_SIZE"):
            validate(pack)

    def test_secret_case_and_salt_not_accepted_as_blind_proof(self):
        self.assertTrue(self.seal["secret_salt_published"] is False)
        self.assertTrue(self.seal["private_question_or_answer_keys_published"] is False)
        self.assertEqual(self.seal["scientific_admission"],"HOLD")

if __name__=="__main__":
    unittest.main()
