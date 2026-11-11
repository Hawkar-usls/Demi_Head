"""TACHYON R3.2: bounded external primary-measurement witness, NOT blind physics proof.

Published labs are independent in origin, but their published data and this
evaluator are visible. This code never trains a model, returns no arbitrary
scientific answers, and does not download/republish raw measurements as artifacts.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, build_opener, HTTPRedirectHandler

SCHEMA="janus.tachyon.r32.external_measurement_families.v1"
RESULT_SCHEMA="janus.tachyon.r32.external_measurement_witness.v1"
SOURCES={
 "SKVI_MUON_CAPTURE_TIMING_2025":(
  "MUON_STOP_DECAY_AND_NEUTRON_CAPTURE",
  "https://zenodo.org/records/15081911/files/decayes_and_neutrons.csv?download=1",
  "59056d97657ed04b3d19c7766a976519",30000000,1986465,
 ),
 "OFFENBURG_BATTERY_OCV_2024":(
  "BATTERY_SOC_VOLTAGE_CURVE",
  "https://zenodo.org/records/13142016/files/OCV_vs_SOC_curve_fresh_cell.csv?download=1",
  "6bb24aed4d06fb4df88de4a3f6a37f3",200000,1001,
 )}
KNOWN_TRAINED_FAMILIES=frozenset({
 "SR_PROPER_TIME_RATIO","TWO_LEVEL_BORN_PROBABILITY",
})
FROZEN_CHECKPOINT_SHA="b3b36dfb3e8c1d0d4a1ae1b867978cfa5f8f28d6768d1a42efac02a4d2e47f01"

def require(ok,message):
    if not ok:raise ValueError(message)

def canonical(data):
    return json.dumps(data,ensure_ascii=False,sort_keys=True,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def sha(data):
    return hashlib.sha256(canonical(data)).hexdigest()

def manifest_check(record):
    require(record.get("schema")==SCHEMA,"R32_BAD_MANIFEST_SCHEMA")
    require(record.get("scientific_admission")=="HOLD"
            and record.get("production_deployment") is False
            and record.get("independent_custodian_connected") is False
            and record.get("independent_blind_evaluation") is False,
            "R32_NO_BLIND_EVALUATOR_AVAILABLE")
    candidate=record.get("candidate",{})
    require(candidate.get("reference_checkpoint_sha256")==FROZEN_CHECKPOINT_SHA
            and candidate.get("pretrained_or_updated_with_external_measurements") is False,
            "R32_CANDIDATE_SHA_OR_TRAINING_DRIFT")
    src=record.get("public_measurement_sources")
    require(isinstance(src,list) and len(src)==2
            and {x.get("id") for x in src}==set(SOURCES),
            "R32_SOURCE_SET_MISMATCH")
    for item in src:
        family,url,md5,limit,count=SOURCES[item["id"]]
        require(item.get("family")==family
                and item.get("data_path")==url.split("/files/")[1].split("?")[0]
                and item.get("expected_md5")==md5
                and item.get("max_bytes")==limit
                and item.get("expected_measurement_count")==count
                and item.get("independent_from_training_families") is True
                and item.get("raw_data_republished") is False,
                "R32_UNPINNED_SOURCE")
    policy=record.get("score_policy",{})
    require(policy.get("training_on_external_holdout") is False
            and policy.get("novel_family_count")==2,
            "R32_UNAUTHORIZED_TRAINING")
    return record

class HostRestrictedRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        parsed=urlparse(newurl)
        require(parsed.scheme=="https" and parsed.hostname=="zenodo.org"
                and parsed.username is None and parsed.password is None,
                "R32_UNSAFE_DOWNLOAD_REDIRECT")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch_official(url,limit):
    require(url in [src[1] for src in SOURCES.values()],"R32_UNTRUSTED_URL")
    opener=build_opener(HostRestrictedRedirect())
    req=Request(url,headers={
        "User-Agent":"JANUS-R32-research-holdout/1.0 (read-only scientific audit)",
        "Accept":"text/csv,application/octet-stream"
    })
    with opener.open(req,timeout=40) as response:
        require(response.status==200,"R32_UNEXPECTED_HTTP_STATUS")
        result=response.read(limit+1)
    require(0<len(result)<=limit,"R32_SOURCE_DOWNLOAD_LIMIT")
    return result

def to_float(raw):
    try:
        x=float(raw.strip())
    except (ValueError,AttributeError):
        raise ValueError("R32_NONNUMERIC_MEASUREMENT") from None
    require(math.isfinite(x),"R32_NONFINITE_MEASUREMENT")
    return x

def muon_summary(raw,count_expected):
    # First 2 fields: decay electron momentum MeV and delay microseconds.
    n=0;n_delay=0;sum_delay=0.;min_delay=None;max_delay=None
    reader=csv.reader(io.StringIO(raw.decode("utf-8-sig")))
    header_skipped=False
    for cols in reader:
        if not cols:continue
        require(len(cols)>=2,"R32_MUON_CSV_COLUMNS")
        try:p=to_float(cols[0]);dt=to_float(cols[1])
        except ValueError:
            require(n==0 and not header_skipped,"R32_MUON_BAD_EVENT")
            header_skipped=True
            continue
        require(p>=0 and dt>=0 and dt<=1000,"R32_MUON_OUT_OF_RANGE")
        n+=1
        require(n<=count_expected+100,"R32_MUON_ROWS_OVER_BUDGET")
        if dt>0:
            n_delay+=1;sum_delay+=dt
            min_delay=dt if min_delay is None else min(min_delay,dt)
            max_delay=dt if max_delay is None else max(max_delay,dt)
    require(n==count_expected and n_delay>0,"R32_MUON_EVENT_COUNT_DRIFT")
    return {
        "raw_event_rows":n,
        "tagged_decay_electron_delays_count":n_delay,
        "tagged_delay_mean_microseconds":round(sum_delay/n_delay,7),
        "tagged_delay_min_microseconds":min_delay,
        "tagged_delay_max_microseconds":max_delay,
        "interpretation":"DETECTOR_TAGGED_DELAY_DESCRIPTIVE_STATISTIC_NOT_MUON_VACUUM_LIFETIME",
        "selection_effects_and_instrument_response_not_corrected":True
    }

def battery_summary(raw,count_expected):
    # OCV vs SOC; accept comma/semicolon/tab, with a possible header line.
    rows=raw.decode("utf-8-sig").splitlines()
    n=0;xmin=math.inf;xmax=-math.inf;ymin=math.inf;ymax=-math.inf
    first=None;last=None
    for line in rows:
        if not line.strip():continue
        # Decimal-comma with semicolon separators is also supported.
        if ";" in line:
            parts=[x.strip().replace(",",".") for x in line.split(";")]
        else:
            parts=[x.strip() for x in re.split(r"[\t,]",line)]
        require(len(parts)>=2,"R32_OCV_CSV_COLUMNS")
        try: x=to_float(parts[0]);y=to_float(parts[1])
        except ValueError:
            require(n==0,"R32_OCV_BAD_MEASUREMENT")
            continue
        require(0<=x<=1.001 and 0<y<10,"R32_OCV_OUT_OF_RANGE")
        n+=1
        require(n<=count_expected+10,"R32_OCV_ROWS_OVER_BUDGET")
        xmin=min(x,xmin);xmax=max(x,xmax)
        ymin=min(y,ymin);ymax=max(y,ymax)
        if first is None:first=(x,y)
        last=(x,y)
    require(n==count_expected,"R32_OCV_ROW_COUNT_DRIFT")
    require(xmin<=.01 and xmax>=.99 and ymax>ymin,
            "R32_OCV_NOT_FULL_SOC_CURVE")
    return {"raw_measurement_rows":n,
            "soc_observed_min":round(xmin,6),
            "soc_observed_max":round(xmax,6),
            "ocv_volts_min":round(ymin,6),
            "ocv_volts_max":round(ymax,6),
            "first_point_soc_ocv":first,
            "last_point_soc_ocv":last,
            "interpretation":"LAB_MEASURED_OPEN_CIRCUIT_VOLTAGE_VS_SOC_NO_BATTERY_MODEL_FIT"}

def evaluate_manifest(manifest,fetch=fetch_official,checkpoint=None):
    manifest_check(manifest)
    actual_ckpt_sha=None
    if checkpoint:
        actual_ckpt_sha=hashlib.sha256(Path(checkpoint).read_bytes()).hexdigest()
        require(actual_ckpt_sha==FROZEN_CHECKPOINT_SHA,
                "R32_CHECKPOINT_NOT_FROZEN_CANDIDATE")
    items=[]
    for entry in manifest["public_measurement_sources"]:
        family,url,expected_md5,budget,count=SOURCES[entry["id"]]
        result={
            "source_id":entry["id"],"family":family,
            "source_dataset_url":entry["dataset_url"],"source_doi":entry["doi"],
            "original_data_embedded_in_artifact":False,
            "trained_candidate_on_source":False,
            "candidate_supports_family":family in KNOWN_TRAINED_FAMILIES,
            "candidate_decision":"ABSTAIN_UNSUPPORTED_PHYSICS_FAMILY",
            "candidate_numeric_prediction":None,
            "source_status":"PROVIDER_UNAVAILABLE",
        }
        try:
            raw=fetch(url,budget)
            require(isinstance(raw,bytes) and 0<len(raw)<=budget,
                    "R32_DOWNLOAD_TOO_LARGE")
            actual_md5=hashlib.md5(raw,usedforsecurity=False).hexdigest()
            require(actual_md5==expected_md5,"R32_SOURCE_MD5_MISMATCH")
            summary=(muon_summary(raw,count) if entry["id"].startswith("SKVI")
                     else battery_summary(raw,count))
            result.update({
                "source_status":"MEASURED_EXTERNAL_DATA_INTEGRITY_PASS",
                "download_size_bytes":len(raw),
                "source_raw_sha256":hashlib.sha256(raw).hexdigest(),
                "source_publisher_md5":actual_md5,
                "descriptive_measurement_summary":summary
            })
        except (ValueError,HTTPError,URLError,TimeoutError,OSError,UnicodeError) as e:
            msg=("R32_HTTP_"+str(e.code) if isinstance(e,HTTPError)
                 else (str(e) if isinstance(e,ValueError) else "R32_NETWORK_UNAVAILABLE"))
            require(re.fullmatch(r"[A-Z0-9_]{4,90}",msg) is not None,
                    "R32_UNSAFE_ERROR_DETAIL")
            result["source_failure_reason"]=msg
        items.append(result)
    avail=sum(x["source_status"]=="MEASURED_EXTERNAL_DATA_INTEGRITY_PASS"
              for x in items)
    return {
        "schema":RESULT_SCHEMA,
        "source_manifest_sha256":sha(manifest),
        "frozen_candidate_checkpoint_sha256":FROZEN_CHECKPOINT_SHA,
        "actual_candidate_checkpoint_sha256_verified":actual_ckpt_sha==FROZEN_CHECKPOINT_SHA,
        "independent_source_families":len(items),
        "external_measurement_sources_verified":avail,
        "external_measurement_sources_unavailable":len(items)-avail,
        "scope":"PUBLISHED_LAB_RAW_MEASUREMENTS_NEW_FAMILIES_NO_NEURAL_PREDICTION",
        "source_families_unseen_by_training":True,
        "unsupported_family_decisions":sum(
            x["candidate_decision"]=="ABSTAIN_UNSUPPORTED_PHYSICS_FAMILY"
            for x in items),
        "new_family_numeric_generalization_demonstrated":False,
        "scientific_claims_fact_checked":False,
        "independently_blind":False,
        "independent_custodian_connected":False,
        "model_weights_updated":False,
        "production_promotion":False,
        "scientific_admission":"HOLD",
        "status":("EXTERNAL_MEASUREMENTS_WITNESSED_NO_NEW_FAMILY_LEARNING"
                  if avail==len(items) else "EXTERNAL_MEASUREMENT_SOURCE_INCOMPLETE"),
        "observations":items
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--checkpoint",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    obj=json.loads(Path(args.manifest).read_text(encoding="utf8"))
    outcome=evaluate_manifest(obj,checkpoint=args.checkpoint)
    outcome["receipt_sha256"]=sha(outcome)
    target=Path(args.output)
    require(not target.exists(),"R32_REFUSE_OVERWRITE")
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(outcome,indent=2,sort_keys=True,
                                 ensure_ascii=False)+"\n",encoding="utf8")
    print(json.dumps({
        "result":outcome["status"],
        "sources_verified":outcome["external_measurement_sources_verified"],
        "sources_expected":len(outcome["observations"]),
        "new_family_predictive_gain":False,
        "science_hold":True,
        "frozen_candidate_sha_verified":outcome[
            "actual_candidate_checkpoint_sha256_verified"]
    },sort_keys=True))

if __name__=="__main__":main()
