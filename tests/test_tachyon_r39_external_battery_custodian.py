"""R3.9 synthetic-only tests. No external lab questions/answers in Actions."""
import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from tachyon.r39_external_battery_custodian import (
    CONFIG_PATH,FORBIDDEN_PUBLIC_STUDY,BASELINE,CANDIDATE,
    PRIVATE_SCHEMA,QUESTIONS_SCHEMA,MIN_DEVICES,
    load_json,validate_config,validate_private,validate_questions,
    verify_source_code,questions_from_private,seal,
    offline_inference,validate_predictions,score_private,sha,write_new
)

SALT=bytes.fromhex("a5"*32)

def fake_private_pack():
    """12 synthetic device traces, two study labels, two chemistry labels.

    These are explicitly NOT real physical measurements or secret lab data.
    """
    devices=[]
    for i in range(12):
        study="FICTIONAL_STUDY_ALPHA" if i<6 else "FICTIONAL_STUDY_BETA"
        chemistry="SYNTHETIC_LFP" if i%2 else "SYNTHETIC_NMC"
        uid=f"FAKE_DEVICE_{i:03d}"
        trace=[]
        for j in range(1441):
            t=j/60
            # Classical double exponential, synthetic fixture by design.
            voltage=(3.4+0.08*math.exp(-t/(.25+i*.01))
                     +0.02*math.exp(-t/6.)
                     +0.00001*i)
            trace.append([t,voltage])
        devices.append({
            "device_uid":uid,
            "source_study_id":study,
            "chemistry":chemistry,
            "trace":trace
        })
    return {"schema":PRIVATE_SCHEMA,
            "cohort_id":"FAKE_EXTERNAL_FIXTURE_001","devices":devices}

