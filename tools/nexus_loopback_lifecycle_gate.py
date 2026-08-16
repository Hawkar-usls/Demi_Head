from __future__ import annotations

import json
import socket
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from nexus_local_transport import sha256, validate_frame
from nexus_loopback_dispatcher import LocalHandler
from nexus_loopback_dispatcher_v2 import dispatch_loopback_v2
from nexus_loopback_exchange import _compact_receipt, _recv_packet, _send_packet, validate_request
from nexus_loopback_socket_guard import BoundLoopbackSocket, LOOPBACK_FAMILIES, bind_loopback_listener, validate_config

CONTRACT = "JANUS_NEXUS_ONE_SHOT_LIFECYCLE_GATE_V1"
POLICY_SCHEMA = "janus.demihead.nexus_one_shot_lifecycle_policy.v1"
OUTCOME_SCHEMA = "janus.demihead.nexus_one_shot_lifecycle_outcome.v1"
MAX_TIMEOUT_MS = 5_000
DEFAULT_ACCEPT_TIMEOUT_MS = 250
DEFAULT_READ_TIMEOUT_MS = 1_000
DEFAULT_WRITE_TIMEOUT_MS = 1_000
REUSABLE_TERMINAL_PHASES = {"CLOSED_CLEAN", "ACKNOWLEDGED_AMBIGUOUS"}
AMBIGUOUS_TERMINAL_PHASE = "CLOSED_AMBIGUOUS"

class LifecycleLedgerUnavailable(OSError):
    pass

def _now_ms(explicit: int | None = None) -> int:
    return int(time.time() * 1000) if explicit is None else int(explicit)

