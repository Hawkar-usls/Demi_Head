"""TACHYON R2F: evidence-aware router around the physics-only research candidate.

The physics source holdout still ABSTAINS on out-of-domain questions. This
separate general-question route returns verified short source cards if present;
otherwise it emits a structured external search request or asks for essential
details. No unsupported live sports results are invented.

No neural training, no unrestricted internet, no change to JANUS Ocean.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

from tachyon.science_generator import ScienceHold, require
from tachyon.r2e_hybrid import hybrid_explain, load_cards
from tachyon.r2d_audit import validate_questions, read_json, save_new

CARD_SCHEMA="janus.tachyon.r2f.general_source_cards.v1"
EXPECTED_CARD_IDS=frozenset({"NAS_ENERGY_BASICS","APPLE_WINTER_CULTIVAR","PIZZA_WITHOUT_YEAST"})
ALLOWED_SOURCE_HOSTS=frozenset({
    "www.energy.gov","www.energystar.gov","extension.missouri.edu",
    "www.extension.umd.edu","www.kingarthurbaking.com"
})
GATES={"GENERAL_SOURCE_ANSWER","PHYSICS_RESEARCH_DRAFT",
       "NEEDS_CLARIFICATION","EXTERNAL_SEARCH_REQUIRED"}

def load_general_cards(path):
    obj=read_json(path)
    require(obj.get("schema")==CARD_SCHEMA and
            obj.get("role")=="OUT_OF_PHYSICS_SOURCE_GROUNDED_ROUTING_NOT_MODEL_TRAINING",
            "GENERAL_SOURCE_SCHEMA")
    provenance=obj.get("provenance",{})
    require(provenance.get("independent_assessor") is False,
            "UNVERIFIED_SOURCE_AUTHORITY")
    cards=obj.get("cards")
    require(isinstance(cards,list) and 1<=len(cards)<=100,"GENERAL_CARDS_LIMIT")
    ids=[s.get("id") for s in cards]
    require(len(ids)==len(set(ids)), "DUPLICATE_CARD_ID")
    require(EXPECTED_CARD_IDS.issubset(set(ids)),"MISSING_REQUIRED_GENERAL_CARDS")
    for s in cards:
        require(set(s)=={"id","domain","required_any","supports_any","title",
                         "answer_ru","citations","caveats","time_sensitive"},
                "UNRECOGNIZED_CARD_FIELD")
        require(isinstance(s["title"],str) and 10<len(s["title"])<200,
                "GENERAL_CARD_TITLE")
        require(isinstance(s["answer_ru"],str) and 90<=len(s["answer_ru"])<=1200,
                "GENERAL_ANSWER_LENGTH")
        for field in ("required_any","supports_any"):
            values=s[field]
            require(isinstance(values,list) and 1<=len(values)<=15
                    and all(isinstance(v,str) and 2<=len(v)<=60 for v in values),
                    "GENERAL_SOURCE_TRIGGER_INVALID")
        require(s["time_sensitive"] is False,"GENERAL_CARD_MUST_BE_EVERGREEN")
        require(isinstance(s["caveats"],list) and len(s["caveats"])>=1,
                "GENERAL_CAVEAT_MISSING")
        citations=s["citations"]
        require(isinstance(citations,list) and 1<=len(citations)<=4,
                "GENERAL_SOURCE_REQUIRED")
        for c in citations:
            require(set(c)=={"title","url","type"},"SOURCE_CITATION_SHAPE")
            parts=urlsplit(c["url"])
            require(parts.scheme=="https" and parts.hostname in ALLOWED_SOURCE_HOSTS
                    and parts.username is None and parts.password is None,
                    "UNTRUSTED_CITATION_HOST")
            require(len(c["title"])>8 and c["type"] in (
                "GOVERNMENT_GUIDANCE","PUBLIC_ENERGY_GUIDANCE",
                "UNIVERSITY_EXTENSION","SPECIALIST_BAKING_GUIDANCE",
                "SPECIALIST_BAKING_RECIPE"),"UNSUPPORTED_CITATION_TYPE")
    return obj

def has_any(query, values):
    q=query.casefold().replace("ё","е")
    return any(item.casefold().replace("ё","е") in q for item in values)

def retrieve_general(question, source_cards):
    """Lexical matches over a *separate* source index, never the physics weights."""
    result=[]
    for s in source_cards["cards"]:
        if has_any(question,s["required_any"]) and has_any(question,s["supports_any"]):
            support=sum(has_any(question,[t]) for t in s["supports_any"])
            result.append((support,s["id"],s))
    result.sort(key=lambda r:(-r[0],r[1]))
    if len(result)>=2 and result[0][0]==result[1][0]:
        return None
    return result[0][2] if result else None

def is_sports_question(question):
    s=question.casefold().replace("ё","е")
    return any(t in s for t in ("футбол","чемпионат","матч","премьер-лиг","лига чемпион"))

def is_fresh_question(question):
    s=question.casefold().replace("ё","е")
    return bool(re.search(r"\b20\d{2}\b",s)) or any(t in s for t in (
        "последн","сегодня","вчера","сейчас",
        "на данный момент","прямо сейчас","актуальн","текущ"))

def known_sports_context(question):
    s=question.casefold()
    return any(t in s for t in ("реал мадрид","манчестер","барселон","динамо киев",
                                "шахтер","арсенал","ливерпул")) and any(
        t in s for t in ("ла лиг","апл","украин","лига чемпион","премьер-лиг"))

def route_question(question,physics_cards,general_cards):
    require(isinstance(question,str) and 10<=len(question)<=1000,
            "GENERAL_QUERY_LIMIT")
    envelope={
        "question":question,
        "research_scope":"ROUTING_DIAGNOSTIC_NOT_NEURAL_SCIENTIFIC_COMPETENCE",
        "scientifically_admitted":False,
        "neural_generated_claim_used":False,
        "janus_ocean_modified":False,
        "access_to_private_measurements":False
    }
    if is_sports_question(question) and is_fresh_question(question):
        if not known_sports_context(question):
            return dict(envelope,decision="NEEDS_CLARIFICATION",
                        reason="LIVE_RESULT_AMBIGUOUS_TEAM_OR_LEAGUE",
                        answer=None,citations=[],question_to_user="Какую команду и какой чемпионат или матч проверить?",
                        external_lookup_query=None,needs_live_source=True)
        return dict(envelope,decision="EXTERNAL_SEARCH_REQUIRED",
                    reason="REAL_TIME_SPORTS_SOURCE_REQUIRED",
                    answer=None,citations=[],
                    question_to_user=None,
                    external_lookup_query=question,
                    needs_live_source=True)
    found=retrieve_general(question,general_cards)
    if found:
        return dict(envelope,decision="GENERAL_SOURCE_ANSWER",
                    reason="CURATED_EVERGREEN_GENERAL_SOURCES",
                    answer=found["answer_ru"],
                    citations=found["citations"],
                    domain=found["domain"],source_card_id=found["id"],
                    caveats=found["caveats"],
                    question_to_user=None,external_lookup_query=None,
                    needs_live_source=False,
                    answer_independently_verified=False)
    physics=hybrid_explain(question,physics_cards)
    if physics["decision"]!="ABSTAIN":
        return dict(envelope,decision="PHYSICS_RESEARCH_DRAFT",
                    reason="SCOPED_PHYSICS_SOURCE_OR_FORMULA",
                    answer=physics.get("answer"),citations=physics["citations"],
                    physics_decision=physics["decision"],
                    requires_scientific_review=True,
                    question_to_user=None,external_lookup_query=None,
                    needs_live_source=False)
    if physics["reason"] in ("AMBIGUOUS_MIXED_RULES","UNSUPPORTED_OR_INVALID_PARAMETERS"):
        return dict(envelope,decision="NEEDS_CLARIFICATION",
                    reason=physics["reason"],
                    answer=None,citations=[],
                    question_to_user="Уточни исходные параметры: обнаружены несовместимые или некорректные значения.",
                    external_lookup_query=None,needs_live_source=False)
    return dict(envelope,decision="EXTERNAL_SEARCH_REQUIRED",
                reason="NO_LOCAL_SOURCE_MATCH_MUST_SEARCH_FURTHER",
                answer=None,citations=[],question_to_user=None,
                external_lookup_query=question,
                needs_live_source=is_fresh_question(question))

def batch_route(questions,physics_cards,general_cards):
    cases=validate_questions(questions)
    results=[{"case_id":c["case_id"],"response":route_question(
        c["question"],physics_cards,general_cards)} for c in cases]
    return {
        "schema":"janus.tachyon.r2f.cross_domain_routing.v1",
        "scope":questions["scope"],
        "local_source_only":True,
        "general_web_search_in_this_runner":False,
        "model_training_performed":False,
        "scientific_admission":False,
        "cases":results,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--questions",required=True)
    ap.add_argument("--physics-cards",required=True)
    ap.add_argument("--general-cards",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    q=read_json(args.questions)
    science=load_cards(args.physics_cards)
    general=load_general_cards(args.general_cards)
    output=batch_route(q,science,general)
    save_new(args.out,output)
    counts={}
    for case in output["cases"]:
        d=case["response"]["decision"]
        counts[d]=counts.get(d,0)+1
    print(json.dumps({"total":len(output["cases"]),"routes":counts,
                      "web_enabled":False,"scientific_admission":False},
                     ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
