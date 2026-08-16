from __future__ import annotations

import json
import socket
import struct
from typing import Any

from nexus_local_transport import canonical_json_bytes, sha256, validate_frame
from nexus_loopback_dispatcher import LocalHandler
from nexus_loopback_dispatcher_v2 import dispatch_loopback_v2
from nexus_loopback_socket_guard import BoundLoopbackSocket, LOOPBACK_FAMILIES


CONTRACT = "JANUS_NEXUS_ONE_SHOT_LOOPBACK_EXCHANGE_V1"
REQUEST_SCHEMA = "janus.demihead.nexus_loopback_exchange_request.v1"
RECEIPT_SCHEMA = "janus.demihead.nexus_loopback_exchange_receipt.v1"
MAX_WIRE_BYTES = 64 * 1024
CONNECTION_TIMEOUT_SECONDS = 1.0


class WireProtocolError(ValueError):
    pass


def _recv_exact(sock: socket.socket, size: int) -> bytes:
    if size < 0:
        raise WireProtocolError("negative read size")
    chunks: list[bytes] = []
    remaining = size
    while remaining:
        chunk = sock.recv(remaining)
        if not chunk:
            raise WireProtocolError("peer closed before declared packet completed")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _encode_packet(value: dict[str, Any], *, max_bytes: int = MAX_WIRE_BYTES) -> bytes:
    if not isinstance(value, dict):
        raise WireProtocolError("wire packet must be a JSON object")
    payload = canonical_json_bytes(value)
    if not payload or len(payload) > max_bytes:
        raise WireProtocolError("wire packet size is outside admitted bounds")
    return struct.pack("!I", len(payload)) + payload


def _recv_packet(sock: socket.socket, *, max_bytes: int = MAX_WIRE_BYTES) -> dict[str, Any]:
    header = _recv_exact(sock, 4)
    (declared,) = struct.unpack("!I", header)
    if declared < 1 or declared > max_bytes:
        raise WireProtocolError("declared wire packet length is outside admitted bounds")
    raw = _recv_exact(sock, declared)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise WireProtocolError("wire packet is not valid UTF-8") from exc
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise WireProtocolError("wire packet is not valid JSON") from exc
    if not isinstance(value, dict):
        raise WireProtocolError("wire packet top level must be an object")
    return value


def _send_packet(sock: socket.socket, value: dict[str, Any], *, max_bytes: int = MAX_WIRE_BYTES) -> None:
    sock.sendall(_encode_packet(value, max_bytes=max_bytes))


