import hashlib, json
from probes.runtime_smoke_receipt_validator import validate
from probes.nexus_probation_gate import evaluate

def _sha(c): return c*64

def _smoke(candidate):
    body={"schema":"janus.runtime_smoke.receipt.v1","candidate_sha256":candidate,"fresh_process":True,
          "isolated_workspace":True,"network_policy":"blocked","network_attempts":0,"writes_outside_workspace":0,
          "timed_out":False,"exit_code":0,"import_ok":True,"abi_ok":True}
    body["receipt_sha256"]=hashlib.sha256(json.dumps(body,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
    return body

def test_probation_eligible_is_not_live_authority():
    candidate=_sha("b")
    smoke=validate(candidate,_smoke(candidate))
    audit={"status":"PASS_STATIC","source_sha256":candidate}
    plan={"status":"PLAN_ONLY","plan_sha256":_sha("c"),"modules":[{"id":"mod_rex","source_sha256":candidate}]}
    approval={"authorized":True,"proposal_sha256":candidate}
    r=evaluate(candidate_sha256=candidate,canonical_module_key="mod_rex",audit_receipt=audit,integration_plan=plan,
               runtime_smoke_validation=smoke,approval_verification=approval)
    assert r["status"]=="PROBATION_ELIGIBLE"
    assert r["authority"]["writes_modules_live"] is False
    assert r["authority"]["starts_task"] is False

def test_protected_and_failure_holds():
    candidate=_sha("b")
    smoke=validate(candidate,_smoke(candidate))
    audit={"status":"PASS_STATIC","source_sha256":candidate}
    plan={"status":"PLAN_ONLY","plan_sha256":_sha("c"),"modules":[{"id":"mod_auditor","source_sha256":candidate}]}
    approval={"authorized":True,"proposal_sha256":candidate}
    r=evaluate(candidate_sha256=candidate,canonical_module_key="mod_auditor",audit_receipt=audit,integration_plan=plan,
               runtime_smoke_validation=smoke,approval_verification=approval,protected_name=True,failure_hold=True)
    assert r["status"]=="HOLD"
    assert "PROTECTED_MODULE_REPLACEMENT_AUTHORITY_MISSING" in r["findings"]
    assert "OPEN_FAILURE_HOLD" in r["findings"]

def test_smoke_receipt_rejects_network_or_outside_write():
    candidate=_sha("b"); receipt=_smoke(candidate); receipt["network_attempts"]=1; receipt["writes_outside_workspace"]=1
    r=validate(candidate,receipt)
    assert r["status"]=="HOLD"
    assert "NETWORK_ATTEMPT_OBSERVED" in r["findings"]
    assert "OUTSIDE_WRITE_OBSERVED" in r["findings"]
