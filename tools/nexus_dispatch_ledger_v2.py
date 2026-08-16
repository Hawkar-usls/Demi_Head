from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path
from typing import Any


ENTRY_SCHEMA = "janus.demihead.nexus_dispatch_ledger_entry.v2"
TABLE = "nexus_dispatch_ledger_v2"
STATES = {"STARTED", "COMPLETED", "FAILED_AMBIGUOUS"}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_sha(value: str, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value.lower()):
        raise ValueError(f"{name} must be a lowercase-compatible SHA-256 hex digest")
    return value.lower()


def validate_intent_bindings(bindings: dict[str, Any]) -> dict[str, str]:
    if not isinstance(bindings, dict):
        raise ValueError("intent bindings must be an object")
    target_head = bindings.get("target_head")
    if not isinstance(target_head, str) or not target_head.strip():
        raise ValueError("target_head must be non-empty")
    return {
        "frame_sha256": _require_sha(bindings.get("frame_sha256"), "frame_sha256"),
        "acceptance_sha256": _require_sha(bindings.get("acceptance_sha256"), "acceptance_sha256"),
        "payload_sha256": _require_sha(bindings.get("payload_sha256"), "payload_sha256"),
        "target_head": target_head,
    }


def intent_digest(bindings: dict[str, Any]) -> str:
    return sha256(validate_intent_bindings(bindings))


def dispatch_digest(intent_sha256: str, handler_id: str) -> str:
    intent = _require_sha(intent_sha256, "intent_sha256")
    if not isinstance(handler_id, str) or not handler_id.strip():
        raise ValueError("handler_id must be non-empty")
    return sha256({"intent_sha256": intent, "handler_id": handler_id})


def _entry(row: sqlite3.Row) -> dict[str, Any]:
    if row["state"] not in STATES:
        raise ValueError("unknown ledger state")
    return {
        "schema": ENTRY_SCHEMA,
        "intent_sha256": row["intent_sha256"],
        "dispatch_sha256": row["dispatch_sha256"],
        "state": row["state"],
        "bindings": {
            "frame_sha256": row["frame_sha256"],
            "acceptance_sha256": row["acceptance_sha256"],
            "payload_sha256": row["payload_sha256"],
            "target_head": row["target_head"],
            "handler_id": row["handler_id"],
        },
        "started_at_ms": int(row["started_at_ms"]),
        "updated_at_ms": int(row["updated_at_ms"]),
        "result_sha256": row["result_sha256"],
        "failure_code": row["failure_code"],
        "control": {
            "persistent": True,
            "duplicate_intent_reinvocation_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


class SqliteDispatchLedgerV2:
    persistent = True
    kind = "SQLITE_V2_INTENT_GUARDED"

    def __init__(self, path: str | Path, *, busy_timeout_ms: int = 5000) -> None:
        if isinstance(busy_timeout_ms, bool) or not isinstance(busy_timeout_ms, int) or busy_timeout_ms < 0:
            raise ValueError("busy_timeout_ms must be a non-negative integer")
        self.path = Path(path)
        self.busy_timeout_ms = busy_timeout_ms
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(
            str(self.path),
            timeout=max(0.001, self.busy_timeout_ms / 1000.0),
            isolation_level=None,
        )
        db.row_factory = sqlite3.Row
        db.execute(f"PRAGMA busy_timeout={self.busy_timeout_ms}")
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {TABLE} (
                    dispatch_sha256 TEXT PRIMARY KEY,
                    intent_sha256 TEXT NOT NULL UNIQUE,
                    frame_sha256 TEXT NOT NULL,
                    acceptance_sha256 TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    target_head TEXT NOT NULL,
                    handler_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('STARTED','COMPLETED','FAILED_AMBIGUOUS')),
                    started_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    result_sha256 TEXT,
                    failure_code TEXT
                )
                """
            )
            db.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABLE}_state ON {TABLE}(state)")

    def begin(
        self,
        *,
        intent_sha256: str,
        dispatch_sha256: str,
        intent_bindings: dict[str, Any],
        handler_id: str,
        now_ms: int,
    ) -> dict[str, Any]:
        intent = _require_sha(intent_sha256, "intent_sha256")
        dispatch = _require_sha(dispatch_sha256, "dispatch_sha256")
        clean = validate_intent_bindings(intent_bindings)
        if intent_digest(clean) != intent:
            raise ValueError("intent_sha256 does not bind supplied intent_bindings")
        if dispatch_digest(intent, handler_id) != dispatch:
            raise ValueError("dispatch_sha256 does not bind supplied intent and handler")
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
            raise ValueError("now_ms must be a non-negative integer")

        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                f"SELECT * FROM {TABLE} WHERE intent_sha256=? OR dispatch_sha256=? LIMIT 1",
                (intent, dispatch),
            ).fetchone()
            if existing is not None:
                db.execute("ROLLBACK")
                return {"admitted": False, "existing": _entry(existing), "kind": self.kind, "persistent": True}
            db.execute(
                f"""
                INSERT INTO {TABLE} (
                    dispatch_sha256, intent_sha256, frame_sha256, acceptance_sha256,
                    payload_sha256, target_head, handler_id, state, started_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'STARTED', ?, ?)
                """,
                (
                    dispatch,
                    intent,
                    clean["frame_sha256"],
                    clean["acceptance_sha256"],
                    clean["payload_sha256"],
                    clean["target_head"],
                    handler_id,
                    now_ms,
                    now_ms,
                ),
            )
            db.execute("COMMIT")
            return {"admitted": True, "intent_sha256": intent, "dispatch_sha256": dispatch, "state": "STARTED", "kind": self.kind, "persistent": True}
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def complete(self, dispatch_sha256: str, *, result_sha256: str, now_ms: int) -> bool:
        dispatch = _require_sha(dispatch_sha256, "dispatch_sha256")
        result = _require_sha(result_sha256, "result_sha256")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                f"UPDATE {TABLE} SET state='COMPLETED', result_sha256=?, failure_code=NULL, updated_at_ms=? WHERE dispatch_sha256=? AND state='STARTED'",
                (result, now_ms, dispatch),
            )
            if cursor.rowcount != 1:
                db.execute("ROLLBACK")
                return False
            db.execute("COMMIT")
            return True
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def fail_ambiguous(self, dispatch_sha256: str, *, failure_code: str, now_ms: int) -> bool:
        dispatch = _require_sha(dispatch_sha256, "dispatch_sha256")
        if not isinstance(failure_code, str) or not failure_code.strip():
            raise ValueError("failure_code must be non-empty")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            cursor = db.execute(
                f"UPDATE {TABLE} SET state='FAILED_AMBIGUOUS', failure_code=?, updated_at_ms=? WHERE dispatch_sha256=? AND state='STARTED'",
                (failure_code, now_ms, dispatch),
            )
            if cursor.rowcount != 1:
                db.execute("ROLLBACK")
                return False
            db.execute("COMMIT")
            return True
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def get_by_intent(self, intent_sha256: str) -> dict[str, Any] | None:
        intent = _require_sha(intent_sha256, "intent_sha256")
        with self._connect() as db:
            row = db.execute(f"SELECT * FROM {TABLE} WHERE intent_sha256=?", (intent,)).fetchone()
        return None if row is None else _entry(row)

    def count(self) -> int:
        with self._connect() as db:
            row = db.execute(f"SELECT COUNT(*) AS n FROM {TABLE}").fetchone()
        return int(row["n"]) if row else 0
