"""TACHYON-R3.10: early-only reliability gate for frozen R3.8 formulas.

Research-only, RETROSPECTIVE, public 8-device re-analysis. Every decision on
the held-out battery uses only its first four hours and a risk threshold
selected using the OTHER 7 battery groups. Future observations are read by
a separate scorer after early-only model predictions have been generated.

Not a conformal guarantee or calibrated probability, and not R3.9 blind.
"""
from __future__ import annotations

from collections import defaultdict
import argparse
import hashlib
import json
import math
from pathlib import Path

from tachyon.r37_real_ocv_evaluator import (
    need, sha, manifest_check, parse_csv, official_fetch, fit_on_early,
    predict as incumbent_predict
)
from tachyon.r38_battery_physical_crossval import (
    GROUPS, fit_new, new_predict
)

SCHEMA="janus.tachyon.r310.public_early_only_reliability_research.v1"
OUT_SCHEMA="janus.tachyon.r310.device_heldout_risk_gate_result.v1"
FIXED_CODE_SHA1={
    "tachyon/r38_battery_physical_crossval.py":"0f2cbb26e0a827d86b71d8e88798dfe348558697",
    "tachyon/r37_real_ocv_evaluator.py":"9dd07cc757e6441c0ee94a3bf3fa16c616dbc5ce"
}
THRESHOLDS=(0.,.002,.005,.01,.02,.04,.08,.16)
CANDIDATE="diffusion_tail"
INCUMBENT="double_exp"
EARLY_N=241
FUTURE_N=1200
EARLY_HOURS=4.
MAX_CAL_REGRESSION=.10
MIN_COVERAGE=.15
MIN_CAL_GAIN=.0

def git_blob_sha1(p):
    raw=Path(p).read_bytes()
    return hashlib.sha1(
        b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw,
        usedforsecurity=False
    ).hexdigest()

def verify_frozen_code():
    root=Path(__file__).resolve().parents[1]
    for name,expect in FIXED_CODE_SHA1.items():
        need(git_blob_sha1(root/name)==expect,
             "R310_DEPENDENT_R38_R37_CODE_BYTES_CHANGED")
    return True

def validate_config(o):
    need(isinstance(o,dict) and o.get("schema")==SCHEMA
         and o.get("scientific_status")=="HOLD"
         and o.get("test_class")==
         "PUBLIC_RETROSPECTIVE_R38_REUSED_8_BATTERIES_NOT_INDEPENDENT_BLIND"
         and o.get("battery_groups")==list(GROUPS)
         and o.get("r38_original_code_git_blob_sha1")==
             FIXED_CODE_SHA1["tachyon/r38_battery_physical_crossval.py"]
         and o.get("r37_original_code_git_blob_sha1")==
             FIXED_CODE_SHA1["tachyon/r37_real_ocv_evaluator.py"],
         "R310_MANIFEST_OR_FROZEN_RESEARCH_IDENTITY")
    p=o.get("model_policy",{})
    need(p.get("candidate")==CANDIDATE and p.get("incumbent")==INCUMBENT
         and p.get("early_points")==EARLY_N
         and p.get("hidden_future_points")==FUTURE_N
         and p.get("minimum_calibration_candidate_coverage")==MIN_COVERAGE
         and p.get("maximum_accepted_device_level_relative_regression")==
             MAX_CAL_REGRESSION
         and p.get("minimum_calibration_device_gain")==MIN_CAL_GAIN
         and p.get("choose_threshold_without_heldout_future_labels") is True,
         "R310_CALIBRATION_POLICY_DRIFT")
    g=o.get("governance",{})
    need(g.get("real_neural_training_authorized") is False
         and g.get("automatic_formula_update") is False
         and g.get("independent_r39_locked_and_unchanged") is True
         and g.get("new_future_blind_gold_used") is False
         and g.get("scientific_admission")=="HOLD",
         "R310_FALSE_SCIENCE_OR_LEARNING_PROMOTION")
    return o

