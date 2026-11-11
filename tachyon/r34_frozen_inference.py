"""TACHYON R3.4: real frozen R31B numerical inference on question-only files.

No access to gold, salt, source measurements, network or training. An R31B
2-family regressor has NO numerical representation for other physics families.
When unsupported it always ABSTAINS. A self-reported receipt is not external
custody attestation or proof of a truly independent blind evaluation.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from tachyon.r31b_neural_formula import build
from tachyon.r31_reference_gate import FAMILY_ORDER
from tachyon.r33_external_custodian import (
    MODEL_SHA256, QUESTIONS_SCHEMA, PREDICTIONS_SCHEMA,
    sha,need,write_new
)

INFER_SCHEMA="janus.tachyon.r34.frozen_candidate_question_only_inference.v1"
TRANSPORT_KEYS={"schema","frozen_candidate_weights_sha256","case_count",
                "items","gold_answers_excluded","not_to_publish_to_public_repo",
                "questions_sha256"}
ITEM_KEYS={"case_id","category","family","question","source_url"}
SUPPORTED={
    "SR_PROPER_TIME_RATIO":re.compile(
        r"Для инерциальных часов при v/c=(0(?:\.\d{1,3})?) вычисли dτ/dt по СТО\."
    ),
    "TWO_LEVEL_BORN_PROBABILITY":re.compile(
        r"При измерении \|0><0\| двухуровневой системы с ρ00=(0(?:\.\d{1,3})?) вычисли P\(0\)\."
    )
}

def validate_transport(questions):
    need(isinstance(questions,dict) and set(questions)==TRANSPORT_KEYS,
         "R34_STRICT_QUESTION_TRANSPORT_SHAPE")
    need(questions["schema"]==QUESTIONS_SCHEMA
         and questions["frozen_candidate_weights_sha256"]==MODEL_SHA256
         and questions["gold_answers_excluded"] is True
         and questions["not_to_publish_to_public_repo"] is True,
         "R34_UNTRUSTED_QUESTION_TRANSPORT")
    expected_sha=sha({k:v for k,v in questions.items()
                     if k!="questions_sha256"})
    need(questions["questions_sha256"]==expected_sha,
         "R34_QUESTION_TRANSPORT_SHA_MISMATCH")
    items=questions["items"]
    need(isinstance(items,list) and 1<=len(items)<=300
         and questions["case_count"]==len(items),
         "R34_QUESTION_COUNT")
    seen=set()
    for row in items:
        need(isinstance(row,dict) and
             set(row).issubset(ITEM_KEYS) and
             {"case_id","category","family","question"}.issubset(row),
             "R34_UNKNOWN_FIELD_OR_GOLD_LEAK")
        case_id=row["case_id"]
        need(isinstance(case_id,str) and
             re.fullmatch(r"[A-Za-z0-9_-]{6,80}",case_id) is not None
             and case_id not in seen,"R34_CASE_DUPLICATE")
        seen.add(case_id)
        need(row["category"] in ("NUMERIC","CONCEPTUAL","OOD")
             and isinstance(row["family"],str)
             and 3<=len(row["family"])<=100
             and isinstance(row["question"],str)
             and 15<=len(row["question"])<=3000,
             "R34_QUESTION_INVALID")
        if "source_url" in row:
            need(isinstance(row["source_url"],str)
                 and len(row["source_url"])<=600
                 and row["source_url"].startswith("https://"),
                 "R34_UNTRUSTED_SOURCE_REFERENCE")
    return expected_sha

def frozen_model(checkpoint):
    import torch
    torch.set_num_threads(1)
    raw=Path(checkpoint).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    need(digest==MODEL_SHA256,"R34_CANDIDATE_SHA_MISMATCH")
    # weights_only prevents arbitrary deserialization of attacker Python code.
    frozen=torch.load(checkpoint,map_location="cpu",weights_only=True)
    need(isinstance(frozen,dict)
         and frozen.get("schema")=="janus.tachyon.r31b.neural_formula_candidate.v1"
         and frozen.get("family_ids")==list(FAMILY_ORDER)
         and frozen.get("hidden_width")==24
         and frozen.get("seed")==20261111
         and frozen.get("production_promotion") is False
         and frozen.get("physical_retrocausality_proven") is False,
         "R34_UNTRUSTED_MODEL_METADATA")
    network=build()
    network.load_state_dict(frozen["model_state"],strict=True)
    network.eval()
    return network,digest

def predict(questions,checkpoint):
    transport_sha=validate_transport(questions)
    network,weights_sha=frozen_model(checkpoint)
    import torch
    answers=[]
    counts=Counter()
    with torch.inference_mode():
        for row in questions["items"]:
            family=row["family"]
            question=row["question"]
            if row["category"]!="NUMERIC" or family not in SUPPORTED:
                answers.append({"case_id":row["case_id"],"kind":"abstain"})
                counts["unsupported_or_non_numeric_abstentions"]+=1
                continue
            m=SUPPORTED[family].fullmatch(question)
            if m is None:
                answers.append({"case_id":row["case_id"],"kind":"abstain"})
                counts["known_family_unparseable_abstentions"]+=1
                continue
            x=float(m.group(1))
            if not 0<=x<1:
                answers.append({"case_id":row["case_id"],"kind":"abstain"})
                counts["invalid_domain_abstentions"]+=1
                continue
            family_indicator=1.0 if family==FAMILY_ORDER[0] else -1.0
            features=torch.tensor([[x,family_indicator]],dtype=torch.float32)
            result=float(network(features).item())
            need(0<=result<=1,"R34_NONFINITE_OR_INVALID_FORWARD_OUTPUT")
            answers.append({"case_id":row["case_id"],"kind":"numeric",
                            "value":result,"unit":"1"})
            counts["real_frozen_neural_forward_calls"]+=1
    obj={
        "schema":PREDICTIONS_SCHEMA,
        "candidate_weights_sha256":weights_sha,
        "questions_sha256":transport_sha,
        "items":answers,
        "research_execution_metadata":{
            "schema":INFER_SCHEMA,
            "candidate_loaded_from_exact_frozen_sha":True,
            "candidate_model_updated":False,
            "network_access_or_external_source_query":False,
            "gold_or_salt_read":False,
            "actual_neural_forward_calls":counts["real_frozen_neural_forward_calls"],
            "unsupported_or_non_numeric_abstentions":counts[
                "unsupported_or_non_numeric_abstentions"],
            "known_family_unparseable_abstentions":counts[
                "known_family_unparseable_abstentions"],
            "new_family_predictive_generalization_demonstrated":False,
            "independent_external_custodian_signature_present":False,
            "scientific_admission":"HOLD",
            "production_promotion":False
        }
    }
    obj["predictions_receipt_sha256"]=sha(obj)
    return obj

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--questions-only",required=True)
    p.add_argument("--frozen-model",required=True)
    p.add_argument("--predictions-out",required=True)
    args=p.parse_args()
    qs=json.loads(Path(args.questions_only).read_text(encoding="utf8"))
    pred=predict(qs,args.frozen_model)
    write_new(args.predictions_out,pred)
    result=pred["research_execution_metadata"]
    print(json.dumps({
        "questions_seen":len(pred["items"]),
        "actual_neural_forward_calls":result["actual_neural_forward_calls"],
        "unsupported_abstentions":result[
            "unsupported_or_non_numeric_abstentions"],
        "independent_external_blind_proven":False,
        "scientific_admission":"HOLD",
    },sort_keys=True))

if __name__=="__main__":
    main()
