"""R3.3 independent-custodian OFFLINE, salted challenge seal and local scoring.

No private challenge/answers are uploaded, printed, logged, or used for training.
The code is NOT an assessor, cryptographic signature service or independent
measurement laboratory. Evidence of independence requires external signature.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime,timezone
import hashlib
import json
import math
from pathlib import Path
import re

MODEL_SHA256="b3b36dfb3e8c1d0d4a1ae1b867978cfa5f8f28d6768d1a42efac02a4d2e47f01"
CHALLENGE_SCHEMA="janus.tachyon.r33.private_challenge.v1"
COMMITMENT_SCHEMA="janus.tachyon.r33.salted_challenge_commitment.v1"
QUESTIONS_SCHEMA="janus.tachyon.r33.questions_only_transport.v1"
PREDICTIONS_SCHEMA="janus.tachyon.r33.custodian_collected_predictions.v1"
RESULT_SCHEMA="janus.tachyon.r33.local_blind_assessor_scoring_receipt.v1"
CATEGORIES=("NUMERIC","CONCEPTUAL","OOD")
NOISY_FAMILIES=frozenset(("SR_PROPER_TIME_RATIO","TWO_LEVEL_BORN_PROBABILITY"))
RUBRIC={
    "numeric_absolute_tolerance":0.0001,
    "numeric_relative_tolerance":0.01,
    "units_must_match_exactly":True,
    "ood_correct_response":"ABSTAIN",
    "conceptual_scored_automatically":False
}

def need(ok,msg):
    if not ok:raise ValueError(msg)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def hexdigest(raw):
    return hashlib.sha256(raw).hexdigest()

def sha(obj):
    return hexdigest(canonical(obj))

def read_obj(path):
    o=json.loads(Path(path).read_text(encoding="utf-8"))
    need(isinstance(o,dict),"R33_JSON_NOT_OBJECT")
    return o

def validate(pack):
    need(pack.get("schema")==CHALLENGE_SCHEMA,"R33_CHALLENGE_SCHEMA")
    items=pack.get("items")
    need(isinstance(items,list) and len(items)>=60 and len(items)<=300,
         "R33_CHALLENGE_SIZE")
    counts=Counter()
    ids=set()
    for row in items:
        need(isinstance(row,dict),"R33_BAD_ITEM")
        case_id=row.get("case_id")
        need(isinstance(case_id,str) and
             re.fullmatch(r"[A-Za-z0-9_-]{6,80}",case_id) is not None and
             case_id not in ids,"R33_DUPLICATE_OR_INVALID_CASE")
        ids.add(case_id)
        category=row.get("category")
        need(category in CATEGORIES,"R33_INVALID_CATEGORY")
        counts[category]+=1
        family=row.get("family")
        need(isinstance(family,str) and 3<=len(family)<=100
             and family not in NOISY_FAMILIES,"R33_TRAINING_FAMILY_LEAK")
        question=row.get("question")
        need(isinstance(question,str) and 15<=len(question)<=3000,
             "R33_MISSING_PRIVATE_QUESTION")
        gold=row.get("gold")
        need(isinstance(gold,dict),"R33_MISSING_GOLD")
        if category=="NUMERIC":
            need(gold.get("kind")=="numeric" and
                 type(gold.get("value")) in (int,float) and
                 math.isfinite(gold["value"]) and
                 isinstance(gold.get("unit"),str)
                 and 1<=len(gold["unit"])<=60,"R33_INVALID_NUMERIC_GOLD")
        elif category=="OOD":
            need(gold=={"kind":"abstain"},"R33_OOD_GOLD_MUST_ABSTAIN")
        else:
            need(gold.get("kind")=="conceptual" and
                 isinstance(gold.get("rubric"),str) and
                 15<=len(gold["rubric"])<=3000,"R33_CONCEPTUAL_REQUIRES_HUMAN_RUBRIC")
        if category!="OOD":
            source=row.get("source_url")
            need(isinstance(source,str) and source.startswith("https://")
                 and len(source)<=600,"R33_NO_SOURCE_PROVENANCE")
    need(all(counts[c]>=20 for c in CATEGORIES),"R33_MIN_20_PER_CATEGORY")
    return dict(counts)

def salt_from_file(path):
    """Private file: 32 random bytes encoded as 64 hexadecimal characters."""
    raw=Path(path).read_text(encoding="ascii").strip()
    need(len(raw)>=64 and len(raw)%2==0 and
         re.fullmatch(r"[0-9a-fA-F]+",raw) is not None,
         "R33_SECRET_SALT_REQUIRES_AT_LEAST_256_BITS")
    return bytes.fromhex(raw)

def model_sha(path):
    digest=hexdigest(Path(path).read_bytes())
    need(digest==MODEL_SHA256,"R33_WRONG_FROZEN_MODEL_SHA")
    return digest

def sealed_commitment(pack,salt,model_digest,now=None):
    counts=validate(pack)
    need(isinstance(salt,bytes) and len(salt)>=32,"R33_WEAK_PRIVATE_SALT")
    need(model_digest==MODEL_SHA256,"R33_WRONG_FROZEN_MODEL_SHA")
    witnessed_at=now or datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    result={
        "schema":COMMITMENT_SCHEMA,
        "challenge_commitment_sha256":hexdigest(salt+canonical(pack)),
        "model_weights_sha256":model_digest,
        "fixed_rubric_sha256":sha(RUBRIC),
        "rubric":RUBRIC,
        "case_count":sum(counts.values()),
        "category_counts":counts,
        "local_clock_seal_utc_not_independently_timestamped":witnessed_at,
        "secret_salt_published":False,
        "private_question_or_answer_keys_published":False,
        "independent_external_signature_present":False,
        "independent_custodian_verified":False,
        "scientific_admission":"HOLD",
        "model_weights_retrained":False,
    }
    result["receipt_sha256"]=sha(result)
    return result

def questions_only(pack,model_digest):
    counts=validate(pack)
    result={
        "schema":QUESTIONS_SCHEMA,
        "frozen_candidate_weights_sha256":model_digest,
        "case_count":sum(counts.values()),
        "items":[
            {k:v for k,v in item.items() if k!="gold"}
            for item in pack["items"]
        ],
        "gold_answers_excluded":True,
        "not_to_publish_to_public_repo":True,
    }
    need(all("gold" not in v for v in result["items"]),
         "R33_QUESTION_GOLD_LEAK")
    return result

def evaluate_private(pack,salt,sealed,predictions,weights_digest):
    counts=validate(pack)
    need(weights_digest==MODEL_SHA256,"R33_WRONG_FROZEN_MODEL_SHA")
    need(sealed.get("schema")==COMMITMENT_SCHEMA and
         sealed.get("receipt_sha256")==sha({
             k:v for k,v in sealed.items() if k!="receipt_sha256"
         }),"R33_BAD_SEAL_RECEIPT")
    need(sealed.get("model_weights_sha256")==weights_digest
         and sealed.get("fixed_rubric_sha256")==sha(RUBRIC)
         and sealed.get("challenge_commitment_sha256")==
             hexdigest(salt+canonical(pack)),
         "R33_SALT_GOLD_OR_CANDIDATE_MISMATCH")
    need(predictions.get("schema")==PREDICTIONS_SCHEMA
         and predictions.get("candidate_weights_sha256")==weights_digest,
         "R33_PREDICTION_MODEL_MISMATCH")
    out=predictions.get("items")
    need(isinstance(out,list) and len(out)==len(pack["items"]),
         "R33_MISSING_PREDICTIONS")
    pred={}
    for answer in out:
        need(isinstance(answer,dict) and
             isinstance(answer.get("case_id"),str) and
             answer["case_id"] not in pred and
             answer.get("kind") in ("numeric","conceptual","abstain"),
             "R33_DUPLICATE_OR_BAD_PREDICTION")
        pred[answer["case_id"]]=answer
    need(set(pred)=={v["case_id"] for v in pack["items"]},
         "R33_QUESTION_SET_DRIFT")
    numeric_total=0;numeric_correct=0;ood_total=0;ood_correct=0
    unsupported_numeric=0
    for item in pack["items"]:
        kind=item["category"];got=pred[item["case_id"]]
        if kind=="NUMERIC":
            numeric_total+=1
            if got["kind"]=="numeric":
                v=got.get("value")
                good=(type(v) in (int,float) and math.isfinite(v) and
                      got.get("unit")==item["gold"]["unit"] and
                      abs(v-item["gold"]["value"])<=max(
                          RUBRIC["numeric_absolute_tolerance"],
                          RUBRIC["numeric_relative_tolerance"]*
                          abs(item["gold"]["value"])))
                numeric_correct+=int(good)
                unsupported_numeric+=1
        elif kind=="OOD":
            ood_total+=1
            ood_correct+=int(got["kind"]=="abstain")
    result={
        "schema":RESULT_SCHEMA,
        "sealed_commitment_receipt_sha256":sealed["receipt_sha256"],
        "model_weights_sha256":weights_digest,
        "predictions_sha256":sha(predictions),
        "private_challenge_sha256_omitted_to_avoid_key_disclosure":True,
        "challenge_case_count":len(pack["items"]),
        "numeric_scored_count":numeric_total,
        "numeric_correct_count":numeric_correct,
        "ood_scored_count":ood_total,
        "ood_correct_abstention_count":ood_correct,
        "conceptual_pending_independent_manual_review":counts["CONCEPTUAL"],
        "new_family_numeric_predictions_attempted":unsupported_numeric,
        "automatic_total_physics_accuracy_not_reported":True,
        "independent_external_custodian_signature_verified":False,
        "predictions_actually_executed_by_candidate_not_cryptographically_verified":True,
        "challenge_created_by_independent_custodian_not_verified":True,
        "source_families_absent_from_neural_training":True,
        "scientific_admission":"HOLD",
        "production_promotion":False,
        "no_model_training_performed":True,
    }
    result["receipt_sha256"]=sha(result)
    return result

def write_new(path,object):
    p=Path(path)
    need(not p.exists(),"R33_REFUSE_OVERWRITE")
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(object,indent=2,ensure_ascii=False,
                            sort_keys=True)+"\n",encoding="utf8")

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="action",required=True)
    seal=sub.add_parser("seal")
    seal.add_argument("--private",required=True,
                      help="Custodian-only original question+gold file; never upload")
    seal.add_argument("--salt-file",required=True,
                      help="Custodian private hex salt of >=32 random bytes")
    seal.add_argument("--frozen-model",required=True)
    seal.add_argument("--public-commitment-out",required=True)
    seal.add_argument("--questions-only-out",required=True,
                      help="Keep private: transport to candidate only after sealing")
    score=sub.add_parser("score")
    score.add_argument("--private",required=True)
    score.add_argument("--salt-file",required=True)
    score.add_argument("--frozen-model",required=True)
    score.add_argument("--sealed",required=True)
    score.add_argument("--predictions",required=True)
    score.add_argument("--public-summary-out",required=True)
    args=p.parse_args()
    pack=read_obj(args.private)
    salt=salt_from_file(args.salt_file)
    weights=model_sha(args.frozen_model)
    if args.action=="seal":
        sealed=sealed_commitment(pack,salt,weights)
        questions=questions_only(pack,weights)
        write_new(args.public_commitment_out,sealed)
        write_new(args.questions_only_out,questions)
        print("R33_SALT_SHA_COMMITMENT_WRITTEN_WITHOUT_PRIVATE_ANSWERS")
    else:
        sealed=read_obj(args.sealed)
        predictions=read_obj(args.predictions)
        report=evaluate_private(pack,salt,sealed,predictions,weights)
        write_new(args.public_summary_out,report)
        print(json.dumps({
            "technical_score_written":True,
            "new_families_blind_proof":False,
            "independent_signature_verified":False,
            "scientific_admission":"HOLD",
        },sort_keys=True))

if __name__=="__main__":main()
