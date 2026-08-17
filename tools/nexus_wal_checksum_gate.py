from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from nexus_wal_sidecar_gate import inspect_wal_sidecar, preflight_evidence_stores_with_wal, wal_guarded_recovery

CONTRACT = "JANUS_NEXUS_WAL_CHECKSUM_SALT_GATE_V1"
SCHEMA = "janus.demihead.nexus_wal_checksum_salt_gate_receipt.v1"
WAL_HEADER_BYTES = 32
WAL_FRAME_HEADER_BYTES = 24
WAL_MAGIC_LITTLE_CHECKSUM_WORDS = 0x377F0682
WAL_MAGIC_BIG_CHECKSUM_WORDS = 0x377F0683
MASK32 = 0xFFFFFFFF


def wal_checksum_bytes(data: bytes, *, byteorder: str, initial: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    """SQLite WAL checksum over an 8-byte-aligned byte sequence.

    Integer interpretation follows the WAL magic. Arithmetic is modulo 2^32.
    Stored checksum fields themselves are always big-endian and are handled by
    the caller rather than by this primitive.
    """
    if byteorder not in {"big", "little"}:
        raise ValueError("byteorder must be 'big' or 'little'")
    if len(data) % 8 != 0:
        raise ValueError("WAL checksum input length must be a multiple of 8 bytes")
    s0, s1 = (int(initial[0]) & MASK32, int(initial[1]) & MASK32)
    for offset in range(0, len(data), 8):
        x0 = int.from_bytes(data[offset:offset + 4], byteorder)
        x1 = int.from_bytes(data[offset + 4:offset + 8], byteorder)
        s0 = (s0 + x0 + s1) & MASK32
        s1 = (s1 + x1 + s0) & MASK32
    return s0, s1


def _stored_checksum(raw: bytes) -> tuple[int, int]:
    if len(raw) != 8:
        raise ValueError("stored WAL checksum must be exactly 8 bytes")
    return int.from_bytes(raw[:4], "big"), int.from_bytes(raw[4:], "big")


def _checksum_byteorder(magic: int) -> str:
    if magic == WAL_MAGIC_BIG_CHECKSUM_WORDS:
        return "big"
    if magic == WAL_MAGIC_LITTLE_CHECKSUM_WORDS:
        return "little"
    raise ValueError("unsupported WAL magic for checksum semantics")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_wal_checksum_salt_chain(db_path: str | Path) -> dict[str, Any]:
    db = Path(db_path)
    physical = inspect_wal_sidecar(db)
    base = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "db_path_redacted": db.name,
        "physical_wal": physical,
        "read_only_inspection": True,
        "wal_repair": False,
        "wal_delete_on_failure": False,
    }

    if physical.get("healthy") is None:
        return {
            **base,
            "status": "NOT_EVALUATED_PHYSICAL_PARENT_UNHEALTHY",
            "healthy": None,
            "reason": "PHYSICAL_PARENT_GATE_MUST_DECIDE",
            "header_checksum_verified": False,
            "salt_chain_verified": False,
            "frame_checksum_chain_verified": False,
        }
    if physical.get("status") == "ABSENT_CHECKPOINTED_STATE_PERMITTED":
        return {
            **base,
            "status": "ABSENT_CHECKPOINTED_STATE_PERMITTED",
            "healthy": True,
            "reason": "NO_WAL_BYTES_TO_AUTHENTICATE",
            "header_checksum_verified": True,
            "salt_chain_verified": True,
            "frame_checksum_chain_verified": True,
            "verified_frame_count": 0,
        }
    if physical.get("healthy") is not True:
        return {
            **base,
            "status": "NOT_EVALUATED_PHYSICAL_WAL_UNHEALTHY",
            "healthy": False,
            "reason": "PHYSICAL_WAL_GATE_FAILED",
            "header_checksum_verified": False,
            "salt_chain_verified": False,
            "frame_checksum_chain_verified": False,
        }

    wal = Path(str(db) + "-wal")
    try:
        before_sha = _file_sha256(wal)
        data = wal.read_bytes()
    except OSError as exc:
        return {
            **base,
            "status": "WAL_INTEGRITY_READ_FAILED",
            "healthy": False,
            "reason": type(exc).__name__,
            "header_checksum_verified": False,
            "salt_chain_verified": False,
            "frame_checksum_chain_verified": False,
        }

    magic = int.from_bytes(data[0:4], "big")
    byteorder = _checksum_byteorder(magic)
    header_salt = data[16:24]
    calculated = wal_checksum_bytes(data[:24], byteorder=byteorder)
    stored_header = _stored_checksum(data[24:32])
    if calculated != stored_header:
        return {
            **base,
            "status": "WAL_CHECKSUM_SALT_CHAIN_FAIL",
            "healthy": False,
            "reason": "WAL_HEADER_CHECKSUM_MISMATCH",
            "checksum_word_byteorder": byteorder,
            "header_checksum_verified": False,
            "salt_chain_verified": False,
            "frame_checksum_chain_verified": False,
            "stored_header_checksum": list(stored_header),
            "calculated_header_checksum": list(calculated),
            "wal_sha256": before_sha,
        }

    page_size = int(physical["page_size"])
    frame_size = WAL_FRAME_HEADER_BYTES + page_size
    frame_count = int(physical["frame_count"])
    chain = calculated
    salts_verified = True

    for index in range(frame_count):
        frame_offset = WAL_HEADER_BYTES + index * frame_size
        frame_header = data[frame_offset:frame_offset + WAL_FRAME_HEADER_BYTES]
        page = data[frame_offset + WAL_FRAME_HEADER_BYTES:frame_offset + frame_size]
        if frame_header[8:16] != header_salt:
            return {
                **base,
                "status": "WAL_CHECKSUM_SALT_CHAIN_FAIL",
                "healthy": False,
                "reason": "WAL_FRAME_SALT_MISMATCH",
                "failed_frame_index": index + 1,
                "checksum_word_byteorder": byteorder,
                "header_checksum_verified": True,
                "salt_chain_verified": False,
                "frame_checksum_chain_verified": False,
                "wal_sha256": before_sha,
            }
        chain = wal_checksum_bytes(frame_header[:8] + page, byteorder=byteorder, initial=chain)
        stored_frame = _stored_checksum(frame_header[16:24])
        if chain != stored_frame:
            return {
                **base,
                "status": "WAL_CHECKSUM_SALT_CHAIN_FAIL",
                "healthy": False,
                "reason": "WAL_FRAME_CHECKSUM_MISMATCH",
                "failed_frame_index": index + 1,
                "checksum_word_byteorder": byteorder,
                "header_checksum_verified": True,
                "salt_chain_verified": salts_verified,
                "frame_checksum_chain_verified": False,
                "stored_frame_checksum": list(stored_frame),
                "calculated_frame_checksum": list(chain),
                "wal_sha256": before_sha,
            }

    try:
        after_sha = _file_sha256(wal)
    except OSError:
        after_sha = None
    return {
        **base,
        "status": "WAL_CHECKSUM_SALT_CHAIN_HEALTHY",
        "healthy": True,
        "reason": "HEADER_CHECKSUM_FRAME_SALTS_AND_CUMULATIVE_FRAME_CHECKSUMS_PASS",
        "checksum_word_byteorder": byteorder,
        "stored_checksums_byteorder": "big",
        "header_checksum_verified": True,
        "salt_chain_verified": True,
        "frame_checksum_chain_verified": True,
        "verified_frame_count": frame_count,
        "wal_sha256": before_sha,
        "bytes_unchanged": before_sha == after_sha,
        "strict_all_physical_frames_policy": True,
    }


