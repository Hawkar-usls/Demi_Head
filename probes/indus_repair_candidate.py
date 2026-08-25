from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA="janus.indus.repair_candidate.v1"

def _canon(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def _is_sha(value:Any)->bool:
    return isinstance(value,str) and len(value)==64 and all(c in "0123456789abcdefABCDEF" for c in value)

def build(*, module_key:str, source_sha256:str, failure_receipt_sha256:str, reason:str, target_path:str|None=None)->dict[str,Any]:
    findings=[]
    key=str(module_key or "").strip().casefold()
    why=" ".join(str(reason or "").split())
    if not key or "/" in key or "\\" in key: findings.append("INVALID_MODULE_KEY")
    if not _is_sha(source_sha256): findings.append("INVALID_SOURCE_SHA256")
    if not _is_sha(failure_receipt_sha256): findings.append("INVALID_FAILURE_RECEIPT_SHA256")
    if not why: findings.append("MISSING_REASON")
    if target_path is not None and not str(target_path).strip(): findings.append("INVALID_TARGET_PATH")
    body={
      "schema":SCHEMA,
      "status":"REPAIR_CANDIDATE" if not findings else "HOLD",
      "findings":findings,
      "module_key":key,
      "source_sha256":source_sha256,
      "failure_receipt_sha256":failure_receipt_sha256,
      "reason":why,
      "reason_sha256":hashlib.sha256(why.encode("utf-8")).hexdigest(),
      "target_path":target_path,
      "requested_action":"DIAGNOSE_AND_PROPOSE_REPAIR",
      "authority":{
        "deletes_module":False,
        "kills_service":False,
        "edits_source":False,
        "runs_candidate":False,
        "reloads_module":False,
        "writes_target":False
      },
      "next_gates":["AUDITOR","EXTERNAL_TEST_RECEIPT","PATCH_PROPOSAL_EVALUATOR","SOVEREIGN_LOCK","NEXUS_PROBATION"],
      "laws":[
        "INDUS_REPAIR_JOB_NE_KILL_ORDER",
        "FAILURE_RECEIPT_MUST_BIND_REPAIR_REQUEST",
        "REPAIR_CANDIDATE_NE_PATCH_APPLICATION"
      ]
    }
    body["repair_candidate_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body
