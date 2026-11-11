"""R3.8 safe public eight-group leave-one-out and physical surrogate tests."""
import copy
import json
import math
from pathlib import Path
import unittest

from tachyon.r38_battery_physical_crossval import (
    GROUPS,BASELINES,CHALLENGERS,ALL_MODELS,
    basis,fit_new,new_predict,per_trace,score_public_lobo,
    verify_config,verify_custodian_slot,posthoc_safety,sha
)

CONF=Path("data/tachyon/r38/eight_battery_cross_validation_manifest.json")
CUST=Path("data/tachyon/r38/external_custodian_control_not_provided.json")

def trace_curve():
    # Artificial fixture: measured public source data not copied here.
    return [(i/60., 3.30+0.09*math.exp(-(i/60.)/.45)
             +0.035*math.exp(-(i/60.)/7.)) for i in range(1441)]

def score_data(challenger_good=True):
    scores={}
    for b in GROUPS:
        scores[b]={}
        for m in ALL_MODELS:
            scores[b][m]=(
                .005 if m=="double_exp" else
                .003 if m=="triple_exp" and challenger_good else
                .012 if m=="triple_exp" else
                .014
            )
    return scores

class TestR38(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf=verify_config(json.loads(CONF.read_text(encoding="utf8")))
        cls.cust=verify_custodian_slot(json.loads(CUST.read_text(encoding="utf8")))

    def test_all_eight_device_groups_and_pinned_families(self):
        self.assertEqual(len(GROUPS),8)
        self.assertEqual(len(ALL_MODELS),6)
        self.assertEqual(len(BASELINES),3)
        self.assertEqual(len(CHALLENGERS),3)
        self.assertEqual(self.conf["candidate_selection"]["early_voltage_fit_hours"],4)

    def test_own_source_is_public_retrospective_not_external_blind(self):
        self.assertTrue(self.conf["candidate_selection"]["historical_previous_r37_exposure"])
        self.assertEqual(self.cust["status"],"NOT_PROVIDED_BY_INDEPENDENT_LAB")
        self.assertFalse(self.cust["independent_external_holdout_completed"])
        self.assertFalse(self.conf["governance"]["neural_retraining_permitted"])

    def test_reject_forged_external_custodian_signatures(self):
        c=copy.deepcopy(self.cust)
        c["independent_identity_signature"]="fake"
        with self.assertRaisesRegex(ValueError,"R38_EXTERNAL_CUSTODIAN_NOT_CONNECTED"):
            verify_custodian_slot(c)

    def test_reject_train_and_production_gate_escalation(self):
        c=copy.deepcopy(self.conf)
        c["governance"]["neural_retraining_permitted"]=True
        with self.assertRaisesRegex(ValueError,"R38_CONFIG_OR_SCIENTIFIC_GATE_DRIFT"):
            verify_config(c)

    def test_dimensional_and_tau_positive_gates(self):
        with self.assertRaisesRegex(ValueError,"R38_RC_TIME_CONSTANT_ORDER"):
            basis("triple_exp",1.,(4.,2.,8.))
        with self.assertRaisesRegex(ValueError,"R38_STRETCH_DOMAIN"):
            basis("stretched_exp",1.,(1.,-1.))
        with self.assertRaisesRegex(ValueError,"R38_DIFFUSION_TIME_DOMAIN"):
            basis("diffusion_tail",2.,(-1.,))
        for name,params in (
            ("triple_exp",(.1,2.,16.)),
            ("stretched_exp",(2.,.6)),
            ("diffusion_tail",(2.,))):
            values=basis(name,1.,params)
            self.assertTrue(all(math.isfinite(x) for x in values))
            self.assertEqual(values[0],1.)

    def test_each_new_physical_surrogate_real_fits_and_forecasts(self):
        source=trace_curve()
        for name in CHALLENGERS:
            fit=fit_new(source,name)
            self.assertEqual(fit["name"],name)
            for t in (4.,12.,24.):
                self.assertTrue(math.isfinite(new_predict(fit,t)))
        scores=per_trace(source)
        self.assertEqual(set(scores),set(ALL_MODELS))
        self.assertEqual(scores["triple_exp"]["forecast_count"],1200)
        self.assertLess(scores["triple_exp"]["forecast_MAE_V"],0.05)

    def test_leave_one_battery_out_never_uses_heldout_as_selection(self):
        folds=score_public_lobo(score_data())
        self.assertEqual(len(folds),8)
        self.assertEqual([f["heldout_battery"] for f in folds],list(GROUPS))
        for f in folds:
            self.assertEqual(len(f["selection_batteries"]),7)
            self.assertNotIn(f["heldout_battery"],f["selection_batteries"])
            self.assertTrue(f["candidate_challenger_beats_baseline"])
            self.assertEqual(f["selected_model"],"triple_exp")

    def test_stronger_baseline_wins_when_challengers_lack_gain(self):
        folds=score_public_lobo(score_data(challenger_good=False))
        self.assertEqual(len(folds),8)
        self.assertTrue(all(not f["challenger_selected"] for f in folds))
        self.assertTrue(all(f["selected_model"]=="double_exp" for f in folds))
        self.assertEqual(sum(f["candidate_challenger_beats_baseline"] for f in folds),0)

    def test_posthoc_regression_guard_does_not_fake_preregistration(self):
        folds=[
            {"heldout_battery":"LI","selected_model":"diffusion_tail",
             "outer_relative_MAE_gain":-0.5176},
            {"heldout_battery":"AR","selected_model":"diffusion_tail",
             "outer_relative_MAE_gain":-0.0862},
            {"heldout_battery":"APR","selected_model":"diffusion_tail",
             "outer_relative_MAE_gain":0.1347}
        ]
        risk=posthoc_safety(folds)
        self.assertEqual(risk["worst_device"],"LI")
        self.assertAlmostEqual(risk["worst_device_relative_MAE_increase_pct"],51.76)
        self.assertEqual(len(risk["devices_with_worse_MAE_than_selected_baseline"]),2)
        self.assertTrue(risk["descriptive_regression_alert_over_10_pct"])
        self.assertFalse(risk["was_preregistered_before_initial_public_result"])
        self.assertFalse(risk["is_approval_metric"])
        self.assertTrue(risk["independent_prospective_evidence_still_required"])

    def test_source_unavailable_scores_reject_instead_of_imputing(self):
        scores=score_data()
        scores["AU"]["double_exp"]=None
        scores["AU"]["triple_exp"]=None
        with self.assertRaisesRegex(ValueError,"R38_OUTER_FOLD_UNAVAILABLE"):
            score_public_lobo(scores)

if __name__=="__main__":
    unittest.main()
