"""JANUS R3.9 — offline, external-custodian-only prospective voltage evaluation.

A true independent experiment is not conducted by running this file in JANUS.
Public CI uses only explicitly SYNTHETIC fixtures; private future labels and
the custodian salt must remain under the external laboratory's own control.
No training, no external network calls, no scientific or production promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
import hashlib
import json
import math
from pathlib import Path
import random
import re

from tachyon.r37_real_ocv_evaluator import (
    fit_on_early, predict as predict_2rc, need, sha
)
from tachyon.r38_battery_physical_crossval import (
    fit_new, new_predict
)

CONFIG_SCHEMA="janus.tachyon.r39.external_new_device_control_contract.v1"
PRIVATE_SCHEMA="janus.tachyon.r39.private_external_new_devices.v1"
SEAL_SCHEMA="janus.tachyon.r39.salted_private_pack_commitment.v1"
QUESTIONS_SCHEMA="janus.tachyon.r39.early_voltage_only_questions.v1"
PRED_SCHEMA="janus.tachyon.r39.actual_frozen_formula_predictions.v1"
SCORE_SCHEMA="janus.tachyon.r39.custodian_local_aggregate_score.v1"
SOURCE_BLOB_SHA={
 "tachyon/r38_battery_physical_crossval.py":"0f2cbb26e0a827d86b71d8e88798dfe348558697",
 "tachyon/r37_real_ocv_evaluator.py":"9dd07cc757e6441c0ee94a3bf3fa16c616dbc5ce"
}
FORBIDDEN_PUBLIC_STUDY="10.21227/651q-8v82"
FORBIDDEN_IDS=frozenset(("APR","BSE","SG","LG","OEM","LI","AR","AU"))
BASELINE="double_exp"
CANDIDATE="diffusion_tail"
EARLY=241
FUTURE=1200
TOTAL=1441
MIN_DEVICES=12
MAX_DEVICES=40
MIN_STUDIES=2
MIN_CHEMISTRIES=2
CONFIG_PATH=Path("data/tachyon/r39/independent_external_device_manifest.json")

def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def digest(data):
    return hashlib.sha256(data).hexdigest()

def git_blob_sha(path):
    raw=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw,
                        usedforsecurity=False).hexdigest()

def verify_source_code():
    root=Path(__file__).resolve().parents[1]
    for path, expected in SOURCE_BLOB_SHA.items():
        need(git_blob_sha(root/path)==expected,"R39_FROZEN_PRIOR_FORMULA_CODE_CHANGED")
    return SOURCE_BLOB_SHA.copy()

def load_json(path):
    o=json.loads(Path(path).read_text(encoding="utf8"))
    need(isinstance(o,dict),"R39_JSON_OBJECT_EXPECTED")
    return o

def validate_config(c):
    need(c.get("schema")==CONFIG_SCHEMA
         and c.get("frozen",{}).get("candidate_model")==CANDIDATE
         and c.get("frozen",{}).get("strongest_incumbent")==BASELINE
         and c.get("frozen",{}).get("model_code_git_blob_sha1")==SOURCE_BLOB_SHA
         and c.get("original_public_cohort",{}).get("source_doi")==FORBIDDEN_PUBLIC_STUDY
         and c.get("original_public_cohort",{}).get("explicitly_ineligible_as_r39_hidden_holdout") is True,
         "R39_FROZEN_MODEL_OR_PAST_DATA_CHANGED")
    p=c.get("private_data_contract",{})
    need(p.get("minimum_new_distinct_devices")==MIN_DEVICES
         and p.get("maximum_devices")==MAX_DEVICES
         and p.get("minimum_distinct_source_studies")==MIN_STUDIES
         and p.get("minimum_distinct_battery_chemistries")==MIN_CHEMISTRIES
         and p.get("expected_per_device_full_trace_minutes")==TOTAL
         and p.get("early_only_visible_to_model_minutes")==EARLY
         and p.get("private_future_label_minutes")==FUTURE
         and p.get("time_units")=="hours from disconnection"
         and p.get("voltage_units")=="V",
         "R39_OBSERVATION_PROTOCOL_DRIFT")
    t=c.get("metric_gates",{})
    need(t.get("positive_candidate_mean_relative_gain_min")==.10
         and t.get("minimum_win_fraction")==.80
         and t.get("max_worst_device_MAE_regression_fraction")==.10
         and t.get("minimum_per_source_study_positive_mean_gain") is True,
         "R39_ACCEPTANCE_METRIC_DRIFT")
    g=c.get("governance",{})
    need(g.get("actual_external_custodian_connected") is False
         and g.get("private_gold_received") is False
         and g.get("independent_custodian_signature_verified") is False
         and g.get("training_on_new_measurements_approved") is False
         and g.get("automatic_neural_training") is False
         and g.get("automatic_formula_promotion") is False
         and g.get("scientific_admission")=="HOLD",
         "R39_CUSTODIAN_OR_TRAINING_FALSE_AUTHORIZATION")
    return c

def validate_trace(trace):
    need(isinstance(trace,list) and len(trace)==TOTAL,
         "R39_REQUIRE_COMPLETE_24H_MINUTE_TRACE")
    for i,item in enumerate(trace):
        need(isinstance(item,list) and len(item)==2
             and all(type(v) in (int,float) and math.isfinite(v) for v in item),
             "R39_BAD_TIME_VOLTAGE_ROW")
        t,v=item
        need(abs(t-i/60)<1e-5 and 2<=v<=5.2,
             "R39_TIME_ORDER_OR_VOLTAGE_DOMAIN")
    return trace

def validate_private(pack):
    need(isinstance(pack,dict) and
         set(pack)=={"schema","cohort_id","devices"} and
         pack["schema"]==PRIVATE_SCHEMA,
         "R39_PRIVATE_PACK_SCHEMA")
    cohort=pack["cohort_id"]
    need(isinstance(cohort,str) and re.fullmatch(r"[A-Za-z0-9_-]{8,80}",cohort),
         "R39_COHORT_ID")
    rows=pack["devices"]
    need(isinstance(rows,list) and MIN_DEVICES<=len(rows)<=MAX_DEVICES,
         "R39_INDEPENDENT_DEVICE_COUNT")
    uids=set();studies=Counter();chemistries=Counter()
    for device in rows:
        need(isinstance(device,dict) and set(device)=={
            "device_uid","source_study_id","chemistry","trace"
        },"R39_PRIVATE_DEVICE_EXTRA_FIELDS")
        uid,study,chem=(device.get("device_uid"),device.get("source_study_id"),
                        device.get("chemistry"))
        need(all(isinstance(v,str) and
                 re.fullmatch(r"[A-Za-z0-9_./-]{4,120}",v) for v in (uid,study,chem)),
             "R39_INVALID_DEVICE_STUDY_CHEMISTRY_ID")
        need(uid.upper() not in FORBIDDEN_IDS and
             study!=FORBIDDEN_PUBLIC_STUDY and
             "bulyk47" not in study.lower() and
             uid not in uids,
             "R39_PREVIOUS_OR_DUPLICATE_DEVICE")
        uids.add(uid);studies[study]+=1;chemistries[chem]+=1
        validate_trace(device["trace"])
    need(len(studies)>=MIN_STUDIES and len(chemistries)>=MIN_CHEMISTRIES,
         "R39_NOT_MULTISOURCE_MULTICHEMISTRY")
    need(min(studies.values())>=3,
         "R39_EACH_INDEPENDENT_STUDY_REQUIRES_3_DEVICES")
    return {"device_count":len(rows),"study_count":len(studies),
            "chemistry_count":len(chemistries)}

def pseudonym(device,salt):
    return digest(b"JANUS-R39-CASE\0"+salt+
                  device["source_study_id"].encode("utf8")+b"\0"+
                  device["device_uid"].encode("utf8"))[:32]

def private_salt(path):
    value=Path(path).read_text(encoding="ascii").strip()
    need(re.fullmatch(r"[0-9a-fA-F]{64,128}",value) and
         len(value)%2==0,"R39_REQUIRE_EXTERNAL_256_BIT_RANDOM_SALT")
    return bytes.fromhex(value)

def questions_from_private(pack,salt,config):
    validate_private(pack);validate_config(config)
    questions={
       "schema":QUESTIONS_SCHEMA,
       "frozen_config_sha256":sha(config),
       "candidate_model":CANDIDATE,
       "baseline_model":BASELINE,
       "expected_raw_source_model_blob_sha1":SOURCE_BLOB_SHA,
       "forecast_minute_indices":list(range(EARLY,TOTAL)),
       "case_count":len(pack["devices"]),
       "questions_include_future_gold":False,
       "private_gold_and_salt_must_not_enter_actions":True,
       "cases":[
          {
            "case_id":pseudonym(dev,salt),
            "early_voltage_trace_hours_volts":dev["trace"][:EARLY]
          }
          for dev in pack["devices"]
       ]
    }
    questions["questions_sha256"]=sha(questions)
    return questions

def validate_questions(q,config):
    need(isinstance(q,dict) and set(q)=={
        "schema","frozen_config_sha256","candidate_model","baseline_model",
        "expected_raw_source_model_blob_sha1","forecast_minute_indices",
        "case_count","questions_include_future_gold",
        "private_gold_and_salt_must_not_enter_actions","cases","questions_sha256"
    },"R39_QUESTIONS_ONLY_NO_UNRECOGNIZED_OR_GOLD_FIELDS")
    need(q["schema"]==QUESTIONS_SCHEMA
         and q["frozen_config_sha256"]==sha(config)
         and q["candidate_model"]==CANDIDATE
         and q["baseline_model"]==BASELINE
         and q["expected_raw_source_model_blob_sha1"]==SOURCE_BLOB_SHA
         and q["questions_include_future_gold"] is False
         and q["private_gold_and_salt_must_not_enter_actions"] is True,
         "R39_FROZEN_INFERENCE_CONTRACT_CHANGED")
    need(q["questions_sha256"]==sha({
        k:v for k,v in q.items() if k!="questions_sha256"}),
        "R39_QUESTION_TAMPERED_SHA")
    need(q["forecast_minute_indices"]==list(range(EARLY,TOTAL)),
         "R39_FUTURE_TIME_GRID_CHANGED")
    cs=q["cases"]
    need(isinstance(cs,list) and MIN_DEVICES<=len(cs)<=MAX_DEVICES
         and type(q["case_count"]) is int and q["case_count"]==len(cs),
         "R39_QUESTION_BUNDLE_SIZE")
    ids=set()
    for c in cs:
        need(isinstance(c,dict)
             and set(c)=={"case_id","early_voltage_trace_hours_volts"},
             "R39_HIDDEN_GOLD_IN_INFERENCE_INPUT")
        cid=c["case_id"]
        need(isinstance(cid,str) and re.fullmatch("[0-9a-f]{32}",cid)
             and cid not in ids,"R39_CASE_ID_INVALID")
        ids.add(cid)
        rows=c["early_voltage_trace_hours_volts"]
        need(isinstance(rows,list) and len(rows)==EARLY,
             "R39_NO_LATE_LABELS_IN_QUESTION_TRANSPORT")
        for i,row in enumerate(rows):
            need(isinstance(row,list) and len(row)==2 and
                 all(type(v) in (int,float) and math.isfinite(v) for v in row)
                 and abs(row[0]-i/60)<1e-5 and 2<=row[1]<=5.2,
                 "R39_UNEXPECTED_EARLY_TIME_OR_VOLTAGE")
    return q

def seal(pack,salt,config):
    properties=validate_private(pack);validate_config(config)
    need(isinstance(salt,bytes) and len(salt)>=32,"R39_INSUFFICIENT_ENTROPY")
    qs=questions_from_private(pack,salt,config)
    receipt={
        "schema":SEAL_SCHEMA,
        "private_pack_salted_commitment_sha256":digest(
            b"JANUS-R39-PRIVATE-PACK\0"+salt+canonical(pack)),
        "questions_sha256":qs["questions_sha256"],
        "frozen_config_sha256":sha(config),
        "source_model_file_blob_sha1":SOURCE_BLOB_SHA,
        "frozen_formula_library_selection":{"candidate":CANDIDATE,"baseline":BASELINE},
        "case_count":properties["device_count"],
        "private_source_study_count":properties["study_count"],
        "private_chemistry_count":properties["chemistry_count"],
        "private_salt_is_public":False,
        "raw_future_labels_are_public":False,
        "external_identity_signature_verification":False,
        "independent_timestamp_exists":False,
        "scientific_admission":"HOLD"
    }
    receipt["receipt_sha256"]=sha(receipt)
    return receipt,qs

def offline_inference(q,config):
    validate_config(config);validate_questions(q,config);verify_source_code()
    out=[]
    for case in q["cases"]:
        early=[(float(t),float(v)) for t,v in
               case["early_voltage_trace_hours_volts"]]
        baseline_fit=fit_on_early(early,BASELINE)
        candidate_fit=fit_new(early,CANDIDATE)
        future_times=[minute/60 for minute in q["forecast_minute_indices"]]
        row={
          "case_id":case["case_id"],
          "candidate_volts":[new_predict(candidate_fit,t) for t in future_times],
          "baseline_volts":[predict_2rc(baseline_fit,t) for t in future_times],
        }
        out.append(row)
    pred={
      "schema":PRED_SCHEMA,
      "questions_sha256":q["questions_sha256"],
      "frozen_config_sha256":sha(config),
      "source_code_git_blob_sha1":SOURCE_BLOB_SHA,
      "candidate_model":CANDIDATE,
      "baseline_model":BASELINE,
      "case_count":len(out),
      "predictions":out,
      "actual_real_early_window_model_fits":2*len(out),
      "any_future_measurements_read":False,
      "neural_weights_updated":False,
      "scientific_admission":"HOLD"
    }
    pred["prediction_receipt_sha256"]=sha(pred)
    return pred

def validate_predictions(pred,q,config):
    need(isinstance(pred,dict) and set(pred)=={
        "schema","questions_sha256","frozen_config_sha256",
        "source_code_git_blob_sha1","candidate_model","baseline_model",
        "case_count","predictions","actual_real_early_window_model_fits",
        "any_future_measurements_read","neural_weights_updated",
        "scientific_admission","prediction_receipt_sha256"},
        "R39_PREDICTION_SCHEMA_UNTRUSTED")
    need(pred["schema"]==PRED_SCHEMA
         and pred["questions_sha256"]==q["questions_sha256"]
         and pred["frozen_config_sha256"]==sha(config)
         and pred["source_code_git_blob_sha1"]==SOURCE_BLOB_SHA
         and pred["candidate_model"]==CANDIDATE
         and pred["baseline_model"]==BASELINE
         and pred["any_future_measurements_read"] is False
         and pred["neural_weights_updated"] is False
         and pred["scientific_admission"]=="HOLD",
         "R39_FROZEN_PREDICTION_CONTRACT_MISMATCH")
    need(pred["prediction_receipt_sha256"]==sha({
       k:v for k,v in pred.items() if k!="prediction_receipt_sha256"}),
       "R39_PREDICTIONS_TAMPERED_SHA")
    rows=pred["predictions"]
    need(isinstance(rows,list) and len(rows)==q["case_count"]
         and pred["case_count"]==len(rows)
         and pred["actual_real_early_window_model_fits"]==2*len(rows),
         "R39_LOST_OR_EXTRA_PREDICTIONS")
    if sorted(r["case_id"] for r in rows)!=sorted(
       c["case_id"] for c in q["cases"]):
        raise ValueError("R39_PREDICTION_SET_CHANGED")
    for row in rows:
        need(isinstance(row,dict) and set(row)=={
            "case_id","candidate_volts","baseline_volts"
        },"R39_PREDICTION_UNEXPECTED_EXTRA_FIELD")
        for k in ("candidate_volts","baseline_volts"):
            vals=row[k]
            need(isinstance(vals,list) and len(vals)==FUTURE
                 and all(type(v) in (int,float) and math.isfinite(v)
                         and 0<v<6 for v in vals),
                 "R39_BAD_FUTURE_PREDICTIONS")
    return pred

def bootstrap_device_gain(pairs):
    """Exploratory device-level resampling, NOT proof of independence."""
    rng=random.Random(20261111)
    n=len(pairs)
    stats=[]
    for _ in range(1000):
        draw=[pairs[rng.randrange(n)] for _ in range(n)]
        base=sum(x[0] for x in draw)/n
        candidate=sum(x[1] for x in draw)/n
        stats.append((base-candidate)/base)
    stats.sort()
    return [stats[25],stats[975]]

def score_private(pack,salt,seal_receipt,q,pred,config):
    details=validate_private(pack);validate_config(config)
    ref,expected_questions=seal(pack,salt,config)
    need(seal_receipt==ref,"R39_INDEPENDENT_SEAL_CHANGED_OR_WRONG_SALT")
    need(q==expected_questions,"R39_QUESTIONS_CHANGED_AFTER_SEAL")
    validate_predictions(pred,q,config)
    bycase={r["case_id"]:r for r in pred["predictions"]}
    rows=[]
    for dev in pack["devices"]:
        cid=pseudonym(dev,salt)
        predrow=bycase[cid]
        truth=[v for t,v in dev["trace"][EARLY:]]
        need(len(truth)==FUTURE,"R39_GOLD_LENGTH_MISMATCH")
        candidate_err=[abs(v-t) for v,t in
                       zip(predrow["candidate_volts"],truth)]
        baseline_err=[abs(v-t) for v,t in
                      zip(predrow["baseline_volts"],truth)]
        a=sum(candidate_err)/FUTURE
        b=sum(baseline_err)/FUTURE
        need(b>1e-10,"R39_DEGENERATE_BASELINE_MAE")
        rows.append({
            "case_id":cid,
            "study":dev["source_study_id"],
            "chemistry":dev["chemistry"],
            "candidate_mae":a,
            "baseline_mae":b,
            "paired_gain":(b-a)/b
        })
    means=lambda field:sum(x[field] for x in rows)/len(rows)
    avg_a=means("candidate_mae");avg_b=means("baseline_mae")
    gain=(avg_b-avg_a)/avg_b
    wins=sum(x["candidate_mae"]<x["baseline_mae"] for x in rows)
    worst=max((x["candidate_mae"]-x["baseline_mae"])/
              x["baseline_mae"] for x in rows)
    study_gains={}
    for study in sorted({x["study"] for x in rows}):
        sub=[x for x in rows if x["study"]==study]
        b=sum(x["baseline_mae"] for x in sub)/len(sub)
        a=sum(x["candidate_mae"] for x in sub)/len(sub)
        study_gains[study]=(b-a)/b
    gate=config["metric_gates"]
    engineering_gate=(
        gain>=gate["positive_candidate_mean_relative_gain_min"] and
        wins/len(rows)>=gate["minimum_win_fraction"] and
        worst<=gate["max_worst_device_MAE_regression_fraction"] and
        all(x>0 for x in study_gains.values())
    )
    # PRIVATE study/device identities and raw gold are never in this summary.
    safe={
      "schema":SCORE_SCHEMA,
      "external_private_pack_salted_sha256":seal_receipt[
          "private_pack_salted_commitment_sha256"],
      "source_frozen_config_sha256":sha(config),
      "seal_receipt_sha256":seal_receipt["receipt_sha256"],
      "questions_sha256":q["questions_sha256"],
      "predictions_sha256":pred["prediction_receipt_sha256"],
      "device_count":details["device_count"],
      "source_study_count":details["study_count"],
      "chemistry_count":details["chemistry_count"],
      "device_weighted_candidate_MAE_volts":avg_a,
      "device_weighted_baseline_MAE_volts":avg_b,
      "candidate_relative_MAE_improvement":gain,
      "devices_better":wins,
      "fraction_devices_better":wins/len(rows),
      "worst_device_MAE_regression_fraction":max(0,worst),
      "source_studies_with_mean_gain":sum(x>0 for x in study_gains.values()),
      "exploratory_device_bootstrap_95pct_gain_interval":
          bootstrap_device_gain([(x["baseline_mae"],x["candidate_mae"])
                                 for x in rows]),
      "preregistered_engineering_thresholds_pass":engineering_gate,
      "actual_source_provenance_and_custodian_independence_cryptographically_verified":False,
      "real_external_custodian_identity_verified":False,
      "real_external_signature_checked":False,
      "external_expert_scientific_review_complete":False,
      "independent_true_blind_established":False,
      "neural_weights_trained":False,
      "automatic_formula_admission":False,
      "scientific_admission":"HOLD",
      "production_promotion":False,
    }
    safe["receipt_sha256"]=sha(safe)
    return safe

def write_new(path,obj):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open("x",encoding="utf8") as f:
        json.dump(obj,f,sort_keys=True,ensure_ascii=False,indent=2,
                  allow_nan=False)
        f.write("\n")

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--config",default=str(CONFIG_PATH))
    sub=cli.add_subparsers(dest="phase",required=True)
    s=sub.add_parser("seal")
    s.add_argument("--private-pack",required=True)
    s.add_argument("--salt-file",required=True)
    s.add_argument("--sealed-output",required=True)
    s.add_argument("--questions-output",required=True)
    i=sub.add_parser("infer")
    i.add_argument("--questions-only",required=True)
    i.add_argument("--predictions-output",required=True)
    f=sub.add_parser("score")
    f.add_argument("--private-pack",required=True)
    f.add_argument("--salt-file",required=True)
    f.add_argument("--sealed",required=True)
    f.add_argument("--questions-only",required=True)
    f.add_argument("--predictions",required=True)
    f.add_argument("--summary-output",required=True)
    args=cli.parse_args()
    config=validate_config(load_json(args.config))
    if args.phase=="seal":
        pack=load_json(args.private_pack)
        salt=private_salt(args.salt_file)
        receipt,q=seal(pack,salt,config)
        write_new(args.sealed_output,receipt)
        write_new(args.questions_output,q)
        print("R39_CUSTODIAN_PRIVATE_SHA_COMMITMENT_AND_EARLY_ONLY_QUESTIONS_WRITTEN")
    elif args.phase=="infer":
        q=load_json(args.questions_only)
        pred=offline_inference(q,config)
        write_new(args.predictions_output,pred)
        print(json.dumps({"models_evaluated":[CANDIDATE,BASELINE],
                          "case_count":len(pred["predictions"]),
                          "gold_read":False,"scientific_admission":"HOLD"}))
    else:
        pack=load_json(args.private_pack)
        q=load_json(args.questions_only)
        sealed=load_json(args.sealed)
        p=load_json(args.predictions)
        salt=private_salt(args.salt_file)
        report=score_private(pack,salt,sealed,q,p,config)
        write_new(args.summary_output,report)
        print(json.dumps({
            "engineering_thresholds_pass":report["preregistered_engineering_thresholds_pass"],
            "scientific_admission":"HOLD",
            "external_signature_verified":False
        },sort_keys=True))

if __name__=="__main__":
    main()
