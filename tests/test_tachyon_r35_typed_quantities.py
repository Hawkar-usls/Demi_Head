"""R3.5 SI quantities, strict provenance, split isolation, lab HOLD tests."""
import copy
import json
from pathlib import Path
import unittest

from tachyon.r35_typed_quantities import (
    D0,DV,DS,DW,FAMILIES,PAIR_VALUES,TRAIN_FAMILIES,UNTRAINED_FAMILY,
    source_manifest_check,check_splits,case_from_si,normalize_case,exact,
    quantity,dataset,digest,typed_lab_observation,refuse_lab_training
)
from tachyon.r35_typed_neural import vector,INPUT_WIDTH,tensors

PATH=Path("data/tachyon/r35/typed_quantity_sandbox_manifest.json")
MUON_SHA="b6bb10270e6c604935b47687293470caeafd01172288170d83349043566cd05a"
BATTERY_SHA="d7dd665e6d356721ceb08bbbbd3e9f7401bc3cfac0a1b3fbea8df74637a506ea"

class R35Types(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(PATH.read_text(encoding="utf8"))

    def test_math_sandbox_not_laboratory_authorization(self):
        source_manifest_check(self.manifest)
        self.assertFalse(self.manifest["curated_external_laboratory_data_training_permitted"])
        self.assertEqual(self.manifest["scientific_admission"],"HOLD")
        self.assertTrue(self.manifest["model_training_permitted_for_educational_sandbox"])

    def test_train_cal_public_split_nonoverlap(self):
        self.assertEqual(check_splits(self.manifest),
                         {"train":48,"calibration":16,"public_dev":30})
        self.assertFalse(any(r["case"]["family"]==UNTRAINED_FAMILY
                             for split in ("train","calibration")
                             for r in dataset(self.manifest,split)))

    def test_dimensionless_unit_percent_conversion(self):
        x=case_from_si("SR_PROPER_TIME_RATIO",(.5,),1)
        self.assertEqual(x["inputs"][0]["unit"],"%")
        self.assertAlmostEqual(normalize_case(x)[1][0].si,.5)
        self.assertAlmostEqual(exact(x),(.75)**.5)

    def test_ohm_milliamp_kiloohm_to_volts(self):
        v=case_from_si("OHMIC_VOLTAGE",(.5,200.),1)
        self.assertAlmostEqual(v["inputs"][0]["value"],500.)
        self.assertAlmostEqual(v["inputs"][1]["value"],.2)
        self.assertAlmostEqual(exact(v),100.)

    def test_kinematics_kmh_and_ms_to_meters(self):
        x=case_from_si("CONSTANT_VELOCITY_DISPLACEMENT",(5.,2.),1)
        self.assertAlmostEqual(x["inputs"][0]["value"],18.)
        self.assertAlmostEqual(x["inputs"][1]["value"],2000.)
        self.assertAlmostEqual(exact(x),10.)

    def test_ohm_wrong_unit_rejected_before_network(self):
        x=case_from_si("OHMIC_VOLTAGE",(.5,10.),0)
        x["inputs"][0]["unit"]="s"
        with self.assertRaisesRegex(ValueError,"R35_DIMENSION_MISMATCH"):
            normalize_case(x)

    def test_target_dimension_and_unknown_units_rejected(self):
        x=case_from_si("OHMIC_VOLTAGE",(.5,10.),0)
        x["target_unit"]="W"
        with self.assertRaisesRegex(ValueError,"R35_TARGET_DIMENSION_MISMATCH"):
            exact(x)
        x["target_unit"]="incorrect"
        with self.assertRaisesRegex(ValueError,"R35_UNKNOWN_TARGET_UNIT"):
            exact(x)

    def test_sr_near_light_speed_does_not_silently_round(self):
        x=case_from_si("SR_PROPER_TIME_RATIO",(.96,),0)
        self.assertAlmostEqual(exact(x),.28,places=10)
        x["inputs"][0]["value"]=1.1
        with self.assertRaisesRegex(ValueError,"R35_SR_BETA_OUT_OF_DOMAIN"):
            exact(x)

    def test_born_invalid_density_component_refused(self):
        x=case_from_si("TWO_LEVEL_BORN_PROBABILITY",(.9,),0)
        x["inputs"][0]["value"]=1.5
        with self.assertRaisesRegex(ValueError,"R35_BORN_PROBABILITY_OUT_OF_DOMAIN"):
            exact(x)

    def test_source_spoof_and_train_rights_escalation_blocked(self):
        x=case_from_si("OHMIC_VOLTAGE",(.5,10.),0)
        x["source_url"]="https://bad.example/unverified"
        with self.assertRaisesRegex(ValueError,"R35_SOURCE_SPOOF"):
            exact(x)
        bad=copy.deepcopy(self.manifest)
        bad["curated_external_laboratory_data_training_permitted"]=True
        with self.assertRaisesRegex(ValueError,"R35_SCIENTIFIC_TRAINING_PROMOTION_DENIED"):
            source_manifest_check(bad)

    def test_typed_battery_data_only_observation_not_gradient(self):
        rec={"family":"BATTERY_SOC_VOLTAGE_CURVE",
             "dataset_url":"https://zenodo.org/records/13142016",
             "dataset_sha256":BATTERY_SHA,
             "observation_id":"battery_synthetic_row_001",
             "input":{"name":"soc","value":50.,"unit":"%"},
             "measured_target":{"name":"ocv","value":3900.,"unit":"mV"},
             "original_license_review_complete":False,
             "independent_curator_approved_for_training":False}
        q=typed_lab_observation(rec)
        self.assertAlmostEqual(q["input_SI"],.5)
        self.assertAlmostEqual(q["observed_target_SI"],3.9)
        self.assertFalse(q["eligible_for_neural_gradient"])
        rec["dataset_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"R35_LAB_DATASET_SHA_OR_ORIGIN_MISMATCH"):
            typed_lab_observation(rec)

    def test_muon_momentum_energy_unit_not_confused(self):
        rec={"family":"MUON_STOP_DECAY_AND_NEUTRON_CAPTURE",
             "dataset_url":"https://zenodo.org/records/15081911",
             "dataset_sha256":MUON_SHA,
             "observation_id":"muon_synthetic_row_001",
             "input":{"name":"electron_momentum","value":35.,"unit":"MeV/c"},
             "measured_target":{"name":"tagged_delay","value":2.,"unit":"µs"},
             "original_license_review_complete":False,
             "independent_curator_approved_for_training":False}
        parsed=typed_lab_observation(rec)
        self.assertAlmostEqual(parsed["observed_target_SI"],2e-6)
        self.assertEqual(parsed["target_dimensions"],DS)
        self.assertFalse(parsed["eligible_for_neural_gradient"])
        rec["input"]["unit"]="m/s"
        with self.assertRaisesRegex(ValueError,"R35_DIMENSION_MISMATCH"):
            typed_lab_observation(rec)

    def test_real_laboratory_training_requires_external_review(self):
        fake={"dataset_url":"https://zenodo.org/records/13142016",
              "source_family":"BATTERY_SOC_VOLTAGE_CURVE",
              "md5_passed":True,"source_sha256":BATTERY_SHA,
              "curator_approved":True}
        with self.assertRaisesRegex(ValueError,"R35_NO_INDEPENDENT_CURATOR_OR_RIGHTS_APPROVAL"):
            refuse_lab_training(fake)

    def test_neural_features_encode_units_and_physical_roles(self):
        x=case_from_si("OHMIC_VOLTAGE",(.7,10.),0)
        y=case_from_si("OHMIC_VOLTAGE",(.7,10.),1)
        self.assertEqual(vector(x),vector(y))
        self.assertEqual(len(vector(x)),INPUT_WIDTH)
        withheld=case_from_si("ELECTRIC_POWER_IV",(.8,8.),0)
        with self.assertRaisesRegex(ValueError,"R35_UNSEEN_FAMILY_CANNOT_BE_MODEL_INPUT"):
            vector(withheld)

    def test_new_family_has_exact_formula_baseline_but_no_model_training(self):
        cases=[r for r in dataset(self.manifest,"public_dev")
               if r["case"]["family"]==UNTRAINED_FAMILY]
        self.assertEqual(len(cases),6)
        self.assertTrue(all(r["target_unit"]=="W" for r in cases))
        self.assertFalse(any(r["train_family_eligible"] for r in cases))
        for x in cases:self.assertAlmostEqual(x["target_value"],exact(x["case"]))

if __name__=="__main__":
    unittest.main()
