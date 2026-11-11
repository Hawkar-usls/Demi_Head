"""TACHYON R3.10: bounded early-only uncertainty, fallback and safety tests."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tachyon.r38_battery_physical_crossval import GROUPS
from tachyon.r310_early_only_formula_reliability import (
    SCHEMA,INCUMBENT,CANDIDATE,THRESHOLDS,
    check_early,evaluate_early_only,score_future,audit_one_trace,
    threshold_score,calibrate_without_heldout,decide,heldout_audit,
    validate_config,verify_frozen_code
)

MANIFEST=Path("data/tachyon/r310/formula_reliability_risk_manifest.json")

def artificial_curve():
    return [
        (i/60.,3.4+.08*math.exp(-(i/60.)/.5)
         +.03*math.exp(-(i/60.)/8.))
        for i in range(1441)
    ]

def seven_development_rows(exclude="LI",candidate_bad=False):
    rows=[]
    for g in GROUPS:
        if g==exclude:continue
        for risk in (.001,.1):
            rows.append({
                "battery":g,
                "column":f"fake_{g}_{risk}",
                "features":{
                    "status":"EARLY_ONLY_MODELS_COMPUTED",
                    "risk_proxy":risk,
                    "baseline_MAE_V":.02,
                    "candidate_MAE_V":.05 if candidate_bad else
                                      (.01 if risk==.001 else .05)
                }
            })
    return rows

class R310Reliability(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=validate_config(
            json.loads(MANIFEST.read_text(encoding="utf8")))

    def test_source_code_sha_freeze_and_r39_not_modified(self):
        self.assertTrue(verify_frozen_code())
        self.assertEqual(self.config["governance"]["independent_r39_locked_and_unchanged"],True)
        self.assertFalse(self.config["governance"]["real_neural_training_authorized"])

    def test_early_only_model_cannot_accept_heldout_points(self):
        points=artificial_curve()
        with self.assertRaisesRegex(ValueError,"R310_EARLY_ONLY_241_POINTS_REQUIRED"):
            evaluate_early_only(points)
        x=evaluate_early_only(points[:241])
        self.assertFalse(x["future_truth_read"])
        self.assertEqual(len(x["candidate_future_predictions"]),1200)
        self.assertEqual(len(x["incumbent_future_predictions"]),1200)
        self.assertTrue(math.isfinite(x["risk_proxy"]))

    def test_early_risk_identical_if_future_gold_altered(self):
        points=artificial_curve()
        changed=copy.deepcopy(points)
        changed[400]=(changed[400][0],changed[400][1]+.25)
        x=evaluate_early_only(points[:241])
        y=evaluate_early_only(changed[:241])
        self.assertEqual(x["risk_proxy"],y["risk_proxy"])
        self.assertEqual(x["candidate_future_predictions"],
                         y["candidate_future_predictions"])
        a=score_future(x,[v for t,v in points[241:]])
        b=score_future(y,[v for t,v in changed[241:]])
        self.assertNotEqual(a,b)

    def test_out_of_domain_early_signal_explicit_abstention(self):
        bad=[list(x) for x in artificial_curve()[:241]]
        bad[0][1]=0.2
        with self.assertRaisesRegex(ValueError,"R310_EARLY_TIME_OR_PHYSICAL_VOLTAGE_REJECT"):
            evaluate_early_only(bad)
        f={"status":"ABSTAIN_UNPHYSICAL_OR_UNRELIABLE_EARLY_SIGNAL",
           "risk_proxy":None}
        self.assertEqual(decide(f,{"candidate_allowed":True,"threshold":.16}),
                         "ABSTAIN")

    def test_normal_lower_voltage_chemistry_is_not_falsely_refused(self):
        # Original published AR/AU measurements include 0.902–1.471 V;
        # do not reject them with a Li-ion-only 2 V floor.
        low=[[t,1.22+.05*math.exp(-t/.8)] for t,v
             in artificial_curve()[:241]]
        parsed=check_early(low)
        self.assertTrue(all(.5<=v<=5.5 for t,v in parsed))
        self.assertEqual(len(parsed),241)

    def test_bad_optional_formula_falls_back_to_healthy_baseline(self):
        early=artificial_curve()[:241]
        with patch(
            "tachyon.r310_early_only_formula_reliability.new_predict",
            side_effect=ValueError("synthetic_unsafe_optional_tail")
        ):
            state=evaluate_early_only(early)
            self.assertEqual(state["status"],
                             "CANDIDATE_UNSAFE_BASELINE_AVAILABLE")
            self.assertIsNone(state["candidate_future_predictions"])
            self.assertIsNone(state["risk_proxy"])
            self.assertEqual(len(state["incumbent_future_predictions"]),1200)
            self.assertEqual(decide(state,{"candidate_allowed":True,
                                           "threshold":.16}),
                             "FALLBACK_DOUBLE_EXP")
            s=score_future(state,[v for t,v in artificial_curve()[241:]])
            self.assertGreater(s["baseline_MAE_V"],0)
            self.assertIsNone(s["candidate_MAE_V"])
            audit=audit_one_trace(artificial_curve())
            self.assertEqual(audit["status"],
                             "CANDIDATE_UNSAFE_BASELINE_AVAILABLE")
            self.assertIsNotNone(audit["baseline_MAE_V"])

    def test_risk_threshold_fit_uses_only_seven_batteries(self):
        development=seven_development_rows()
        gate=calibrate_without_heldout(development,"LI")
        self.assertTrue(gate["candidate_allowed"])
        self.assertIn(gate["threshold"],THRESHOLDS)
        self.assertGreater(gate["threshold"],0.)
        self.assertLess(gate["threshold"],.1)
        self.assertEqual(decide(
          {"status":"EARLY_ONLY_MODELS_COMPUTED","risk_proxy":.001},gate),
          "CANDIDATE_DIFFUSION_TAIL")
        self.assertEqual(decide(
          {"status":"EARLY_ONLY_MODELS_COMPUTED","risk_proxy":.1},gate),
          "FALLBACK_DOUBLE_EXP")
        leak=development+[{
           "battery":"LI","features":{"status":"EARLY_ONLY_MODELS_COMPUTED",
                   "risk_proxy":.0,"baseline_MAE_V":2.,
                   "candidate_MAE_V":0.},
           "column":"secret_test_row"
        }]
        with self.assertRaisesRegex(ValueError,"R310_TEST_BATTERY_LEAKS_TO_CALIBRATION"):
            calibrate_without_heldout(leak,"LI")

    def test_no_supported_risk_threshold_means_strong_baseline_fallback(self):
        rows=seven_development_rows(candidate_bad=True)
        gate=calibrate_without_heldout(rows,"LI")
        self.assertFalse(gate["candidate_allowed"])
        self.assertIsNone(gate["threshold"])
        self.assertEqual(decide({
           "status":"EARLY_ONLY_MODELS_COMPUTED","risk_proxy":.0001
        },gate),"FALLBACK_DOUBLE_EXP")

    def test_no_misleading_families_or_units(self):
        self.assertEqual(CANDIDATE,"diffusion_tail")
        self.assertEqual(INCUMBENT,"double_exp")
        x=artificial_curve()
        score=audit_one_trace(x)
        self.assertEqual(score["status"],"EARLY_ONLY_MODELS_COMPUTED")
        self.assertGreater(score["baseline_MAE_V"],0)
        self.assertGreater(score["candidate_MAE_V"],0)
        self.assertFalse("future_prediction" in json.dumps(score))

    def test_device_folds_record_all_fallback_and_abstain_reasons(self):
        development=seven_development_rows(candidate_bad=True)
        target={
           "battery":"LI","column":"synthetic_LI_case",
           "features":{
               "status":"EARLY_ONLY_MODELS_COMPUTED",
               "risk_proxy":.001,
               "baseline_MAE_V":.01,
               "candidate_MAE_V":.025
           }
        }
        folds=heldout_audit(development+[target],"LI")
        self.assertEqual(folds["heldout_battery"],"LI")
        self.assertEqual(folds["num_candidate_used"],0)
        self.assertEqual(folds["num_baseline_fallback"],1)
        self.assertEqual(folds["selected_relative_gain"],0.)
        self.assertFalse(folds["regression_over_10pct"])
        self.assertTrue(folds["past_public_heldout_is_not_independent_blind"])

    def test_configuration_science_hold_is_not_optional(self):
        changed=copy.deepcopy(self.config)
        changed["governance"]["real_neural_training_authorized"]=True
        with self.assertRaisesRegex(ValueError,"R310_FALSE_SCIENCE_OR_LEARNING_PROMOTION"):
            validate_config(changed)
        changed=copy.deepcopy(self.config)
        changed["governance"]["independent_r39_locked_and_unchanged"]=False
        with self.assertRaisesRegex(ValueError,"R310_FALSE_SCIENCE_OR_LEARNING_PROMOTION"):
            validate_config(changed)

    def test_calibration_has_no_unsupported_scientific_probability_claim(self):
        rows=seven_development_rows()
        r=threshold_score(rows,[b for b in GROUPS if b!="LI"],.002)
        self.assertTrue(r["admissible"])
        self.assertGreaterEqual(r["accepted_candidate_fraction"],.15)
        self.assertGreater(r["device_equal_calibration_gain"],0)
        self.assertFalse("confidence_probability" in r)

if __name__=="__main__":
    unittest.main()
