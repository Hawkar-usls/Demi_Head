#!/usr/bin/env python3
"""Read-only, pin-verified DemiHead adapter for JANUS Unified Memory v2 SQLite FTS5.

Consumes a *derived* Meta Registry index prepared in an isolated environment.
No git/network/NAS access, graph mutation, writer capability, or claim promotion.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

SCHEMA = "janus.demihead.unified_memory_search.v1"
ORIGIN = "Hawkar-usls/janus-meta-registry"
INDEX_SCHEMA = "janus.unified_memory.v2.isolated"
SHA40 = re.compile(r"^[0-9a-f]{40}$")
SHA256 = re.compile(r"^[0-9a-f]{64}$")
MAX_INDEX_BYTES = 750_000_000
MAX_MATCHES = 20
MAX_NEIGHBORS = 8

def canonical(x: Any) -> bytes:
    return json.dumps(x, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def digest(x: Any) -> str:
    return hashlib.sha256(canonical(x)).hexdigest()

def hash_file(path: Path) -> str:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_INDEX_BYTES:
        raise ValueError("INDEX_FILE_HOLD")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while block := fh.read(1048576):
            h.update(block)
    return h.hexdigest()

def literal_query(text: str) -> str:
    tokens = re.findall(r"\w+", text, re.UNICODE)[:20]
    if not tokens:
        raise ValueError("EMPTY_QUERY_HOLD")
    return " AND ".join('"' + t + '"' for t in tokens)

def _load_metadata(db: sqlite3.Connection, *, commit: str, manifest: str) -> dict:
    data = {str(k): json.loads(v) for k, v in db.execute("SELECT k,v FROM metadata")}
    if data.get("schema") != INDEX_SCHEMA or data.get("source_commit") != commit:
        raise ValueError("INDEX_SOURCE_COMMIT_HOLD")
    if data.get("source_manifest_sha256") != manifest:
        raise ValueError("INDEX_MANIFEST_SHA256_HOLD")
    if data.get("coverage_complete") is not True or data.get("read_only") is not True:
        raise ValueError("INDEX_COVERAGE_HOLD")
    if data.get("scientific_authority_granted") is not False or data.get("historical_git_included") is not False:
        raise ValueError("INDEX_AUTHORITY_HOLD")
    total = data.get("indexed_json")
    if type(total) is not int or total < 1 or total > 1000000:
        raise ValueError("INDEX_COUNT_HOLD")
    if db.execute("SELECT COUNT(*) FROM documents").fetchone()[0] != total:
        raise ValueError("INDEX_DOCUMENT_COUNT_HOLD")
    if db.execute("SELECT COUNT(*) FROM docs_fts").fetchone()[0] != total:
        raise ValueError("INDEX_FTS_COUNT_HOLD")
    if db.execute("SELECT COUNT(*) FROM edges").fetchone()[0] != data.get("explicit_relations"):
        raise ValueError("INDEX_EDGE_COUNT_HOLD")
    return data

def _source_url(commit: str, path: str) -> str:
    if not isinstance(path, str) or not path.endswith(".json") or not path or "\\" in path:
        raise ValueError("INVALID_JSON_PATH_HOLD")
    parts = path.split("/")
    if any(p in ("", ".", "..") for p in parts) or any(ord(ch) < 32 for ch in path) or "?" in path or "#" in path:
        raise ValueError("INVALID_JSON_PATH_HOLD")
    return "https://github.com/" + ORIGIN + "/blob/" + commit + "/" + path

def make_packet(index: Path, text: str, *, expected_commit: str, expected_manifest: str, limit: int = 8) -> dict:
    if not SHA40.fullmatch(expected_commit) or not SHA256.fullmatch(expected_manifest):
        raise ValueError("EXPECTED_SOURCE_PIN_REQUIRED")
    if type(limit) is not int or not 1 <= limit <= MAX_MATCHES:
        raise ValueError("RESULT_BUDGET_HOLD")
    fts = literal_query(text)
    filehash = hash_file(index)
    conn = sqlite3.connect(index.resolve().as_uri() + "?mode=ro&immutable=1", uri=True, timeout=10)
    try:
        conn.execute("PRAGMA query_only=ON")
        if conn.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("INDEX_INTEGRITY_HOLD")
        meta = _load_metadata(conn, commit=expected_commit, manifest=expected_manifest)
        entries = conn.execute("""
          SELECT d.id,d.path,d.title,d.sha256,d.source_url,d.parse_status,
            snippet(docs_fts,2,'[',']','...',12)
          FROM docs_fts JOIN documents d ON d.id=docs_fts.rowid
          WHERE docs_fts MATCH ? ORDER BY rank LIMIT ?
        """, (fts, limit)).fetchall()
        matches = []
        for ident, path, title, source_sha, url, parse_status, excerpt in entries:
            if not SHA256.fullmatch(source_sha) or url != _source_url(expected_commit,path):
                raise ValueError("INDEX_SOURCE_URL_HOLD")
            links = []
            for destid, destpath, destsha, desturl, kind in conn.execute("""
              SELECT d.id,d.path,d.sha256,d.source_url,e.kind FROM edges e
              JOIN documents d ON d.id=e.target_id
              WHERE e.source_id=? ORDER BY e.target_id,e.kind LIMIT ?
            """,(ident,MAX_NEIGHBORS)).fetchall():
                if kind not in ("EXPLICIT_PATH", "EXPLICIT_URL") or not SHA256.fullmatch(destsha) or desturl != _source_url(expected_commit,destpath):
                    raise ValueError("INDEX_RELATION_HOLD")
                links.append({"id":destid,"path":destpath,"sha256":destsha,"url":desturl,"kind":kind})
            matches.append({"id":ident,"path":path,"title":title[:240],"sha256":source_sha,
                "url":url,"parse_status":parse_status,"excerpt":excerpt[:500],"related":links})
        payload = {
            "schema":SCHEMA,
            "origin":{"repository":ORIGIN,"source_commit":expected_commit,
                      "source_manifest_sha256":expected_manifest,"index_sha256":filehash,
                      "indexed_json":meta["indexed_json"],"explicit_relations":meta["explicit_relations"]},
            "query":{"text":text[:250],"fts_literal":fts,"limit":limit},
            "matches":matches,
            "control":{"read_only":True,"external_effect_permitted":False,
                       "direct_graph_mutation_permitted":False,"github_write_permitted":False,
                       "authority_delta":0,"mass_effect_budget_delta":0},
            "claim_ceiling":{"catalog_presence_is_truth":False,"reference_is_independent_evidence":False,
                             "memory_proposal_is_admission":False,"receipts_are_authentication":False}
        }
        payload["packet_sha256"] = digest(payload)
        return payload
    finally:
        conn.close()

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--index",type=Path,required=True)
    p.add_argument("--query",required=True)
    p.add_argument("--expected-source-commit",required=True)
    p.add_argument("--expected-manifest-sha256",required=True)
    p.add_argument("--limit",type=int,default=8)
    p.add_argument("--output",type=Path)
    args=p.parse_args()
    result=make_packet(args.index,args.query,expected_commit=args.expected_source_commit,
                       expected_manifest=args.expected_manifest_sha256,limit=args.limit)
    body=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if args.output:
        with args.output.open("x",encoding="utf-8") as fh:
            fh.write(body)
    else:
        print(body,end="")
    return 0
if __name__=="__main__":
    raise SystemExit(main())
