from __future__ import annotations

import socket
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_loopback_socket_guard import (  # noqa: E402
    BoundLoopbackSocket,
    bind_loopback_listener,
    default_config,
    validate_config,
)


class NexusLoopbackSocketGuardTests(unittest.TestCase):
    def test_default_config_is_disabled_and_performs_no_bind(self):
        config = default_config()
        result = bind_loopback_listener(config)
        self.assertEqual(result["status"], "HOLD_LISTENER_DISABLED")
        self.assertFalse(result["control"]["socket_created"])
        self.assertFalse(result["control"]["bind_performed"])
        self.assertFalse(result["control"]["listen_performed"])

    def test_enabled_config_still_requires_explicit_runtime_enable(self):
        config = default_config()
        config["listener_enabled"] = True
        result = bind_loopback_listener(config, explicit_enable=False)
        self.assertEqual(result["status"], "HOLD_EXPLICIT_ENABLE_REQUIRED")
        self.assertFalse(result["control"]["socket_created"])

    def test_non_loopback_and_hostname_binds_are_rejected(self):
        for host in ("0.0.0.0", "::", "localhost", "192.168.1.10", "10.0.0.1", "127.0.0.2"):
            config = default_config()
            config["host"] = host
            with self.subTest(host=host):
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_ipv4_ephemeral_listener_binds_exact_literal_loopback_only(self):
        config = default_config("127.0.0.1")
        config["listener_enabled"] = True
        bound = bind_loopback_listener(config, explicit_enable=True)
        self.assertIsInstance(bound, BoundLoopbackSocket)
        try:
            receipt = bound.receipt
            self.assertEqual(receipt["status"], "BOUND_LOOPBACK_LISTENER")
            self.assertEqual(receipt["binding"]["bound_host"], "127.0.0.1")
            self.assertGreater(receipt["binding"]["bound_port"], 0)
            self.assertTrue(receipt["binding"]["literal_loopback_verified"])
            self.assertFalse(receipt["control"]["accept_performed"])
            self.assertFalse(receipt["control"]["frame_received"])
            self.assertFalse(receipt["control"]["network_delivery_established"])
            self.assertFalse(receipt["control"]["external_network_reachability_established"])
        finally:
            bound.close()

    def test_ipv6_ephemeral_listener_when_platform_supports_loopback(self):
        if not socket.has_ipv6:
            self.skipTest("platform reports no IPv6 support")
        config = default_config("::1")
        config["listener_enabled"] = True
        try:
            bound = bind_loopback_listener(config, explicit_enable=True)
        except OSError as exc:
            self.skipTest(f"IPv6 loopback bind unavailable: {exc}")
        self.assertIsInstance(bound, BoundLoopbackSocket)
        try:
            self.assertEqual(bound.receipt["binding"]["bound_host"], "::1")
            self.assertEqual(bound.receipt["binding"]["address_family"], "AF_INET6")
            self.assertFalse(bound.receipt["control"]["network_delivery_established"])
        finally:
            bound.close()

    def test_retry_external_effect_and_authority_escalation_fail_closed(self):
        mutations = (
            ("automatic_retry_permitted", True),
            ("external_effect_permitted", True),
            ("authority_delta", 1),
            ("mass_effect_budget_delta", 1),
        )
        for field, value in mutations:
            config = default_config()
            config[field] = value
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    validate_config(config)

    def test_backlog_timeout_and_frame_limits_are_bounded(self):
        for field, value in (
            ("backlog", 17),
            ("backlog", 0),
            ("accept_timeout_ms", 0),
            ("accept_timeout_ms", 5001),
            ("max_frame_bytes", 0),
            ("max_frame_bytes", 65537),
        ):
            config = default_config()
            config[field] = value
            with self.subTest(field=field, value=value):
                with self.assertRaises(ValueError):
                    validate_config(config)


if __name__ == "__main__":
    unittest.main()
