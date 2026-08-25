from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA="janus.nexus.probation_gate.v1"

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->bool:
    return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdefABCDEF" for c in v)

def evaluate(*, candidate_sha256:str, canonical_module_key:str, audit_receipt:dict[str,Any], integration_plan:dict[str,Any], runtime_smoke_validation:dict[str,Any], approval_verification:dict[str,Any], protected_name:bool=False, protected_replacement_authority:bool=False, failure_hold:bool=False)->dict[str,Any]:
    findings=[]
    if not _sha(candidate_sha256): findings.append("INVALID_CANDIDATE_SHA256")
    if not canonical_module_key or "/" in canonical_module_key or "\\" in canonical_module_key: findings.append("INVALID_CANONICAL_MODULE_KEY")
    if audit_receipt.get("status")!="PASS_STATIC" or audit_receipt.get("source_sha256")!=candidate_sha256:
        findings.append("AUDITOR_GATE_NOT_BOUND_PASS")
    if integration_plan.get("status")!="PLAN_ONLY" or not integration_plan.get("plan_sha256"):
        findings.append("INTEGRATION_PLAN_NOT_PASS")
    else:
        matches=[m for m in integration_plan.get("modules",[]) if str(m.get("id","")).casefold()==canonical_module_key.casefold()]
        if not matches: findings.append("MODULE_NOT_IN_PLAN")
        elif matches[0].get("source_sha256") not in {None,candidate_sha256}:
            findings.append("PLAN_SOURCE_IDENTITY_MISMATCH")
    if runtime_smoke_validation.get("status")!="PASS_RECEIPT_VALIDATED" or runtime_smoke_validation.get("candidate_sha256")!=candidate_sha256:
        findings.append("RUNTIME_SMOKE_NOT_BOUND_PASS")
    if approval_verification.get("authorized") is not True or approval_verification.get("proposal_sha256") not in {None,candidate_sha256}:
        findings.append("SOVEREIGN_LOCK_NOT_BOUND_AUTHORIZED")
    if protected_name and not protected_replacement_authority:
        findings.append("PROTECTED_MODULE_REPLACEMENT_AUTHORITY_MISSING")
    if failure_hold:
        findings.append("OPEN_FAILURE_HOLD")
    body={
      "schema":SCHEMA,"candidate_sha256":candidate_sha256,"canonical_module_key":canonical_module_key,
      "status":"PROBATION_ELIGIBLE" if not findings else "HOLD","findings":findings,
      "authority":{
        "writes_modules_live":False,"starts_task":False,"replaces_protected_module":False,
        "grants_external_effect_authority":False,"probation_evidence_only":True
      },
      "next_gate":"SEPARATE_LIVE_PROMOTION_AND_WRITE_AUTHORITY",
      "laws":[
        "STATIC_PASS + SANDBOX_RECEIPT + HUMAN_APPROVAL != LIVE_AUTHORITY",
        "PROTECTED_NAME_REPLACEMENT_REQUIRES_SEPARATE_AUTHORITY",
        "OPEN_FAILURE_HOLD_BLOCKS_PROMOTION"
      ]
    }
    body["probation_receipt_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body