def preflight_evidence_stores_with_wal_integrity(*, lifecycle_db: str | Path, dispatch_db: str | Path,
                                                  replay_db: str | Path) -> dict[str, Any]:
    paths = {
        "lifecycle": Path(lifecycle_db),
        "dispatch": Path(dispatch_db),
        "replay": Path(replay_db),
    }
    integrity = {name: inspect_wal_checksum_salt_chain(path) for name, path in paths.items()}
    if any(item.get("healthy") is False for item in integrity.values()):
        return {
            "schema": SCHEMA,
            "contract": CONTRACT,
            "status": "HOLD_WAL_INTEGRITY_UNAVAILABLE",
            "wal_integrity": integrity,
            "parent_wal_storage_preflight": None,
            "control": {
                "read_only": True,
                "wal_repair": False,
                "wal_delete_on_failure": False,
                "automatic_recovery_permitted": False,
                "automatic_restart_permitted": False,
                "automatic_retry_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }
    parent = preflight_evidence_stores_with_wal(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
    )
    return {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "WAL_INTEGRITY_STORAGE_PREFLIGHT_PASS" if parent["status"] == "WAL_STORAGE_PREFLIGHT_PASS" else parent["status"],
        "wal_integrity": integrity,
        "parent_wal_storage_preflight": parent,
        "control": {
            "read_only": True,
            "wal_repair": False,
            "wal_delete_on_failure": False,
            "automatic_recovery_permitted": False,
            "automatic_restart_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def wal_integrity_guarded_recovery(*, lifecycle_db: str | Path, dispatch_db: str | Path, replay_db: str | Path,
                                   service_id: str, expected_instance_id: str, operator_ack: bool,
                                   process_dead_attested: bool, now_ms: int | None = None) -> dict[str, Any]:
    gate = preflight_evidence_stores_with_wal_integrity(
        lifecycle_db=lifecycle_db,
        dispatch_db=dispatch_db,
        replay_db=replay_db,
    )
    if gate["status"] != "WAL_INTEGRITY_STORAGE_PREFLIGHT_PASS":
        return {
            **gate,
            "recovery": None,
            "wal_integrity_gate_blocked_recovery_mutation": True,
        }
    recovery = wal_guarded_recovery(
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
        "wal_integrity_gate_blocked_recovery_mutation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only JANUS Nexus SQLite WAL checksum and salt-chain gate.")
    parser.add_argument("--lifecycle-db", required=True, type=Path)
    parser.add_argument("--dispatch-db", required=True, type=Path)
    parser.add_argument("--replay-db", required=True, type=Path)
    args = parser.parse_args()
    result = preflight_evidence_stores_with_wal_integrity(
        lifecycle_db=args.lifecycle_db,
        dispatch_db=args.dispatch_db,
        replay_db=args.replay_db,
    )
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "WAL_INTEGRITY_STORAGE_PREFLIGHT_PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
