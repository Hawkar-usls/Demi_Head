from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from nexus_storage_fault_gate import (
    _inspect_main_db_envelope,
    preflight_evidence_stores,
    storage_guarded_recovery,
)

CONTRACT = "JANUS_NEXUS_PHYSICAL_WAL_SIDECAR_GATE_V1"
SCHEMA = "janus.demihead.nexus_wal_sidecar_gate_receipt.v1"
WAL_HEADER_BYTES = 32
WAL_FRAME_HEADER_BYTES = 24
WAL_MAGIC = {0x377F0682, 0x377F0683}
WAL_FORMAT_VERSION = 3007000


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _valid_page_size(page_size: int) -> bool:
    return page_size == 65536 or (512 <= page_size <= 32768 and page_size & (page_size - 1) == 0)


def inspect_wal_sidecar(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path)
    wal = Path(str(db) + "-wal")
    main = _inspect_main_db_envelope(db) if db.exists() and db.is_file() else {
        "valid": False,
        "reason": "MAIN_DB_MISSING_OR_INVALID_PATH",
        "file_size": None,
        "page_size": None,
    }
    base = {
        "db_path_redacted": db.name,
        "wal_path_redacted": wal.name,
        "main_physical_envelope": main,
        "wal_exists": wal.exists(),
        "read_only_inspection": True,
        "repair_attempted": False,
        "delete_attempted": False,
    }
    if main.get("valid") is not True:
        return {
            **base,
            "status": "NOT_EVALUATED_MAIN_UNHEALTHY",
            "healthy": None,
            "reason": "PARENT_MAIN_DB_GATE_MUST_DECIDE",
            "wal_sha256": None,
        }
    if not wal.exists():
        return {
            **base,
            "status": "ABSENT_CHECKPOINTED_STATE_PERMITTED",
            "healthy": True,
            "reason": "NO_WAL_SIDECAR_PRESENT",
            "wal_sha256": None,
            "frame_count": 0,
        }
    if not wal.is_file():
        return {
            **base,
            "status": "WAL_INVALID_PATH",
            "healthy": False,
            "reason": "WAL_NOT_REGULAR_FILE",
            "wal_sha256": None,
        }
    try:
        before_sha = _sha256(wal)
        size = wal.stat().st_size
        with wal.open("rb") as handle:
            header = handle.read(WAL_HEADER_BYTES)
    except OSError as exc:
        return {
            **base,
            "status": "WAL_UNREADABLE",
            "healthy": False,
            "reason": type(exc).__name__,
            "wal_sha256": None,
        }
    if size < WAL_HEADER_BYTES or len(header) < WAL_HEADER_BYTES:
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_TRUNCATED_BELOW_HEADER",
            "wal_sha256": before_sha,
            "wal_size": size,
        }
    magic = int.from_bytes(header[0:4], "big")
    version = int.from_bytes(header[4:8], "big")
    page_size = int.from_bytes(header[8:12], "big")
    if magic not in WAL_MAGIC:
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_MAGIC_MISMATCH",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "wal_sha256": before_sha,
            "wal_size": size,
        }
    if version != WAL_FORMAT_VERSION:
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_FORMAT_VERSION_MISMATCH",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "wal_sha256": before_sha,
            "wal_size": size,
        }
    if not _valid_page_size(page_size):
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_INVALID_PAGE_SIZE",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "wal_sha256": before_sha,
            "wal_size": size,
        }
    if page_size != main.get("page_size"):
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_MAIN_PAGE_SIZE_MISMATCH",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "main_page_size": main.get("page_size"),
            "wal_sha256": before_sha,
            "wal_size": size,
        }
    frame_bytes = WAL_FRAME_HEADER_BYTES + page_size
    payload_bytes = size - WAL_HEADER_BYTES
    if payload_bytes % frame_bytes != 0:
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_FRAME_ALIGNMENT_MISMATCH",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "wal_sha256": before_sha,
            "wal_size": size,
            "frame_bytes": frame_bytes,
        }
    frame_count = payload_bytes // frame_bytes
    invalid_frame_index = None
    try:
        with wal.open("rb") as handle:
            for index in range(frame_count):
                handle.seek(WAL_HEADER_BYTES + index * frame_bytes)
                frame_header = handle.read(WAL_FRAME_HEADER_BYTES)
                if len(frame_header) != WAL_FRAME_HEADER_BYTES:
                    invalid_frame_index = index
                    break
                page_number = int.from_bytes(frame_header[0:4], "big")
                if page_number < 1:
                    invalid_frame_index = index
                    break
        after_sha = _sha256(wal)
    except OSError:
        return {
            **base,
            "status": "WAL_UNREADABLE",
            "healthy": False,
            "reason": "WAL_FRAME_READ_FAILED",
            "wal_sha256": before_sha,
        }
    if invalid_frame_index is not None:
        return {
            **base,
            "status": "WAL_PHYSICAL_ENVELOPE_FAIL",
            "healthy": False,
            "reason": "WAL_FRAME_PAGE_NUMBER_INVALID",
            "magic": f"0x{magic:08x}",
            "version": version,
            "page_size": page_size,
            "wal_sha256": before_sha,
            "wal_size": size,
            "frame_count": frame_count,
            "invalid_frame_index": invalid_frame_index,
            "bytes_unchanged": before_sha == after_sha,
        }
    return {
        **base,
        "status": "WAL_SIDECAR_HEALTHY",
        "healthy": True,
        "reason": "WAL_PHYSICAL_ENVELOPE_PASS",
        "magic": f"0x{magic:08x}",
        "version": version,
        "page_size": page_size,
        "wal_sha256": before_sha,
        "wal_size": size,
        "frame_count": frame_count,
        "bytes_unchanged": before_sha == after_sha,
        "checksum_chain_verified": False,
        "salt_chain_verified": False,
    }


