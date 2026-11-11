"""TACHYON R3.1B neural fit training-authorization and train/test firewall."""
import json
from pathlib import Path
import unittest
from tachyon.r31_reference_gate import (
    validate_pack,exported_training_pack,make_rows,sha
)
from tachyon.r31b_neural_formula import SEED,STEPS,HIDDEN

PACK=Path("data/tachyon/r31/formal_reference_pack.json")

class NeuralR31B(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=validate_pack(json.loads(PACK.read_text(encoding="utf8")))

    def test_train_source_only_and_heldout_disjoint(self):
        e=exported_training_pack(self.pack)
        train={x["parameter"]+"|"+x["formula_id"] for x in e["examples"]}
        test={x["parameter"]+"|"+x["formula_id"]
              for x in make_rows(self.pack,"public_unseen_dev")}
        val={x["parameter"]+"|"+x["formula_id"]
             for x in make_rows(self.pack,"calibration")}
        self.assertFalse(train&test)
        self.assertFalse(train&val)
        self.assertFalse(test&val)
        self.assertFalse(e["production_authorization"])

    def test_fixed_resource_budget(self):
        self.assertEqual(SEED,20261111)
        self.assertLessEqual(STEPS,1200)
        self.assertLessEqual(HIDDEN,32)
        self.assertEqual(len(make_rows(self.pack,"train")),16)

    def test_source_pack_not_external_blind(self):
        self.assertFalse(self.pack["independent_external_blind_assessor"])
        self.assertEqual(self.pack["scientific_admission"],"HOLD")
        out=exported_training_pack(self.pack)
        self.assertEqual(out["source_reference_pack_sha256"],sha(self.pack))

if __name__=="__main__":
    unittest.main()
