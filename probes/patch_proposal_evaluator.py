from __future__ import annotations
import hashlib, json
from pathlib import Path
from typing import Any

SCHEMA="janus.patch_proposal.evaluation.v1"
LEDGER_SCHEMA="janus.patch_proposal.ledger.v1"
ZERO="0"*64

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _valid_sha(v:Any)->bool:
    return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdefABCDEF" for c in v)

def evaluate(*, proposal:dict[str,Any], audit_receipt:dict[str,Any], metric_receipt:dict[str,Any]) -> dict[str,Any]:
    findings=[]
    baseline=proposal.get("baseline_sha256"); candidate=proposal.get("candidate_sha256")
    if proposal.get("origin")!="janus": findings.append("ORIGIN_NOT_JANUS")
    if not _valid_sha(baseline): findings.append("INVALID_BASELINE_SHA256")
    if not _valid_sha(candidate): findings.append("INVALID_CANDIDATE_SHA256")
    if baseline==candidate and _valid_sha(candidate): findings.append("NO_SOURCE_DELTA")
    if audit_receipt.get("status")!="PASS_STATIC": findings.append("STATIC_AUDIT_NOT_PASS")
    if audit_receipt.get("source_sha256")!=candidate: findings.append("AUDIT_NOT_BOUND_TO_CANDIDATE")
    if metric_receipt.get("candidate_sha256")!=candidate or metric_receipt.get("baseline_sha256")!=baseline:
        findings.append("METRIC_NOT_BOUND_TO_PROPOSAL")
    if metric_receipt.get("execution_origin") not in {"external_test","ci_test","sandbox_test"}:
        findings.append("METRIC_ORIGIN_NOT_EXTERNAL_TEST")
    direction=metric_receipt.get("direction")
    before=metric_receipt.get("baseline_metric"); after=metric_receipt.get("candidate_metric")
    if direction not in {"maximize","minimize"}: findings.append("INVALID_DIRECTION")
    if not isinstance(before,(int,float)) or isinstance(before,bool) or not isinstance(after,(int,float)) or isinstance(after,bool):
        findings.append("INVALID_METRIC")
        improvement=None
    else:
        improvement=(after-before) if direction=="maximize" else (before-after)
    decision="ELIGIBLE_FOR_HUMAN_REVIEW" if not findings and improvement is not None and improvement>0 else "HOLD"
    body={
      "schema":SCHEMA,"decision":decision,"findings":findings,
      "origin":proposal.get("origin"),"baseline_sha256":baseline,"candidate_sha256":candidate,
      "patch_class":proposal.get("patch_class"),"metric_name":metric_receipt.get("metric_name"),
      "direction":direction,"baseline_metric":before,"candidate_metric":after,"improvement":improvement,
      "authority":{"executes_candidate":False,"reloads_module":False,"applies_patch":False,"reverts_patch":False,"writes_target":False},
      "next_gate":"SOVEREIGN_LOCK_HASH_BOUND_HUMAN_APPROVAL",
      "laws":["PROPOSAL_EVALUATION != PATCH_APPLICATION","EXTERNAL_TEST_RECEIPT_REQUIRED","ORIGIN_MARKER_ALONE != TRUST"]
    }
    body["evaluation_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body

def _read_ledger(path:Path)->list[dict[str,Any]]:
    if not path.exists(): return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

def append_evaluation(path:str|Path, evaluation:dict[str,Any])->dict[str,Any]:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); rows=_read_ledger(p)
    eid=evaluation.get("evaluation_sha256")
    for row in rows:
        if row.get("evaluation_sha256")==eid: return {"appended":False,"record":row}
    prev=rows[-1]["record_sha256"] if rows else ZERO
    body={"schema":LEDGER_SCHEMA,"seq":len(rows)+1,"previous_hash":prev,"evaluation_sha256":eid,
          "decision":evaluation.get("decision"),"candidate_sha256":evaluation.get("candidate_sha256"),"improvement":evaluation.get("improvement")}
    body["record_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    with p.open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    return {"appended":True,"record":body}

def verify_ledger(path:str|Path)->dict[str,Any]:
    rows=_read_ledger(Path(path)); prev=ZERO
    for i,row in enumerate(rows,1):
        if row.get("seq")!=i or row.get("previous_hash")!=prev: return {"valid":False,"failed_at":i}
        copy=dict(row); claimed=copy.pop("record_sha256",None)
        if hashlib.sha256(_canon(copy)).hexdigest()!=claimed: return {"valid":False,"failed_at":i}
        prev=claimed
    return {"valid":True,"records":len(rows),"head":prev}
