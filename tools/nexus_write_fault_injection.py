from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2
from nexus_loopback_lifecycle_gate import SqliteLifecycleLedger


class InjectedWriteFault(sqlite3.OperationalError):
    """Deterministic test-only persistence failure."""


class FaultInjectingDispatchLedger(SqliteDispatchLedgerV2):
    """Test-only subclass that can fail selected durable dispatch operations.

    It intentionally remains an isinstance(SqliteDispatchLedgerV2) so the production
    dispatcher exercises its real type boundary and normal error handling.
    """

    kind = "SQLITE_V2_INTENT_GUARDED_FAULT_INJECTION_TEST_ONLY"

    def __init__(self, path: str | Path, *, fail_operations: set[str] | None = None,
                 busy_timeout_ms: int = 5000) -> None:
        self.fail_operations = set(fail_operations or set())
        self.injected_failures: list[str] = []
        super().__init__(path, busy_timeout_ms=busy_timeout_ms)

    def _maybe_fail(self, operation: str) -> None:
        if operation in self.fail_operations:
            self.injected_failures.append(operation)
            raise InjectedWriteFault(f"injected dispatch write failure: {operation}")

    def begin(self, **kwargs: Any) -> dict[str, Any]:
        self._maybe_fail("begin")
        return super().begin(**kwargs)

    def complete(self, dispatch_sha256: str, *, result_sha256: str, now_ms: int) -> bool:
        self._maybe_fail("complete")
        return super().complete(dispatch_sha256, result_sha256=result_sha256, now_ms=now_ms)

    def fail_ambiguous(self, dispatch_sha256: str, *, failure_code: str, now_ms: int) -> bool:
        self._maybe_fail("fail_ambiguous")
        return super().fail_ambiguous(dispatch_sha256, failure_code=failure_code, now_ms=now_ms)


class FaultInjectingLifecycleLedger(SqliteLifecycleLedger):
    """Test-only lifecycle ledger with deterministic begin/phase write failures."""

    kind = "SQLITE_LIFECYCLE_FAULT_INJECTION_TEST_ONLY"

    def __init__(self, path: str | Path, *, fail_begin: bool = False,
                 fail_phases: set[str] | None = None) -> None:
        self.fail_begin = bool(fail_begin)
        self.fail_phases = set(fail_phases or set())
        self.injected_failures: list[str] = []
        super().__init__(path)

    def begin(self, service_id: str, instance_id: str, *, now_ms: int) -> dict[str, Any]:
        if self.fail_begin:
            self.injected_failures.append("begin")
            raise InjectedWriteFault("injected lifecycle write failure: begin")
        return super().begin(service_id, instance_id, now_ms=now_ms)

    def transition(self, service_id: str, instance_id: str, phase: str, *, now_ms: int,
                   request_sha256: str | None = None, frame_sha256: str | None = None,
                   dispatch_sha256: str | None = None, detail_code: str | None = None) -> None:
        if phase in self.fail_phases:
            self.injected_failures.append(phase)
            raise InjectedWriteFault(f"injected lifecycle write failure: {phase}")
        return super().transition(
            service_id,
            instance_id,
            phase,
            now_ms=now_ms,
            request_sha256=request_sha256,
            frame_sha256=frame_sha256,
            dispatch_sha256=dispatch_sha256,
            detail_code=detail_code,
        )