def check_early(early):
    """This entire function receives ONLY 241 early (time, V) pairs."""
    need(isinstance(early,list) and len(early)==EARLY_N,
         "R310_EARLY_ONLY_241_POINTS_REQUIRED")
    for i,x in enumerate(early):
        need(isinstance(x,(list,tuple)) and len(x)==2
             and all(type(v) in (int,float) and math.isfinite(v) for v in x),
             "R310_INVALID_EARLY_ROW")
        t,v=x
        need(abs(t-i/60.)<1e-5 and 2.<=v<=5.2,
             "R310_EARLY_TIME_OR_PHYSICAL_VOLTAGE_REJECT")
    return [(float(t),float(v)) for t,v in early]

def evaluate_early_only(early):
    """Return deterministic gate features and both future model predictions.

    No future labels are accepted as an input. Never expose this function to
    a path that can mix test scores or raw future measurements.
    """
    early=check_early(early)
    incumbent_fit=fit_on_early(early,INCUMBENT)
    future_times=[i/60. for i in range(EARLY_N,EARLY_N+FUTURE_N)]
    base=[incumbent_predict(incumbent_fit,t) for t in future_times]
    # A physically invalid BASELINE is a genuine reason to abstain.
    need(all(math.isfinite(v) and 2<=v<=5.2 for v in base),
         "R310_BASELINE_FUTURE_EXTRAPOLATION_OUT_OF_SCOPE")
    early_inc_rmse=math.sqrt(sum(
        (incumbent_predict(incumbent_fit,t)-v)**2 for t,v in early
    )/len(early))
    try:
        challenger_fit=fit_new(early,CANDIDATE)
        cand=[new_predict(challenger_fit,t) for t in future_times]
        need(all(math.isfinite(v) and 2<=v<=5.2 for v in cand),
             "R310_CANDIDATE_FUTURE_EXTRAPOLATION_OUT_OF_SCOPE")
        early_cand_rmse=math.sqrt(sum(
            (new_predict(challenger_fit,t)-v)**2 for t,v in early
        )/len(early))
        denom=sum(v for t,v in early)/len(early)
        disagreement=sum(abs(a-b) for a,b in zip(base,cand))/FUTURE_N/denom
        score=disagreement+max(0.,early_cand_rmse-early_inc_rmse)/denom
        need(math.isfinite(score) and score>=0,"R310_INVALID_RISK_SCORE")
    except ValueError as exc:
        # A bad *optional* formula must not suppress a healthy 2RC forecast.
        return {
            "status":"CANDIDATE_UNSAFE_BASELINE_AVAILABLE",
            "candidate_failure_reason":str(exc)[:120],
            "risk_proxy":None,
            "early_incumbent_RMSE_V":early_inc_rmse,
            "early_candidate_RMSE_V":None,
            "normalized_model_disagreement":None,
            "incumbent_future_predictions":base,
            "candidate_future_predictions":None,
            "future_truth_read":False,
        }
    return {
        "status":"EARLY_ONLY_MODELS_COMPUTED",
        "risk_proxy":score,
        "candidate_failure_reason":None,
        "early_incumbent_RMSE_V":early_inc_rmse,
        "early_candidate_RMSE_V":early_cand_rmse,
        "normalized_model_disagreement":disagreement,
        "incumbent_future_predictions":base,
        "candidate_future_predictions":cand,
        "future_truth_read":False,
    }

def score_future(early_record, gold_future):
    """Only the later holdout evaluator receives the 1200 actual voltages."""
    need(isinstance(gold_future,list) and len(gold_future)==FUTURE_N
         and all(type(x) in (int,float) and math.isfinite(x)
                 and 2<=x<=5.2 for x in gold_future),
         "R310_INVALID_HIDDEN_FUTURE_VOLTAGE")
    def mae(x):
        return sum(abs(a-b) for a,b in zip(x,gold_future))/FUTURE_N
    return {"baseline_MAE_V":mae(early_record["incumbent_future_predictions"]),
            "candidate_MAE_V":(mae(early_record["candidate_future_predictions"])
              if early_record["candidate_future_predictions"] is not None
              else None)}