def preflight_evidence_stores_with_wal(*, lifecycle_db: str | Path, dispatch_db: str | Path,
                                       replay_db: str | Path) -> dict[str, Any]:
    paths = {
        "lifecycle": Path(lifecycle_db),
        "dispatch": Path(dispatch_db),
        "replay": Path(replay_db),
    }
    wal = {name: inspect_wal_sidecar(path) for name, path in paths.items()}
    wal_failure = any(item.get("healthy") is False for item in wal.values())
    if wal_failure:
        return {
            "schema": SCHEMA,
            "contract": CONTRACT,
            "status": "HOLD_WAL_EVIDENCE_UNAVAILABLE",
            "wal_sidecars": wal,
            "parent_storage_preflight": None,
            "control": {
                "wal_inspection_read_only": True,
                "wal_repair": False,
                "wal_delete_on_failure": False,
                "automatic_recovery_permitted": False,
                "automatic_restart_permitted": False,
                "automatic_retry_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }
    parent = preflight_evidence_stores(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
    )
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "WAL_STORAGE_PREFLIGHT_PASS" if parent["status"] == "STORAGE_PREFLIGHT_PASS" else parent["status"],
        "wal_sidecars": wal,
        "parent_storage_preflight": parent,
        "control": {
            "wal_inspection_read_only": True,
            "wal_repair": False,
            "wal_delete_on_failure": False,
            "automatic_recovery_permitted": False,
            "automatic_restart_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def wal_guarded_recovery(*, lifecycle_db: str | Path, dispatch_db: str | Path, replay_db: str | Path,
                         service_id: str, expected_instance_id: str, operator_ack: bool,
                         process_dead_attested: bool, now_ms: int | None = None) -> dict[str, Any]:
    gate = preflight_evidence_stores_with_wal(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
    )
    if gate["status"] != "WAL_STORAGE_PREFLIGHT_PASS":
        return {
            **gate,
            "recovery": None,
            "wal_gate_blocked_recovery_mutation": True,
        }
    recovery = storage_guarded_recovery(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
        service_id=service_id,
        expected_instance_id=expected_instance_id,
        operator_ack=operator_ack,
        process_dead_attested=process_dead_attested,
        now_ms=now_ms,
    )
    return {
        **gate,
        "status": recovery["status"],
        "recovery": recovery,
        "wal_gate_blocked_recovery_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JANUS Nexus physical WAL sidecar gate.")
    parser.add_argument("--lifecycle-db", required=True, type=Path)
    parser.add_argument("--dispatch-db", required=True, type=Path)
    parser.add_argument("--replay-db", required=True, type=Path)
    args = parser.parse_args()
    result = preflight_evidence_stores_with_wal(
        lifecycle_db=args.lifecycle_db,
        dispatch_db=args.dispatch_db,
        replay_db=args.replay_db,
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "WAL_STORAGE_PREFLIGHT_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