def default_lifecycle_policy() -> dict[str, Any]:
    return {
        "schema": POLICY_SCHEMA,
        "startup_enabled": False,
        "automatic_start_permitted": False,
        "automatic_restart_permitted": False,
        "accept_timeout_ms": DEFAULT_ACCEPT_TIMEOUT_MS,
        "read_timeout_ms": DEFAULT_READ_TIMEOUT_MS,
        "write_timeout_ms": DEFAULT_WRITE_TIMEOUT_MS,
        "max_connections": 1,
        "max_requests_per_connection": 1,
        "external_effect_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }

def validate_lifecycle_policy(policy: dict[str, Any]) -> None:
    if not isinstance(policy, dict) or policy.get("schema") != POLICY_SCHEMA:
        raise ValueError("unexpected one-shot lifecycle policy schema")
    if not isinstance(policy.get("startup_enabled"), bool):
        raise ValueError("startup_enabled must be boolean")
    if policy.get("automatic_start_permitted") is not False:
        raise ValueError("automatic startup must remain forbidden")
    if policy.get("automatic_restart_permitted") is not False:
        raise ValueError("automatic restart must remain forbidden")
    for name in ("accept_timeout_ms", "read_timeout_ms", "write_timeout_ms"):
        value = policy.get(name)
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= MAX_TIMEOUT_MS:
            raise ValueError(f"{name} must be an integer in [1, {MAX_TIMEOUT_MS}]")
    if policy.get("max_connections") != 1:
        raise ValueError("one-shot lifecycle permits exactly one accepted connection")
    if policy.get("max_requests_per_connection") != 1:
        raise ValueError("one-shot lifecycle permits exactly one request per connection")
    if policy.get("external_effect_permitted") is not False:
        raise ValueError("external effects must remain forbidden")
    if policy.get("authority_delta") != 0 or policy.get("mass_effect_budget_delta") != 0:
        raise ValueError("lifecycle gate cannot alter authority or mass-effect budget")

class SqliteLifecycleLedger:
    kind = "SQLITE"
    persistent = True

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
        with self._connect() as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS nexus_one_shot_lifecycle (
                    service_id TEXT PRIMARY KEY,
                    instance_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    started_at_ms INTEGER NOT NULL,
                    updated_at_ms INTEGER NOT NULL,
                    request_sha256 TEXT,
                    frame_sha256 TEXT,
                    dispatch_sha256 TEXT,
                    detail_code TEXT
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS nexus_one_shot_lifecycle_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    service_id TEXT NOT NULL,
                    instance_id TEXT NOT NULL,
                    phase TEXT NOT NULL,
                    recorded_at_ms INTEGER NOT NULL,
                    detail_code TEXT
                )
            """)

    @staticmethod
    def _validate_ids(service_id: str, instance_id: str) -> None:
        if not isinstance(service_id, str) or not service_id.strip():
            raise ValueError("service_id must be a non-empty string")
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise ValueError("instance_id must be a non-empty string")

    def begin(self, service_id: str, instance_id: str, *, now_ms: int) -> dict[str, Any]:
        self._validate_ids(service_id, instance_id)
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT instance_id, phase, detail_code FROM nexus_one_shot_lifecycle WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            if row is not None and row[1] not in REUSABLE_TERMINAL_PHASES:
                db.execute("ROLLBACK")
                return {"admitted": False, "existing": {"instance_id": row[0], "phase": row[1], "detail_code": row[2]}}
            if row is None:
                db.execute("""
                    INSERT INTO nexus_one_shot_lifecycle (
                        service_id, instance_id, phase, started_at_ms, updated_at_ms,
                        request_sha256, frame_sha256, dispatch_sha256, detail_code
                    ) VALUES (?, ?, 'STARTING', ?, ?, NULL, NULL, NULL, NULL)
                """, (service_id, instance_id, now_ms, now_ms))
            else:
                db.execute("""
                    UPDATE nexus_one_shot_lifecycle
                    SET instance_id = ?, phase = 'STARTING', started_at_ms = ?, updated_at_ms = ?,
                        request_sha256 = NULL, frame_sha256 = NULL, dispatch_sha256 = NULL, detail_code = NULL
                    WHERE service_id = ?
                """, (instance_id, now_ms, now_ms, service_id))
            db.execute("""
                INSERT INTO nexus_one_shot_lifecycle_events
                (service_id, instance_id, phase, recorded_at_ms, detail_code)
                VALUES (?, ?, 'STARTING', ?, NULL)
            """, (service_id, instance_id, now_ms))
            db.execute("COMMIT")
            return {"admitted": True, "existing": None}
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def transition(self, service_id: str, instance_id: str, phase: str, *, now_ms: int,
                   request_sha256: str | None = None, frame_sha256: str | None = None,
                   dispatch_sha256: str | None = None, detail_code: str | None = None) -> None:
        self._validate_ids(service_id, instance_id)
        if not isinstance(phase, str) or not phase:
            raise ValueError("phase must be a non-empty string")
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT instance_id, phase FROM nexus_one_shot_lifecycle WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            if row is None:
                raise ValueError("lifecycle service has no active ledger row")
            if row[0] != instance_id:
                raise ValueError("lifecycle instance_id does not match current active instance")
            if row[1] == AMBIGUOUS_TERMINAL_PHASE:
                raise ValueError("ambiguous lifecycle is frozen until explicit acknowledgment")
            if row[1] == "CLOSED_CLEAN":
                raise ValueError("closed lifecycle cannot transition further")
            db.execute("""
                UPDATE nexus_one_shot_lifecycle
                SET phase = ?, updated_at_ms = ?,
                    request_sha256 = COALESCE(?, request_sha256),
                    frame_sha256 = COALESCE(?, frame_sha256),
                    dispatch_sha256 = COALESCE(?, dispatch_sha256),
                    detail_code = ?
                WHERE service_id = ?
            """, (phase, now_ms, request_sha256, frame_sha256, dispatch_sha256, detail_code, service_id))
            db.execute("""
                INSERT INTO nexus_one_shot_lifecycle_events
                (service_id, instance_id, phase, recorded_at_ms, detail_code)
                VALUES (?, ?, ?, ?, ?)
            """, (service_id, instance_id, phase, now_ms, detail_code))
            db.execute("COMMIT")
        except Exception:
            try:
                db.execute("ROLLBACK")
            except sqlite3.Error:
                pass
            raise
        finally:
            db.close()

    def acknowledge_ambiguous(self, service_id: str, expected_instance_id: str, *, operator_ack: bool, now_ms: int) -> bool:
        self._validate_ids(service_id, expected_instance_id)
        if operator_ack is not True:
            return False
        db = self._connect()
        try:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute(
                "SELECT instance_id, phase FROM nexus_one_shot_lifecycle WHERE service_id = ?",
                (service_id,),
            ).fetchone()
            if row is None or row[0] != expected_instance_id or row[1] != AMBIGUOUS_TERMINAL_PHASE:
                db.execute("ROLLBACK")
                return False
            db.execute("""
                UPDATE nexus_one_shot_lifecycle
                SET phase = 'ACKNOWLEDGED_AMBIGUOUS', updated_at_ms = ?, detail_code = 'OPERATOR_ACK'
                WHERE service_id = ?
            """, (now_ms, service_id))
            db.execute("""
                INSERT INTO nexus_one_shot_lifecycle_events
                (service_id, instance_id, phase, recorded_at_ms, detail_code)
                VALUES (?, ?, 'ACKNOWLEDGED_AMBIGUOUS', ?, 'OPERATOR_ACK')
            """, (service_id, expected_instance_id, now_ms))
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

    def state(self, service_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("""
                SELECT instance_id, phase, started_at_ms, updated_at_ms,
                       request_sha256, frame_sha256, dispatch_sha256, detail_code
                FROM nexus_one_shot_lifecycle WHERE service_id = ?
            """, (service_id,)).fetchone()
        if row is None:
            return None
        return {
            "service_id": service_id, "instance_id": row[0], "phase": row[1],
            "started_at_ms": row[2], "updated_at_ms": row[3], "request_sha256": row[4],
            "frame_sha256": row[5], "dispatch_sha256": row[6], "detail_code": row[7],
        }

@dataclass
class PreparedLifecycleListener:
    listener: BoundLoopbackSocket
    ledger: SqliteLifecycleLedger
    service_id: str
    instance_id: str
    policy: dict[str, Any]
    started_at_ms: int

    @property
    def host(self) -> str:
        return str(self.listener.receipt["binding"]["bound_host"])

    @property
    def port(self) -> int:
        return int(self.listener.receipt["binding"]["bound_port"])

    def close_clean(self, *, detail_code: str = "EXPLICIT_PRE_EXCHANGE_CLOSE", now_ms: int | None = None) -> None:
        try:
            self.listener.close()
        finally:
            self.ledger.transition(self.service_id, self.instance_id, "CLOSED_CLEAN", now_ms=_now_ms(now_ms), detail_code=detail_code)

def _local_hold(status: str, *, service_id: str, instance_id: str, detail_code: str,
                phase: str, socket_created: bool, manual_ack_required: bool = False) -> dict[str, Any]:
    return {
        "schema": OUTCOME_SCHEMA, "contract": CONTRACT, "status": status,
        "lifecycle": {
            "service_id": service_id, "instance_id": instance_id, "phase": phase,
            "detail_code": detail_code, "socket_created": socket_created,
            "wire_receipt_send_completed": False, "manual_ack_required": manual_ack_required,
        },
        "control": {
            "automatic_start_permitted": False, "automatic_restart_permitted": False,
            "automatic_retry_permitted": False, "external_effect_permitted": False,
            "authority_delta": 0, "mass_effect_budget_delta": 0,
        },
    }

def prepare_lifecycle_listener(config: dict[str, Any], policy: dict[str, Any], *,
                               lifecycle_ledger: SqliteLifecycleLedger, service_id: str,
                               instance_id: str, explicit_enable: bool,
                               now_ms: int | None = None) -> PreparedLifecycleListener | dict[str, Any]:
    validate_config(config)
    validate_lifecycle_policy(policy)
    now = _now_ms(now_ms)
    if policy["startup_enabled"] is not True:
        return _local_hold("HOLD_STARTUP_DISABLED", service_id=service_id, instance_id=instance_id,
                           detail_code="STARTUP_ENABLED_FALSE", phase="NOT_STARTED", socket_created=False)
    if explicit_enable is not True:
        return _local_hold("HOLD_EXPLICIT_START_REQUIRED", service_id=service_id, instance_id=instance_id,
                           detail_code="EXPLICIT_RUNTIME_ENABLE_MISSING", phase="NOT_STARTED", socket_created=False)
    try:
        begin = lifecycle_ledger.begin(service_id, instance_id, now_ms=now)
    except Exception:
        return _local_hold("HOLD_LIFECYCLE_LEDGER_UNAVAILABLE", service_id=service_id, instance_id=instance_id,
                           detail_code="LIFECYCLE_LEDGER_BEGIN_FAILED", phase="NOT_STARTED", socket_created=False)
    if begin.get("admitted") is not True:
        existing = begin.get("existing") or {}
        phase = str(existing.get("phase", "UNKNOWN"))
        return _local_hold("HOLD_LIFECYCLE_BUSY_OR_AMBIGUOUS", service_id=service_id, instance_id=instance_id,
                           detail_code=f"EXISTING_{phase}", phase=phase, socket_created=False,
                           manual_ack_required=phase == AMBIGUOUS_TERMINAL_PHASE)
    try:
        bound = bind_loopback_listener(config, explicit_enable=True)
    except Exception:
        try:
            lifecycle_ledger.transition(service_id, instance_id, "CLOSED_CLEAN", now_ms=now, detail_code="BIND_FAILED_FAIL_CLOSED")
        except Exception:
            pass
        return _local_hold("HOLD_BIND_FAILED", service_id=service_id, instance_id=instance_id,
                           detail_code="BIND_FAILED_FAIL_CLOSED", phase="CLOSED_CLEAN", socket_created=False)
    if not isinstance(bound, BoundLoopbackSocket):
        try:
            lifecycle_ledger.transition(service_id, instance_id, "CLOSED_CLEAN", now_ms=now,
                                        detail_code=str(bound.get("status", "SOCKET_ADMISSION_HOLD")))
        except Exception:
            pass
        return _local_hold(str(bound.get("status", "HOLD_SOCKET_ADMISSION")), service_id=service_id,
                           instance_id=instance_id, detail_code="SOCKET_ADMISSION_HOLD", phase="CLOSED_CLEAN",
                           socket_created=False)
    try:
        bound.sock.settimeout(policy["accept_timeout_ms"] / 1000.0)
        lifecycle_ledger.transition(service_id, instance_id, "LISTENER_BOUND", now_ms=now,
                                    detail_code="LITERAL_LOOPBACK_BOUND")
    except Exception:
        bound.close()
        return _local_hold("HOLD_LIFECYCLE_LEDGER_UNAVAILABLE_AFTER_BIND", service_id=service_id,
                           instance_id=instance_id, detail_code="POST_BIND_LEDGER_FAILURE",
                           phase="UNKNOWN_FAIL_CLOSED", socket_created=True)
    return PreparedLifecycleListener(bound, lifecycle_ledger, service_id, instance_id,
                                     json.loads(json.dumps(policy)), now)

def _outcome(status: str, prepared: PreparedLifecycleListener, *, phase: str, detail_code: str,
             wire_receipt: dict[str, Any] | None, wire_send_completed: bool,
             manual_ack_required: bool, dispatch_invocation_attempted: bool,
             dispatch_completion_established: bool) -> dict[str, Any]:
    return {
        "schema": OUTCOME_SCHEMA, "contract": CONTRACT, "status": status,
        "lifecycle": {
            "service_id": prepared.service_id, "instance_id": prepared.instance_id,
            "phase": phase, "detail_code": detail_code,
            "wire_receipt_sha256": sha256(wire_receipt) if isinstance(wire_receipt, dict) else None,
            "wire_receipt_send_completed": wire_send_completed,
            "manual_ack_required": manual_ack_required,
        },
        "dispatch": {
            "handler_invocation_attempted": dispatch_invocation_attempted,
            "completion_established": dispatch_completion_established,
        },
        "control": {
            "one_connection_only": True, "one_request_only": True,
            "automatic_start_permitted": False, "automatic_restart_permitted": False,
            "automatic_retry_permitted": False, "external_effect_permitted": False,
            "authority_delta": 0, "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "response_delivery_guaranteed": False, "exactly_once_delivery_established": False,
            "cross_host_transport": False, "general_network_service": False, "persistent_daemon": False,
        },
    }

def _transition_or_fail_closed(prepared: PreparedLifecycleListener, phase: str, *, now_ms: int,
                               request_sha256: str | None = None, frame_sha256: str | None = None,
                               dispatch_sha256: str | None = None, detail_code: str | None = None) -> None:
    try:
        prepared.ledger.transition(prepared.service_id, prepared.instance_id, phase, now_ms=now_ms,
                                   request_sha256=request_sha256, frame_sha256=frame_sha256,
                                   dispatch_sha256=dispatch_sha256, detail_code=detail_code)
    except Exception as exc:
        raise LifecycleLedgerUnavailable("persistent lifecycle transition failed") from exc

def _send_and_finalize(prepared: PreparedLifecycleListener, conn: socket.socket,
                       wire_receipt: dict[str, Any], *, now_ms: int,
                       dispatch_invocation_attempted: bool, dispatch_completion_established: bool,
                       receipt_sender: Callable[[socket.socket, dict[str, Any]], None]) -> dict[str, Any]:
    _transition_or_fail_closed(prepared, "RECEIPT_PENDING", now_ms=now_ms, detail_code="WIRE_RECEIPT_PENDING")
    conn.settimeout(prepared.policy["write_timeout_ms"] / 1000.0)
    try:
        receipt_sender(conn, wire_receipt)
        send_completed = True
    except Exception:
        send_completed = False
    execution_ambiguous = dispatch_invocation_attempted and not dispatch_completion_established
    response_ambiguous = dispatch_completion_established and not send_completed
    if execution_ambiguous or response_ambiguous:
        detail = "DISPATCH_COMPLETED_RECEIPT_UNCONFIRMED" if response_ambiguous else "HANDLER_INVOCATION_COMPLETION_AMBIGUOUS"
        _transition_or_fail_closed(prepared, AMBIGUOUS_TERMINAL_PHASE, now_ms=now_ms, detail_code=detail)
        return _outcome("CLOSED_AMBIGUOUS", prepared, phase=AMBIGUOUS_TERMINAL_PHASE,
                        detail_code=detail, wire_receipt=wire_receipt, wire_send_completed=send_completed,
                        manual_ack_required=True, dispatch_invocation_attempted=dispatch_invocation_attempted,
                        dispatch_completion_established=dispatch_completion_established)
    if send_completed:
        _transition_or_fail_closed(prepared, "RECEIPT_SENT", now_ms=now_ms, detail_code="SENDALL_RETURNED")
    detail = "CLEAN_ONE_SHOT_CLOSE" if send_completed else "RECEIPT_UNCONFIRMED_NO_HANDLER_INVOCATION"
    _transition_or_fail_closed(prepared, "CLOSED_CLEAN", now_ms=now_ms, detail_code=detail)
    return _outcome("CLOSED_CLEAN", prepared, phase="CLOSED_CLEAN", detail_code=detail,
                    wire_receipt=wire_receipt, wire_send_completed=send_completed,
                    manual_ack_required=False, dispatch_invocation_attempted=dispatch_invocation_attempted,
                    dispatch_completion_established=dispatch_completion_established)

def serve_one_exchange_lifecycle(prepared: PreparedLifecycleListener, *,
                                 principal_lookup: dict[str, dict[str, Any]],
                                 public_principal_lookup: dict[str, dict[str, Any]],
                                 endpoint_catalog: dict[str, Any], handlers: dict[str, LocalHandler],
                                 replay_guard: Any, dispatch_ledger: Any, now_ms: int | None = None,
                                 receipt_sender: Callable[[socket.socket, dict[str, Any]], None] | None = None) -> dict[str, Any]:
    if not isinstance(prepared, PreparedLifecycleListener):
        raise ValueError("prepared lifecycle listener is required")
    now = _now_ms(now_ms)
    sender = receipt_sender or (lambda sock, value: _send_packet(sock, value))
    conn: socket.socket | None = None
    dispatch_invocation_attempted = False
    dispatch_completion_established = False
    try:
        _transition_or_fail_closed(prepared, "ACCEPTING", now_ms=now, detail_code="BOUNDED_ACCEPT_WAIT")
        try:
            conn, peer = prepared.listener.sock.accept()
        except socket.timeout:
            _transition_or_fail_closed(prepared, "CLOSED_CLEAN", now_ms=now, detail_code="ACCEPT_TIMEOUT_NO_PEER")
            return _outcome("HOLD_ACCEPT_TIMEOUT", prepared, phase="CLOSED_CLEAN",
                            detail_code="ACCEPT_TIMEOUT_NO_PEER", wire_receipt=None,
                            wire_send_completed=False, manual_ack_required=False,
                            dispatch_invocation_attempted=False, dispatch_completion_established=False)
        peer_host = str(peer[0])
        _transition_or_fail_closed(prepared, "CONNECTED", now_ms=now, detail_code="ONE_PEER_ACCEPTED")
        if peer_host != prepared.host or peer_host not in LOOPBACK_FAMILIES:
            wire = _compact_receipt("HOLD_NON_LOOPBACK_PEER", bound_host=prepared.host, bound_port=prepared.port,
                                    peer_host=peer_host, rejection_stage="PEER_ADDRESS")
            return _send_and_finalize(prepared, conn, wire, now_ms=now, dispatch_invocation_attempted=False,
                                      dispatch_completion_established=False, receipt_sender=sender)
        conn.settimeout(prepared.policy["read_timeout_ms"] / 1000.0)
        try:
            request = _recv_packet(conn)
            frame, payload = validate_request(request)
        except Exception:
            wire = _compact_receipt("HOLD_WIRE_PROTOCOL", bound_host=prepared.host, bound_port=prepared.port,
                                    peer_host=peer_host, rejection_stage="WIRE_PROTOCOL_OR_READ_TIMEOUT")
            return _send_and_finalize(prepared, conn, wire, now_ms=now, dispatch_invocation_attempted=False,
                                      dispatch_completion_established=False, receipt_sender=sender)
        request_sha = sha256(request)
        frame_sha = sha256(frame)
        _transition_or_fail_closed(prepared, "REQUEST_RECEIVED", now_ms=now, request_sha256=request_sha,
                                   frame_sha256=frame_sha, detail_code="BOUNDED_REQUEST_RECEIVED")
        key_id = frame.get("key_id")
        principal_state = public_principal_lookup.get(key_id) if isinstance(key_id, str) else None
        if not isinstance(principal_state, dict):
            wire = _compact_receipt("HOLD_TRANSPORT_REJECTED", bound_host=prepared.host, bound_port=prepared.port,
                                    peer_host=peer_host, request_sha256=request_sha, frame_sha256=frame_sha,
                                    rejection_stage="CURRENT_PRINCIPAL_LOOKUP")
            return _send_and_finalize(prepared, conn, wire, now_ms=now, dispatch_invocation_attempted=False,
                                      dispatch_completion_established=False, receipt_sender=sender)
        try:
            admission = validate_frame(frame, principal_lookup=principal_lookup, replay_guard=replay_guard, now_ms=now)
        except Exception:
            wire = _compact_receipt("HOLD_TRANSPORT_REJECTED", bound_host=prepared.host, bound_port=prepared.port,
                                    peer_host=peer_host, request_sha256=request_sha, frame_sha256=frame_sha,
                                    rejection_stage="TRANSPORT_OR_REPLAY_STATE")
            return _send_and_finalize(prepared, conn, wire, now_ms=now, dispatch_invocation_attempted=False,
                                      dispatch_completion_established=False, receipt_sender=sender)
        if admission.get("status") != "AUTHENTICATED_FRAME_ADMITTED":
            wire = _compact_receipt("HOLD_TRANSPORT_NOT_ADMITTED", bound_host=prepared.host, bound_port=prepared.port,
                                    peer_host=peer_host, request_sha256=request_sha, frame_sha256=frame_sha,
                                    transport_status=str(admission.get("status")), rejection_stage="TRANSPORT_ADMISSION")
            return _send_and_finalize(prepared, conn, wire, now_ms=now, dispatch_invocation_attempted=False,
                                      dispatch_completion_established=False, receipt_sender=sender)
        _transition_or_fail_closed(prepared, "TRANSPORT_ADMITTED", now_ms=now, request_sha256=request_sha,
                                   frame_sha256=frame_sha, detail_code="AUTHENTICATED_FRAME_ADMITTED")
        _transition_or_fail_closed(prepared, "DISPATCH_STARTED", now_ms=now, detail_code="ENTER_INTENT_GUARDED_DISPATCH")
        try:
            dispatch = dispatch_loopback_v2(frame, admission, principal_state, endpoint_catalog, payload, handlers,
                                            dispatch_ledger=dispatch_ledger, now_ms=now)
        except Exception:
            _transition_or_fail_closed(prepared, AMBIGUOUS_TERMINAL_PHASE, now_ms=now,
                                       detail_code="UNEXPECTED_DISPATCH_EXCEPTION")
            return _outcome("CLOSED_AMBIGUOUS", prepared, phase=AMBIGUOUS_TERMINAL_PHASE,
                            detail_code="UNEXPECTED_DISPATCH_EXCEPTION", wire_receipt=None,
                            wire_send_completed=False, manual_ack_required=True,
                            dispatch_invocation_attempted=True, dispatch_completion_established=False)
        dispatch_binding = dispatch.get("binding") if isinstance(dispatch, dict) else {}
        dispatch_sha = dispatch_binding.get("dispatch_sha256") if isinstance(dispatch_binding, dict) else None
        hold = dispatch.get("hold") if isinstance(dispatch, dict) else {}
        dispatch_invocation_attempted = bool(isinstance(hold, dict) and hold.get("handler_invocation_attempted") is True)
        if dispatch.get("status") == "LOOPBACK_DISPATCH_COMPLETED_LOCAL":
            dispatch_invocation_attempted = True
            dispatch_completion_established = True
            _transition_or_fail_closed(prepared, "DISPATCH_COMPLETED", now_ms=now, dispatch_sha256=dispatch_sha,
                                       detail_code="DURABLE_LOCAL_DISPATCH_COMPLETED")
        elif dispatch_invocation_attempted:
            _transition_or_fail_closed(prepared, "DISPATCH_AMBIGUOUS", now_ms=now, dispatch_sha256=dispatch_sha,
                                       detail_code=str(dispatch.get("status")))
        else:
            _transition_or_fail_closed(prepared, "DISPATCH_HOLD_NO_INVOCATION", now_ms=now,
                                       dispatch_sha256=dispatch_sha, detail_code=str(dispatch.get("status")))
        wire = _compact_receipt(
            "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED" if dispatch_completion_established else "ONE_SHOT_LOOPBACK_EXCHANGE_HOLD",
            bound_host=prepared.host, bound_port=prepared.port, peer_host=peer_host,
            request_sha256=request_sha, frame_sha256=frame_sha,
            transport_status="AUTHENTICATED_FRAME_ADMITTED", dispatch_status=str(dispatch.get("status")),
            dispatch_result_sha256=sha256(dispatch),
            rejection_stage=None if dispatch_completion_established else "LOCAL_DISPATCH_HOLD",
        )
        return _send_and_finalize(prepared, conn, wire, now_ms=now,
                                  dispatch_invocation_attempted=dispatch_invocation_attempted,
                                  dispatch_completion_established=dispatch_completion_established,
                                  receipt_sender=sender)
    except LifecycleLedgerUnavailable:
        return _outcome("HOLD_LIFECYCLE_LEDGER_UNAVAILABLE", prepared, phase="UNKNOWN_FAIL_CLOSED",
                        detail_code="LIFECYCLE_LEDGER_TRANSITION_FAILED", wire_receipt=None,
                        wire_send_completed=False, manual_ack_required=True,
                        dispatch_invocation_attempted=dispatch_invocation_attempted,
                        dispatch_completion_established=dispatch_completion_established)
    finally:
        if conn is not None:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        prepared.listener.close()
