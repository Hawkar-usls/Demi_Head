from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any
from urllib.parse import quote

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2
from nexus_lifecycle_recovery import reconcile_stale_lifecycle
from nexus_loopback_lifecycle_gate import SqliteLifecycleLedger

CONTRACT = "JANUS_NEXUS_STORAGE_FAULT_GATE_V1"
SCHEMA = "janus.demihead.nexus_storage_fault_gate_receipt.v1"
SQLITE_HEADER = b"SQLite format 3\x00"
SQLITE_HEADER_BYTES = 100

STORE_REQUIREMENTS = {
    "lifecycle": ["nexus_one_shot_lifecycle", "nexus_one_shot_lifecycle_events"],
    "dispatch": ["nexus_dispatch_ledger_v2"],
    "replay": ["nexus_replay_ledger"],
}


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _ro_uri(path: Path) -> str:
    return f"file:{quote(str(path.resolve()))}?mode=ro"


def _inspect_main_db_envelope(path: Path) -> dict[str, Any]:
    """Validate the physical main SQLite file before WAL-aware SQLite open.

    SQLite may reconstruct a readable logical database from a surviving WAL even when
    the main .db file has been overwritten or truncated. For an evidence store, that
    must not silently turn explicit main-file damage into a healthy preflight result.
    """
    try:
        size = path.stat().st_size
        with path.open("rb") as handle:
            header = handle.read(SQLITE_HEADER_BYTES)
    except OSError as exc:
        return {
            "valid": False,
            "reason": type(exc).__name__,
            "file_size": None,
            "page_size": None,
        }

    if size < SQLITE_HEADER_BYTES or len(header) < SQLITE_HEADER_BYTES:
        return {
            "valid": False,
            "reason": "MAIN_DB_TOO_SMALL_FOR_SQLITE_HEADER",
            "file_size": size,
            "page_size": None,
        }
    if header[:16] != SQLITE_HEADER:
        return {
            "valid": False,
            "reason": "MAIN_DB_SQLITE_HEADER_MISMATCH",
            "file_size": size,
            "page_size": None,
        }

    raw_page_size = int.from_bytes(header[16:18], "big")
    page_size = 65536 if raw_page_size == 1 else raw_page_size
    valid_page_size = page_size == 65536 or (
        512 <= page_size <= 32768 and page_size & (page_size - 1) == 0
    )
    if not valid_page_size:
        return {
            "valid": False,
            "reason": "MAIN_DB_INVALID_PAGE_SIZE",
            "file_size": size,
            "page_size": page_size,
        }
    if size < page_size:
        return {
            "valid": False,
            "reason": "MAIN_DB_TRUNCATED_BELOW_ONE_PAGE",
            "file_size": size,
            "page_size": page_size,
        }
    if size % page_size != 0:
        return {
            "valid": False,
            "reason": "MAIN_DB_SIZE_NOT_WHOLE_PAGES",
            "file_size": size,
            "page_size": page_size,
        }
    return {
        "valid": True,
        "reason": "MAIN_DB_PHYSICAL_ENVELOPE_PASS",
        "file_size": size,
        "page_size": page_size,
    }


