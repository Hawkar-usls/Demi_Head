"""TACHYON R2E guarded deterministic hybrid, strictly RESEARCH_ONLY.

R2D found tiny generators produced 0/8 correct numeric outputs on a transparent,
self-authored development test. This candidate routes narrowly supported numerical
questions through explicit physics formulas and provenance-checked DOI cards;
it never silently turns neural prose into an authoritative physics answer.

This is NOT improved neural intelligence, real laboratory analysis, or retrocausality.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path

from tachyon.science_generator import require, sha, ScienceHold
from tachyon.r2c_grounded import new_source_rows, retrieve, review_gate
from tachyon.r2d_audit import (
    SOURCE_CARD_SHA, SPEED, RHO, formula_response, validate_questions, save_new, read_json,
)

RULE_SOURCES = {
    "SR_PROPER_TIME_RATIO": "SR_EINSTEIN_1905",
    "TWO_LEVEL_BORN_PROBABILITY": "QBAYES_2002",
}
RULE_MECHANISMS = {
    "SR_PROPER_TIME_RATIO": (
        "В инерциальной системе, для часов с постоянной относительной скоростью, "
        "отношение собственного времени к координатному равно dτ/dt = sqrt(1 - (v/c)^2). "
        "Область применения: 0 ≤ v/c < 1, без гравитационных поправок."
    ),
    "TWO_LEVEL_BORN_PROBABILITY": (
        "Для заданной двухуровневой матрицы плотности и проектора |0><0| "
        "правило Борна даёт P(0) = tr(ρ |0><0|) = ρ00. "
        "Область применения: корректно нормированная матрица плотности и указанное измерение."
    ),
}

def load_cards(path):
    p=Path(path)
    require(p.is_file() and sha(p.read_bytes())==SOURCE_CARD_SHA,
            "R2E_SOURCE_CARD_SHA_MISMATCH")
    data,_,_=new_source_rows(p)
    return data

def hybrid_explain(question, cards):
    require(isinstance(question,str) and 10<=len(question)<=1000,
            "R2E_QUESTION_LIMIT")
    speed=SPEED.search(question)
    rho=RHO.search(question)
    base={
        "question":question,
        "model":"TACHYON_R2E_RULE_AND_RETRIEVAL_RESEARCH_ONLY",
        "scientifically_admitted":False,
        "independent_physics_review":False,
        "model_generated_explanation_used_as_fact":False,
        "laboratory_clock_data_accessed":False,
        "retrocausal_signal_claimed":False,
        "requires_scientific_review":True,
        "status":"HOLD",
    }
    if speed and rho:
        return dict(base,decision="ABSTAIN",reason="AMBIGUOUS_MIXED_RULES",
                    answer=None,citations=[],formula_id=None,computed_numeric=None)
    calculated=formula_response(question)
    if speed or rho:
        if calculated["rule"] not in RULE_SOURCES:
            return dict(base,decision="ABSTAIN",reason="UNSUPPORTED_OR_INVALID_PARAMETERS",
                        answer=None,citations=[],formula_id=None,computed_numeric=None)
        family=RULE_SOURCES[calculated["rule"]]
        entry=next((s for s in cards["sources"] if s["family"]==family),None)
        require(entry is not None and entry.get("url")=="https://doi.org/"+entry["doi"],
                "R2E_REFERENCE_MISSING")
        number=float(calculated["text"].split(": ",1)[1])
        require(math.isfinite(number) and 0 <= number <= 1,"R2E_NONPHYSICAL_OUTPUT")
        return dict(
            base,
            decision="DETERMINISTIC_FORMULA_WITH_CITED_SOURCE",
            reason="EXPLICIT_STANDARD_RULE_AND_INPUT_PARAMETER",
            answer=RULE_MECHANISMS[calculated["rule"]]+" Расчётное числовое значение: "+
                   format(number,".10g")+".",
            citations=[{"family":family,"doi":entry["doi"],"url":entry["url"],
                        "citation_scope":"SOURCE_OF_THEORETICAL_CONTEXT_NOT_INDEPENDENT_PEER_REVIEW"}],
            formula_id=calculated["rule"],computed_numeric=number,
            numeric_result_verified_against_formula=True,
            numeric_result_verified_against_lab_measurement=False,
            calculation_overrides_unverified_neural_text=True,
        )
    hits=retrieve(question,cards)
    gate=review_gate(question,hits)
    if not hits or gate["decision"]=="ABSTAIN":
        return dict(base,decision="ABSTAIN",reason="NO_RELIABLE_MATCH",
                    answer=None,citations=[],formula_id=None,computed_numeric=None)
    first=hits[0]
    return dict(
        base,
        decision="SOURCE_PARAPHRASE_REQUIRES_REVIEW",
        reason="DOI_RETRIEVAL_MATCH_NOT_PHYSICS_PROOF",
        answer=first["answer"],
        citations=[{"family":first["family"],"doi":first["doi"],"url":first["url"],
                    "citation_scope":"CURATED_PARAPHRASE_REQUIRES_EXTERNAL_REVIEW"}],
        formula_id=None,computed_numeric=None,
        numeric_result_verified_against_formula=False,
        calculation_overrides_unverified_neural_text=False,
    )

def batch_explain(questions,cards):
    cases=validate_questions(questions)
    return {
        "schema":"janus.tachyon.r2e.guarded_hybrid_answers.v1",
        "scope":questions["scope"],
        "candidate_checkpoint_used":False,
        "main_or_ocean_modified":False,
        "independent_scientific_validation":False,
        "candidate_admitted":False,
        "cases":[{"case_id":c["case_id"],
                  "explanation":hybrid_explain(c["question"],cards)} for c in cases],
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--questions",required=True)
    ap.add_argument("--cards",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    cards=load_cards(args.cards)
    questions=read_json(args.questions)
    output=batch_explain(questions,cards)
    save_new(args.out,output)
    counts={}
    for case in output["cases"]:
        d=case["explanation"]["decision"];counts[d]=counts.get(d,0)+1
    print(json.dumps({"scope":output["scope"],"n":len(output["cases"]),
                      "routes":counts,"scientifically_admitted":False},
                     ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
