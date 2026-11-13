"""ESSENCE public mailbox subscriber: no authority on untrusted peer messages."""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/".janus/essence"))
import peer_mailbox_v10 as m

local_path=ROOT/".janus/essence/innovations.json"

def sample():
    raw=local_path.read_bytes()
    repo=json.loads(raw)["repository"]
    original=json.loads(raw)["entries"][0]
    message={
        "message_id":"local-peer-test-01",
        "from_repository":"Hawkar-usls/Janus_Genesis",
        "to_repository":repo,
        "in_reply_to_idea_id":original["id"],
        "role":original["role"],
        "source_innovations_git_blob_sha1":m.git_blob(raw),
        "source_document_sha256":original["evidence_sha256"],
        "source_origin_receipt_sha256":original["origin_receipt_sha256"],
        "response":"IDEA_RECEIVED_RESEARCH_MICROCORE_GENERATED_BUT_UNVERIFIED",
        "action_requested":"COLLECT_NEW_FUTURE_PAIRED_TASK_EVIDENCE_ONLY",
    }
    round_data={
        "schema":m.ROUND_SCHEMA,"publisher":"Hawkar-usls/Janus_Genesis",
        "published_via":"REVIEWED_META_REGISTRY_GITHUB_PR",
        "message_type":"RESEARCH_REPLY_TO_PUBLIC_INNOVATION",
        "messages":[message],
        "message_limits":{"working_model_mutation_allowed":False,
                          "recipient_code_execution_allowed":False,
                          "subscriber_delivery_acked":False},
    }
    encoded=m.canonical(round_data)
    index={
        "schema":m.IDX_SCHEMA,
        "current_round_path":"data/essence_peer_mailbox/round-2026-11-13-v1.json",
        "current_round_git_blob_sha1":m.git_blob(encoded),
        "status":"PUBLIC_READ_ONLY_DATA_NOT_EXECUTABLE_AUTHORITY",
        "updates":"REVIEWED_PR_ONLY","records_are_append_only":True,
    }
    return repo,raw,index,round_data

def run(data=None):
    repo,raw,index,round_data=sample()
    if data:
        data(index,round_data)
    rd=m.canonical(round_data)
    if not data:
        index["current_round_git_blob_sha1"]=m.git_blob(rd)
    return m.consume(repo,raw,m.canonical(index),rd,index["current_round_git_blob_sha1"])

class InboundMailboxContracts(unittest.TestCase):
    def test_actual_local_origin_is_bound(self):
        repo,raw,idx,d=sample()
        self.assertIn(repo,m.RECEIVERS)
        self.assertEqual(len(json.loads(raw)["entries"]),1)
        self.assertIn(json.loads(raw)["entries"][0]["role"],("memory","recovery"))

    def test_synthetic_reply_seen_and_stays_research(self):
        r=run()
        self.assertTrue(r["cross_repository_reply_received"])
        self.assertEqual(r["message_count_addressed"],1)
        self.assertFalse(r["production_authority"])
        self.assertFalse(r["source_code_executed"])
        self.assertFalse(r["generation_advanced"])
        self.assertFalse(r["outbound_messages_sent"])
        self.assertEqual(r["receipt_sha256"],m.digest({k:v for k,v in r.items() if k!="receipt_sha256"}))

    def test_tampered_round_denied(self):
        repo,raw,idx,d=sample()
        rd=m.canonical(d)
        with self.assertRaisesRegex(ValueError,"PEER_INDEX_OR_ROUND_INTEGRITY_HOLD"):
            m.consume(repo,raw,m.canonical(idx),rd+b" ",idx["current_round_git_blob_sha1"])

    def test_forged_authority_denied(self):
        def mutate(i,d):
            d["message_limits"]["working_model_mutation_allowed"]=True
            i["current_round_git_blob_sha1"]=m.git_blob(m.canonical(d))
        with self.assertRaisesRegex(ValueError,"PEER_UNTRUSTED_AUTHORITY"):
            run(mutate)

    def test_garbled_own_origin_sha_denied(self):
        def mutate(i,d):
            d["messages"][0]["source_document_sha256"]="a"*64
            i["current_round_git_blob_sha1"]=m.git_blob(m.canonical(d))
        with self.assertRaisesRegex(ValueError,"PEER_IDEA_ANCHOR_MISMATCH"):
            run(mutate)

    def test_fake_local_blob_sha_denied(self):
        def mutate(i,d):
            d["messages"][0]["source_innovations_git_blob_sha1"]="f"*40
            i["current_round_git_blob_sha1"]=m.git_blob(m.canonical(d))
        with self.assertRaisesRegex(ValueError,"PEER_MESSAGE_UNAUTHENTICATED"):
            run(mutate)

    def test_duplicate_message_denied(self):
        def mutate(i,d):
            d["messages"].append(copy.deepcopy(d["messages"][0]))
            i["current_round_git_blob_sha1"]=m.git_blob(m.canonical(d))
        with self.assertRaisesRegex(ValueError,"PEER_DUPLICATE_ID"):
            run(mutate)

    def test_unrelated_message_not_for_repo_ignored(self):
        def mutate(i,d):
            d["messages"][0]["to_repository"]="Hawkar-usls/SomeOtherRepo"
            i["current_round_git_blob_sha1"]=m.git_blob(m.canonical(d))
        self.assertFalse(run(mutate)["cross_repository_reply_received"])

    def test_network_path_traversal_denied_before_fetch(self):
        with self.assertRaisesRegex(ValueError,"UNAPPROVED_META_REGISTRY_PATH"):
            m.get("../private")

if __name__=="__main__":
    unittest.main()
