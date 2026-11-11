"""R35B frozen typed transport contract (no Torch weights or hidden gold)."""
import copy
import unittest
from tachyon.r35_typed_quantities import case_from_si
from tachyon.r35b_frozen_typed_inference import (
 FROZEN_CHECKPOINT_SHA,SCHEMA,validate
)
from tachyon.r35_typed_quantities import digest

def canaries():
    cases=[
      dict(case_id="r35b_sr_000",task_kind="NUMERIC",
           **case_from_si("SR_PROPER_TIME_RATIO",(.5,),1)),
      dict(case_id="r35b_ohm_000",task_kind="NUMERIC",
           **case_from_si("OHMIC_VOLTAGE",(.5,20.),1)),
      dict(case_id="r35b_power_000",task_kind="NUMERIC",
           **case_from_si("ELECTRIC_POWER_IV",(1.,9.),0)),
      dict(case_id="r35b_battery_000",task_kind="NUMERIC",
           family="BATTERY_SOC_VOLTAGE_CURVE",
           inputs=[{"name":"soc","value":50.,"unit":"%"}],
           target_unit="V",
           source_url="https://zenodo.org/records/13142016",
           dataset_sha256="d7dd665e6d356721ceb08bbbbd3e9f7401bc3cfac0a1b3fbea8df74637a506ea")
    ]
    result={"schema":SCHEMA,"candidate_checkpoint_sha256":FROZEN_CHECKPOINT_SHA,
            "case_count":len(cases),"contains_gold_answers":False,"items":cases}
    result["questions_sha256"]=digest(result)
    return result

def resign(doc):
    doc["questions_sha256"]=digest({k:v for k,v in doc.items()
                                    if k!="questions_sha256"})
    return doc

class StrictR35B(unittest.TestCase):
    def setUp(self):
        self.p=canaries()

    def test_expected_strict_canaries(self):
        self.assertEqual(validate(self.p),self.p["questions_sha256"])
        self.assertEqual(len(self.p["items"]),4)

    def test_tampered_question_hash_rejected(self):
        x=copy.deepcopy(self.p)
        x["items"][0]["inputs"][0]["value"]=47.
        with self.assertRaisesRegex(ValueError,"R35B_QUESTIONS_SHA_MISMATCH"):
            validate(x)

    def test_injected_gold_and_unexpected_fields_rejected(self):
        x=copy.deepcopy(self.p)
        x["items"][0]["gold"]={"value":1.}
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_EXTRA_ITEM_FIELD_MAY_LEAK_GOLD"):
            validate(x)
        y=copy.deepcopy(self.p)
        y["hidden_answers"]=["1.0"]
        with self.assertRaisesRegex(ValueError,"R35B_UNKNOWN_ROOT_OR_GOLD_FIELD"):
            validate(y)

    def test_source_forgery_rejected(self):
        x=copy.deepcopy(self.p)
        x["items"][3]["dataset_sha256"]="0"*64
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_MEASURED_DATASET_IDENTITY_MISMATCH"):
            validate(x)

    def test_incompatible_units_rejected(self):
        x=copy.deepcopy(self.p)
        x["items"][1]["inputs"][0]["unit"]="s"
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35_DIMENSION_MISMATCH"):
            validate(x)
        x=copy.deepcopy(self.p)
        x["items"][3]["target_unit"]="W"
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_LAB_TARGET_UNIT_INCOMPATIBLE"):
            validate(x)

    def test_duplicate_and_misdeclared_size_rejected(self):
        x=copy.deepcopy(self.p)
        x["items"][3]["case_id"]=x["items"][2]["case_id"]
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_INVALID_OR_DUPLICATE_CASE_ID"):
            validate(x)
        x=copy.deepcopy(self.p)
        x["case_count"]=5
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_QUESTION_COUNT"):
            validate(x)

    def test_unrecognized_family_not_implicitly_mapped(self):
        x=copy.deepcopy(self.p)
        x["items"][0]["family"]="FUTURE_UNKNOWN_MUON_LAW"
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_UNKNOWN_SCIENTIFIC_FAMILY"):
            validate(x)

    def test_frozen_checkpoint_cannot_be_changed_by_question(self):
        x=copy.deepcopy(self.p)
        x["candidate_checkpoint_sha256"]="1"*64
        resign(x)
        with self.assertRaisesRegex(ValueError,"R35B_WRONG_VERSION_OR_CANDIDATE"):
            validate(x)

if __name__=="__main__":
    unittest.main()
