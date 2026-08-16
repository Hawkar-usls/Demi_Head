from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from nexus_dispatch_ledger_v2 import SqliteDispatchLedgerV2, dispatch_digest, intent_digest
from nexus_loopback_lifecycle_gate import PreparedLifecycleListener, SqliteLifecycleLedger, default_lifecycle_policy, prepare_lifecycle_listener
from nexus_loopback_socket_guard import default_config

FRAME_SHA256 = "a" * 64


def _seed_dispatch(path: Path, *, state: str, now_ms: int) -> dict[str, str]:
    ledger = SqliteDispatchLedgerV2(path)
    bindings = {
        "frame_sha256": FRAME_SHA256,
        "acceptance_sha256": "b" * 64,
        "payload_sha256": "c" * 64,
        "target_head": "RELEASE_CONTROL",
    }
    intent = intent_digest(bindings)
    dispatch = dispatch_digest(intent, "RELEASE_CONTROL.REAL_KILL_PROBE.V1")
    started = ledger.begin(
        intent_sha256=intent,
        dispatch_sha256=dispatch,
        intent_bindings=bindings,
        handler_id="RELEASE_CONTROL.REAL_KILL_PROBE.V1",
        now_ms=now_ms,
    )
    if started.get("admitted") is not True:
        raise RuntimeError("probe dispatch evidence could not be admitted")
    if state == "COMPLETED":
        if not ledger.complete(dispatch, result_sha256="d" * 64, now_ms=now_ms + 1):
            raise RuntimeError("probe dispatch evidence could not be completed")
    elif state != "STARTED":
        raise ValueError("dispatch evidence state must be STARTED or COMPLETED")
    return {"intent_sha256": intent, "dispatch_sha256": dispatch, "state": state}


def main() -> int:
    parser = argparse.ArgumentParser(description="Subprocess crash probe for JANUS Nexus lifecycle durability tests.")
    parser.add_argument("--lifecycle-db", required=True, type=Path)
    parser.add_argument("--dispatch-db", required=True, type=Path)
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--instance-id", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--marker", required=True, type=Path)
    parser.add_argument("--dispatch-evidence", choices=("NONE", "STARTED", "COMPLETED"), default="NONE")
    parser.add_argument("--real-loopback-bind", action="store_true")
    parser.add_argument("--now-ms", type=int, default=1_800_000_020_000)
    args = parser.parse_args()

    args.marker.parent.mkdir(parents=True, exist_ok=True)
    ledger = SqliteLifecycleLedger(args.lifecycle_db)
    prepared: PreparedLifecycleListener | None = None
    port = None

    if args.real_loopback_bind:
        if args.phase != "LISTENER_BOUND":
            raise ValueError("real loopback bind probe is only valid for LISTENER_BOUND")
        config = default_config("127.0.0.1")
        config["listener_enabled"] = True
        config["accept_timeout_ms"] = 1000
        policy = default_lifecycle_policy()
        policy["startup_enabled"] = True
        prepared_result = prepare_lifecycle_listener(
            config,
            policy,
            lifecycle_ledger=ledger,
            service_id=args.service_id,
            instance_id=args.instance_id,
            explicit_enable=True,
            now_ms=args.now_ms,
        )
        if not isinstance(prepared_result, PreparedLifecycleListener):
            raise RuntimeError(f"loopback bind probe held: {prepared_result}")
        prepared = prepared_result
        port = prepared.port
    else:
        begin = ledger.begin(args.service_id, args.instance_id, now_ms=args.now_ms)
        if begin.get("admitted") is not True:
            raise RuntimeError("lifecycle probe could not acquire service lease")
        if args.phase != "STARTING":
            if args.phase == "DISPATCH_COMPLETED":
                ledger.transition(
                    args.service_id,
                    args.instance_id,
                    "DISPATCH_STARTED",
                    now_ms=args.now_ms + 1,
                    frame_sha256=FRAME_SHA256,
                    detail_code="REAL_KILL_PROBE_DISPATCH_STARTED",
                )
            else:
                ledger.transition(
                    args.service_id,
                    args.instance_id,
                    args.phase,
                    now_ms=args.now_ms + 1,
                    frame_sha256=FRAME_SHA256,
                    detail_code=f"REAL_KILL_PROBE_{args.phase}",
                )

    dispatch = None
    if args.dispatch_evidence != "NONE":
        dispatch = _seed_dispatch(args.dispatch_db, state=args.dispatch_evidence, now_ms=args.now_ms + 2)

    if args.phase == "DISPATCH_COMPLETED" and not args.real_loopback_bind:
        ledger.transition(
            args.service_id,
            args.instance_id,
            "DISPATCH_COMPLETED",
            now_ms=args.now_ms + 4,
            frame_sha256=FRAME_SHA256,
            dispatch_sha256=dispatch["dispatch_sha256"] if dispatch else None,
            detail_code="REAL_KILL_PROBE_DISPATCH_COMPLETED",
        )

    state = ledger.state(args.service_id)
    marker_payload = {
        "pid": os.getpid(),
        "service_id": args.service_id,
        "instance_id": args.instance_id,
        "phase": state["phase"] if state else None,
        "frame_sha256": state.get("frame_sha256") if state else None,
        "dispatch_evidence": dispatch,
        "bound_port": port,
        "ready_for_parent_termination": True,
    }
    with args.marker.open("w", encoding="utf-8") as handle:
        json.dump(marker_payload, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())

    while True:
        time.sleep(60)


if __name__ == "__main__":
    raise SystemExit(main())
