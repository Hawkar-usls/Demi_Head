from __future__ import annotations

import copy
import socket
import struct
import sys
import tempfile
import threading
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2  # noqa: E402
from nexus_local_transport import build_frame, canonical_json_bytes, sha256  # noqa: E402
from nexus_loopback_dispatcher import LocalHandler  # noqa: E402
from nexus_loopback_exchange import (  # noqa: E402
    MAX_WIRE_BYTES,
    _recv_packet,
    build_request,
    client_exchange_once,
    serve_one_exchange,
)
from nexus_loopback_socket_guard import bind_loopback_listener, default_config  # noqa: E402
from nexus_replay_ledger import SqliteReplayGuard  # noqa: E402


class NexusOneShotLoopbackExchangeTests(unittest.TestCase):
    KEY = b"one-shot-loopback-exchange-test-key"
    ISSUED = 1_800_000_000_000

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.replay_path = self.root / "replay.db"
        self.dispatch_path = self.root / "dispatch.db"
        self.calls: list[str] = []

    def tearDown(self):
        self.temp.cleanup()

    def payload(self):
        return {"decision": "WAIT_FOR_NEW_EVIDENCE", "authority_delta": 0}

    def principals(self):
        runtime = {
            "key": self.KEY,
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        public = {
            "key_id": "GUARDIAN_E1",
            "sender_id": "DEMIHEAD.GUARDIAN",
            "allowed_source_heads": ["GUARDIAN"],
            "enabled": True,
            "revoked": False,
            "epoch": 1,
            "not_before_ms": 1_700_000_000_000,
            "not_after_ms": 1_900_000_000_000,
        }
        return {"GUARDIAN_E1": runtime}, {"GUARDIAN_E1": public}

    def frame(self, *, payload=None, nonce="one-shot-loopback-nonce-000001", issued_at_ms=None):
        payload = payload or self.payload()
        envelope = {
            "schema": "janus.demihead.nexus_envelope.v1",
            "contract": "JANUS_NEXUS_HABITAT_V1",
            "envelope_id": "one-shot-loopback-exchange-test",
            "source_head": "GUARDIAN",
            "target_head": "RELEASE_CONTROL",
            "payload_kind": "GUARDIAN_RESULT",
            "payload_ref": {"sha256": sha256(payload)},
            "trace": [],
            "control": {
                "read_only_transfer": True,
                "direct_workspace_mutation": False,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
                "ttl_hops": 4,
            },
        }
        return build_frame(
            envelope,
            sender_id="DEMIHEAD.GUARDIAN",
            key_id="GUARDIAN_E1",
            key_epoch=1,
            key=self.KEY,
            issued_at_ms=self.ISSUED if issued_at_ms is None else issued_at_ms,
            nonce=nonce,
            ttl_ms=30_000,
        )

    def catalog(self):
        return {
            "schema": "janus.demihead.nexus_endpoint_catalog.v1",
            "live_network_endpoints": False,
            "endpoints": [{
                "schema": "janus.demihead.nexus_endpoint_policy.v1",
                "endpoint_id": "DEMIHEAD.RELEASE_CONTROL.LOCAL",
                "enabled": True,
                "accepted_target_heads": ["RELEASE_CONTROL"],
                "local_dispatch_only": True,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            }],
        }

    def handlers(self):
        def callback(payload):
            self.calls.append(sha256(payload))
            return {
                "schema": "janus.demihead.one_shot_handler_ack.v1",
                "status": "ACK_LOCAL_ONLY",
                "input_sha256": sha256(payload),
            }
        return {
            "RELEASE_CONTROL": LocalHandler(
                handler_id="RELEASE_CONTROL.ONE_SHOT_ACK.V1",
                target_head="RELEASE_CONTROL",
                callback=callback,
            )
        }

    def listener(self):
        config = default_config("127.0.0.1")
        config["listener_enabled"] = True
        config["accept_timeout_ms"] = 1000
        return bind_loopback_listener(config, explicit_enable=True)

    def start_server(self, listener, *, now_ms=None, replay_path=None, dispatch_path=None):
        runtime, public = self.principals()
        box: dict[str, object] = {}

        def target():
            try:
                box["receipt"] = serve_one_exchange(
                    listener,
                    principal_lookup=runtime,
                    public_principal_lookup=public,
                    endpoint_catalog=self.catalog(),
                    handlers=self.handlers(),
                    replay_guard=SqliteReplayGuard(replay_path or self.replay_path),
                    dispatch_ledger=SqliteDispatchLedgerV2(dispatch_path or self.dispatch_path),
                    now_ms=self.ISSUED + 200 if now_ms is None else now_ms,
                )
            except BaseException as exc:  # surfaced in calling test
                box["error"] = exc

        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        return thread, box

    @staticmethod
    def port(listener):
        return int(listener.receipt["binding"]["bound_port"])

    def assert_server_clean(self, thread, box):
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "one-shot server did not terminate")
        if "error" in box:
            raise box["error"]
        self.assertIn("receipt", box)

    def test_real_authenticated_one_shot_roundtrip_dispatches_once(self):
        payload = self.payload()
        request = build_request(self.frame(payload=payload), payload)
        listener = self.listener()
        port = self.port(listener)
        thread, box = self.start_server(listener)
        client_receipt = client_exchange_once("127.0.0.1", port, request)
        self.assert_server_clean(thread, box)
        self.assertEqual(client_receipt["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED")
        self.assertEqual(client_receipt, box["receipt"])
        self.assertEqual(client_receipt["binding"]["peer_host"], "127.0.0.1")
        self.assertEqual(client_receipt["binding"]["transport_status"], "AUTHENTICATED_FRAME_ADMITTED")
        self.assertEqual(client_receipt["binding"]["dispatch_status"], "LOOPBACK_DISPATCH_COMPLETED_LOCAL")
        self.assertTrue(client_receipt["control"]["loopback_network_io_performed"])
        self.assertFalse(client_receipt["control"]["cross_host_delivery_established"])
        self.assertFalse(client_receipt["control"]["handler_output_transmitted"])
        self.assertLessEqual(len(canonical_json_bytes(client_receipt)), MAX_WIRE_BYTES)
        self.assertEqual(len(self.calls), 1)

    def test_hmac_tamper_is_rejected_before_dispatch(self):
        payload = self.payload()
        frame = self.frame(payload=payload)
        frame["auth"]["tag"] = "0" * 64
        listener = self.listener()
        thread, box = self.start_server(listener)
        receipt = client_exchange_once("127.0.0.1", self.port(listener), build_request(frame, payload))
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "HOLD_TRANSPORT_REJECTED")
        self.assertEqual(self.calls, [])
        self.assertEqual(SqliteReplayGuard(self.replay_path).count_active(now_ms=self.ISSUED + 200), 0)

    def test_stale_frame_is_rejected_before_dispatch(self):
        payload = self.payload()
        request = build_request(self.frame(payload=payload), payload)
        listener = self.listener()
        thread, box = self.start_server(listener, now_ms=self.ISSUED + 30_001)
        receipt = client_exchange_once("127.0.0.1", self.port(listener), request)
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "HOLD_TRANSPORT_REJECTED")
        self.assertEqual(self.calls, [])

    def test_persistent_transport_replay_rejects_second_exchange(self):
        payload = self.payload()
        request = build_request(self.frame(payload=payload), payload)

        first_listener = self.listener()
        first_thread, first_box = self.start_server(first_listener)
        first = client_exchange_once("127.0.0.1", self.port(first_listener), request)
        self.assert_server_clean(first_thread, first_box)
        self.assertEqual(first["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED")

        second_listener = self.listener()
        second_thread, second_box = self.start_server(second_listener)
        second = client_exchange_once("127.0.0.1", self.port(second_listener), request)
        self.assert_server_clean(second_thread, second_box)
        self.assertEqual(second["status"], "HOLD_TRANSPORT_REJECTED")
        self.assertEqual(len(self.calls), 1)

    def test_dispatch_intent_guard_is_defense_in_depth_if_replay_db_is_lost(self):
        payload = self.payload()
        request = build_request(self.frame(payload=payload), payload)

        first_listener = self.listener()
        first_thread, first_box = self.start_server(first_listener, replay_path=self.root / "replay-a.db")
        first = client_exchange_once("127.0.0.1", self.port(first_listener), request)
        self.assert_server_clean(first_thread, first_box)
        self.assertEqual(first["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_COMPLETED")

        second_listener = self.listener()
        second_thread, second_box = self.start_server(second_listener, replay_path=self.root / "replay-b.db")
        second = client_exchange_once("127.0.0.1", self.port(second_listener), request)
        self.assert_server_clean(second_thread, second_box)
        self.assertEqual(second["status"], "ONE_SHOT_LOOPBACK_EXCHANGE_HOLD")
        self.assertEqual(second["binding"]["dispatch_status"], "HOLD_DUPLICATE_INTENT")
        self.assertEqual(len(self.calls), 1)

    def test_payload_hash_mismatch_is_rejected_after_transport_without_handler(self):
        original = self.payload()
        frame = self.frame(payload=original)
        mutated = dict(original)
        mutated["decision"] = "MUTATED_AFTER_SIGNING"
        listener = self.listener()
        thread, box = self.start_server(listener)
        receipt = client_exchange_once("127.0.0.1", self.port(listener), build_request(frame, mutated))
        self.assert_server_clean(thread, box)
        self.assertEqual(receipt["status"], "HOLD_DISPATCH_REJECTED")
        self.assertEqual(self.calls, [])
        self.assertEqual(SqliteReplayGuard(self.replay_path).count_active(now_ms=self.ISSUED + 200), 1)

    def raw_exchange(self, declared: int, body: bytes, *, shutdown_write=False, close_without_read=False):
        listener = self.listener()
        port = self.port(listener)
        thread, box = self.start_server(listener)
        sock = socket.create_connection(("127.0.0.1", port), timeout=1.0)
        try:
            sock.sendall(struct.pack("!I", declared) + body)
            if shutdown_write:
                sock.shutdown(socket.SHUT_WR)
            if close_without_read:
                sock.close()
                sock = None
                self.assert_server_clean(thread, box)
                return box["receipt"]
            receipt = _recv_packet(sock)
        finally:
            if sock is not None:
                sock.close()
        self.assert_server_clean(thread, box)
        return receipt

    def test_oversized_declared_packet_is_rejected_without_body_read(self):
        receipt = self.raw_exchange(MAX_WIRE_BYTES + 1, b"")
        self.assertEqual(receipt["status"], "HOLD_WIRE_PROTOCOL")
        self.assertEqual(self.calls, [])

    def test_partial_packet_then_half_close_is_rejected(self):
        receipt = self.raw_exchange(100, b'{"schema":', shutdown_write=True)
        self.assertEqual(receipt["status"], "HOLD_WIRE_PROTOCOL")
        self.assertEqual(self.calls, [])

    def test_malformed_json_is_rejected(self):
        raw = b"{not-json}"
        receipt = self.raw_exchange(len(raw), raw)
        self.assertEqual(receipt["status"], "HOLD_WIRE_PROTOCOL")
        self.assertEqual(self.calls, [])

    def test_client_disconnect_does_not_reopen_or_retry(self):
        receipt = self.raw_exchange(100, b"{", close_without_read=True)
        self.assertEqual(receipt["status"], "HOLD_WIRE_PROTOCOL")
        self.assertEqual(self.calls, [])
        self.assertFalse(receipt["control"]["automatic_retry_permitted"])

    def test_client_refuses_non_loopback_destination(self):
        payload = self.payload()
        request = build_request(self.frame(payload=payload), payload)
        with self.assertRaises(ValueError):
            client_exchange_once("0.0.0.0", 12345, request)
        with self.assertRaises(ValueError):
            client_exchange_once("localhost", 12345, request)


if __name__ == "__main__":
    unittest.main()