def audit_one_trace(points):
    need(isinstance(points,list) and len(points)==EARLY_N+FUTURE_N,
         "R310_FULL_SOURCE_TRACE_REQUIRED_FOR_OFFLINE_SCORER")
    early=[[t,v] for t,v in points[:EARLY_N]]
    try:
        early_model=evaluate_early_only(early)
    except ValueError as e:
        return {
            "status":"ABSTAIN_UNPHYSICAL_OR_UNRELIABLE_EARLY_SIGNAL",
            "abstention_reason":str(e)[:120],
            "risk_proxy":None,
            "baseline_MAE_V":None,
            "candidate_MAE_V":None
        }
    future=[v for t,v in points[EARLY_N:]]
    vals=score_future(early_model,future)
    return {
        "status":early_model["status"],
        "candidate_failure_reason":early_model["candidate_failure_reason"],
        "risk_proxy":early_model["risk_proxy"],
        "normalized_model_disagreement":
            early_model["normalized_model_disagreement"],
        "early_incumbent_RMSE_V":early_model["early_incumbent_RMSE_V"],
        "early_candidate_RMSE_V":early_model["early_candidate_RMSE_V"],
        **vals
    }

def threshold_score(rows,groups,threshold):
    """Training groups only; returns device-balanced selective policy metrics."""
    chosen=[r for r in rows if r["battery"] in groups]
    coverage_total=0;available=0
    bygroup=defaultdict(list)
    for r in chosen:
        a=r["features"]
        if a["status"] not in ("EARLY_ONLY_MODELS_COMPUTED",
                              "CANDIDATE_UNSAFE_BASELINE_AVAILABLE"):
            continue
        available+=1
        use_candidate=(a["status"]=="EARLY_ONLY_MODELS_COMPUTED"
                       and a["risk_proxy"]<=threshold)
        coverage_total+=int(use_candidate)
        bygroup[r["battery"]].append({
            "baseline":a["baseline_MAE_V"],
            "selected":a["candidate_MAE_V"] if use_candidate
                       else a["baseline_MAE_V"],
        })
    if available==0 or set(bygroup)!=set(groups):
        return {"admissible":False,"reason":"R310_CALIBRATION_MISSING_DEVICES"}
    pergroup={}
    for group,pieces in bygroup.items():
        b=sum(x["baseline"] for x in pieces)/len(pieces)
        selected=sum(x["selected"] for x in pieces)/len(pieces)
        need(b>0,"R310_DEGENERATE_CALIBRATION_BASELINE")
        pergroup[group]={
            "baseline_MAE_V":b,
            "selected_MAE_V":selected,
            "relative_gain":(b-selected)/b,
        }
    base=sum(v["baseline_MAE_V"] for v in pergroup.values())/len(pergroup)
    selected=sum(v["selected_MAE_V"] for v in pergroup.values())/len(pergroup)
    gain=(base-selected)/base
    coverage=coverage_total/available
    worst=max(-x["relative_gain"] for x in pergroup.values())
    admissible=(coverage>=MIN_COVERAGE
                and gain>MIN_CAL_GAIN
                and worst<=MAX_CAL_REGRESSION)
    return {
       "admissible":admissible,
       "device_equal_calibration_gain":gain,
       "worst_development_device_regression_fraction":max(0.,worst),
       "accepted_candidate_fraction":coverage,
       "included_development_device_count":len(pergroup),
    }

def calibrate_without_heldout(rows,heldout):
    """Threshold selection sees only seven OTHER development device groups."""
    need(heldout in GROUPS,"R310_HELDOUT_DEVICE_NOT_KNOWN")
    selected_groups=[b for b in GROUPS if b!=heldout]
    need(all(r["battery"]!=heldout for r in rows),
         "R310_TEST_BATTERY_LEAKS_TO_CALIBRATION")
    trials=[]
    for threshold in THRESHOLDS:
        item={"threshold":threshold,
              **threshold_score(rows,selected_groups,threshold)}
        trials.append(item)
    valid=[x for x in trials if x["admissible"]]
    if valid:
        best=max(valid,key=lambda x:(
            x["device_equal_calibration_gain"],
            -x["threshold"]))
        return {"threshold":best["threshold"],
                "candidate_allowed":True,
                "trials":trials,
                "reason":"R310_DEV_ONLY_CALIBRATED_RISK_ACCEPTANCE"}
    return {"threshold":None,"candidate_allowed":False,"trials":trials,
            "reason":"R310_NO_THRESHOLD_WITH_DEV_GAIN_AND_WORST_RISK"}

