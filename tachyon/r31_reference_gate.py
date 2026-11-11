"""TACHYON-R3.1: fixed public reference pack, disjoint split & guarded baseline.

This *does not* train a neural model and the public dev set is not independent.
It verifies source-grounded equations/units on unseen parameter values, and
records both successes and failures without permitting model promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

PACK_SCHEMA="janus.tachyon.r31.formal_physics_reference_pack.v1"
REFS={
 "SR_PROPER_TIME_RATIO":"https://openstax.org/books/university-physics-volume-3/pages/5-3-time-dilation",
 "TWO_LEVEL_BORN_PROBABILITY":"https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements"
}
SPLITS=("train","calibration","public_unseen_dev")
FAMILY_ORDER=tuple(REFS)
R2H_KNOWN={
 "SR_PROPER_TIME_RATIO":set(("0.11","0.22","0.44","0.66","0.77","0.88")),
 "TWO_LEVEL_BORN_PROBABILITY":set(("0.10","0.25","0.35","0.55","0.70","0.95")),
}
R2D_KNOWN={
 "SR_PROPER_TIME_RATIO":set(("0.3","0.5","0.8","0.9")),
 "TWO_LEVEL_BORN_PROBABILITY":set(("0.2","0.4","0.65","0.85")),
}
NEG_IDS={"beta_superluminal","beta_negative","born_above_one",
         "born_below_zero","not_our_physics","mixed_ambiguous"}

def require(condition, message):
    if not condition:raise ValueError(message)

def canonical(obj):
    return json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":"),
                      allow_nan=False).encode("utf8")

def sha(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def validate_pack(data):
    require(data.get("schema")==PACK_SCHEMA,"BAD_PACK_SCHEMA")
    require(data.get("independent_external_blind_assessor") is False
            and data.get("production_training_authorized") is False
            and data.get("scientific_admission")=="HOLD"
            and data.get("public_dev_not_external_blind") is True,
            "UNAUTHORIZED_SCIENCE_ADMISSION")
    refs=data.get("references")
    require(isinstance(refs,list) and len(refs)==2 and
            {r["formula_id"]:r["url"] for r in refs}==REFS,
            "UNEXPECTED_REFERENCE_DOMAIN")
    splits=data.get("splits")
    require(isinstance(splits,dict) and set(splits)==set(SPLITS),
            "BAD_SPLIT_INVENTORY")
    seen={}
    for split in SPLITS:
        sub=splits[split]
        require(isinstance(sub,dict) and set(sub)==set(FAMILY_ORDER),
                "SPLIT_MISSING_FORMULA")
        for formula,values in sub.items():
            require(isinstance(values,list) and
                    4<=len(values)<=12,"BOUNDED_SPLIT_SIZE")
            require(len(set(values))==len(values),"DUPLICATE_WITHIN_SPLIT")
            for text in values:
                require(isinstance(text,str) and
                        re.fullmatch(r"0\.\d{1,3}",text) is not None and
                        0<=float(text)<1,"BAD_PARAMETER")
                key=(formula,float(text))
                require(key not in seen,"TRAIN_EVALUATION_PARAMETER_OVERLAP")
                seen[key]=split
                if split=="public_unseen_dev":
                    require(text not in R2H_KNOWN[formula] and
                            text not in R2D_KNOWN[formula],
                            "PUBLIC_HOLDOUT_ALREADY_USED_IN_R2H_R2D")
    negatives=data.get("negative_public_unseen",[])
    require(isinstance(negatives,list) and
            len(negatives)==len(NEG_IDS) and
            {x["id"] for x in negatives}==NEG_IDS and
            all(x["expect"]=="ABSTAIN" for x in negatives),
            "NEGATIVE_CONTROL_MISSING")
    return data

def expected(formula,value):
    x=float(value)
    if formula=="SR_PROPER_TIME_RATIO":return math.sqrt(1-x*x)
    if formula=="TWO_LEVEL_BORN_PROBABILITY":return x
    raise ValueError("UNKNOWN_FORMULA")

def prompt(formula,value):
    if formula=="SR_PROPER_TIME_RATIO":
        return "Для инерциальных часов при v/c="+value+" вычисли dτ/dt по СТО."
    return "При измерении |0><0| двухуровневой системы с ρ00="+value+" вычисли P(0)."

def make_rows(pack,split):
    require(split in SPLITS,"INVALID_SPLIT")
    out=[]
    for family in FAMILY_ORDER:
        for i,value in enumerate(pack["splits"][split][family]):
            out.append({"case_id":split+"-"+family.lower()+"-"+str(i).zfill(2),
                        "formula_id":family,"question":prompt(family,value),
                        "parameter":value,"expected_numeric":expected(family,value),
                        "source_url":REFS[family],
                        "data_type":"AUTHOR_DERIVED_FORMULA_LABEL_NOT_LAB_MEASUREMENT"})
    return out

def score_guarded(pack, cards):
    from tachyon.r2e_hybrid import hybrid_explain
    rows=make_rows(pack,"public_unseen_dev")
    baselines={}
    for family in FAMILY_ORDER:
        vals=pack["splits"]["train"][family]
        baselines[family]=sum(expected(family,v) for v in vals)/len(vals)
    results=[]
    passed=0;const_hit=0
    for row in rows:
        answer=hybrid_explain(row["question"],cards)
        y=row["expected_numeric"]
        numeric=answer.get("computed_numeric")
        good=(answer.get("decision")=="DETERMINISTIC_FORMULA_WITH_CITED_SOURCE"
              and answer.get("formula_id")==row["formula_id"]
              and isinstance(numeric,(int,float)) and
              math.isclose(numeric,y,rel_tol=0,abs_tol=1e-6))
        prior=baselines[row["formula_id"]]
        prior_hit=math.isclose(prior,y,rel_tol=0,abs_tol=1e-6)
        passed+=int(good);const_hit+=int(prior_hit)
        results.append({"case_id":row["case_id"],"family":row["formula_id"],
                        "expected":y,"computed":numeric,
                        "model_kind":"DETERMINISTIC_FORMULA_NOT_NEURAL",
                        "formula_pass":good,"mean_train_formula_baseline":prior,
                        "baseline_pass":prior_hit,"source_url":row["source_url"]})
    neg=[]
    for item in pack["negative_public_unseen"]:
        a=hybrid_explain(item["question"],cards)
        neg.append({"case_id":item["id"],"status":a.get("decision"),
                    "abstain_pass":a.get("decision")=="ABSTAIN"})
    return {"schema":"janus.tachyon.r31.public_development_reference_baselines.v1",
            "pack_sha256":sha(pack),
            "train_cases":len(make_rows(pack,"train")),
            "calibration_cases":len(make_rows(pack,"calibration")),
            "public_unseen_numeric_count":len(rows),
            "guarded_formula_correct":passed,
            "mean_training_label_baseline_correct":const_hit,
            "negative_count":len(neg),
            "negative_abstentions":sum(x["abstain_pass"] for x in neg),
            "public_author_development_only":True,
            "independently_blind":False,
            "neural_weights_trained":False,
            "lab_data_read":False,
            "scientific_admission":"HOLD",
            "production_promotion":False,
            "numeric_tolerance_absolute":1e-6,
            "observations":results,
            "negative_observations":neg}

def exported_training_pack(pack):
    """Separate reviewed-source TRAIN inputs; no dev/calibration examples leaked."""
    rows=make_rows(pack,"train")
    return {
        "schema":"janus.tachyon.r31.formula_router_training_examples.v1",
        "source_reference_pack_sha256":sha(pack),
        "split":"train",
        "examples":rows,
        "external_blind_labels_used":False,
        "lab_measurements_used":False,
        "admission":"EXPERIMENTAL_CURATOR_REVIEW_REQUIRED",
        "production_authorization":False,
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--pack",required=True)
    p.add_argument("--cards",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--train-out",required=True)
    args=p.parse_args()
    pack=validate_pack(json.loads(Path(args.pack).read_text(encoding="utf8")))
    from tachyon.r2e_hybrid import load_cards
    cards=load_cards(args.cards)
    record=score_guarded(pack,cards)
    out=Path(args.out);train=Path(args.train_out)
    require(not out.exists() and not train.exists()
            and out!=train,"REFUSE_OVERWRITE_EXPERIMENT")
    out.parent.mkdir(parents=True,exist_ok=True)
    train.parent.mkdir(parents=True,exist_ok=True)
    train_obj=exported_training_pack(pack)
    train_obj["receipt_sha256"]=sha(train_obj)
    train.write_text(json.dumps(train_obj,ensure_ascii=False,
                                sort_keys=True,indent=2)+"\n",encoding="utf8")
    record["receipt_sha256"]=sha(record)
    out.write_text(json.dumps(record,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                   encoding="utf8")
    print(json.dumps({k:v for k,v in record.items() if k in (
        "pack_sha256","public_unseen_numeric_count","guarded_formula_correct",
        "mean_training_label_baseline_correct","negative_abstentions",
        "neural_weights_trained","scientific_admission")},sort_keys=True))

if __name__=="__main__":main()
