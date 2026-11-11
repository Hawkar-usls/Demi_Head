"""JANUS R3.7: real CC BY 4.0 battery voltage-relaxation forecast comparison.

NO neural weights updated. 16 original CSVs, each Git-blob pinned; test battery
groups downloaded ONLY AFTER a development-model choice is sealed to disk.
Self-selected public research evaluation is NOT independent external blinding.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, build_opener, HTTPRedirectHandler

SCHEMA="janus.tachyon.r37.real_ocv_group_holdout_v1"
RESULT_SCHEMA="janus.tachyon.r37.read_only_real_ocv_forecast_audit.v1"
MODEL_TYPES=("constant_last","single_exp","double_exp","log_relax","exp_plus_drift")
BASELINES=("constant_last","single_exp","double_exp")
CHALLENGERS=("log_relax","exp_plus_drift")
TAUS=(.05,.10,.20,.50,1.,2.,4.,8.,16.,32.,64.)
TAUS_FAST=(.05,.10,.25,.50,1.,2.)
TAUS_SLOW=(2.,4.,8.,16.,32.,64.)
TRAIN=("APR","BSE","SG","LG")
VALIDATION=("OEM","LI")
TEST=("AR","AU")
MAX_BYTES=120000
EARLY_HOURS=4.

def need(ok,msg):
    if not ok:raise ValueError(msg)

def canonical(x):
    return json.dumps(x,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf-8")

def sha(x):return hashlib.sha256(canonical(x)).hexdigest()

def manifest_check(m):
    need(m.get("schema")==SCHEMA
         and m.get("source_repo")=="BulyK47/battery-datasets"
         and m.get("source_license")=="CC BY 4.0"
         and m.get("scientific_admission",None) is None,
         "R37_SOURCE_MANIFEST_IDENTITY")
    p=m.get("experiment_pre_registration",{})
    need(p.get("train_batteries")==list(TRAIN)
         and p.get("validation_batteries")==list(VALIDATION)
         and p.get("test_batteries")==list(TEST)
         and p.get("per_trace_early_fit_window_hours")==EARLY_HOURS
         and p.get("parametric_models")==list(MODEL_TYPES)
         and p.get("model_structure_choice")==
             "VALIDATION_ONLY_NO_TEST_LOOK",
         "R37_GROUP_SPLIT_OR_MODEL_SELECTION_DRIFT")
    governance=m.get("governance",{})
    need(governance.get("neural_gradient_training_on_real_lab_data") is False
         and governance.get("require_independent_review_for_real_neural_training") is True,
         "R37_NEURAL_TRAINING_NOT_AUTHORIZED")
    s=m.get("rights_and_security",{})
    need(s.get("neural_weight_training_authorized") is False
         and s.get("neural_weight_auto_promotion") is False
         and s.get("scientific_admission")=="HOLD",
         "R37_NO_AUTO_PROMOTION")
    files=m.get("input_files")
    need(isinstance(files,list) and len(files)==16,
         "R37_EXPECT_16_CSV_FILES")
    seen=set()
    for f in files:
        path=f.get("path")
        group=f.get("battery_group")
        need(isinstance(path,str) and
             path.startswith("ocv-relaxation-24h/csv/ocv_relaxation_24h__24h_")
             and path.endswith(".csv")
             and isinstance(group,str)
             and path.lower().endswith("_"+group.lower()+".csv"),
             "R37_UNTRUSTED_FILE_PATH")
        need(group in TRAIN+VALIDATION+TEST
             and f.get("group_role")==(
               "TRAIN" if group in TRAIN else
               "VALIDATION" if group in VALIDATION else "TEST"),
             "R37_BATTERY_ROLE_LEAK")
        blob=f.get("github_blob_sha1")
        need(isinstance(blob,str) and len(blob)==40
             and all(c in "0123456789abcdef" for c in blob),
             "R37_UNPINNED_GIT_BLOB")
        need(type(f.get("size_bytes")) is int
             and 5000<=f["size_bytes"]<MAX_BYTES,
             "R37_SIZE_LIMIT")
        need(path not in seen,"R37_DUPLICATE_FILE")
        seen.add(path)
    for group in TRAIN+VALIDATION+TEST:
        need(len([x for x in files if x["battery_group"]==group])==2,
             "R37_EXPECT_TWO_CHARGE_DISCHARGE_FILES_PER_BATTERY")
    return m

class BlockRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ValueError("R37_UNEXPECTED_REDIRECT")

def official_fetch(f):
    path=f["path"]
    url="https://raw.githubusercontent.com/BulyK47/battery-datasets/main/"+quote(path,safe="/")
    request=Request(url,headers={"Accept":"text/csv",
                "User-Agent":"JANUS-R37-readonly-research/1.0"})
    with build_opener(BlockRedirect()).open(request,timeout=35) as response:
        need(response.status==200,"R37_PUBLIC_SOURCE_HTTP_ERROR")
        raw=response.read(MAX_BYTES+1)
    need(0<len(raw)<=MAX_BYTES,"R37_DOWNLOAD_BYTE_LIMIT")
    return raw

def git_blob_sha1(raw):
    return hashlib.sha1(
        b"blob "+str(len(raw)).encode("ascii")+b"\0"+raw,
        usedforsecurity=False).hexdigest()

def parse_csv(raw,f):
    need(isinstance(raw,bytes) and len(raw)==f["size_bytes"],
         "R37_SOURCE_SIZE_MISMATCH")
    need(git_blob_sha1(raw)==f["github_blob_sha1"],
         "R37_ORIGINAL_SOURCE_GIT_BLOB_MISMATCH")
    rows=list(csv.reader(io.StringIO(raw.decode("utf-8-sig"))))
    need(len(rows)==1442,"R37_SOURCE_1441_EXPECTED_ROWS")
    head=rows[0]
    need(2<=len(head)<=12 and head[0]=="Timestamp [h]"
         and all(x.startswith("BATT_") and "_OCV_V_" in x for x in head[1:]),
         "R37_CSV_HEADER_NOT_PUBLISHED_SCHEMA")
    need(len(set(head))==len(head),"R37_DUPLICATE_OCV_COLUMN")
    series=[[] for _ in head[1:]]
    times=[]
    for line in rows[1:]:
        need(len(line)==len(head),"R37_CSV_INCOMPLETE_MEASUREMENT")
        try:
            t=float(line[0]);voltages=[float(x) for x in line[1:]]
        except (ValueError,TypeError) as e:
            raise ValueError("R37_CSV_NONNUMERIC") from e
        need(math.isfinite(t) and 0<=t<=24.00001 and
             all(math.isfinite(v) and 0<v<6 for v in voltages),
             "R37_UNPHYSICAL_OCV_OR_TIME")
        need(not times or t>times[-1],"R37_OUT_OF_ORDER_TIME")
        times.append(t)
        for k,v in enumerate(voltages):
            series[k].append((t,v))
    need(len(times)==1441 and abs(times[0])<1e-8
         and abs(times[-1]-24)<1e-8,
         "R37_FULL_24H_MEASUREMENT_MISSING")
    return list(zip(head[1:],series))

def fit_linear(xs,ys):
    """Stable <=3-feature least squares with small ridge; no optimizers/plugins."""
    k=len(xs[0])
    need(k<=3 and len(xs)>=20
         and len(ys)==len(xs)
         and all(len(row)==k for row in xs),
         "R37_BAD_LINEAR_FIT")
    mat=[[sum(v[i]*v[j] for v in xs)+(1e-8 if i==j else 0.)
          for j in range(k)] for i in range(k)]
    out=[sum(v[i]*y for v,y in zip(xs,ys)) for i in range(k)]
    a=[[float(x) for x in mat[i]]+[out[i]] for i in range(k)]
    for col in range(k):
        pivot=max(range(col,k),key=lambda r:abs(a[r][col]))
        a[col],a[pivot]=a[pivot],a[col]
        need(abs(a[col][col])>1e-14,"R37_SINGULAR_EARLY_MODEL")
        z=a[col][col]
        for c in range(col,k+1):a[col][c]/=z
        for j in range(k):
            if j==col:continue
            mult=a[j][col]
            for c in range(col,k+1):a[j][c]-=mult*a[col][c]
    coefficients=[a[i][-1] for i in range(k)]
    need(all(math.isfinite(v) and abs(v)<100 for v in coefficients),
         "R37_UNBOUNDED_FIT")
    return coefficients

def basis(name,t,taus=()):
    if name=="single_exp":
        return [1.,math.exp(-t/taus[0])]
    if name=="double_exp":
        return [1.,math.exp(-t/taus[0]),math.exp(-t/taus[1])]
    if name=="log_relax":
        return [1.,math.log1p(t/taus[0])]
    if name=="exp_plus_drift":
        return [1.,math.exp(-t/taus[0]),t/24.]
    raise ValueError("R37_UNKNOWN_MODEL_BASIS")

def model_parameters(name):
    if name in ("single_exp","log_relax","exp_plus_drift"):
        return ((x,) for x in TAUS)
    if name=="double_exp":
        return ((a,b) for a in TAUS_FAST for b in TAUS_SLOW
                if a<b)
    return ((),)

def fit_on_early(points,name):
    early=[(t,y) for t,y in points if t<=EARLY_HOURS+1e-9]
    need(220<=len(early)<=242,"R37_BAD_EARLY_TRAIN_WINDOW")
    if name=="constant_last":
        return {"model":name,"taus":[],"coefficients":[early[-1][1]],
                "early_fit_RMSE_V":0.0}
    best=None
    for params in model_parameters(name):
        X=[basis(name,t,params) for t,y in early]
        try:
            coefs=fit_linear(X,[y for t,y in early])
        except ValueError:
            continue
        errors=[sum(a*b for a,b in zip(basis(name,t,params),coefs))-y
                for t,y in early]
        loss=math.sqrt(sum(v*v for v in errors)/len(errors))
        # Penalize ill-conditioned or overly complex extrapolation.
        cost=loss+(.00025 if len(coefs)==3 else 0.)
        if best is None or (cost,params)<(best[0],best[1]):
            best=(cost,params,coefs,loss)
    need(best is not None,"R37_NO_EARLY_MODEL_FIT")
    return {"model":name,"taus":list(best[1]),"coefficients":best[2],
            "early_fit_RMSE_V":best[3]}

def predict(fit,t):
    if fit["model"]=="constant_last":
        return fit["coefficients"][0]
    return sum(a*b for a,b in zip(
        basis(fit["model"],t,fit["taus"]),fit["coefficients"]))

def eval_trace(points):
    need(len(points)==1441,"R37_INVALID_TRACE_LENGTH")
    later=[(t,y) for t,y in points if t>EARLY_HOURS+1e-9]
    need(len(later)>=1000,"R37_NO_FUTURE_WINDOW")
    scores={}
    for name in MODEL_TYPES:
        m=fit_on_early(points,name)
        errors=[predict(m,t)-v for t,v in later]
        scores[name]={
            "forecast_MAE_V":sum(abs(x) for x in errors)/len(errors),
            "forecast_RMSE_V":math.sqrt(sum(x*x for x in errors)/len(errors)),
            "forecast_count":len(errors)
        }
    return scores

def load_role_files(manifest,role,fetch):
    rows=[];receipts=[]
    for f in sorted(manifest["input_files"],key=lambda x:x["path"]):
        if f["group_role"]!=role:continue
        raw=fetch(f)
        traces=parse_csv(raw,f)
        receipts.append({"path":f["path"],"battery_group":f["battery_group"],
                         "role":role,"raw_sha256":hashlib.sha256(raw).hexdigest(),
                         "publisher_mirror_git_blob_sha1":git_blob_sha1(raw),
                         "raw_rows":1441,"traces":len(traces),"bytes":len(raw)})
        for column,series in traces:
            rows.append({"battery_group":f["battery_group"],
                         "role":role,"csv_column":column,
                         "scores":eval_trace(series)})
    need(rows and receipts,"R37_NO_SOURCE_ROWS")
    return rows,receipts

def aggregated(rows):
    mean={}
    for name in MODEL_TYPES:
        scores=[r["scores"][name]["forecast_MAE_V"] for r in rows]
        mean[name]=sum(scores)/len(scores)
    return mean

def choose_frozen(val_rows,manifest):
    scores=aggregated(val_rows)
    # Score candidate against strongest fitted standard baseline on VALIDATION.
    base=min(BASELINES,key=lambda name:(scores[name],name))
    challenger=min(CHALLENGERS,key=lambda name:(scores[name],name))
    # A candidate may be called ahead only if it beats strongest standard
    # baseline by at least 5% on validation, not merely persistence.
    improvement=(scores[base]-scores[challenger])/scores[base]
    selected=challenger if improvement>=.05 else base
    frozen={
        "model_family_selected_by_validation":selected,
        "best_established_baseline":base,
        "best_new_symbolic_challenger":challenger,
        "validation_unweighted_mean_trace_MAE_V":scores,
        "validation_challenger_vs_strongest_baseline_relative_gain":improvement,
        "selection_threshold_relative_gain":.05,
        "candidate_is_selected":selected==challenger,
        "source_manifest_sha256":sha(manifest),
        "validation_batteries":list(VALIDATION),
        "test_batteries_unread_at_freeze":True,
        "no_real_neural_weight_training":True,
        "independent_custodian_signed":False,
        "scientific_admission":"HOLD",
    }
    frozen["pretest_selection_receipt_sha256"]=sha(frozen)
    return frozen

def run(manifest_path,outdir,fetch=official_fetch):
    manifest=json.loads(Path(manifest_path).read_text(encoding="utf8"))
    manifest_check(manifest)
    out=Path(outdir)
    need(not out.exists() or not any(out.iterdir()),
         "R37_FAIL_CLOSED_EXISTING_OUTPUT")
    out.mkdir(parents=True,exist_ok=True)
    # Source fetching order is fixed, test-group bytes are not accessed
    # before the validation-only model selection is SEALED TO DISK.
    train,train_meta=load_role_files(manifest,"TRAIN",fetch)
    val,val_meta=load_role_files(manifest,"VALIDATION",fetch)
    frozen=choose_frozen(val,manifest)
    pretest=out/"r37_pretest_selection_seal.json"
    pretest.write_text(json.dumps(frozen,sort_keys=True,indent=2)+"\n",
                       encoding="utf8")
    need(sha(json.loads(pretest.read_text(encoding="utf8")))==
         sha(frozen),"R37_FROZEN_MODEL_ID_DRIFT")
    test,test_meta=load_role_files(manifest,"TEST",fetch)
    test_metrics=aggregated(test)
    sel=frozen["model_family_selected_by_validation"]
    standard=frozen["best_established_baseline"]
    gain=(test_metrics[standard]-test_metrics[sel])/test_metrics[standard]
    if not frozen["candidate_is_selected"]:gain=0.
    test_by_battery={}
    for b in TEST:
        b_rows=[r for r in test if r["battery_group"]==b]
        need(b_rows,"R37_TEST_GROUP_UNAVAILABLE")
        test_by_battery[b]=aggregated(b_rows)
    success=bool(frozen["candidate_is_selected"] and gain>.05
                 and all(test_by_battery[b][sel]<test_by_battery[b][standard]
                         for b in TEST))
    # Keep a small selected model prediction audit as source metadata only,
    # NEVER raw data or measured voltage series.
    report={
        "schema":RESULT_SCHEMA,
        "original_real_source_license":"CC BY 4.0",
        "attribution":manifest["source_attribution"],
        "dataset_doi":manifest["original_dataset_doi"],
        "source_manifest_sha256":sha(manifest),
        "raw_source_file_sha256_receipts":train_meta+val_meta+test_meta,
        "battery_groups":{"TRAIN":list(TRAIN),"VALIDATION":list(VALIDATION),
                          "TEST":list(TEST)},
        "raw_source_files_received":len(train_meta+val_meta+test_meta),
        "total_traces_train":len(train),
        "total_traces_validation":len(val),
        "total_traces_test":len(test),
        "model_family_selection_sha256":frozen["pretest_selection_receipt_sha256"],
        "selected_model":sel,
        "strongest_standard_baseline_on_validation":standard,
        "validation_mean_trace_MAE_V":frozen["validation_unweighted_mean_trace_MAE_V"],
        "test_mean_trace_MAE_V":test_metrics,
        "test_mean_trace_MAE_V_by_battery":test_by_battery,
        "selected_challenger_relative_gain_vs_strongest_baseline_on_test":gain,
        "positive_new_symbolic_forecast_gain_both_batteries":success,
        "per_trace_test_scores":test,
        "real_observational_data_fitted_only_per_trace_first_4h":True,
        "test_batteries_loaded_after_validation_selection_seal":True,
        "no_test_battery_used_to_choose_formula_structure":True,
        "no_true_external_blind_custodian":True,
        "neural_weights_trained":False,
        "neural_training_authorized":False,
        "scientific_discovery_admitted":False,
        "known_battery_relaxation_laws_not_proven_incomplete":True,
        "production_model_promoted":False,
        "scientific_admission":"HOLD",
        "interpretation":("REAL_MEASURED_FORECAST_RESEARCH_CHALLENGER_GAIN"
                         if success else
                         "REAL_MEASURED_FORECAST_NO_STRONG_BASELINE_GAIN"),
    }
    report["receipt_sha256"]=sha(report)
    (out/"r37_real_ocv_forecast_evaluation.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",
        encoding="utf8")
    return report

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--manifest",required=True)
    a.add_argument("--outdir",required=True)
    args=a.parse_args()
    r=run(args.manifest,args.outdir)
    print(json.dumps({
       "source_files_integrity_verified":r["raw_source_files_received"],
       "train_traces":r["total_traces_train"],
       "validation_traces":r["total_traces_validation"],
       "test_traces":r["total_traces_test"],
       "selected_model":r["selected_model"],
       "strongest_baseline":r["strongest_standard_baseline_on_validation"],
       "test_MAE_by_model_volts":r["test_mean_trace_MAE_V"],
       "test_gain":r["selected_challenger_relative_gain_vs_strongest_baseline_on_test"],
       "scientific_admission":"HOLD",
       "neural_training_authorized":False
    },sort_keys=True))

if __name__=="__main__":main()
