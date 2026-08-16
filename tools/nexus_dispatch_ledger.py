from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "janus.demihead.nexus_dispatch_ledger_entry.v1"
STATES = {"STARTED", "COMPLETED", "FAILED_AMBIGUOUS"}


def _require_sha256(value: str, field: str) -> str:
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"{field} must be a 64-character SHA-256 digest")
    if any(char not in "0123456789abcdef" for char in value.lower()):
        raise ValueError(f"{field} must be hexadecimal")
    return value.lower()


def dispatch_digest(value: dict[str, Any]) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _validate_bindings(bindings: dict[str, Any]) -> dict[str, str]:
    if not isinstance(bindings, dict):
        raise ValueError("dispatch bindings must be an object")
    handler_id = bindings.get("handler_id")
    if not isinstance(handler_id, str) or not handler_id.strip():
        raise ValueError("handler_id must be non-empty")
    return {
        "frame_sha256": _require_sha256(bindings.get("frame_sha256"), "frame_sha256"),
        "acceptance_sha256": _require_sha256(bindings.get("acceptance_sha256"), "acceptance_sha256"),
        "payload_sha256": _require_sha256(bindings.get("payload_sha256"), "payload_sha256"),
        "handler_id": handler_id,
    }


def _entry(
    *,
    dispatch_sha256: str,
    bindings: dict[str, str],
    state: str,
    started_at_ms: int,
    updated_at_ms: int,
    result_sha256: str | None = None,
    failure_code: str | None = None,
    persistent: bool,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "dispatch_sha256": dispatch_sha256,
        "state": state,
        "bindings": dict(bindings),
        "started_at_ms": started_at_ms,
        "updated_at_ms": updated_at_ms,
        "result_sha256": result_sha256,
        "failure_code": failure_code,
        "control": {
            "persistent": persistent,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


class SqliteDispatchLedger:
    """Crash-safe local dispatch attempt ledger.

    STARTED is committed before a handler may be invoked. Any existing row for the
    same content-addressed dispatch key blocks a second invocation, including after
    process restart. This is conservative: a crash after STARTED but before handler
    invocation can leave a permanently ambiguous attempt and therefore sacrifice
    liveness to preserve duplicate suppression.
    """

    persistent = True
    kind = "SQLITE"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self.path), timeout=5.0, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS nexus_dispatch_ledger (
                    dispatch_sha256 TEXT PRIMARY KEY,
                    frame_sha256 TEXT NOT NULL,
                    acceptance_sha256 TEXT NOT NULL,
                    payload_sha256 TEXT NOT NULL,
                    handler_id TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('STARTED','COMPLETED','FAILED_AMBIGUOUS')),
                    started_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    result_sha256 TEXT,
                    failure_code TEXT
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_nexus_dispatch_state ON nexus_dispatch_ledger(state)"
            )

    def begin(
        self,
        dispatch_sha256: str,
        *,
        bindings: dict[str, Any],
        now_ms: int,
    ) -> dict[str, Any]:
        digest = _require_sha256(dispatch_sha256, "dispatch_sha256")
        clean = _validate_bindings(bindings)
        if isinstance(now_ms, bool) or not isinstance(now_ms, int) or now_ms < 0:
            raise ValueError("now_ms must be a non-negative integer")

        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT * FROM nexus_dispatch_ledger WHERE dispatch_sha256 = ?",
                (digest,),
            ).fetchone()
            if existing is not None:
                db.execute("ROLLBACK")
                return {
                    "admitted": False,
                    "existing": self._row_to_entry(existing),
                    "persistent": True,
                    "kind": self.kind,
                }
            db.execute(
                """
                INSERT INTO nexus_dispatch_ledger (
                    dispatch_sha256, frame_sha256, acceptance_sha256, payload_sha256,
                    handler_id, state, started_at_ms, updated_at_ms
                ) VALUES (?, ?, ?, ?, ?, 'STARTED', ?, ?)
                """,
                (
                    digest,
                    clean["frame_sha256"],
                    clean["acceptance_sha256"],
                    clean["payload_sha256"],
                    clean["handler_id"],
                    now_ms,
                    now_ms,
                ),
            )
            db.execute("COMMIT")
            return {
                "admitted": True,
                "entry": _entry(
                    dispatch_sha256=digest,
                    bindings=clean,
                    state="STARTED",
                    started_at_ms=now_ms,
                    updated_at_ms=now_ms,
                    persistent=True,
                ),
                "persistent": True,
                "kind": self.kind,
            }
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def complete(self, dispatch_sha256: str, *, result_sha256: str, now_ms: int) -> bool:
        digest = _require_sha256(dispatch_sha256, "dispatch_sha256")
        result = _require_sha256(result_sha256, "result_sha256")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT state FROM nexus_dispatch_ledger WHERE dispatch_sha256 = ?",
                (digest,),
            ).fetchone()
            if row is None or row["state"] != "STARTED":
                db.execute("ROLLBACK")
                return False
            db.execute(
                """
                UPDATE nexus_dispatch_ledger
                SET state='COMPLETED', updated_at_ms=?, result_sha256=?, failure_code=NULL
                WHERE dispatch_sha256=? AND state='STARTED'
                """,
                (now_ms, result, digest),
            )
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
        digest = _require_sha256(dispatch_sha256, "dispatch_sha256")
        if not isinstance(failure_code, str) or not failure_code.strip():
            raise ValueError("failure_code must be non-empty")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT state FROM nexus_dispatch_ledger WHERE dispatch_sha256 = ?",
                (digest,),
            ).fetchone()
            if row is None or row["state"] != "STARTED":
                db.execute("ROLLBACK")
                return False
            db.execute(
                """
                UPDATE nexus_dispatch_ledger
                SET state='FAILED_AMBIGUOUS', updated_at_ms=?, failure_code=?
                WHERE dispatch_sha256=? AND state='STARTED'
                """,
                (now_ms, failure_code, digest),
            )
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

    def get(self, dispatch_sha256: str) -> dict[str, Any] | None:
        digest = _require_sha256(dispatch_sha256, "dispatch_sha256")
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM nexus_dispatch_ledger WHERE dispatch_sha256 = ?",
                (digest,),
            ).fetchone()
        return None if row is None else self._row_to_entry(row)

    def count(self) -> int:
        with self._connect() as db:
            row = db.execute("SELECT COUNT(*) AS n FROM nexus_dispatch_ledger").fetchone()
        return int(row["n"]) if row else 0

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> dict[str, Any]:
        state = row["state"]
        if state not in STATES:
            raise ValueError("Unknown dispatch ledger state")
        bindings = {
            "frame_sha256": row["frame_sha256"],
            "acceptance_sha256": row["acceptance_sha256"],
            "payload_sha256": row["payload_sha256"],
            "handler_id": row["handler_id"],
        }
        return _entry(
            dispatch_sha256=row["dispatch_sha256"],
            bindings=bindings,
            state=state,
            started_at_ms=int(row["started_at_ms"]),
            updated_at_ms=int(row["updated_at_ms"]),
            result_sha256=row["result_sha256"],
            failure_code=row["failure_code"],
            persistent=True,
        )


