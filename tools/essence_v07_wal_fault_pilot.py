#!/usr/bin/env python3
"""ESSENCE v0.7: REAL SQLite engine, induced WAL fault pilot; no natural-fault claims.

Compares frozen physical main-DB baseline vs existing WAL sidecar proposal.
Also reports already-existing stronger WAL checksum/salt gate to disclose
weaknesses of the proposed physical-only idea. ALWAYS development-only until
prospective post-freeze external assessment on independent instances.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from nexus_storage_fault_gate import _inspect_main_db_envelope
from nexus_wal_sidecar_gate import inspect_wal_sidecar
from nexus_wal_checksum_gate import inspect_wal_checksum_salt_chain

MODES = (
    "healthy", "magic_corrupt", "version_corrupt", "page_size_corrupt",
    "frame_page_zero", "frame_truncation", "payload_bit_flip",
    "frame_salt_flip",
)
SCHEMA = "janus.essence.v07.wal_fault_pilot/0.1"

def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def corrupt(data: bytes, mode: str) -> bytes:
    if mode not in MODES:
        raise ValueError("UNREGISTERED_FAULT_FAMILY")
    if mode == "healthy":
        return data
    raw = bytearray(data)
    if len(raw) < 60:
        raise ValueError("WAL_HAS_NO_REAL_FRAMES")
    if mode == "magic_corrupt":
        raw[0] ^= 0x80
    elif mode == "version_corrupt":
        raw[4] ^= 0x01
    elif mode == "page_size_corrupt":
        raw[8:12] = (1234).to_bytes(4, "big")
    elif mode == "frame_page_zero":
        raw[32:36] = b"\0\0\0\0"
    elif mode == "frame_truncation":
        return bytes(raw[:-1])
    elif mode == "payload_bit_flip":
        raw[32 + 24 + 13] ^= 0x01
    elif mode == "frame_salt_flip":
        raw[32 + 8] ^= 0x01
    return bytes(raw)

def pilot(cycles=3):
    if type(cycles) is not int or not 1 <= cycles <= 16:
        raise ValueError("UNBOUNDED_CYCLES")
    records = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        live = root / "actual-engine.db"
        # SQLite itself creates genuine WAL pages; only subsequent fault
        # injection is controlled. No fake WAL header constructed by us.
        keeper = sqlite3.connect(str(live), isolation_level=None)
        try:
            keeper.execute("PRAGMA journal_mode=WAL")
            keeper.execute("PRAGMA wal_autocheckpoint=0")
            keeper.execute("CREATE TABLE journal (id INTEGER PRIMARY KEY, value TEXT NOT NULL)")
            for i in range(cycles * len(MODES) + 4):
                keeper.execute("INSERT INTO journal(value) VALUES (?)",
                               (f"JANUS_V07_REAL_SQLITE_TX_{i}",))
            wal = Path(str(live) + "-wal")
            if not wal.exists() or wal.stat().st_size < 60:
                raise RuntimeError("REAL_WAL_NOT_AVAILABLE")
            original_main, original_wal = live.read_bytes(), wal.read_bytes()
            if not _inspect_main_db_envelope(live)["valid"]:
                raise RuntimeError("REAL_MAIN_DB_NOT_VALID")
            for cycle in range(cycles):
                for mode in MODES:
                    trial_id = cycle * len(MODES) + MODES.index(mode)
                    destination = root / f"copy-{trial_id:03d}.db"
                    destination.write_bytes(original_main)
                    changed = corrupt(original_wal, mode)
                    sidecar = Path(str(destination) + "-wal")
                    sidecar.write_bytes(changed)
                    before_hash = digest(changed)
                    baseline = _inspect_main_db_envelope(destination)
                    physical = inspect_wal_sidecar(destination)
                    stronger = inspect_wal_checksum_salt_chain(destination)
                    if digest(sidecar.read_bytes()) != before_hash:
                        raise RuntimeError("AUDITOR_MUTATED_SOURCE")
                    is_bad = mode != "healthy"
                    records.append({
                        "trial_id": f"sqlite-{trial_id:03d}",
                        "case_kind": mode,
                        "origin":"LOCAL_SQLITE_RUNTIME_PLUS_INDUCED_FAULT",
                        "ground_truth_bad": is_bad,
                        "baseline_says_bad": baseline["valid"] is not True,
                        "candidate_says_bad": physical["healthy"] is not True,
                        "stronger_existing_gate_says_bad": stronger["healthy"] is not True,
                        "main_sha256": digest(original_main),
                        "wal_sha256": before_hash,
                        "physical_status": physical["status"],
                        "stronger_status": stronger["status"],
                    })
        finally:
            keeper.close()
    def errors(key):
        false_accept = sum(r["ground_truth_bad"] and not r[key] for r in records)
        false_reject = sum(not r["ground_truth_bad"] and r[key] for r in records)
        return {"correct": len(records) - false_accept - false_reject,
                "false_accept_corrupt_wal": false_accept,
                "false_reject_intact_wal": false_reject}
    report={
        "schema": SCHEMA,
        "evidence_class":"REAL_SQLITE_ENGINE_CONTROLLED_INDUCED_FAULTS",
        "scientific_gate":"DEVELOPMENT_ONLY_NO_PROSPECTIVE_OR_EXTERNAL_REPLICATION",
        "source_repository":"Hawkar-usls/Demi_Head",
        "existing_main_baseline_git_blob_sha1":"8cb257dbb65d34f095610a60ea9d491d940b09bc",
        "physical_candidate_git_blob_sha1":"0305c55cf2987480beb94275a71eab3d34963bc5",
        "generated_new_faults_not_natural_failures":True,
        "total_trials":len(records),
        "fault_families":list(MODES),
        "baseline":errors("baseline_says_bad"),
        "candidate":errors("candidate_says_bad"),
        "already_existing_stronger_checksum_gate":errors("stronger_existing_gate_says_bad"),
        "records":records,
        "new_neural_model_trained":False,
        "externally_independent_verifier":False,
        "production_authority":False,
        "offspring_activation":False,
    }
    report["report_sha256"]=hashlib.sha256(json.dumps(
        report,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycles",type=int,default=3)
    p.add_argument("--out",required=True)
    args=p.parse_args()
    result=pilot(args.cycles)
    dest=Path(args.out)
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():
        raise FileExistsError("NO_OVERWRITE")
    dest.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print(json.dumps({k:result[k] for k in
          ("scientific_gate","total_trials","baseline","candidate","already_existing_stronger_checksum_gate")}))
if __name__=="__main__":
    main()