def decide(early_features,calibration):
    """No actual future labels, heldout device ID or score is an argument."""
    if early_features["status"]=="CANDIDATE_UNSAFE_BASELINE_AVAILABLE":
        return "FALLBACK_DOUBLE_EXP"
    if early_features["status"]!="EARLY_ONLY_MODELS_COMPUTED":
        return "ABSTAIN"
    if calibration["candidate_allowed"] and (
        early_features["risk_proxy"]<=calibration["threshold"]):
        return "CANDIDATE_DIFFUSION_TAIL"
    return "FALLBACK_DOUBLE_EXP"

def read_public_sources(source,fetch):
    manifest_check(source);verify_frozen_code()
    rows=[];receipt=[]
    for entry in sorted(source["input_files"],key=lambda x:x["path"]):
        raw=fetch(entry)
        traces=parse_csv(raw,entry)  # rejects altered original file bytes
        receipt.append({
            "path":entry["path"],
            "battery_group":entry["battery_group"],
            "git_blob_sha1":entry["github_blob_sha1"],
            "actual_raw_sha256":hashlib.sha256(raw).hexdigest(),
            "raw_bytes":len(raw),"traces":len(traces),
        })
        for name,points in traces:
            rows.append({
                "battery":entry["battery_group"],
                "column":name,
                "features":audit_one_trace(points),
            })
    need(len(receipt)==16 and len(rows)==30,
         "R310_EXPECT_16_ORIGINAL_FILES_30_TRACES")
    return rows,receipt

def heldout_audit(rows,heldout):
    """Fold outcome calculated AFTER calibration and early-only decision."""
    cal=calibrate_without_heldout(
        [r for r in rows if r["battery"]!=heldout],heldout)
    target=[r for r in rows if r["battery"]==heldout]
    need(target,"R310_NO_HELDOUT_TRACES")
    scored=[];actions=defaultdict(int)
    for row in target:
        f=row["features"]
        action=decide(f,cal)
        actions[action]+=1
        if action=="ABSTAIN":
            scored.append({
                "trace":row["column"],"action":action,
                "risk_proxy":None,
                "baseline_MAE_V":None,"selected_MAE_V":None
            })
            continue
        chosen=(f["candidate_MAE_V"] if action=="CANDIDATE_DIFFUSION_TAIL"
                else f["baseline_MAE_V"])
        scored.append({
          "trace":row["column"],"action":action,
          "risk_proxy":f["risk_proxy"],
          "baseline_MAE_V":f["baseline_MAE_V"],
          "selected_MAE_V":chosen,
          "raw_candidate_MAE_V":f["candidate_MAE_V"]
        })
    comparable=[x for x in scored if x["action"]!="ABSTAIN"]
    if comparable:
        base=sum(x["baseline_MAE_V"] for x in comparable)/len(comparable)
        final=sum(x["selected_MAE_V"] for x in comparable)/len(comparable)
        gain=(base-final)/base if base else 0.
    else:base=final=gain=None
    return {
        "heldout_battery":heldout,
        "calibration_batteries":[b for b in GROUPS if b!=heldout],
        "threshold_selected_from_other_devices":cal["threshold"],
        "calibration_candidate_allowed":cal["candidate_allowed"],
        "calibration_reason":cal["reason"],
        "calibration_all_threshold_trials":cal["trials"],
        "num_heldout_traces":len(target),
        "num_abstentions":actions["ABSTAIN"],
        "num_baseline_fallback":actions["FALLBACK_DOUBLE_EXP"],
        "num_candidate_used":actions["CANDIDATE_DIFFUSION_TAIL"],
        "selected_MAE_V":final,
        "baseline_MAE_V":base,
        "selected_relative_gain":gain,
        "regression_over_10pct":bool(gain is not None and gain<-.10),
        "per_trace_action_audit":scored,
        "past_public_heldout_is_not_independent_blind":True,
        "science_admission":"HOLD",
    }

