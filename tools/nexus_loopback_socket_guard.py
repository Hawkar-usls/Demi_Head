from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Any


CONFIG_SCHEMA = "janus.demihead.nexus_loopback_socket_config.v1"
RECEIPT_SCHEMA = "janus.demihead.nexus_loopback_socket_receipt.v1"
CONTRACT = "JANUS_NEXUS_LOOPBACK_SOCKET_ADMISSION_V1"
LOOPBACK_FAMILIES = {
    "127.0.0.1": socket.AF_INET,
    "::1": socket.AF_INET6,
}
MAX_BACKLOG = 16
MAX_FRAME_BYTES = 64 * 1024


@dataclass
class BoundLoopbackSocket:
    sock: socket.socket
    receipt: dict[str, Any]

    def close(self) -> None:
        self.sock.close()

    def __enter__(self) -> "BoundLoopbackSocket":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict) or config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("unexpected loopback socket config schema")
    if not isinstance(config.get("listener_enabled"), bool):
        raise ValueError("listener_enabled must be boolean")

    host = config.get("host")
    if host not in LOOPBACK_FAMILIES:
        raise ValueError("host must be the literal loopback address 127.0.0.1 or ::1")

    port = config.get("port")
    if isinstance(port, bool) or not isinstance(port, int) or not 0 <= port <= 65535:
        raise ValueError("port must be an integer in [0, 65535]")

    backlog = config.get("backlog")
    if isinstance(backlog, bool) or not isinstance(backlog, int) or not 1 <= backlog <= MAX_BACKLOG:
        raise ValueError(f"backlog must be an integer in [1, {MAX_BACKLOG}]")

    timeout_ms = config.get("accept_timeout_ms")
    if isinstance(timeout_ms, bool) or not isinstance(timeout_ms, int) or not 1 <= timeout_ms <= 5000:
        raise ValueError("accept_timeout_ms must be an integer in [1, 5000]")

    frame_bytes = config.get("max_frame_bytes")
    if isinstance(frame_bytes, bool) or not isinstance(frame_bytes, int) or not 1 <= frame_bytes <= MAX_FRAME_BYTES:
        raise ValueError(f"max_frame_bytes must be an integer in [1, {MAX_FRAME_BYTES}]")

    if config.get("automatic_retry_permitted") is not False:
        raise ValueError("automatic retry must remain disabled")
    if config.get("external_effect_permitted") is not False:
        raise ValueError("external effects must remain disabled")
    if config.get("authority_delta") != 0 or config.get("mass_effect_budget_delta") != 0:
        raise ValueError("socket admission cannot alter authority or mass-effect budget")


def _hold(status: str, config: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "schema": RECEIPT_SCHEMA,
        "contract": CONTRACT,
        "status": status,
        "binding": {
            "requested_host": config["host"],
            "requested_port": config["port"],
        },
        "hold": {"reason": reason},
        "control": {
            "socket_created": False,
            "bind_performed": False,
            "listen_performed": False,
            "accept_performed": False,
            "frame_received": False,
            "network_delivery_established": False,
            "external_effect_permitted": False,
            "automatic_retry_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def bind_loopback_listener(
    config: dict[str, Any],
    *,
    explicit_enable: bool = False,
) -> BoundLoopbackSocket | dict[str, Any]:
    validate_config(config)
    if config["listener_enabled"] is not True:
        return _hold("HOLD_LISTENER_DISABLED", config, "listener_enabled=false")
    if explicit_enable is not True:
        return _hold("HOLD_EXPLICIT_ENABLE_REQUIRED", config, "explicit runtime enable was not supplied")

    host = config["host"]
    family = LOOPBACK_FAMILIES[host]
    sock = socket.socket(family, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if family == socket.AF_INET6:
            try:
                sock.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 1)
            except OSError:
                pass
        sock.bind((host, config["port"]))
        sock.listen(config["backlog"])
        sock.settimeout(config["accept_timeout_ms"] / 1000.0)
        bound = sock.getsockname()
        bound_host = str(bound[0])
        bound_port = int(bound[1])
        if bound_host != host:
            raise RuntimeError("OS socket did not bind to the exact requested loopback literal")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "contract": CONTRACT,
            "status": "BOUND_LOOPBACK_LISTENER",
            "binding": {
                "requested_host": host,
                "requested_port": config["port"],
                "bound_host": bound_host,
                "bound_port": bound_port,
                "address_family": "AF_INET6" if family == socket.AF_INET6 else "AF_INET",
                "literal_loopback_verified": True,
            },
            "control": {
                "socket_created": True,
                "bind_performed": True,
                "listen_performed": True,
                "accept_performed": False,
                "frame_received": False,
                "network_delivery_established": False,
                "external_network_reachability_established": False,
                "external_effect_permitted": False,
                "automatic_retry_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
            "claim_ceiling": {
                "loopback_bind_only": True,
                "authenticated_frame_exchange": False,
                "destination_dispatch_over_socket": False,
                "cross_host_delivery": False,
                "external_effect_authority": False,
            },
        }
        return BoundLoopbackSocket(sock=sock, receipt=receipt)
    except Exception:
        sock.close()
        raise


def default_config(host: str = "127.0.0.1") -> dict[str, Any]:
    return {
        "schema": CONFIG_SCHEMA,
        "listener_enabled": False,
        "host": host,
        "port": 0,
        "backlog": 4,
        "accept_timeout_ms": 250,
        "max_frame_bytes": MAX_FRAME_BYTES,
        "automatic_retry_permitted": False,
        "external_effect_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