def _sidecar_inventory(path: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for suffix, label in (("-wal", "wal"), ("-shm", "shm")):
        sidecar = Path(str(path) + suffix)
        if not sidecar.exists():
            result[label] = {"exists": False, "sha256": None, "size": None}
            continue
        try:
            result[label] = {
                "exists": True,
                "sha256": _file_sha256(sidecar),
                "size": sidecar.stat().st_size,
            }
        except OSError:
            result[label] = {"exists": True, "sha256": None, "size": None}
    return result


def inspect_sqlite_store(path: str | Path, *, store_kind: str) -> dict[str, Any]:
    if store_kind not in STORE_REQUIREMENTS:
        raise ValueError(f"unknown store_kind: {store_kind}")
    target = Path(path)
    base = {
        "store_kind": store_kind,
        "path_redacted": target.name,
        "required_tables": STORE_REQUIREMENTS[store_kind],
        "exists": target.exists(),
        "regular_file": target.is_file(),
        "read_only_preflight": True,
        "mutation_performed": False,
    }
    if not target.exists():
        return {**base, "status": "MISSING", "healthy": False, "reason": "STORE_MISSING", "file_sha256": None}
    if not target.is_file():
        return {**base, "status": "INVALID_PATH", "healthy": False, "reason": "STORE_NOT_REGULAR_FILE", "file_sha256": None}
    try:
        before_sha = _file_sha256(target)
    except OSError:
        return {**base, "status": "UNREADABLE", "healthy": False, "reason": "STORE_BYTES_UNREADABLE", "file_sha256": None}

    envelope = _inspect_main_db_envelope(target)
    sidecars_before = _sidecar_inventory(target)
    if envelope["valid"] is not True:
        return {
            **base,
            "status": "PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": envelope["reason"],
            "physical_envelope": envelope,
            "sidecars": sidecars_before,
            "file_sha256": before_sha,
            "bytes_unchanged": True,
        }

    try:
        db = sqlite3.connect(_ro_uri(target), uri=True, timeout=0.25)
        try:
            db.execute("PRAGMA query_only=ON")
            quick = db.execute("PRAGMA quick_check").fetchone()
            quick_value = str(quick[0]) if quick else "NO_RESULT"
            table_rows = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            tables = sorted(str(row[0]) for row in table_rows)
        finally:
            db.close()
    except sqlite3.Error as exc:
        return {
            **base,
            "status": "SQLITE_ERROR",
            "healthy": False,
            "reason": type(exc).__name__,
            "physical_envelope": envelope,
            "sidecars": sidecars_before,
            "file_sha256": before_sha,
        }
    try:
        after_sha = _file_sha256(target)
    except OSError:
        after_sha = None
    missing = sorted(set(STORE_REQUIREMENTS[store_kind]) - set(tables))
    if quick_value.lower() != "ok":
        return {
            **base,
            "status": "INTEGRITY_FAIL",
            "healthy": False,
            "reason": "SQLITE_QUICK_CHECK_NOT_OK",
            "quick_check": quick_value,
            "tables": tables,
            "missing_required_tables": missing,
            "physical_envelope": envelope,
            "sidecars": sidecars_before,
            "file_sha256": before_sha,
            "bytes_unchanged": before_sha == after_sha,
        }
    if missing:
        return {
            **base,
            "status": "SCHEMA_MISMATCH",
            "healthy": False,
            "reason": "REQUIRED_TABLES_MISSING",
            "quick_check": quick_value,
            "tables": tables,
            "missing_required_tables": missing,
            "physical_envelope": envelope,
            "sidecars": sidecars_before,
            "file_sha256": before_sha,
            "bytes_unchanged": before_sha == after_sha,
        }
    return {
        **base,
        "status": "HEALTHY",
        "healthy": True,
        "reason": "PHYSICAL_ENVELOPE_AND_READ_ONLY_INTEGRITY_SCHEMA_CHECK_PASS",
        "quick_check": quick_value,
        "tables": tables,
        "missing_required_tables": [],
        "physical_envelope": envelope,
        "sidecars": sidecars_before,
        "file_sha256": before_sha,
        "bytes_unchanged": before_sha == after_sha,
    }


def preflight_evidence_stores(*, lifecycle_db: str | Path, dispatch_db: str | Path, replay_db: str | Path) -> dict[str, Any]:
    stores = {
        "lifecycle": inspect_sqlite_store(lifecycle_db, store_kind="lifecycle"),
        "dispatch": inspect_sqlite_store(dispatch_db, store_kind="dispatch"),
        "replay": inspect_sqlite_store(replay_db, store_kind="replay"),
    }
    healthy = all(item["healthy"] is True for item in stores.values())
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "STORAGE_PREFLIGHT_PASS" if healthy else "HOLD_STORAGE_EVIDENCE_UNAVAILABLE",
        "stores": stores,
        "control": {
            "preflight_read_only": True,
            "main_db_physical_envelope_required_before_wal_aware_open": True,
            "missing_store_auto_creation": False,
            "corrupt_store_auto_replacement": False,
            "schema_auto_migration": False,
            "automatic_recovery_permitted": False,
            "automatic_restart_permitted": False,
            "automatic_retry_permitted": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "full_filesystem_health_established": False,
            "future_write_success_established": False,
            "wal_semantic_consistency_fully_established": False,
            "power_loss_tolerance_established": False,
            "semantic_database_correctness_established": False,
            "production_storage_readiness": False,
        },
    }


def storage_guarded_recovery(*, lifecycle_db: str | Path, dispatch_db: str | Path, replay_db: str | Path,
                             service_id: str, expected_instance_id: str, operator_ack: bool,
                             process_dead_attested: bool, now_ms: int | None = None) -> dict[str, Any]:
    preflight = preflight_evidence_stores(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
    )
    if preflight["status"] != "STORAGE_PREFLIGHT_PASS":
        return {
            **preflight,
            "recovery": None,
            "storage_gate_blocked_recovery_mutation": True,
        }
    try:
        lifecycle = SqliteLifecycleLedger(lifecycle_db)
        dispatch = SqliteDispatchLedgerV2(dispatch_db)
    except (sqlite3.Error, OSError) as exc:
        return {
            **preflight,
            "status": "HOLD_STORAGE_EVIDENCE_UNAVAILABLE",
            "recovery": None,
            "storage_gate_blocked_recovery_mutation": True,
            "post_preflight_open_failure": type(exc).__name__,
        }
    recovery = reconcile_stale_lifecycle(
        lifecycle,
        dispatch,
        service_id=service_id,
        expected_instance_id=expected_instance_id,
        operator_ack=operator_ack,
        process_dead_attested=process_dead_attested,
        now_ms=now_ms,
    )
    return {
        **preflight,
        "status": recovery["status"],
        "recovery": recovery,
        "storage_gate_blocked_recovery_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JANUS Nexus storage integrity/schema gate.")
    parser.add_argument("--lifecycle-db", required=True, type=Path)
    parser.add_argument("--dispatch-db", required=True, type=Path)
    parser.add_argument("--replay-db", required=True, type=Path)
    parser.add_argument("--service-id")
    parser.add_argument("--expected-instance-id")
    parser.add_argument("--operator-ack", action="store_true")
    parser.add_argument("--process-dead-attested", action="store_true")
    parser.add_argument("--now-ms", type=int)
    args = parser.parse_args()
    if args.service_id or args.expected_instance_id:
        if not args.service_id or not args.expected_instance_id:
            parser.error("guarded recovery requires both --service-id and --expected-instance-id")
        result = storage_guarded_recovery(
            lifecycle_db=args.lifecycle_db,
            dispatch_db=args.dispatch_db,
            replay_db=args.replay_db,
            service_id=args.service_id,
            expected_instance_id=args.expected_instance_id,
            operator_ack=args.operator_ack,
            process_dead_attested=args.process_dead_attested,
            now_ms=args.now_ms,
        )
    else:
        result = preflight_evidence_stores(
            lifecycle_db=args.lifecycle_db,
            dispatch_db=args.dispatch_db,
            replay_db=args.replay_db,
        )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] != "HOLD_STORAGE_EVIDENCE_UNAVAILABLE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
