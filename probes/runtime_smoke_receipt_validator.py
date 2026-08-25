from __future__ import annotations
import hashlib, json
from typing import Any

SCHEMA="janus.runtime_smoke.receipt.v1"
VALIDATION_SCHEMA="janus.runtime_smoke.validation.v1"

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def _sha(v:Any)->bool:
    return isinstance(v,str) and len(v)==64 and all(c in "0123456789abcdefABCDEF" for c in v)

def validate(candidate_sha256:str, receipt:dict[str,Any])->dict[str,Any]:
    findings=[]
    if not _sha(candidate_sha256): findings.append("INVALID_CANDIDATE_SHA256")
    if receipt.get("schema")!=SCHEMA: findings.append("INVALID_SCHEMA")
    if receipt.get("candidate_sha256")!=candidate_sha256: findings.append("RECEIPT_NOT_BOUND_TO_CANDIDATE")
    if receipt.get("fresh_process") is not True: findings.append("NOT_FRESH_PROCESS")
    if receipt.get("isolated_workspace") is not True: findings.append("WORKSPACE_NOT_ISOLATED")
    if receipt.get("network_policy") not in {"blocked","none"}: findings.append("NETWORK_NOT_BLOCKED")
    if receipt.get("network_attempts",0)!=0: findings.append("NETWORK_ATTEMPT_OBSERVED")
    if receipt.get("writes_outside_workspace",0)!=0: findings.append("OUTSIDE_WRITE_OBSERVED")
    if receipt.get("timed_out") is not False: findings.append("TIMEOUT_OR_UNKNOWN")
    if receipt.get("exit_code")!=0: findings.append("NONZERO_EXIT")
    if receipt.get("import_ok") is not True: findings.append("IMPORT_NOT_OK")
    if receipt.get("abi_ok") is not True: findings.append("ABI_NOT_OK")
    source=dict(receipt); claimed=source.pop("receipt_sha256",None)
    computed=hashlib.sha256(_canon(source)).hexdigest()
    if claimed is not None and claimed!=computed: findings.append("RECEIPT_HASH_MISMATCH")
    body={"schema":VALIDATION_SCHEMA,"candidate_sha256":candidate_sha256,
          "status":"PASS_RECEIPT_VALIDATED" if not findings else "HOLD","findings":findings,
          "runtime_receipt_sha256":computed,
          "boundary":"VALIDATES_CLAIMED_SANDBOX_RECEIPT; DOES_NOT_EXECUTE_CODE_OR_PROVE_COMPLETE_SECURITY",
          "authority":{"executes_candidate":False,"writes_target":False,"promotes_live":False}}
    body["validation_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body
