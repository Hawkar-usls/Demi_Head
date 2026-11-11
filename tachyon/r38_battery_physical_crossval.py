"""TACHYON R3.8: 8-battery public LOBO physical-relaxation model benchmark.

Runs on the *same* CC BY4 8-battery data as R3.7, all files Git-blob-pinned.
This retrospective battery-group CV is NOT an independent external blind test.
No model weights trained, no hidden scientific holdout collected.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from itertools import combinations

from tachyon.r37_real_ocv_evaluator import (
    need,sha,manifest_check,official_fetch,parse_csv,
    load_role_files,eval_trace,MODEL_TYPES as OLD_MODELS,
    TRAIN,VALIDATION,TEST,fit_on_early,predict as old_predict
)
# Derivative of empirically motivated families; a diffusion-like tail is not
# a full PDE solution. No arbitrary expressions or imported code from sources.
GROUPS=TRAIN+VALIDATION+TEST
BASELINES=("constant_last","single_exp","double_exp")
CHALLENGERS=("triple_exp","stretched_exp","diffusion_tail")
ALL_MODELS=BASELINES+CHALLENGERS
TAUS3=(.08,.25,.8,2.,6.,16.,48.)
STRETCH_BETAS=(.4,.6,.8,1.,1.2)
TAUS=(.05,.12,.25,.5,1.,2.,4.,8.,16.,32.,64.)
SCHEMA="janus.tachyon.r38.battery_groups_cross_validation_v1"
RESULT="janus.tachyon.r38.8group_real_battery_lobo_result.v1"

def verify_config(conf):
    need(conf.get("schema")==SCHEMA
         and conf.get("battery_groups")==list(GROUPS)
         and conf.get("model_families",{}).get("incumbents")==list(BASELINES)
         and conf.get("model_families",{}).get("challengers")==list(CHALLENGERS)
         and conf.get("candidate_selection",{}).get("early_voltage_fit_hours")==4
         and conf.get("candidate_selection",{}).get("challenger_minimum_inner_relative_gain")==.05
         and conf.get("candidate_selection",{}).get("challenger_minimum_outer_relative_gain")==.05
         and conf.get("candidate_selection",{}).get("independent_reproducible_gain_threshold_batteries")==6
         and conf.get("governance",{}).get("neural_retraining_permitted") is False
         and conf.get("governance",{}).get("automatic_formula_promotion") is False
         and conf.get("governance",{}).get("scientific_admission")=="HOLD",
         "R38_CONFIG_OR_SCIENTIFIC_GATE_DRIFT")
    return conf

def verify_custodian_slot(c):
    need(c.get("schema")=="janus.tachyon.r38.external_custodian_control_slot_v1"
         and c.get("status")=="NOT_PROVIDED_BY_INDEPENDENT_LAB"
         and c.get("scientific_admission")=="HOLD"
         and c.get("private_correct_answers_in_GitHub") is False
         and c.get("independent_external_holdout_completed") is False
         and all(c.get(k) is None for k in (
             "independent_custodian_id","independent_identity_signature",
             "new_original_dataset_doi","source_new_device_ids_sha256_commitment",
             "private_gold_source_manifest_sha256","private_question_only_bundle_sha256",
             "frozen_candidate_model_selection_sha256","blinded_result_signature",
             "independent_timestamp_receipt")),
         "R38_EXTERNAL_CUSTODIAN_NOT_CONNECTED")
    return c

def invert(a,b):
    """Small ridge linear least squares, max 4 coefficients."""
    n=len(a)
    need(n>20 and n==len(b) and 1<=len(a[0])<=4,
         "R38_FIT_SHAPE")
    k=len(a[0])
    need(all(len(row)==k for row in a),"R38_FIT_RAGGED")
    # Scale columns before solving to suppress rank loss on multi-exponentials.
    norms=[math.sqrt(sum(row[j]**2 for row in a)) for j in range(k)]
    need(all(z>1e-8 for z in norms),"R38_ILL_CONDITIONED_MODEL")
    z=[[row[j]/norms[j] for j in range(k)] for row in a]
    lam=1e-6
    mat=[[sum(v[i]*v[j] for v in z)+(lam if i==j else 0.)
          for j in range(k)] for i in range(k)]
    bb=[sum(v[i]*y for v,y in zip(z,b)) for i in range(k)]
    aug=[mat[i]+[bb[i]] for i in range(k)]
    for j in range(k):
        pivot=max(range(j,k),key=lambda i:abs(aug[i][j]))
        aug[j],aug[pivot]=aug[pivot],aug[j]
        need(abs(aug[j][j])>1e-12,"R38_RANK_DEFICIENT")
        denom=aug[j][j]
        for t in range(j,k+1):aug[j][t]/=denom
        for i in range(k):
            if i==j:continue
            factor=aug[i][j]
            for t in range(j,k+1):aug[i][t]-=factor*aug[j][t]
    coefs=[aug[j][k]/norms[j] for j in range(k)]
    need(all(math.isfinite(v) and abs(v)<100 for v in coefs),
         "R38_UNSTABLE_COEFFICIENTS")
    return coefs

def basis(model,t,params):
    need(0<=t<=24.00001,"R38_TIME_DOMAIN")
    if model=="triple_exp":
        need(len(params)==3 and 0<params[0]<params[1]<params[2],
             "R38_RC_TIME_CONSTANT_ORDER")
        return [1.]+[math.exp(-t/tau) for tau in params]
    if model=="stretched_exp":
        tau,beta=params
        need(tau>0 and .3<=beta<=1.3,"R38_STRETCH_DOMAIN")
        return [1.,math.exp(-((t/tau)**beta))]
    if model=="diffusion_tail":
        tau=params[0]
        need(tau>0,"R38_DIFFUSION_TIME_DOMAIN")
        # Tail approximately t^-1/2; heuristic, NOT exact Fick PDE
        return [1.,1./math.sqrt(1.+t/tau)]
    raise ValueError("R38_UNRECOGNIZED_MODEL")

def param_grid(model):
    if model=="triple_exp":
        return combinations(TAUS3,3)
    if model=="stretched_exp":
        return ((tau,beta) for tau in TAUS for beta in STRETCH_BETAS)
    if model=="diffusion_tail":
        return ((tau,) for tau in TAUS)
    raise ValueError("R38_UNSUPPORTED_GRID")

def fit_new(points,model):
    need(model in CHALLENGERS,"R38_NEW_MODEL_ONLY")
    early=[(t,y) for t,y in points if t<=4.+1e-9]
    need(220<=len(early)<=242,"R38_EARLY_DATA_REQUIRED")
    best=None
    for params in param_grid(model):
        xs=[basis(model,t,params) for t,y in early]
        try:
            coefs=invert(xs,[y for t,y in early])
        except ValueError:
            continue
        residual=[sum(x*c for x,c in zip(feat,coefs))-y
                  for feat,(t,y) in zip(xs,early)]
        err=math.sqrt(sum(z*z for z in residual)/len(residual))
        # Fixed early-complexity penalty to discourage 3RC overfit
        cost=err+(0.00015 if len(coefs)>=4 else 0.)
        candidate=(cost,tuple(params),coefs,err)
        if best is None or (candidate[0],candidate[1])<(best[0],best[1]):
            best=candidate
    need(best is not None,"R38_ALL_CANDIDATES_UNFIT")
    return {"name":model,"params":list(best[1]),"coefficients":best[2],
            "fit_rmse_early_volts":best[3]}

def new_predict(fit,t):
    val=sum(a*b for a,b in zip(
        basis(fit["name"],t,fit["params"]),fit["coefficients"]))
    need(math.isfinite(val) and 0<val<6,"R38_OUT_OF_RANGE_MODEL_PREDICTION")
    return val

def per_trace(points):
    later=[(t,y) for t,y in points if t>4.+1e-9]
    need(len(later)==1200,"R38_STRICT_20H_TEST_WINDOW")
    output=eval_trace(points)
    # r37 already implements three incumbents; re-evaluate all 3 for the
    # same model-fitting protocol and preserve a paired per-trace record.
    for model in CHALLENGERS:
        try:
            fit=fit_new(points,model)
            delta=[new_predict(fit,t)-y for t,y in later]
            output[model]={
                "forecast_MAE_V":sum(abs(e) for e in delta)/len(delta),
                "forecast_RMSE_V":math.sqrt(sum(e*e for e in delta)/len(delta)),
                "forecast_count":len(delta),
                "fit_failed":False,
            }
        except ValueError as exc:
            # Refuse to silently omit any failed candidate. It remains in
            # metrics as unavailable with a structured reason.
            output[model]={
                "forecast_MAE_V":None,"forecast_RMSE_V":None,
                "forecast_count":len(later),
                "fit_failed":True,"failure_reason":str(exc)[:120]
            }
    return {name:output[name] for name in ALL_MODELS}

def source_data(source_manifest,fetch):
    """Read original source group files; all eight already public in R3.7."""
    manifest_check(source_manifest)
    all_rows=[];files=[]
    for item in sorted(source_manifest["input_files"],key=lambda i:i["path"]):
        raw=fetch(item)
        # parse_csv rejects any raw-byte source mismatch using pinned Git SHA.
        traces=parse_csv(raw,item)
        files.append({
            "path":item["path"],"battery_group":item["battery_group"],
            "original_git_blob_sha1":item["github_blob_sha1"],
            "raw_sha256":hashlib.sha256(raw).hexdigest(),
            "bytes":len(raw),"number_traces":len(traces)
        })
        for column,points in traces:
            all_rows.append({
              "battery":item["battery_group"],
              "column":column,
              "scores":per_trace(points)
            })
    need(len(files)==16 and len(all_rows)==30,"R38_EXPECT_30_REAL_TRACES")
    need(set(x["battery"] for x in all_rows)==set(GROUPS),
         "R38_MISSING_BATTERY_GROUP")
    return all_rows,files

def group_scores(rows):
    out={}
    for group in GROUPS:
        pieces=[r for r in rows if r["battery"]==group]
        need(pieces,"R38_EMPTY_BATTERY_GROUP")
        out[group]={}
        for model in ALL_MODELS:
            nums=[r["scores"][model]["forecast_MAE_V"] for r in pieces]
            out[group][model]=sum(nums)/len(nums) if all(
                x is not None for x in nums) else None
    return out

def avg_group_scores(group_maes,groups,model):
    vals=[group_maes[b][model] for b in groups]
    return sum(vals)/len(vals) if all(x is not None for x in vals) else math.inf

def score_public_lobo(group_maes):
    need(set(group_maes)==set(GROUPS),"R38_BATTERY_GROUP_DRIFT")
    folds=[]
    for holdout in GROUPS:
        inner=[x for x in GROUPS if x!=holdout]
        baseline=min(BASELINES,key=lambda m:(avg_group_scores(
            group_maes,inner,m),m))
        challenger=min(CHALLENGERS,key=lambda m:(avg_group_scores(
            group_maes,inner,m),m))
        base_inner=avg_group_scores(group_maes,inner,baseline)
        challenger_inner=avg_group_scores(group_maes,inner,challenger)
        train_gain=(base_inner-challenger_inner)/base_inner
        selected=(challenger if train_gain>=.05 else baseline)
        test_base=group_maes[holdout][baseline]
        test_selected=group_maes[holdout][selected]
        need(test_base is not None and test_selected is not None,
             "R38_OUTER_FOLD_UNAVAILABLE")
        fold_gain=(test_base-test_selected)/test_base
        folds.append({
            "heldout_battery":holdout,
            "selection_batteries":inner,
            "best_baseline_selected_on_inner_groups":baseline,
            "best_challenger_selected_on_inner_groups":challenger,
            "selected_model":selected,
            "challenger_selected":selected==challenger,
            "inner_relative_MAE_gain":train_gain,
            "outer_MAE_baseline_V":test_base,
            "outer_MAE_selected_V":test_selected,
            "outer_relative_MAE_gain":fold_gain,
            "heldout_battery_beaten_baseline":fold_gain>.05,
            "candidate_challenger_beats_baseline":selected==challenger
                                                and fold_gain>.05
        })
    return folds

def run(source_manifest_path,config_path,custodian_path,outdir,fetch=official_fetch):
    conf=verify_config(json.loads(Path(config_path).read_text()))
    cust=verify_custodian_slot(json.loads(Path(custodian_path).read_text()))
    original=json.loads(Path(source_manifest_path).read_text())
    manifest_check(original)
    output=Path(outdir)
    need(not output.exists() or not any(output.iterdir()),
         "R38_APPEND_ONLY_NO_OVERWRITE")
    rows,receipts=source_data(original,fetch)
    scores=group_scores(rows)
    folds=score_public_lobo(scores)
    selected_challenger=[f for f in folds if f["challenger_selected"]]
    challenger_success=[f for f in folds if f["candidate_challenger_beats_baseline"]]
    # Posthoc safety annotation added AFTER reviewing the FIRST public R3.8
    # run. This is explicitly NOT retroactively a preregistered hypothesis test.
    regressions=[
      {"battery":f["heldout_battery"],
       "selected_model":f["selected_model"],
       "relative_error_increase_pct":(-100.*f["outer_relative_MAE_gain"])}
      for f in folds if f["outer_relative_MAE_gain"]<0
    ]
    worst_regression=max(
      (x["relative_error_increase_pct"] for x in regressions),default=0.
    )
    worst_group=(max(regressions,key=lambda x:x["relative_error_increase_pct"])["battery"]
                 if regressions else None)
    # These alarms cannot make a candidate pass; they only document risk.
    posthoc_safety_audit={
      "review_trigger":"Observed negative results on initial public 8-battery R3.8 run",
      "was_preregistered_before_initial_public_result":False,
      "is_approval_metric":False,
      "devices_with_worse_MAE_than_selected_baseline":regressions,
      "worst_device_relative_MAE_increase_pct":worst_regression,
      "worst_device":worst_group,
      "descriptive_regression_alert_over_10_pct":worst_regression>10.,
      "independent_prospective_evidence_still_required":True,
    }
    # No independently sealed new source: ALWAYS HOLD despite any LOBO gain.
    summary={
      "schema":RESULT,
      "source_original_doi":original["original_dataset_doi"],
      "source_license":original["source_license"],
      "source_author_attribution":original["source_attribution"],
      "public_data_r37_reused_no_true_blind":True,
      "source_manifest_sha256":sha(original),
      "R38_pre_registered_configuration_sha256":sha(conf),
      "external_custodian_status_sha256":sha(cust),
      "external_independent_control_set_status":"NOT_PROVIDED_BY_INDEPENDENT_LAB",
      "num_independent_battery_devices_held_out_per_fold":1,
      "num_public_lobo_folds":len(folds),
      "num_distinct_public_device_groups_evaluated":len(GROUPS),
      "total_real_raw_source_files":len(receipts),
      "total_real_ocv_voltage_curves":len(rows),
      "original_source_file_integrity_receipts":receipts,
      "battery_group_mean_trace_MAE_volts":scores,
      "all_model_families":list(ALL_MODELS),
      "lobo_fold_selection_and_test_results":folds,
      "challenger_selected_in_n_folds":len(selected_challenger),
      "challenger_beats_baseline_n_folds":len(challenger_success),
      "pre_registered_public_crossval_device_consistency_threshold":6,
      "public_retro_crossval_challenger_consistency_pass":
         len(challenger_success)>=6,
      "posthoc_safety_audit_not_preregistered":posthoc_safety_audit,
      "physical_new_discovery_verified":False,
      "all_new_models_are_existing_or_empirical_relaxation_approximations":True,
      "independent_external_custodian_connected":False,
      "new_independent_experimental_dataset_evaluated":False,
      "model_neural_weights_changed":False,
      "real_measurements_used_for_neural_gradient":False,
      "automatic_formula_or_weight_promotion":False,
      "scientific_admission":"HOLD",
      "research_only":True
    }
    summary["receipt_sha256"]=sha(summary)
    output.mkdir(parents=True,exist_ok=True)
    p=output/"r38_public_eight_battery_cross_validation.json"
    p.write_text(json.dumps(summary,sort_keys=True,indent=2,
                            ensure_ascii=False)+"\n",encoding="utf8")
    return summary

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-manifest",required=True)
    p.add_argument("--config",required=True)
    p.add_argument("--external-custodian",required=True)
    p.add_argument("--output-dir",required=True)
    a=p.parse_args()
    result=run(a.source_manifest,a.config,a.external_custodian,a.output_dir)
    print(json.dumps({
        "eight_battery_groups":result["num_distinct_public_device_groups_evaluated"],
        "all_16_source_files_sha_verified":result["total_real_raw_source_files"],
        "real_traces":result["total_real_ocv_voltage_curves"],
        "challenger_selected_folds":result["challenger_selected_in_n_folds"],
        "challenger_win_folds":result["challenger_beats_baseline_n_folds"],
        "public_lobo_consistency_pass":
            result["public_retro_crossval_challenger_consistency_pass"],
        "external_custodian":"NOT_PROVIDED",
        "neural_retraining":False,
        "scientific_admission":"HOLD"
    },sort_keys=True))

if __name__=="__main__":main()
