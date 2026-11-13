#!/usr/bin/env python3
"""ESSENCE v1.0 public cross-repo reply subscriber, strictly read-only.

Queries a pinned index in the append-only JANUS Meta Registry over HTTPS,
verifies Git blob bytes and the local originating idea, and emits a receipt.
This never dispatches jobs, modifies a Git repository, imports other
repositories' Python, loads weights or grants production authority.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import re
import urllib.request

OWNER="Hawkar-usls"
META="Hawkar-usls/janus-meta-registry"
INDEX="data/essence_peer_mailbox/index.json"
PATH_PREFIX="data/essence_peer_mailbox/round-"
IDX_SCHEMA="janus.essence.peer_mailbox_index/1.0"
ROUND_SCHEMA="janus.essence.peer_mailbox_round/1.0"
INNOV_SCHEMA="janus.essence.innovations/0.1"
RECEIPT_SCHEMA="janus.essence.peer_reply_consumed/1.0"
RECEIVERS=frozenset(("Hawkar-usls/janus-distributed-ai-swarm","Hawkar-usls/Demi_Head"))
HEX40=re.compile(r"^[0-9a-f]{40}$")
HEX64=re.compile(r"^[0-9a-f]{64}$")
MAX_BYTES=100_000

def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()

def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()

def git_blob(raw):
    return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()

def obj(raw):
    if len(raw)>MAX_BYTES:raise ValueError("PEER_OVERSIZED_PAYLOAD")
    return json.loads(raw,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("NONFINITE_JSON")))

def get(path):
    if not (path==INDEX or (path.startswith(PATH_PREFIX) and
            re.fullmatch(r"data/essence_peer_mailbox/round-[0-9a-z-]{4,70}\.json",path))):
        raise ValueError("UNAPPROVED_META_REGISTRY_PATH")
    request=urllib.request.Request(
        f"https://api.github.com/repos/{META}/contents/{path}?ref=main",
        headers={"Accept":"application/vnd.github+json",
                 "User-Agent":"JANUS-ESSENCE-Peer-Mailbox/1"})
    with urllib.request.urlopen(request,timeout=15) as conn:
        data=conn.read(200_001)
    if len(data)>200_000:raise ValueError("PEER_API_OVERSIZE")
    response=obj(data)
    if (response.get("type")!="file" or response.get("encoding")!="base64"
        or not isinstance(response.get("sha"),str)):
        raise ValueError("UNTRUSTED_GITHUB_CONTENT")
    raw=base64.b64decode(response["content"],validate=False)
    if git_blob(raw)!=response["sha"]:
        raise ValueError("GITHUB_SOURCE_BLOB_MISMATCH")
    return raw,response["sha"]

def consume(repo,local_raw,index_raw,round_raw,round_blob):
    if repo not in RECEIVERS:raise ValueError("PEER_NOT_APPROVED_RECEIVER")
    ideas=obj(local_raw);idx=obj(index_raw);round_doc=obj(round_raw)
    if (ideas.get("schema")!=INNOV_SCHEMA or ideas.get("repository")!=repo
        or ideas.get("authority")!="RESEARCH_PROPOSAL_ONLY"):
        raise ValueError("LOCAL_GENE_SOURCE_NOT_VERIFIED")
    if (idx.get("schema")!=IDX_SCHEMA
        or idx.get("current_round_path") is None
        or idx.get("status")!="PUBLIC_READ_ONLY_DATA_NOT_EXECUTABLE_AUTHORITY"
        or idx.get("updates")!="REVIEWED_PR_ONLY"
        or idx.get("records_are_append_only") is not True
        or not HEX40.fullmatch(str(idx.get("current_round_git_blob_sha1","")))
        or idx["current_round_git_blob_sha1"]!=round_blob
        or git_blob(round_raw)!=round_blob):
        raise ValueError("PEER_INDEX_OR_ROUND_INTEGRITY_HOLD")
    if (round_doc.get("schema")!=ROUND_SCHEMA
        or round_doc.get("publisher")!="Hawkar-usls/Janus_Genesis"
        or round_doc.get("published_via")!="REVIEWED_META_REGISTRY_GITHUB_PR"
        or round_doc.get("message_type")!="RESEARCH_REPLY_TO_PUBLIC_INNOVATION"
        or round_doc.get("message_limits",{}).get("working_model_mutation_allowed") is not False
        or round_doc.get("message_limits",{}).get("recipient_code_execution_allowed") is not False
        or round_doc.get("message_limits",{}).get("subscriber_delivery_acked") is not False):
        raise ValueError("PEER_UNTRUSTED_AUTHORITY")
    all_messages=round_doc.get("messages")
    if not isinstance(all_messages,list) or not 1<=len(all_messages)<=16:
        raise ValueError("PEER_UNBOUNDED_MAILBOX")
    seen=set();matches=[]
    local={x["id"]:x for x in ideas.get("entries",[])}
    for msg in all_messages:
        if not isinstance(msg,dict) or not isinstance(msg.get("message_id"),str):
            raise ValueError("PEER_BAD_MESSAGE")
        if msg["message_id"] in seen:raise ValueError("PEER_DUPLICATE_ID")
        seen.add(msg["message_id"])
        if msg.get("to_repository")!=repo:continue
        if (msg.get("from_repository")!="Hawkar-usls/Janus_Genesis"
            or msg.get("response")!="IDEA_RECEIVED_RESEARCH_MICROCORE_GENERATED_BUT_UNVERIFIED"
            or msg.get("source_innovations_git_blob_sha1")!=git_blob(local_raw)
            or msg.get("action_requested") not in (
                "COLLECT_NEW_FUTURE_PAIRED_TASK_EVIDENCE_ONLY",
                "RETAIN_STRONG_CHECKSUM_CHECKER_AND_PROSPECTIVE_HOLDOUT_ONLY")):
            raise ValueError("PEER_MESSAGE_UNAUTHENTICATED")
        item=local.get(msg.get("in_reply_to_idea_id"))
        if (not isinstance(item,dict)
            or item.get("role")!=msg.get("role")
            or item.get("evidence_sha256")!=msg.get("source_document_sha256")
            or item.get("origin_receipt_sha256")!=msg.get("source_origin_receipt_sha256")):
            raise ValueError("PEER_IDEA_ANCHOR_MISMATCH")
        matches.append({"message_id":msg["message_id"],
                        "idea_id":item["id"],"role":item["role"],
                        "evidence_sha256":item["evidence_sha256"],
                        "receipt":"RESEARCH_REPLY_OBSERVED_NOT_PROVEN_IMPROVEMENT"})
    result={
        "schema":RECEIPT_SCHEMA,"repository":repo,
        "registry_repository":META,
        "registry_round_path":idx["current_round_path"],
        "registry_round_git_blob_sha1":round_blob,
        "message_count_addressed":len(matches),
        "messages":matches,
        "input_class":"PUBLIC_GITHUB_READONLY_MESSAGE",
        "cross_repository_reply_received":bool(matches),
        "independent_performance_gain":"NOT_ESTABLISHED",
        "reply_is_not_external_scientific_attestation":True,
        "source_code_executed":False,
        "production_authority":False,
        "generation_advanced":False,
        "outbound_messages_sent":False,
    }
    result["receipt_sha256"]=digest(result)
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo",required=True)
    parser.add_argument("--local",default=".janus/essence/innovations.json")
    parser.add_argument("--out",required=True)
    args=parser.parse_args()
    local_path=Path(args.local)
    if local_path.is_symlink() or not local_path.is_file() or local_path.stat().st_size>MAX_BYTES:
        raise ValueError("PEER_LOCAL_SOURCE_UNSAFE")
    raw_local=local_path.read_bytes()
    index_raw,_=get(INDEX)
    index=obj(index_raw)
    round_path=index.get("current_round_path")
    if not isinstance(round_path,str):
        raise ValueError("PEER_INDEX_PATH_MISSING")
    round_raw,round_sha=get(round_path)
    report=consume(args.repo,raw_local,index_raw,round_raw,round_sha)
    output=Path(args.out)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf-8") as fp:
        json.dump(report,fp,sort_keys=True,indent=2);fp.write("\n")
    print(json.dumps({"repo":args.repo,
        "addressed":report["message_count_addressed"],
        "status":"REPLY_RECEIVED_RESEARCH_ONLY" if report["cross_repository_reply_received"] else "NO_NEW_REPLIES",
        "production_authority":False}))
if __name__=="__main__":
    main()
