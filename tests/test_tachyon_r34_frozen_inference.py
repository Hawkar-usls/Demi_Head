"""R3.4 frozen-model question-only API security tests (no private gold sent)."""
import copy
import unittest

from tachyon.r33_external_custodian import (
    CHALLENGE_SCHEMA,MODEL_SHA256,questions_only,sha
)
from tachyon.r34_frozen_inference import (
    SUPPORTED,ITEM_KEYS,TRANSPORT_KEYS,validate_transport
)

def synthetic_60():
    items=[]
    for category in ("NUMERIC","CONCEPTUAL","OOD"):
        for i in range(20):
            gold=({"kind":"numeric","value":1.0,"unit":"m/s"}
                  if category=="NUMERIC" else
                  {"kind":"conceptual","rubric":"Independent assessment of verified physics with units."}
                  if category=="CONCEPTUAL" else
                  {"kind":"abstain"})
            items.append({
                "case_id":category.lower()+"_"+str(i).zfill(3),
                "category":category,
                "family":"UNSEEN_"+category,
                "question":"New source family hidden question without model knowledge.",
                "source_url":"https://example.org/independent",
                "gold":gold,
            })
    return {"schema":CHALLENGE_SCHEMA,"items":items}

class FrozenTransport(unittest.TestCase):
    def setUp(self):
        self.private=synthetic_60()
        self.q=questions_only(self.private,MODEL_SHA256)

    def test_every_question_only_export_is_gold_free(self):
        self.assertEqual(validate_transport(self.q),
                         self.q["questions_sha256"])
        self.assertEqual(len(self.q["items"]),60)
        self.assertTrue(all(set(row).issubset(ITEM_KEYS)
                            and "gold" not in row
                            for row in self.q["items"]))
        self.assertEqual(set(self.q),TRANSPORT_KEYS)

    def test_no_extra_root_payload_or_answer_field_accepted(self):
        x=copy.deepcopy(self.q)
        x["answer_map"]={"numeric_000":1}
        with self.assertRaisesRegex(ValueError,
                                    "R34_STRICT_QUESTION_TRANSPORT_SHAPE"):
            validate_transport(x)
        x=copy.deepcopy(self.q)
        x["items"][0]["gold"]={"value":100}
        x["questions_sha256"]=sha({
            k:v for k,v in x.items() if k!="questions_sha256"
        })
        with self.assertRaisesRegex(ValueError,"R34_UNKNOWN_FIELD_OR_GOLD_LEAK"):
            validate_transport(x)

    def test_hash_catches_question_tamper(self):
        x=copy.deepcopy(self.q)
        x["items"][0]["question"]="Changed after source seal"
        with self.assertRaisesRegex(ValueError,
                                    "R34_QUESTION_TRANSPORT_SHA_MISMATCH"):
            validate_transport(x)

    def test_public_transport_cannot_claim_model_weights_or_approval(self):
        x=copy.deepcopy(self.q)
        x["frozen_candidate_weights_sha256"]="a"*64
        x["questions_sha256"]=sha({k:v for k,v in x.items()
                                    if k!="questions_sha256"})
        with self.assertRaisesRegex(ValueError,"R34_UNTRUSTED_QUESTION_TRANSPORT"):
            validate_transport(x)

    def test_source_families_not_mapped_to_training_formulas(self):
        self.assertEqual(set(SUPPORTED),{
            "SR_PROPER_TIME_RATIO","TWO_LEVEL_BORN_PROBABILITY"
        })
        self.assertTrue(all(row["family"] not in SUPPORTED
                            for row in self.q["items"]))
        self.assertTrue(self.q["not_to_publish_to_public_repo"])

    def test_duplicate_or_incomplete_transport_detected(self):
        x=copy.deepcopy(self.q)
        x["items"][-1]["case_id"]=x["items"][0]["case_id"]
        x["questions_sha256"]=sha({k:v for k,v in x.items()
                                    if k!="questions_sha256"})
        with self.assertRaisesRegex(ValueError,"R34_CASE_DUPLICATE"):
            validate_transport(x)

if __name__=="__main__":
    unittest.main()