def self_test() -> dict[str, Any]:
    now = 1_800_000_000_000
    bindings = {
        "frame_sha256": "1" * 64,
        "acceptance_sha256": "2" * 64,
        "payload_sha256": "3" * 64,
        "handler_id": "RELEASE_CONTROL.SELFTEST.V1",
    }
    dispatch_sha = dispatch_digest(bindings)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "dispatch.db"
        first = SqliteDispatchLedger(path)
        begin = first.begin(dispatch_sha, bindings=bindings, now_ms=now)
        restarted = SqliteDispatchLedger(path)
        duplicate = restarted.begin(dispatch_sha, bindings=bindings, now_ms=now + 1)
        completed = restarted.complete(dispatch_sha, result_sha256="4" * 64, now_ms=now + 2)
        after = SqliteDispatchLedger(path).get(dispatch_sha)

        other_bindings = dict(bindings)
        other_bindings["payload_sha256"] = "5" * 64
        other_sha = dispatch_digest(other_bindings)
        second = SqliteDispatchLedger(path)
        second_begin = second.begin(other_sha, bindings=other_bindings, now_ms=now + 3)
        failed = second.fail_ambiguous(other_sha, failure_code="HANDLER_EXCEPTION", now_ms=now + 4)
        failed_entry = SqliteDispatchLedger(path).get(other_sha)

        checks = {
            "first_begin_admitted": begin["admitted"] is True,
            "duplicate_rejected_after_restart": duplicate["admitted"] is False,
            "duplicate_observes_started": duplicate["existing"]["state"] == "STARTED",
            "completion_recorded": completed is True,
            "completion_survives_restart": after is not None and after["state"] == "COMPLETED",
            "failed_attempt_started": second_begin["admitted"] is True,
            "ambiguous_failure_recorded": failed is True,
            "ambiguous_failure_survives_restart": failed_entry is not None and failed_entry["state"] == "FAILED_AMBIGUOUS",
            "two_dispatches_recorded": SqliteDispatchLedger(path).count() == 2,
        }

    return {
        "schema": "janus.demihead.nexus_dispatch_ledger_selftest.v1",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "claim_ceiling": {
            "crash_safe_local_duplicate_attempt_suppression": True,
            "guaranteed_delivery": False,
            "exactly_once_delivery": False,
            "distributed_consensus": False,
            "automatic_retry": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Crash-safe local JANUS Nexus dispatch attempt ledger.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("reference CLI exposes only --self-test")
    result = self_test()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
