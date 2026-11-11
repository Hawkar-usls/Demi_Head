"""TACHYON-R3.1: independent train-vs-dev parameter partition policy tests."""
import copy
import json
from pathlib import Path
import unittest

from tachyon.r31_reference_gate import (
    FAMILY_ORDER,R2H_KNOWN,R2D_KNOWN,validate_pack,make_rows,score_guarded,
    exported_training_pack,sha,
)

PACK_PATH=Path("data/tachyon/r31/formal_reference_pack.json")
CARDS_PATH=Path("data/tachyon/r2c/science_cards.json")

class R31FormalPack(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pack=validate_pack(json.loads(PACK_PATH.read_text(encoding="utf8")))

    def test_sources_exact_references(self):
        self.assertEqual(self.pack["scientific_admission"],"HOLD")
        self.assertFalse(self.pack["independent_external_blind_assessor"])
        self.assertEqual(len(self.pack["references"]),2)

    def test_all_splits_independent_and_bounded(self):
        groups=self.pack["splits"]
        for family in FAMILY_ORDER:
            train=set(groups["train"][family])
            calibration=set(groups["calibration"][family])
            new=set(groups["public_unseen_dev"][family])
            self.assertFalse(train&calibration)
            self.assertFalse(train&new)
            self.assertFalse(calibration&new)
            self.assertFalse(new&R2H_KNOWN[family])
            self.assertFalse(new&R2D_KNOWN[family])
        self.assertEqual(len(make_rows(self.pack,"train")),16)
        self.assertEqual(len(make_rows(self.pack,"calibration")),8)
        self.assertEqual(len(make_rows(self.pack,"public_unseen_dev")),12)

    def test_training_export_has_no_unseen_answers(self):
        export=exported_training_pack(self.pack)
        heldout={x["question"] for x in make_rows(self.pack,"public_unseen_dev")}
        self.assertTrue(all(x["question"] not in heldout
                            for x in export["examples"]))
        self.assertFalse(export["production_authorization"])
        self.assertFalse(export["external_blind_labels_used"])

    def test_train_test_overlap_must_fail(self):
        bad=copy.deepcopy(self.pack)
        bad["splits"]["public_unseen_dev"]["SR_PROPER_TIME_RATIO"][0]=(
            bad["splits"]["train"]["SR_PROPER_TIME_RATIO"][0])
        with self.assertRaisesRegex(ValueError,"TRAIN_EVALUATION_PARAMETER_OVERLAP"):
            validate_pack(bad)

    def test_source_url_rewrite_denied(self):
        bad=copy.deepcopy(self.pack)
        bad["references"][0]["url"]="https://evil.example/physics"
        with self.assertRaisesRegex(ValueError,"UNEXPECTED_REFERENCE_DOMAIN"):
            validate_pack(bad)

    def test_blind_claim_or_production_flag_denied(self):
        bad=copy.deepcopy(self.pack);bad["independent_external_blind_assessor"]=True
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SCIENCE_ADMISSION"):
            validate_pack(bad)
        bad=copy.deepcopy(self.pack);bad["production_training_authorized"]=True
        with self.assertRaisesRegex(ValueError,"UNAUTHORIZED_SCIENCE_ADMISSION"):
            validate_pack(bad)

    def test_actual_existing_guarded_hybrid_vs_baseline_public_development(self):
        from tachyon.r2e_hybrid import load_cards
        cards=load_cards(CARDS_PATH)
        score=score_guarded(self.pack,cards)
        self.assertEqual(score["public_unseen_numeric_count"],12)
        self.assertEqual(len(score["negative_observations"]),6)
        self.assertFalse(score["independently_blind"])
        self.assertFalse(score["neural_weights_trained"])
        self.assertFalse(score["production_promotion"])
        # No perfect-score assertion here: real score failures must be visible.
        self.assertTrue(0<=score["guarded_formula_correct"]<=12)
        self.assertTrue(0<=score["negative_abstentions"]<=6)

    def test_holdout_not_physical_measurement(self):
        for item in make_rows(self.pack,"public_unseen_dev"):
            self.assertEqual(item["data_type"],
                "AUTHOR_DERIVED_FORMULA_LABEL_NOT_LAB_MEASUREMENT")
        self.assertFalse(self.pack["independently_measured_physical_dataset"])

if __name__=="__main__":
    unittest.main()