def validate_request(request: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(request, dict) or request.get("schema") != REQUEST_SCHEMA:
        raise WireProtocolError("unexpected one-shot exchange request schema")
    if set(request) != {"schema", "frame", "payload"}:
        raise WireProtocolError("one-shot request must contain exactly schema, frame and payload")
    frame = request.get("frame")
    payload = request.get("payload")
    if not isinstance(frame, dict):
        raise WireProtocolError("frame must be an object")
    if not isinstance(payload, dict):
        raise WireProtocolError("payload must be an object")
    return frame, payload


def build_request(frame: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    request = {"schema": REQUEST_SCHEMA, "frame": frame, "payload": payload}
    validate_request(request)
    if len(canonical_json_bytes(request)) > MAX_WIRE_BYTES:
        raise WireProtocolError("one-shot request exceeds maximum wire size")
    return request


def _compact_receipt(
    status: str,
    *,
    bound_host: str,
    bound_port: int,
    peer_host: str | None,
    request_sha256: str | None = None,
    frame_sha256: str | None = None,
    transport_status: str | None = None,
    dispatch_status: str | None = None,
    dispatch_result_sha256: str | None = None,
    rejection_stage: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "binding": {
            "bound_host": bound_host,
            "bound_port": bound_port,
            "peer_host": peer_host,
            "request_sha256": request_sha256,
            "frame_sha256": frame_sha256,
            "transport_status": transport_status,
            "dispatch_status": dispatch_status,
            "dispatch_result_sha256": dispatch_result_sha256,
        },
        "rejection": {
            "stage": rejection_stage,
            "details_disclosed": False,
        } if rejection_stage is not None else None,
        "control": {
            "one_connection_only": True,
            "one_request_only": True,
            "loopback_network_io_performed": True,
            "cross_host_delivery_established": False,
            "handler_output_transmitted": False,
            "automatic_retry_permitted": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "authenticated_loopback_frame_exchange": status == "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED",
            "cross_host_transport": False,
            "general_network_service": False,
            "multi_request_session": False,
            "external_effect_authority": False,
        },
    }


def serve_one_exchange(
    listener: BoundLoopbackSocket,
    *,
    principal_lookup: dict[str, dict[str, Any]],
    public_principal_lookup: dict[str, dict[str, Any]],
    endpoint_catalog: dict[str, Any],
    handlers: dict[str, LocalHandler],
    replay_guard: Any,
    dispatch_ledger: Any,
    now_ms: int | None = None,
) -> dict[str, Any]:
    if not isinstance(listener, BoundLoopbackSocket):
        raise ValueError("serve_one_exchange requires an explicitly bound loopback listener")
    bind = listener.receipt.get("binding", {})
    bound_host = bind.get("bound_host")
    bound_port = bind.get("bound_port")
    if bound_host not in LOOPBACK_FAMILIES or not isinstance(bound_port, int):
        listener.close()
        raise ValueError("listener receipt does not prove an admitted literal loopback bind")

    conn: socket.socket | None = None
    peer_host: str | None = None
    receipt: dict[str, Any] | None = None
    try:
        conn, peer = listener.sock.accept()
        conn.settimeout(CONNECTION_TIMEOUT_SECONDS)
        peer_host = str(peer[0])
        if peer_host != bound_host or peer_host not in LOOPBACK_FAMILIES:
            receipt = _compact_receipt(
                "HOLD_NON_LOOPBACK_PEER",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                rejection_stage="PEER_ADDRESS",
            )
            _send_packet(conn, receipt)
            return receipt

        try:
            request = _recv_packet(conn)
            frame, payload = validate_request(request)
        except (WireProtocolError, socket.timeout, OSError):
            receipt = _compact_receipt(
                "HOLD_WIRE_PROTOCOL",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                rejection_stage="WIRE_PROTOCOL",
            )
            try:
                _send_packet(conn, receipt)
            except OSError:
                pass
            return receipt

        request_sha = sha256(request)
        frame_sha = sha256(frame)
        key_id = frame.get("key_id")
        if not isinstance(key_id, str):
            receipt = _compact_receipt(
                "HOLD_TRANSPORT_REJECTED",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                request_sha256=request_sha,
                frame_sha256=frame_sha,
                rejection_stage="TRANSPORT_VALIDATION",
            )
            _send_packet(conn, receipt)
            return receipt

        principal_state = public_principal_lookup.get(key_id)
        if not isinstance(principal_state, dict):
            receipt = _compact_receipt(
                "HOLD_TRANSPORT_REJECTED",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                request_sha256=request_sha,
                frame_sha256=frame_sha,
                rejection_stage="CURRENT_PRINCIPAL_LOOKUP",
            )
            _send_packet(conn, receipt)
            return receipt

        try:
            admission = validate_frame(
                frame,
                principal_lookup=principal_lookup,
                replay_guard=replay_guard,
                now_ms=now_ms,
            )
        except (ValueError, OSError):
            receipt = _compact_receipt(
                "HOLD_TRANSPORT_REJECTED",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                request_sha256=request_sha,
                frame_sha256=frame_sha,
                rejection_stage="TRANSPORT_VALIDATION",
            )
            _send_packet(conn, receipt)
            return receipt

        if admission.get("status") != "AUTHENTICATED_FRAME_ADMITTED":
            receipt = _compact_receipt(
                "HOLD_TRANSPORT_NOT_ADMITTED",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                request_sha256=request_sha,
                frame_sha256=frame_sha,
                transport_status=str(admission.get("status")),
                rejection_stage="TRANSPORT_ADMISSION",
            )
            _send_packet(conn, receipt)
            return receipt

        try:
            dispatch = dispatch_loopback_v2(
                frame,
                admission,
                principal_state,
                endpoint_catalog,
                payload,
                handlers,
                dispatch_ledger=dispatch_ledger,
                now_ms=now_ms,
            )
        except (ValueError, OSError):
            receipt = _compact_receipt(
                "HOLD_DISPATCH_REJECTED",
                bound_host=bound_host,
                bound_port=bound_port,
                peer_host=peer_host,
                request_sha256=request_sha,
                frame_sha256=frame_sha,
                transport_status="AUTHENTICATED_FRAME_ADMITTED",
                rejection_stage="LOCAL_DISPATCH_VALIDATION",
            )
            _send_packet(conn, receipt)
            return receipt

        dispatch_sha = sha256(dispatch)
        completed = dispatch.get("status") == "LOOPBACK_DISPATCH_COMPLETED_LOCAL"
        receipt = _compact_receipt(
            "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED" if completed else "ONE_SHOT_LOOPBACK_EXCHANGE_HOLD",
            bound_host=bound_host,
            bound_port=bound_port,
            peer_host=peer_host,
            request_sha256=request_sha,
            frame_sha256=frame_sha,
            transport_status="AUTHENTICATED_FRAME_ADMITTED",
            dispatch_status=str(dispatch.get("status")),
            dispatch_result_sha256=dispatch_sha,
            rejection_stage=None if completed else "LOCAL_DISPATCH_HOLD",
        )
        _send_packet(conn, receipt)
        return receipt
    finally:
        if conn is not None:
            try:
                conn.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            conn.close()
        listener.close()


def client_exchange_once(
    host: str,
    port: int,
    request: dict[str, Any],
    *,
    timeout_seconds: float = CONNECTION_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    if host not in LOOPBACK_FAMILIES:
        raise ValueError("client exchange host must be an admitted literal loopback address")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise ValueError("client exchange port must be in [1, 65535]")
    validate_request(request)
    family = LOOPBACK_FAMILIES[host]
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.settimeout(timeout_seconds)
        sock.connect((host, port))
        _send_packet(sock, request)
        return _recv_packet(sock)
    finally:
        sock.close()