def run(source_manifest_path,config_path,outdir,fetch=official_fetch):
    config=validate_config(json.loads(Path(config_path).read_text()))
    source=json.loads(Path(source_manifest_path).read_text())
    manifest_check(source)
    out=Path(outdir)
    need(not out.exists() or not any(out.iterdir()),
         "R310_APPEND_ONLY_REFUSE_OVERWRITE")
    rows,receipts=read_public_sources(source,fetch)
    folds=[heldout_audit(rows,b) for b in GROUPS]
    pergroup={r["heldout_battery"]:r for r in folds}
    baseline_battery={b:r["baseline_MAE_V"] for b,r in pergroup.items()}
    chosen_battery={b:r["selected_MAE_V"] for b,r in pergroup.items()}
    comparable=[b for b in GROUPS if chosen_battery[b] is not None]
    need(comparable,"R310_NO_EVALUABLE_BATTERIES")
    base=sum(baseline_battery[b] for b in comparable)/len(comparable)
    selected=sum(chosen_battery[b] for b in comparable)/len(comparable)
    gain=(base-selected)/base
    regressions=[r for r in folds if r["regression_over_10pct"]]
    summary={
       "schema":OUT_SCHEMA,
       "source_doi":source["original_dataset_doi"],
       "source_attribution":source["source_attribution"],
       "source_license":source["source_license"],
       "source_manifest_sha256":sha(source),
       "risk_policy_config_sha256":sha(config),
       "original_r37_r38_dependencies_sha_verified":True,
       "real_public_source_csv_SHA256_receipts":receipts,
       "raw_public_lab_voltage_series_stored_in_artifact":False,
       "source_file_count":len(receipts),
       "real_trace_count":len(rows),
       "distinct_public_battery_groups":len(GROUPS),
       "folds":folds,
       "candidate_accepted_traces_total":sum(x["num_candidate_used"] for x in folds),
       "strong_baseline_fallback_traces_total":sum(x["num_baseline_fallback"] for x in folds),
       "abstentions_total":sum(x["num_abstentions"] for x in folds),
       "equal_device_baseline_MAE_V":base,
       "equal_device_selective_MAE_V":selected,
       "equal_device_selective_relative_gain":gain,
       "batteries_with_more_than_10pct_regression":[
           r["heldout_battery"] for r in regressions],
       "worst_heldout_relative_MAE_regression":max(
            [max(0.,-(r["selected_relative_gain"] or 0.)) for r in folds],
            default=0.),
       "reliability_score_is_heuristic_not_calibrated_probability":True,
       "selection_uses_heldout_battery_future_labels":False,
       "prior_R38_results_were_seen_before_development":True,
       "public_retro_check_not_independent_blind":True,
       "r39_frozen_branch_changed":False,
       "r39_hidden_private_gold_used":False,
       "neural_weights_updated":False,
       "scientific_admission":"HOLD",
       "production_model_promotion":False,
       "policy_is_safe_for_production":False,
    }
    summary["receipt_sha256"]=sha(summary)
    out.mkdir(parents=True,exist_ok=True)
    p=out/"r310_public_early_only_reliability_audit.json"
    p.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,
                            indent=2)+"\n",encoding="utf8")
    return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-manifest",required=True)
    parser.add_argument("--config",required=True)
    parser.add_argument("--output-dir",required=True)
    a=parser.parse_args()
    res=run(a.source_manifest,a.config,a.output_dir)
    print(json.dumps({
       "source_files":res["source_file_count"],
       "traces":res["real_trace_count"],
       "candidate_traces":res["candidate_accepted_traces_total"],
       "fallback_traces":res["strong_baseline_fallback_traces_total"],
       "abstentions":res["abstentions_total"],
       "device_mean_gain":res["equal_device_selective_relative_gain"],
       "worst_device_regression":res["worst_heldout_relative_MAE_regression"],
       "scientific_admission":"HOLD"
    },sort_keys=True))

if __name__=="__main__":main()
