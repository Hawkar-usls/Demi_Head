"""R2G: bounded live evidence broker for R2F EXTERNAL_SEARCH_REQUIRED.

Public queries only, explicit network opt-in, deterministic fixed API hosts.
Never fetch URLs supplied by search results. Search snippets are untrusted DATA,
not instructions or proof. No training, no production or Ocean modifications.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone, date
import html
import ipaddress
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from tachyon.science_generator import ScienceHold, require, sha
from tachyon.r2d_audit import read_json, save_new
from tachyon.r2f_general_router import (
    load_general_cards, route_question, is_fresh_question, is_sports_question,
)
from tachyon.r2e_hybrid import load_cards

WIKI_ENDPOINT="https://ru.wikipedia.org/w/api.php"
OPENALEX_ENDPOINT="https://api.openalex.org/works"
BRAVE_ENDPOINT="https://api.search.brave.com/res/v1/web/search"
FIXED_HOSTS={"ru.wikipedia.org","api.openalex.org","api.search.brave.com"}
SAFE_ARTICLE_HOSTS={"ru.wikipedia.org","en.wikipedia.org","doi.org","openalex.org"}
MAX_RESULTS=4
MAX_REQUEST_BYTES=160_000
USER_AGENT="JANUS-Tachyon-R2G/0.1 (https://github.com/Hawkar-usls/Demi_Head; research connector)"
SENSITIVE_PATTERNS=(
    re.compile(r"(?i)\b(?:api[_ -]?key|auth[_ -]?token|password|парол[ья]|секретный ключ|bearer)\b"),
    re.compile(r"(?i)\b[\w.+%-]+@[\w.-]+\.[a-z]{2,}\b"),
    re.compile(r"(?i)(?:https?://|ssh://|smb://|ftp://|\\\\|/home/|/mnt/|[a-z]:\\)",re.I),
    re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)"),
    re.compile(r"(?i)\b(?:sk-[a-z0-9_-]{10,}|gh[pousr]_[a-z0-9]{20,})\b"),
)
WORD=re.compile(r"[^\W\d_]{4,}",re.U)
STOP=set("какая какой какие почему когда можно чтобы если зачем что где это как него него этой есть была были были ли год году года про для при и или".split())

class ProviderUnavailable(RuntimeError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        raise ProviderUnavailable("REDIRECT_NOT_PERMITTED")

def clean(text,limit=260):
    value=html.unescape(re.sub(r"<[^>]*>"," ",str(text or "")))
    value=re.sub(r"[\x00-\x1f\x7f-\x9f]+"," ",value)
    value=re.sub(r"\s+"," ",value).strip()
    return value[:limit]

def query_terms(text):
    return set(w.lower() for w in WORD.findall(text) if w.lower() not in STOP)

def safe_public_query(q):
    require(isinstance(q,str) and 10<=len(q)<=300,"PUBLIC_QUERY_LENGTH")
    require(not any(p.search(q) for p in SENSITIVE_PATTERNS),
            "POSSIBLE_PRIVATE_INFORMATION_SEARCH_BLOCKED")
    require("\n" not in q and "\r" not in q and "\x00" not in q,
            "INVALID_PUBLIC_QUERY")
    return q.strip()

def safe_http_url(url,allowed_hosts):
    p=urllib.parse.urlsplit(str(url))
    require(p.scheme=="https" and (p.hostname or "").lower() in allowed_hosts
            and not p.username and not p.password and p.port in (None,443),
            "UNTRUSTED_HTTP_URL")
    return url

def safe_result_url(raw,provider):
    p=urllib.parse.urlsplit(str(raw))
    if p.scheme!="https" or p.username or p.password or p.port not in (None,443):
        return None
    hostname=(p.hostname or "").lower()
    if not hostname or hostname=="localhost" or hostname.endswith(".local"):
        return None
    try:
        ipaddress.ip_address(hostname)
        return None
    except ValueError:
        pass
    if provider=="wikipedia" and hostname not in SAFE_ARTICLE_HOSTS:
        return None
    if provider=="openalex" and hostname not in ("doi.org","openalex.org"):
        return None
    if len(str(raw))>1200:
        return None
    return str(raw)

def fetch_json(endpoint,params,headers=None,timeout=7):
    """Built-in network adapter: exact API origin, bounded body, no redirects."""
    safe_http_url(endpoint,FIXED_HOSTS)
    url=endpoint+"?"+urllib.parse.urlencode(params)
    safe_http_url(url,FIXED_HOSTS)
    hdr={"User-Agent":USER_AGENT,"Accept":"application/json"}
    if headers:
        require(set(headers)=={"X-Subscription-Token"}
                and endpoint==BRAVE_ENDPOINT,"UNEXPECTED_API_AUTH_HEADER")
        hdr.update(headers)
    request=urllib.request.Request(url,headers=hdr,method="GET")
    opener=urllib.request.build_opener(NoRedirect)
    try:
        with opener.open(request,timeout=timeout) as response:
            if response.status!=200:
                raise ProviderUnavailable("UPSTREAM_HTTP_STATUS")
            data=response.read(MAX_REQUEST_BYTES+1)
            if len(data)>MAX_REQUEST_BYTES:
                raise ProviderUnavailable("UPSTREAM_RESPONSE_TOO_LARGE")
            obj=json.loads(data.decode("utf-8"))
            if not isinstance(obj,dict):
                raise ProviderUnavailable("UPSTREAM_RESPONSE_NOT_OBJECT")
            return obj
    except (urllib.error.URLError,TimeoutError,ValueError,UnicodeError,OSError) as exc:
        raise ProviderUnavailable("UPSTREAM_REQUEST_FAILED_"+type(exc).__name__) from None

def common_record(provider,title,url,excerpt,query,date_published=None,kind="SOURCE_METADATA"):
    link=safe_result_url(url,provider)
    if not link or not title:
        return None
    title=clean(title,180)
    excerpt=clean(excerpt,260)
    overlap=len(query_terms(query)&query_terms(title+" "+excerpt))
    return {
        "provider":provider,"title":title,"url":link,
        "excerpt":excerpt,
        "published_at":date_published,
        "relevance_overlap":overlap,
        "evidence_kind":kind,
        "independently_fact_checked":False,
        "instructions_from_source_executed":False,
    }

def wiki_search(query,fetch=fetch_json):
    params={
        "action":"query","generator":"search","gsrsearch":query,
        "gsrnamespace":"0","gsrlimit":str(MAX_RESULTS),
        "prop":"extracts|info","inprop":"url","exintro":"1",
        "explaintext":"1","exsentences":"3","format":"json","formatversion":"2",
    }
    obj=fetch(WIKI_ENDPOINT,params)
    pages=obj.get("query",{}).get("pages",[])
    if not isinstance(pages,list):
        raise ProviderUnavailable("WIKI_BAD_SCHEMA")
    results=[]
    for page in pages:
        if not isinstance(page,dict):
            continue
        title=page.get("title")
        if not title:
            continue
        raw_url=page.get("fullurl")
        if not raw_url:
            raw_url="https://ru.wikipedia.org/wiki/"+urllib.parse.quote(
                title.replace(" ","_"),safe="")
        rec=common_record("wikipedia",title,raw_url,page.get("extract",""),
                          query,kind="ENCYCLOPEDIA_EXTRACT_CC_BY_SA")
        if rec:
            rec["attribution"]="Wikipedia contributors, CC BY-SA; check article and license"
            results.append(rec)
    return results[:MAX_RESULTS]

def openalex_search(query,fetch=fetch_json):
    obj=fetch(OPENALEX_ENDPOINT,{
        "search":query,"per_page":str(MAX_RESULTS),
        "select":"id,title,doi,publication_date,abstract_inverted_index",
    })
    works=obj.get("results",[])
    if not isinstance(works,list):
        raise ProviderUnavailable("OPENALEX_BAD_SCHEMA")
    result=[]
    for work in works:
        if not isinstance(work,dict):
            continue
        url=work.get("doi") or work.get("id")
        title=work.get("title")
        # We do not reconstruct journal abstracts: reuse rights are not established.
        rec=common_record("openalex",title,url,"",query,
                          date_published=work.get("publication_date"),
                          kind="SCHOLARLY_BIBLIOGRAPHIC_METADATA")
        if rec:
            rec["abstract_reused"]=False
            result.append(rec)
    return result[:MAX_RESULTS]

def brave_search(query,api_key,fetch=fetch_json,needs_fresh=False):
    require(api_key and isinstance(api_key,str),"BRAVE_KEY_MISSING")
    params={"q":query[:600],"count":str(MAX_RESULTS),"safesearch":"strict"}
    if needs_fresh:
        params["freshness"]="pw"
    obj=fetch(BRAVE_ENDPOINT,params,{"X-Subscription-Token":api_key})
    results=obj.get("web",{}).get("results",[])
    if not isinstance(results,list):
        raise ProviderUnavailable("BRAVE_BAD_SCHEMA")
    output=[]
    for item in results[:MAX_RESULTS]:
        if not isinstance(item,dict):continue
        rec=common_record("brave",item.get("title"),item.get("url"),
                          item.get("description"),query,
                          kind="WEB_SEARCH_SNIPPET_UNVERIFIED")
        if rec:
            output.append(rec)
    return output

def decide_evidence(query,sources,needs_fresh,provider_errors):
    ordered=sorted(sources,key=lambda x:(-x["relevance_overlap"],x["provider"],x["title"]))
    eligible=[x for x in ordered if x["relevance_overlap"]>=1]
    rec={
        "source_count":len(ordered),"sources":ordered[:MAX_RESULTS],
        "answer":None,"answer_source_url":None,
        "scientifically_admitted":False,
        "verified_independent_fact":False,
        "provider_errors":provider_errors,
        "source_evidence_only":True,
    }
    if not eligible:
        rec["decision"]="NO_VERIFIABLE_SOURCE"
        rec["reason"]="ZERO_RELEVANT_PROVIDER_RESULTS"
    elif needs_fresh:
        # Date of retrieval never substitutes for date of an event/publication.
        rec["decision"]="EVIDENCE_REQUIRES_FRESHNESS_VERIFICATION"
        rec["reason"]="NO_INDEPENDENT_DATED_EVENT_CONFIRMATION"
    elif eligible[0]["provider"]=="wikipedia" and eligible[0]["excerpt"] and eligible[0]["relevance_overlap"]>=2:
        rec["decision"]="ATTRIBUTED_EXTRACT_AVAILABLE"
        rec["reason"]="ENCYCLOPEDIA_SUMMARY_NOT_INDEPENDENT_SCIENCE_REVIEW"
        rec["answer"]=eligible[0]["excerpt"]
        rec["answer_source_url"]=eligible[0]["url"]
    else:
        rec["decision"]="EVIDENCE_FOUND_REVIEW_REQUIRED"
        rec["reason"]="SOURCES_NOT_SUFFICIENT_FOR_EXTRACTIVE_ANSWER"
    return rec

def route_with_external_search(question,physics_cards,general_cards,*,public_approved=False,
                               providers=("wikipedia","openalex"),brave_key=None,
                               fetch=fetch_json):
    route=route_question(question,physics_cards,general_cards)
    envelope={
        "schema":"janus.tachyon.r2g.external_evidence_result.v1",
        "local_route":route["decision"],
        "query_sha256":sha(question.encode("utf-8")),
        "public_network_consent_for_this_query":bool(public_approved),
        "retrieved_at":datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "network_request_count":0,
        "model_training_performed":False,"production_write":False,
        "janus_ocean_modified":False,"scientific_admission":False,
    }
    if route["decision"]!="EXTERNAL_SEARCH_REQUIRED":
        return dict(envelope,decision="LOCAL_ROUTE_HANDLED",local_response=route,
                    sources=[],answer=route.get("answer"),provider_errors={})
    if not public_approved:
        return dict(envelope,decision="PUBLIC_NETWORK_CONSENT_REQUIRED",
                    sources=[],answer=None,provider_errors={})
    public_query=safe_public_query(route.get("external_lookup_query") or question)
    needs_fresh=bool(route.get("needs_live_source")) or is_fresh_question(public_query)
    opts=set(providers)
    require(opts<= {"wikipedia","openalex","brave"} and opts,
            "UNSUPPORTED_PROVIDER")
    results=[];errors={};calls=0
    # Sports/current results require a proper web index, not static Wikipedia.
    effective=["brave"] if is_sports_question(public_query) and needs_fresh else [
        p for p in ("wikipedia","openalex","brave") if p in opts
    ]
    if "brave" in effective and not brave_key and needs_fresh and is_sports_question(public_query):
        return dict(envelope,decision="WEB_PROVIDER_KEY_REQUIRED",
                    reason="LIVE_SPORTS_REQUIRE_BRAVE_SEARCH_OR_OTHER_APPROVED_DATED_PROVIDER",
                    sources=[],answer=None,provider_errors={})
    for provider in effective:
        if provider not in opts or (provider=="brave" and not brave_key):
            continue
        calls+=1
        try:
            if provider=="wikipedia":
                found=wiki_search(public_query,fetch)
            elif provider=="openalex":
                found=openalex_search(public_query,fetch)
            else:
                found=brave_search(public_query,brave_key,fetch,needs_fresh)
            results+=found
        except (ProviderUnavailable,ScienceHold) as exc:
            errors[provider]=str(exc)[:110]
        if calls>=3:break
    decision=decide_evidence(public_query,results,needs_fresh,errors)
    return dict(envelope,**decision,network_request_count=calls)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--questions",required=True)
    ap.add_argument("--physics-cards",required=True)
    ap.add_argument("--general-cards",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--public-network-approved",action="store_true")
    ap.add_argument("--providers",default="wikipedia,openalex")
    args=ap.parse_args()
    physics=load_cards(args.physics_cards)
    general=load_general_cards(args.general_cards)
    q=read_json(args.questions)
    require(q.get("scope")=="PUBLIC_DEVELOPMENT",
            "ONLY_PUBLIC_DIAGNOSTIC_QUESTIONS_ALLOWED_IN_THIS_RUNNER")
    from tachyon.r2d_audit import validate_questions
    cases=validate_questions(q)
    results=[]
    providers=tuple(x.strip() for x in args.providers.split(","))
    for case in cases:
        response=route_with_external_search(case["question"],physics,general,
            public_approved=args.public_network_approved,providers=providers,
            brave_key=None)
        results.append({"case_id":case["case_id"],"response":response})
    out={
        "schema":"janus.tachyon.r2g.public_external_broker_receipt.v1",
        "scope":"PUBLIC_DEVELOPMENT","case_count":len(cases),
        "external_provider_opt_in":args.public_network_approved,
        "model_training_performed":False,
        "scientifically_admitted":False,
        "results":results
    }
    save_new(args.out,out)
    counts={}
    for item in results:
        x=item["response"]["decision"]
        counts[x]=counts.get(x,0)+1
    print(json.dumps({"case_count":len(cases),"decisions":counts,
                      "scientifically_admitted":False},sort_keys=True))

if __name__=="__main__":
    main()