class R39ExternalProtocol(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config=validate_config(load_json(CONFIG_PATH))

    def setUp(self):
        self.pack=fake_private_pack()

    def test_frozen_real_code_sha_no_prior_model_churn(self):
        self.assertEqual(len(verify_source_code()),2)
        self.assertEqual(self.config["frozen"]["candidate_model"],CANDIDATE)
        self.assertEqual(self.config["frozen"]["strongest_incumbent"],BASELINE)

    def test_new_device_requirements_and_no_old_public_study(self):
        self.assertEqual(validate_private(self.pack)["device_count"],12)
        bad=copy.deepcopy(self.pack)
        bad["devices"][0]["source_study_id"]=FORBIDDEN_PUBLIC_STUDY
        with self.assertRaisesRegex(ValueError,"R39_PREVIOUS_OR_DUPLICATE_DEVICE"):
            validate_private(bad)
        bad=copy.deepcopy(self.pack)
        bad["devices"]=bad["devices"][:11]
        with self.assertRaisesRegex(ValueError,"R39_INDEPENDENT_DEVICE_COUNT"):
            validate_private(bad)

    def test_requires_multisource_multichemistry_and_complete_trace(self):
        bad=copy.deepcopy(self.pack)
        for row in bad["devices"]:
            row["chemistry"]="SYNTHETIC_LFP"
        with self.assertRaisesRegex(ValueError,"R39_NOT_MULTISOURCE_MULTICHEMISTRY"):
            validate_private(bad)
        bad=copy.deepcopy(self.pack)
        bad["devices"][0]["trace"].pop()
        with self.assertRaisesRegex(ValueError,"R39_REQUIRE_COMPLETE_24H_MINUTE_TRACE"):
            validate_private(bad)
        bad=copy.deepcopy(self.pack)
        bad["devices"][0]["trace"][300][1]=float("nan")
        with self.assertRaisesRegex(ValueError,"R39_BAD_TIME_VOLTAGE_ROW"):
            validate_private(bad)

    def test_salted_seal_is_gold_free_and_questions_have_only_4_hours(self):
        receipt,q=seal(self.pack,SALT,self.config)
        self.assertEqual(receipt["case_count"],12)
        self.assertTrue(receipt["private_salt_is_public"] is False)
        self.assertEqual(q["schema"],QUESTIONS_SCHEMA)
        self.assertEqual(len(q["cases"][0]["early_voltage_trace_hours_volts"]),241)
        self.assertEqual(len(q["forecast_minute_indices"]),1200)
        self.assertEqual(q["forecast_minute_indices"][0],241)
        self.assertTrue(q["questions_include_future_gold"] is False)
        self.assertEqual(validate_questions(q,self.config),q)
        self.assertNotIn("trace",json.dumps(q))
        self.assertNotIn("FAKE_DEVICE",json.dumps(q))
        self.assertNotIn("source_study_id",json.dumps(q))

    def test_question_tampering_and_gold_field_injection_rejected(self):
        _,q=seal(self.pack,SALT,self.config)
        changed=copy.deepcopy(q)
        changed["cases"][0]["early_voltage_trace_hours_volts"][0][1]=4.5
        with self.assertRaisesRegex(ValueError,"R39_QUESTION_TAMPERED_SHA"):
            validate_questions(changed,self.config)
        changed=copy.deepcopy(q)
        changed["cases"][0]["future_gold"]=[4.2]*1200
        changed["questions_sha256"]=sha({
            k:v for k,v in changed.items() if k!="questions_sha256"
        })
        with self.assertRaisesRegex(ValueError,"R39_HIDDEN_GOLD_IN_INFERENCE_INPUT"):
            validate_questions(changed,self.config)

    def test_false_independent_connected_or_auto_training_blocked(self):
        fake=copy.deepcopy(self.config)
        fake["governance"]["actual_external_custodian_connected"]=True
        with self.assertRaisesRegex(ValueError,"R39_CUSTODIAN_OR_TRAINING_FALSE_AUTHORIZATION"):
            validate_config(fake)
        fake=copy.deepcopy(self.config)
        fake["governance"]["automatic_neural_training"]=True
        with self.assertRaisesRegex(ValueError,"R39_CUSTODIAN_OR_TRAINING_FALSE_AUTHORIZATION"):
            validate_config(fake)

    def test_entire_custodian_only_offline_pipeline_and_no_science_admission(self):
        receipt,q=seal(self.pack,SALT,self.config)
        prediction=offline_inference(q,self.config)
        self.assertEqual(len(prediction["predictions"]),12)
        self.assertEqual(prediction["actual_real_early_window_model_fits"],24)
        self.assertFalse(prediction["any_future_measurements_read"])
        self.assertEqual(validate_predictions(prediction,q,self.config),prediction)
        report=score_private(self.pack,SALT,receipt,q,prediction,self.config)
        self.assertEqual(report["device_count"],12)
        self.assertEqual(report["source_study_count"],2)
        self.assertEqual(report["chemistry_count"],2)
        self.assertGreater(report["device_weighted_baseline_MAE_volts"],0)
        self.assertEqual(report["scientific_admission"],"HOLD")
        self.assertFalse(report["production_promotion"])
        self.assertFalse(report["independent_true_blind_established"])
        self.assertFalse(report["real_external_signature_checked"])
        self.assertFalse(report["neural_weights_trained"])
        self.assertFalse(report["external_expert_scientific_review_complete"])
        self.assertEqual(len(report["exploratory_device_bootstrap_95pct_gain_interval"]),2)
        self.assertNotIn("FAKE_DEVICE",json.dumps(report))
        self.assertNotIn("SYNTHETIC_LFP",json.dumps(report))
        self.assertEqual(report["receipt_sha256"],sha({
            k:v for k,v in report.items() if k!="receipt_sha256"
        }))

    def test_private_salt_gold_and_predictions_mismatch_rejected(self):
        receipt,q=seal(self.pack,SALT,self.config)
        pred=offline_inference(q,self.config)
        with self.assertRaisesRegex(ValueError,"R39_INDEPENDENT_SEAL_CHANGED_OR_WRONG_SALT"):
            score_private(self.pack,b"0"*32,receipt,q,pred,self.config)
        bad=copy.deepcopy(self.pack)
        bad["devices"][0]["trace"][1000][1]+=.1
        with self.assertRaisesRegex(ValueError,"R39_INDEPENDENT_SEAL_CHANGED_OR_WRONG_SALT"):
            score_private(bad,SALT,receipt,q,pred,self.config)
        tampered=copy.deepcopy(pred)
        tampered["predictions"][0]["candidate_volts"][0]+=.4
        with self.assertRaisesRegex(ValueError,"R39_PREDICTIONS_TAMPERED_SHA"):
            score_private(self.pack,SALT,receipt,q,tampered,self.config)

    def test_append_only_output_rejects_second_report(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/"report.json"
            write_new(path,{"scientific_admission":"HOLD"})
            with self.assertRaises(FileExistsError):
                write_new(path,{"scientific_admission":"PASS"})

if __name__=="__main__":
    unittest.main()
