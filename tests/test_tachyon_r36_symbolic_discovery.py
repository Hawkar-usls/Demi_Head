"""R3.6 symbolic regression: no physical-law claims from synthetic observations."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tachyon.r36_symbolic_discovery import (
    SCENARIOS,TERM_NAMES,candidates,validate_formula_dimensions,
    validate_manifest,admit_training_source,generate_simulator,fit_terms,
    frozen_candidate,run_one,experiment,sha,need,Observation,
    validate_observation,rmse,baseline,predict,equation
)

MANIFEST_PATH=Path("data/tachyon/r36/symbolic_discovery_sandbox_manifest.json")

class R36Discovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=validate_manifest(
            json.loads(MANIFEST_PATH.read_text(encoding="utf8")))

    def test_si_dimensions_physical_basis_and_grammar(self):
        self.assertEqual(len(candidates()),16)
        self.assertTrue(validate_formula_dimensions(("theta",)))
        self.assertTrue(validate_formula_dimensions(
            ("theta","theta_times_normalized_current")))
        with self.assertRaisesRegex(ValueError,"R36_UNAPPROVED_FORMULA_GRAMMAR"):
            validate_formula_dimensions(("current_times_temperature_kelvin",))
        with self.assertRaisesRegex(ValueError,"R36_UNAPPROVED_FORMULA_GRAMMAR"):
            validate_formula_dimensions(("theta","theta","normalized_current"))

    def test_different_train_val_future_samples(self):
        train=generate_simulator("TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC","train")
        val=generate_simulator("TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC","validation")
        future=generate_simulator("TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC","future_test")
        self.assertEqual((len(train),len(val),len(future)),(84,42,54))
        self.assertFalse({x.case_id for x in train}&{x.case_id for x in val})
        self.assertFalse({x.case_id for x in future}&{x.case_id for x in train+val})

    def test_generates_candidate_from_measurements_not_from_own_labels(self):
        train=generate_simulator("TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC","train")
        val=generate_simulator("TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC","validation")
        a=frozen_candidate(train,val)
        self.assertEqual(len(a["all_16_candidate_trials"]),16)
        self.assertEqual(len(a["candidate_pre_test_sha256"]),64)
        self.assertTrue(a["terms"])
        self.assertIn("theta",a["terms"])
        self.assertTrue(a["equation"].startswith("V = I*R*(1 "))
        self.assertEqual(a["scientific_admission"],"HOLD")

    def test_positive_sandbox_beats_incomplete_ohmic_law_on_future_samples(self):
        r=run_one(self.manifest,"TEMPERATURE_DEPENDENT_RESISTOR_SYNTHETIC")
        self.assertTrue(r["synthetic_independent_future_test_pass"])
        self.assertGreater(r["future_test_relative_RMSE_improvement"],.15)
        self.assertLess(r["candidate_future_test_RMSE_volts"],
                        r["baseline_ohm_future_test_RMSE_volts"])
        self.assertTrue(r["automatic_research_refit_done"])
        self.assertFalse(r["new_general_physics_law_discovered"])
        self.assertFalse(r["training_curated_real_lab_measurements"])
        self.assertEqual(r["scientific_admission"],"HOLD")
        self.assertEqual(r["receipt_sha256"],sha({k:v for k,v in r.items()
                                                 if k!="receipt_sha256"}))

    def test_negative_sandbox_does_not_claim_superiority_to_exact_ohm(self):
        r=run_one(self.manifest,"PURE_OHM_SYNTHETIC_NEGATIVE_CONTROL")
        self.assertFalse(r["synthetic_independent_future_test_pass"])
        self.assertFalse(r["candidate_autopromoted_to_production"])
        self.assertFalse(r["learned_from_own_predictions"])
        self.assertEqual(r["scientific_admission"],"HOLD")

    def test_verified_doi_and_sha_does_not_authorize_laboratory_gradient(self):
        for url in (
          "https://zenodo.org/records/15081911",
          "https://zenodo.org/records/13142016"):
            with self.assertRaisesRegex(ValueError,
                         "R36_REAL_LAB_CURATOR_RIGHTS_AND_BLIND_HOLD"):
                admit_training_source(url,curator_signed=True)
        with self.assertRaisesRegex(ValueError,
                         "R36_SELF_ASSERTED_CURATOR_SIGNATURE_NOT_TRUSTED"):
            admit_training_source("SYNTHETIC_GENERATOR_ONLY",curator_signed=True)
        self.assertTrue(admit_training_source("SYNTHETIC_GENERATOR_ONLY"))

    def test_untrusted_manifest_cannot_escalate_scientific_admission(self):
        changed=copy.deepcopy(self.manifest)
        changed["scientific_admission"]="ACCEPTED"
        with self.assertRaisesRegex(ValueError,"R36_NOT_APPROVED_FOR_EXTERNAL_LAB_TRAINING"):
            validate_manifest(changed)
        changed=copy.deepcopy(self.manifest)
        changed["source_rights_curator_approved_real_lab_data"]=True
        with self.assertRaisesRegex(ValueError,"R36_NOT_APPROVED_FOR_EXTERNAL_LAB_TRAINING"):
            validate_manifest(changed)

    def test_refuse_wrong_units_or_nonphysical_measured_rows(self):
        row=Observation("fake",.5,10.,12.,-5.,"SYNTHETIC_GENERATOR_ONLY")
        with self.assertRaisesRegex(ValueError,"R36_OBSERVATION_DOMAIN"):
            validate_observation(row)
        row=Observation("fake",.5,10.,12.,5.,"PUBLISHED_LAB_UNAPPROVED")
        with self.assertRaisesRegex(ValueError,"R36_UNAPPROVED_OBSERVATION_SOURCE"):
            validate_observation(row)

    def test_bounded_formula_domain_and_coefficients(self):
        data=generate_simulator("PURE_OHM_SYNTHETIC_NEGATIVE_CONTROL","train")
        adversarial=Observation("over_limit_case",.5,10.,16.,5.,
                                "SYNTHETIC_GENERATOR_ONLY")
        with self.assertRaisesRegex(ValueError,"R36_CORRECTION_EXCEEDS_SANDBOX_SCOPE"):
            predict(adversarial,("theta",),(.99,))
        with self.assertRaisesRegex(ValueError,"R36_FORMULA_COEFFICIENT_COUNT"):
            predict(data[0],("theta",),())
        self.assertEqual(fit_terms(data,()),())
        self.assertGreater(rmse(data),0)

    def test_real_measurement_inventory_stays_unapproved(self):
        source=Path('data/tachyon/r36/real_measurement_candidate_sources.json')
        inventory=json.loads(source.read_text(encoding='utf8'))
        self.assertEqual(inventory['scientific_admission'],'HOLD')
        self.assertFalse(inventory['automated_training_on_these_sources_allowed'])
        self.assertFalse(inventory['curator_signatures_present'])
        self.assertEqual(len(inventory['candidates']),2)
        for c in inventory['candidates']:
            self.assertEqual(c['training_status'],'REVIEW_REQUIRED_DO_NOT_TRAIN')
            self.assertTrue(c['record_url'].startswith('https://zenodo.org/records/'))
            self.assertTrue(c['data_fit_warning'])
    def test_full_report_no_overwrite_and_no_promotion(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/"evidence"
            report=experiment(MANIFEST_PATH,out)
            self.assertTrue(out.joinpath("r36_symbolic_formula_discovery.json").exists())
            self.assertTrue(report["synthetic_positive_control_detected"])
            self.assertTrue(report["synthetic_negative_control_rejected"])
            self.assertFalse(report["real_experimental_measured_data_scored"])
            self.assertFalse(report["self_generated_predictions_used_as_gold"])
            self.assertFalse(report["production_promotion"])
            self.assertEqual(report["scientific_admission"],"HOLD")
            with self.assertRaisesRegex(ValueError,"R36_REFUSE_OVERWRITE_EXISTING_EVIDENCE"):
                experiment(MANIFEST_PATH,out)

if __name__=="__main__":
    unittest.main()
