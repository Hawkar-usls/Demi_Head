"""Bounded review of archived COSMOS scientific scenes through existing Guardian."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
from pathlib import Path
from nexus_guardian_ingress import guardian_ingest, release_control, sha256
from epistemic_execution_gate import compute_sha256_file

SOURCES = {
    "cosmos": ("experiments/kusto/zn-r2/2026-11-26-run-45830969841.json", "fc495da08d13c10e11953a7ecab58338fb24d0d6"),
    "eye": ("experiments/janus-eye/r1/2026-11-26-run-45833030382.json", "2a2d84bb0c0b4a78d93d205fa0d22cce71168223"),
}
CLAIMS = {"MODELLED_GEOMETRY", "UNIQUE_OBJECT", "DIRECT_SONAR", "INDEPENDENT_REPLICATION"}

def read_sources(root):
    data, witnesses = {}, {}
    for name, (path, expected) in SOURCES.items():
        p = Path(root)/path
        raw = p.read_bytes()
        if len(raw)>2_000_000:
            raise ValueError("source cap")
        blob = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        if blob != expected:
            raise ValueError("frozen source mismatch")
        data[name] = json.loads(raw)
        witnesses[name] = {"path":path,"git_blob":blob,"execution":compute_sha256_file(p)}
    return data, witnesses

def build_request(root, claim="MODELLED_GEOMETRY"):
    if claim not in CLAIMS:
        raise ValueError("unsupported claim")
    d,w = read_sources(root)
    c,e=d["cosmos"]["receipt"],d["eye"]["receipt"]
    if str(c["run_id"])!="45830969841" or d["eye"]["run_id"]!=45833030382:
        raise ValueError("source identity")
    if e["authority"]!="MODELLED" or e["scene_id"]!="KUSTO_ZERO_NODE":
        raise ValueError("authority/source identity")
    n=next(n for n in e["nodes"] if n["id"]=="LOCAL_NODE")
    t=c["target"]["06"]
    if n["sample_xy_m"] != [1000*t["x_km"],1000*t["y_km"]] or not math.isclose(n["fields"]["gravity"],t["peak_mgal"],abs_tol=1e-9,rel_tol=0):
        raise ValueError("COSMOS EYE geometry/field disagreement")
    s=c["control_summary"]
    return {"schema":"janus.demihead.spatial_review_request.v1","scene_id":e["scene_id"],"claim":claim,"data_class":e["authority"],
            "frame":e["frame"],"node":n,"cosmos_control_summary":s,"closed_proxy":t["closed_proxy"],
            "sources":{k:{"git_blob":v["git_blob"],"sha256":v["execution"]["computed_value"]} for k,v in w.items()},
            "limitations":e["limitations"]+c["limitations"],"authority_delta":0,"production_promotion":False}

def review(root, request):
    expected=build_request(root,request.get("claim"))
    if request != expected:
        raise ValueError("request differs from frozen source replay")
    # Existing Guardian is the final bounded route; no direct observation promotion.
    claim=request["claim"]
    hold=claim!="MODELLED_GEOMETRY"
    if hold:
        payload={"schema":"janus.demihead.nexus_fundamentum_receipt.v1","status":"HOLD","payload_kind":"HOLD_RECEIPT",
                 "assessment":{"evidence_state":"CONTEXT_ONLY_NOT_EVIDENCE","required_next_input":"NEW_INDEPENDENT_MEASUREMENT","definitive_claim_permitted":False},
                 "control":{"external_effect_permitted":False,"authority_delta":0,"mass_effect_budget_delta":0,"may_be_promoted_to_evidence_receipt_without_new_witness":False}}
        guardian=guardian_ingest("HOLD_RECEIPT",payload)
    else:
        payload={"schema":"janus.demihead.observation_signal.v1","source":{"raw_identifiers_included":False,"raw_syslog_included":False,"scene_request_sha256":sha256(request)},
                 "quality":{"quantum_randomness_claim":False},
                 "control":{"authority_delta":0,"mass_effect_budget_delta":0,"direct_model_temperature_control":False,"cryptographic_entropy_source":False}}
        guardian=guardian_ingest("OBSERVATION_SIGNAL",payload)
    result={"schema":"janus.demihead.spatial_review_receipt.v1","request_sha256":sha256(request),
            "decision":"HOLD_FOR_NEW_INDEPENDENT_EVIDENCE" if hold else "ACCEPT_DESCRIPTIVE_MODEL_ONLY",
            "scene_id":request["scene_id"],"claim":claim,"data_class":"MODELLED",
            "guardian":guardian,"release":release_control(guardian),"authority_delta":0,"production_promotion":False,
            "independent_observation":False,"unique_object_established":False}
    result["review_sha256"]=sha256(result)
    return result

def verify_review(root,request,result):
    return result==review(root,request)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("registry",type=Path)
    p.add_argument("output",type=Path)
    a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=True)
    req=build_request(a.registry)
    res=review(a.registry,req)
    for name,value in (("request",req),("review",res)):
        (a.output/(name+".json")).write_text(json.dumps(value,indent=2,allow_nan=False)+"\n")
    print(json.dumps(res,indent=2))
if __name__=="__main__":
    main()
