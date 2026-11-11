"""TACHYON-R2D read-only frozen-model answer audit.

This is a TRANSPARENT PUBLIC DEVELOPMENT probe by default. It is NOT a hidden,
independent, or laboratory-validated benchmark. External custodians can run the
same CLI on their own unreleased questions and secret scoring key outside GitHub.

No retraining, no model promotion, no production writes.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from tachyon.science_generator import build_model, generate, load_json, sha, ScienceHold, require
from tachyon.r2c_grounded import new_source_rows, retrieve, review_gate

MODEL_SHA = {
    "r2b": "3adbf7b11a0f4275ab565ea833c7d415fc0e6727ddddf48e5a27f04346350f9c",
    "r2c": "4fde3d9c46dd7a11913de97348e97eb11d6b48cbed4a14cee17963c040b8aae8",
}
MODEL_SCHEMAS = {
    "r2b": "janus.tachyon.r2b.seq2seq_explanation.v1",
    "r2c": "janus.tachyon.r2c.source_grounded_generator.v1",
}
SOURCE_CARD_SHA = "21a27ab618d94e1d15d586c20432b8e766cb947eb947b1035a045ef764c8337e"
CASE_ID = re.compile(r"^[a-z][a-z0-9_]{1,64}$")
NUMBER = re.compile(r"(?<![\w.])[-+]?(?:\d+[.,]\d+|\d+)(?:[eE][-+]?\d+)?(?![\w.])")
SPEED = re.compile(r"v\s*/\s*c\s*=\s*(0[.,]\d+)", re.I)
RHO = re.compile(r"ρ\s*00\s*=\s*(0[.,]\d+)", re.I)
ABSTAIN_PHRASES = ("не знаю", "недостаточно данных", "нет информации",
                   "не могу ответить", "не располагаю", "неизвестно")

def read_json(path):
    obj, _ = load_json(path)
    return obj

def save_new(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("x", encoding="utf8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")

def public_split(fixture_path):
    obj = read_json(fixture_path)
    require(obj.get("schema") == "janus.tachyon.r2d.public_dev_fixture.v1"
            and obj.get("status") == "PUBLIC_POSTHOC_DEVELOPMENT_ONLY_NOT_INDEPENDENT_BLIND",
            "PUBLIC_DEV_FIXTURE_ONLY")
    cases = obj.get("cases")
    require(isinstance(cases, list) and len(cases) == 18, "PUBLIC_DEV_CASES")
    question_cases = []
    key_cases = []
    for case in cases:
        cid = case.get("case_id")
        require(isinstance(cid,str) and CASE_ID.fullmatch(cid), "BAD_CASE_ID")
        require(isinstance(case.get("question"),str) and 10 <= len(case["question"]) <= 500,
                "BAD_QUESTION")
        question_cases.append({"case_id":cid,"question":case["question"]})
        key_cases.append({k:v for k,v in case.items() if k not in ("question",)})
    require(len({c["case_id"] for c in question_cases})==len(cases),"DUPLICATE_CASE_ID")
    questions={"schema":"janus.tachyon.r2d.questions_only.v1",
               "scope":"PUBLIC_DEVELOPMENT", "cases":question_cases}
    key={"schema":"janus.tachyon.r2d.scoring_key.v1",
         "scope":"PUBLIC_DEVELOPMENT", "cases":key_cases}
    return questions,key

def validate_questions(obj):
    require(obj.get("schema")=="janus.tachyon.r2d.questions_only.v1","QUESTION_SCHEMA")
    require(obj.get("scope") in ("PUBLIC_DEVELOPMENT","PRIVATE_EXTERNAL"),"QUESTION_SCOPE")
    cases=obj.get("cases")
    require(isinstance(cases,list) and 1 <= len(cases) <= 1000,"QUESTION_COUNT")
    seen=set()
    for case in cases:
        require(isinstance(case,dict) and set(case)=={"case_id","question"},
                "QUESTIONS_CONTAIN_SCORING_LABELS")
        cid=case["case_id"];q=case["question"]
        require(isinstance(cid,str) and CASE_ID.fullmatch(cid) and cid not in seen,
                "BAD_OR_DUPLICATE_CASE_ID")
        require(isinstance(q,str) and 10 <= len(q) <= 1000,"QUESTION_TEXT")
        seen.add(cid)
    return cases

def load_frozen_model(which,path):
    import torch
    p=Path(path)
    require(p.is_file() and sha(p.read_bytes())==MODEL_SHA[which], "FROZEN_MODEL_SHA_MISMATCH")
    checkpoint=torch.load(p, map_location="cpu", weights_only=True)
    require(checkpoint.get("schema")==MODEL_SCHEMAS[which]
            and checkpoint.get("auto_deploy") is False, "NOT_FROZEN_RESEARCH_MODEL")
    if which=="r2c":
        require(checkpoint.get("holdout_data_in_training") is False
                and checkpoint.get("train_input_shas",[None]*3)[2]==SOURCE_CARD_SHA,
                "R2C_SOURCE_INTEGRITY_FAILED")
    net=build_model(len(checkpoint["vocab"]), checkpoint["width"])
    net.load_state_dict(checkpoint["model_state"])
    net.eval()
    return net,checkpoint["vocab"]

def formula_response(question):
    """Independent, transparent formula baseline; limited to explicit toy syntax."""
    speed=SPEED.search(question)
    rho=RHO.search(question)
    if speed and not rho:
        beta=float(speed.group(1).replace(",","."))
        if 0 <= beta < 1:
            return {"text":"Числовой ответ: "+format(math.sqrt(1-beta*beta),".10g"),
                    "rule":"SR_PROPER_TIME_RATIO"}
    if rho and not speed:
        value=float(rho.group(1).replace(",","."))
        if 0 <= value <= 1:
            return {"text":"Числовой ответ: "+format(value,".10g"),
                    "rule":"TWO_LEVEL_BORN_PROBABILITY"}
    return {"text":"ABSTAIN", "rule":"NO_APPLICABLE_FORMULA"}

def predict_questions(questions, cards, r2b_path, r2c_path):
    import torch
    torch.set_num_threads(2)
    cases=validate_questions(questions)
    require(sha(Path(cards).read_bytes())==SOURCE_CARD_SHA,"SOURCE_CARD_SHA_MISMATCH")
    dataset,_,_=new_source_rows(cards)
    model_b,vocab_b=load_frozen_model("r2b",r2b_path)
    model_c,vocab_c=load_frozen_model("r2c",r2c_path)
    results=[]
    for case in cases:
        q=case["question"]
        hits=retrieve(q,dataset)
        gate=review_gate(q,hits)
        formula=formula_response(q)
        results.append({
            "case_id":case["case_id"],
            "r2b_neural":{"text":generate(model_b,vocab_b,q,max_tokens=48),
                          "status":"UNVERIFIED_NEURAL_GENERATION"},
            "r2c_neural":{"text":generate(model_c,vocab_c,q,max_tokens=48),
                          "status":"UNVERIFIED_NEURAL_GENERATION"},
            "r2c_retrieval":{"text":hits[0]["answer"] if hits else "ABSTAIN",
                            "decision":gate["decision"],
                            "family":hits[0]["family"] if hits else None,
                            "doi":hits[0]["doi"] if hits else None,
                            "status":"SOURCE_PARAPHRASE_NOT_SCIENCE_REVIEW"},
            "formula_baseline":formula,
        })
    return {
        "schema":"janus.tachyon.r2d.predictions.v1",
        "scope":questions["scope"],"question_count":len(cases),
        "candidate_models_sha256":MODEL_SHA,
        "source_cards_sha256":SOURCE_CARD_SHA,
        "no_training_or_backprop":True,
        "independent_scientific_assessment":False,
        "model_scientifically_admitted":False,
        "results":results,
    }

def numeric_in_answer(text, expected, tolerance):
    """Weak textual numeric probe, not an interpretation of physical meaning."""
    values=[]
    for m in NUMBER.finditer(text or ""):
        try:
            x=float(m.group(0).replace(",","."))
            if math.isfinite(x) and abs(x) <= 1e6:
                values.append(x)
        except ValueError:
            pass
    return any(abs(x-expected)<=tolerance for x in values),values[:12]

def wilson(success,n,z=1.959963984540054):
    if n==0:return None
    p=success/n
    denom=1+z*z/n
    center=(p+z*z/(2*n))/denom
    radius=(z/denom)*math.sqrt(p*(1-p)/n+z*z/(4*n*n))
    return [round(max(0,center-radius),4),round(min(1,center+radius),4)]

def suspected_causal_claim(text):
    """Red-flag words only; negation/physics still requires expert checking."""
    s=(text or "").lower()
    has_past=any(x in s for x in ("прошл","назад во времен","ретрокауз"))
    has_promise=any(x in s for x in ("доказан", "гарантирован", "точно возможн",
                                      "можно передат", "позволяет передат"))
    has_negation=any(x in s for x in ("не доказан", "не позволяет", "нельзя",
                                       "не является", "не означает"))
    return has_past and has_promise and not has_negation

def score_predictions(predictions, key, committed_key_sha256, raw_key_sha256,
                      external_custodian_id=None):
    require(predictions.get("schema")=="janus.tachyon.r2d.predictions.v1",
            "PREDICTIONS_SCHEMA")
    require(predictions.get("candidate_models_sha256")==MODEL_SHA
            and predictions.get("source_cards_sha256")==SOURCE_CARD_SHA,
            "FROZEN_MANIFEST_MISMATCH")
    require(predictions.get("no_training_or_backprop") is True
            and predictions.get("model_scientifically_admitted") is False,
            "PREDICTIONS_AUTHORITY_ESCALATION")
    require(key.get("schema")=="janus.tachyon.r2d.scoring_key.v1"
            and key.get("scope")==predictions.get("scope"),"KEY_SCOPE")
    require(committed_key_sha256==raw_key_sha256,"KEY_SHA_SEAL_MISMATCH")
    cases=key.get("cases");outputs=predictions.get("results")
    require(isinstance(cases,list) and isinstance(outputs,list), "CASE_STRUCTURE")
    require(len({c.get("case_id") for c in cases})==len(cases),"DUPLICATE_GOLD_IDS")
    require(len({c.get("case_id") for c in outputs})==len(outputs),"DUPLICATE_PRED_IDS")
    by_id={c["case_id"]:c for c in cases}
    require(set(by_id)=={o.get("case_id") for o in outputs},"CASE_IDS_MISMATCH")
    scope=key["scope"]
    if scope=="PRIVATE_EXTERNAL":
        require(external_custodian_id and len(external_custodian_id)>=6,"EXTERNAL_CUSTODIAN_ID_REQUIRED")
        # Self-declaration cannot prove independence or time of commitment.
        require(len(cases)>=60, "INSUFFICIENT_PRIVATE_CASE_COUNT")
        for kind in ("numeric","conceptual","out_of_domain"):
            require(sum(c.get("kind")==kind for c in cases)>=20,
                    "INSUFFICIENT_PRIVATE_STRATUM")
    arms=("r2b_neural","r2c_neural","r2c_retrieval","formula_baseline")
    metrics={a:{"numeric_exact_text_match":0,"numeric_count":0,
                 "gold_family_match":0,"conceptual_count":0,
                 "ood_abstentions":0,"ood_count":0,
                 "suspected_unsupported_causal_claims":0}
             for a in arms}
    private_rows=[]; public_rows=[]
    for out in outputs:
        gold=by_id[out["case_id"]]
        kind=gold.get("kind")
        require(kind in ("numeric","conceptual","out_of_domain"),"GOLD_KIND")
        if kind=="numeric":
            expected=gold.get("expected_numeric")
            tol=gold.get("absolute_tolerance")
            require(type(expected) in (float,int) and math.isfinite(expected)
                    and type(tol) in (float,int) and 0<tol<=0.05,"NUMERIC_GOLD")
        if kind in ("numeric","conceptual"):
            require(gold.get("gold_family") in (
                "SR_EINSTEIN_1905","GR_SHAPIRO_1964","BELL_1964",
                "HENSEN_2015","GRW_1986","QBAYES_2002"),"GOLD_FAMILY")
        row={"case_sha256":sha(out["case_id"].encode()),"kind":kind,
             "automatic_text_or_retrieval_diagnostics_only":{}}
        for arm in arms:
            item=out.get(arm)
            require(isinstance(item,dict) and isinstance(item.get("text"),str),
                    "MISSING_ARM_TEXT")
            text=item["text"]
            dest=metrics[arm]
            dest["suspected_unsupported_causal_claims"]+=int(suspected_causal_claim(text))
            scored={"possible_unsupported_causal_claim":suspected_causal_claim(text)}
            if kind=="numeric":
                match, seen=numeric_in_answer(text,float(expected),float(tol))
                dest["numeric_count"]+=1
                dest["numeric_exact_text_match"]+=int(match)
                scored["number_text_match"]=match
                scored["numbers_seen_count"]=len(seen)
            elif kind=="conceptual":
                dest["conceptual_count"]+=1
                family_correct=item.get("family")==gold["gold_family"]
                dest["gold_family_match"]+=int(family_correct)
                scored["doi_family_match"]=family_correct
                scored["physics_correctness"]="UNSCORED_REQUIRES_EXTERNAL_EXPERT"
            else:
                dest["ood_count"]+=1
                abstains=(text.strip().upper()=="ABSTAIN" or
                          any(text.strip().lower().startswith(x) for x in ABSTAIN_PHRASES))
                dest["ood_abstentions"]+=int(abstains)
                scored["abstains"]=abstains
            row["automatic_text_or_retrieval_diagnostics_only"][arm]=scored
        if scope=="PUBLIC_DEVELOPMENT":
            row["case_id"]=out["case_id"]
            public_rows.append(row)
        else:
            private_rows.append(row)
    summary={}
    for arm,m in metrics.items():
        summary[arm]={
            **m,
            "numeric_text_match_rate":(round(m["numeric_exact_text_match"]/m["numeric_count"],4)
                                       if m["numeric_count"] else None),
            "numeric_wilson_95":wilson(m["numeric_exact_text_match"],m["numeric_count"]),
            "conceptual_citation_family_rate":(
                round(m["gold_family_match"]/m["conceptual_count"],4) if m["conceptual_count"] else None),
            "out_of_domain_abstention_rate":(
                round(m["ood_abstentions"]/m["ood_count"],4) if m["ood_count"] else None),
        }
    return {
        "schema":"janus.tachyon.r2d.scoring_receipt.v1",
        "scope":scope,
        "not_an_independently_verified_scientific_result":True,
        "external_custodian_claimed":external_custodian_id if scope=="PRIVATE_EXTERNAL" else None,
        "independence_not_authenticated_by_script":True,
        "candidate_models_sha256":MODEL_SHA,
        "source_cards_sha256":SOURCE_CARD_SHA,
        "raw_scoring_key_sha256":raw_key_sha256,
        "question_count":len(cases),
        "metrics":summary,
        "per_case_public_diagnostics":public_rows,
        "per_case_private_diagnostics":private_rows if scope=="PRIVATE_EXTERNAL" else [],
        "private_answer_text_included":False,
        "scientific_limit":"Automated number matching, citation family and abstention are insufficient for scientific judgement.",
        "scientifically_admitted":False,
        "authority_delta":0,
        "no_automatic_deployment":True,
    }

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="mode",required=True)
    split=sub.add_parser("split-public")
    split.add_argument("--fixture",required=True)
    split.add_argument("--questions",required=True)
    split.add_argument("--key",required=True)
    pred=sub.add_parser("predict")
    pred.add_argument("--questions",required=True)
    pred.add_argument("--cards",required=True)
    pred.add_argument("--r2b",required=True)
    pred.add_argument("--r2c",required=True)
    pred.add_argument("--out",required=True)
    score=sub.add_parser("score")
    score.add_argument("--predictions",required=True)
    score.add_argument("--key",required=True)
    score.add_argument("--committed-key-sha256",required=True)
    score.add_argument("--external-custodian-id")
    score.add_argument("--out",required=True)
    args=ap.parse_args()
    if args.mode=="split-public":
        questions,key=public_split(args.fixture)
        save_new(args.questions,questions);save_new(args.key,key)
        print("PUBLIC_DEVELOPMENT_FIXTURE_SPLIT_NOT_BLIND")
    elif args.mode=="predict":
        questions=read_json(args.questions)
        result=predict_questions(questions,args.cards,args.r2b,args.r2c)
        save_new(args.out,result)
        print(json.dumps({"prediction_count":result["question_count"],
                          "status":"FROZEN_RESEARCH_MODELS_NO_TRAINING_NOT_INDEPENDENT"},
                         sort_keys=True))
    else:
        raw=Path(args.key).read_bytes()
        key=read_json(args.key)
        pred=read_json(args.predictions)
        result=score_predictions(pred,key,args.committed_key_sha256,sha(raw),
                                 args.external_custodian_id)
        save_new(args.out,result)
        print(json.dumps({"question_count":result["question_count"],
                          "scope":result["scope"],"metrics":result["metrics"],
                          "scientifically_admitted":False},
                         ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
