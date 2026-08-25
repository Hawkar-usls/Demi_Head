from __future__ import annotations
import hashlib, json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA="janus.sovereign_lock.approval.v2"
CONSUME_SCHEMA="janus.sovereign_lock.consume.v1"

def _canon(x:Any)->bytes:
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def sha256_file(path:str|Path)->str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def make_proposal(proposal_path:str|Path,target_path:str)->dict[str,Any]:
    p=Path(proposal_path)
    return {"proposal_name":p.name,"proposal_sha256":sha256_file(p),"target_path":target_path,"size":p.stat().st_size}

def make_approval(proposal:dict[str,Any], *, approved_by_label:str, nonce:str, expires_at:str|None=None)->dict[str,Any]:
    body={"schema":SCHEMA,"proposal_sha256":proposal["proposal_sha256"],"target_path":proposal["target_path"],
          "approved_by_label":approved_by_label,"nonce":nonce,"expires_at":expires_at,
          "identity_boundary":"LABEL_IS_NOT_CRYPTOGRAPHIC_IDENTITY_PROOF"}
    body["approval_id"]=hashlib.sha256(_canon(body)).hexdigest()
    return body

def _consumed_ids(path:Path)->set[str]:
    if not path.exists(): return set()
    ids=set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip(): ids.add(json.loads(line)["approval_id"])
    return ids

def verify(proposal_path:str|Path, target_path:str, approval:dict[str,Any], consumed_ledger:str|Path|None=None, now:datetime|None=None)->dict[str,Any]:
    if approval.get("schema")!=SCHEMA: return {"authorized":False,"reason":"schema"}
    expected=sha256_file(proposal_path)
    if approval.get("proposal_sha256")!=expected: return {"authorized":False,"reason":"proposal_hash_mismatch"}
    if approval.get("target_path")!=target_path: return {"authorized":False,"reason":"target_mismatch"}
    check=dict(approval); claimed=check.pop("approval_id",None)
    if hashlib.sha256(_canon(check)).hexdigest()!=claimed: return {"authorized":False,"reason":"approval_receipt_tampered"}
    if approval.get("expires_at"):
        t=now or datetime.now(timezone.utc)
        exp=datetime.fromisoformat(approval["expires_at"].replace("Z","+00:00"))
        if t>exp: return {"authorized":False,"reason":"expired"}
    if consumed_ledger and claimed in _consumed_ids(Path(consumed_ledger)):
        return {"authorized":False,"reason":"replay"}
    return {"authorized":True,"approval_id":claimed,"proposal_sha256":expected,
            "boundary":"HASH_AND_TARGET_BINDING_ONLY_NOT_HUMAN_IDENTITY_PROOF_AND_NOT_WRITE_AUTHORITY"}

def consume(consumed_ledger:str|Path, approval:dict[str,Any], *, outcome:str)->dict[str,Any]:
    p=Path(consumed_ledger); p.parent.mkdir(parents=True,exist_ok=True)
    if approval["approval_id"] in _consumed_ids(p): raise ValueError("approval already consumed")
    rec={"schema":CONSUME_SCHEMA,"approval_id":approval["approval_id"],"proposal_sha256":approval["proposal_sha256"],
         "target_path":approval["target_path"],"outcome":outcome}
    rec["receipt_sha256"]=hashlib.sha256(_canon(rec)).hexdigest()
    with p.open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(rec,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n")
    return rec
