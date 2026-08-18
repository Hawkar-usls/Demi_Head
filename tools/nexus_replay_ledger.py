from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "janus.demihead.nexus_replay_ledger.v1"


def replay_digest(replay_key: str) -> str:
    if not isinstance(replay_key, str) or not replay_key:
        raise ValueError("replay_key must be a non-empty string")
    return hashlib.sha256(replay_key.encode("utf-8")).hexdigest()


class MemoryReplayGuard:
    persistent = False
    kind = "MEMORY"

    def __init__(self) -> None:
        self._entries: dict[str, int] = {}

    def _prune(self, now_ms: int) -> None:
        expired = [key for key, expiry in self._entries.items() if expiry <= now_ms]
        for key in expired:
            del self._entries[key]

    def seen(self, replay_key: str, *, now_ms: int) -> bool:
        self._prune(now_ms)
        return replay_digest(replay_key) in self._entries

    def consume(self, replay_key: str, *, expires_at_ms: int, now_ms: int) -> bool:
        if expires_at_ms <= now_ms:
            raise ValueError("Cannot consume an already-expired replay key")
        self._prune(now_ms)
        digest = replay_digest(replay_key)
        if digest in self._entries:
            return False
        self._entries[digest] = expires_at_ms
        return True


class SqliteReplayGuard:
    persistent = True
    kind = "SQLITE"

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(str(self.path), timeout=5.0, isolation_level=None)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        connection.execute("PRAGMA busy_timeout=5000")
        return connection

    def _initialize(self) -> None:
        # sqlite3.Connection as a context manager commits/rolls back but does not
        # close the connection.  Initialization must close explicitly so a late
        # GC finalizer cannot checkpoint/remove a WAL sidecar after a later
        # evidence snapshot has already been created.
        db = self._connect()
        try:
            db.execute(
                """
                CREATE TABLE IF NOT EXISTS nexus_replay_ledger (
                    replay_sha256 TEXT PRIMARY KEY,
                    expires_at_ms INTEGER NOT NULL,
                    recorded_at_ms INTEGER NOT NULL
                )
                """
            )
            db.execute(
                "CREATE INDEX IF NOT EXISTS idx_nexus_replay_expiry ON nexus_replay_ledger(expires_at_ms)"
            )
        finally:
            db.close()

    def seen(self, replay_key: str, *, now_ms: int) -> bool:
        digest = replay_digest(replay_key)
        db = self._connect()
        try:
            db.execute("DELETE FROM nexus_replay_ledger WHERE expires_at_ms <= ?", (now_ms,))
            row = db.execute(
                "SELECT 1 FROM nexus_replay_ledger WHERE replay_sha256 = ?",
                (digest,),
            ).fetchone()
            return row is not None
        finally:
            db.close()

    def consume(self, replay_key: str, *, expires_at_ms: int, now_ms: int) -> bool:
        if expires_at_ms <= now_ms:
            raise ValueError("Cannot consume an already-expired replay key")
        digest = replay_digest(replay_key)
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM nexus_replay_ledger WHERE expires_at_ms <= ?", (now_ms,))
            existing = db.execute(
                "SELECT 1 FROM nexus_replay_ledger WHERE replay_sha256 = ?",
                (digest,),
            ).fetchone()
            if existing is not None:
                db.execute("ROLLBACK")
                return False
            db.execute(
                "INSERT INTO nexus_replay_ledger (replay_sha256, expires_at_ms, recorded_at_ms) VALUES (?, ?, ?)",
                (digest, expires_at_ms, now_ms),
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

    def count_active(self, *, now_ms: int) -> int:
        db = self._connect()
        try:
            db.execute("DELETE FROM nexus_replay_ledger WHERE expires_at_ms <= ?", (now_ms,))
            row = db.execute("SELECT COUNT(*) FROM nexus_replay_ledger").fetchone()
            return int(row[0]) if row else 0
        finally:
            db.close()


def self_test() -> dict[str, Any]:
    now = 1_800_000_000_000
    replay_key = "DEMIHEAD.GUARDIAN:KEY:nonce-001"
    memory = MemoryReplayGuard()
    checks = {
        "memory_initially_unseen": not memory.seen(replay_key, now_ms=now),
        "memory_first_consume": memory.consume(replay_key, expires_at_ms=now + 30_000, now_ms=now),
        "memory_seen_after_consume": memory.seen(replay_key, now_ms=now + 1),
        "memory_replay_rejected": not memory.consume(replay_key, expires_at_ms=now + 30_000, now_ms=now + 1),
    }

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "replay.db"
        first = SqliteReplayGuard(path)
        checks["sqlite_initially_unseen"] = not first.seen(replay_key, now_ms=now)
        checks["sqlite_first_consume"] = first.consume(replay_key, expires_at_ms=now + 30_000, now_ms=now)
        checks["sqlite_seen_after_consume"] = first.seen(replay_key, now_ms=now + 1)
        checks["sqlite_count_one"] = first.count_active(now_ms=now + 1) == 1

        restarted = SqliteReplayGuard(path)
        checks["sqlite_seen_survives_restart"] = restarted.seen(replay_key, now_ms=now + 2)
        checks["sqlite_replay_survives_restart"] = not restarted.consume(
            replay_key,
            expires_at_ms=now + 30_000,
            now_ms=now + 2,
        )
        checks["sqlite_expiry_prunes"] = restarted.count_active(now_ms=now + 30_001) == 0
        checks["sqlite_unseen_after_expiry"] = not restarted.seen(replay_key, now_ms=now + 30_001)
        checks["sqlite_reuse_after_expiry"] = restarted.consume(
            replay_key,
            expires_at_ms=now + 60_000,
            now_ms=now + 30_001,
        )

    return {
        "schema": SCHEMA,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "claim_ceiling": {
            "crash_safe_local_replay_persistence": True,
            "early_seen_check_is_atomic_with_final_consume": False,
            "final_nonce_consumption_is_atomic": True,
            "distributed_replay_consensus": False,
            "network_delivery": False,
            "production_database_tuning": False
        }
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Crash-safe local replay guard for JANUS Nexus transport.")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not args.self_test:
        parser.error("reference CLI exposes only --self-test")
    result = self_test()
    sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
