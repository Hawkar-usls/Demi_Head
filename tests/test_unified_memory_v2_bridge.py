from __future__ import annotations
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

TARGET=Path(__file__).resolve().parents[1]/"tools"/"unified_memory_v2_bridge.py"
spec=importlib.util.spec_from_file_location("umv2_demihead",TARGET)
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

COMMIT="a"*40
MANIFEST="b"*64

class ReadOnlyMemoryBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"sandbox.sqlite"
        c=sqlite3.connect(self.db)
        c.executescript("""
        CREATE TABLE metadata(k TEXT PRIMARY KEY,v TEXT);
        CREATE TABLE documents(
          id INTEGER PRIMARY KEY, path TEXT UNIQUE NOT NULL, sha256 TEXT,
          bytes INTEGER, namespace TEXT, title TEXT, parse_status TEXT,
          body TEXT, source_url TEXT);
        CREATE VIRTUAL TABLE docs_fts USING fts5(path,title,body,content='documents',content_rowid='id');
        CREATE TABLE edges(source_id INTEGER,target_id INTEGER,kind TEXT,pointer TEXT);
        """)
        self.url=lambda p:"https://github.com/Hawkar-usls/janus-meta-registry/blob/"+COMMIT+"/"+p
        rows=[
          (1,"research/scoby.json","1"*64,100,"research","SCOBY bio-cellulose","OK","SCOBY bio cellulose",self.url("research/scoby.json")),
          (2,"research/skin.json","2"*64,75,"research","SkinGPT membrane","OK","SkinGPT",self.url("research/skin.json"))
        ]
        c.executemany("INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?)",rows)
        c.executemany("INSERT INTO docs_fts(rowid,path,title,body) VALUES(?,?,?,?)",[(x[0],x[1],x[5],x[7]) for x in rows])
        c.execute("INSERT INTO edges VALUES(1,2,'EXPLICIT_PATH','/reference')")
        meta={"schema":bridge.INDEX_SCHEMA,"source_commit":COMMIT,"source_manifest_sha256":MANIFEST,
              "coverage_complete":True,"read_only":True,"scientific_authority_granted":False,
              "historical_git_included":False,"indexed_json":2,"explicit_relations":1}
        c.executemany("INSERT INTO metadata VALUES(?,?)",[(k,json.dumps(v)) for k,v in meta.items()])
        c.commit();c.close()
    def tearDown(self):self.temp.cleanup()
    def run_query(self,text="SCOBY"):
        return bridge.make_packet(self.db,text,expected_commit=COMMIT,expected_manifest=MANIFEST)
    def test_bounded_receipt_and_explicit_graph_links(self):
        pkt=self.run_query()
        self.assertEqual(len(pkt["matches"]),1)
        self.assertEqual(pkt["matches"][0]["related"][0]["path"],"research/skin.json")
        self.assertEqual(pkt["packet_sha256"],bridge.digest({k:v for k,v in pkt.items() if k!="packet_sha256"}))
        self.assertFalse(pkt["control"]["github_write_permitted"])
        self.assertFalse(pkt["claim_ceiling"]["catalog_presence_is_truth"])
    def test_literal_query_escapes_fts_metacharacters(self):
        pkt=self.run_query('SCOBY - "bio-cellulose"')
        self.assertEqual(pkt["matches"][0]["path"],"research/scoby.json")
        with self.assertRaisesRegex(ValueError,"EMPTY_QUERY_HOLD"):
            self.run_query("!!!")
    def test_fail_closed_on_wrong_pinned_commit(self):
        with self.assertRaisesRegex(ValueError,"INDEX_SOURCE_COMMIT_HOLD"):
            bridge.make_packet(self.db,"SCOBY",expected_commit="c"*40,expected_manifest=MANIFEST)
        with self.assertRaisesRegex(ValueError,"INDEX_MANIFEST_SHA256_HOLD"):
            bridge.make_packet(self.db,"SCOBY",expected_commit=COMMIT,expected_manifest="d"*64)
    def test_fail_closed_on_tampered_url(self):
        c=sqlite3.connect(self.db)
        c.execute("UPDATE documents SET source_url=? WHERE id=1",("https://evil.example/record",))
        c.commit();c.close()
        with self.assertRaisesRegex(ValueError,"INDEX_SOURCE_URL_HOLD"):
            self.run_query()
    def test_no_graph_or_database_mutations(self):
        before=self.db.read_bytes()
        self.run_query("SCOBY")
        self.assertEqual(self.db.read_bytes(),before)
        with self.assertRaisesRegex(ValueError,"RESULT_BUDGET_HOLD"):
            bridge.make_packet(self.db,"SCOBY",expected_commit=COMMIT,expected_manifest=MANIFEST,limit=100)
if __name__=="__main__":unittest.main()
