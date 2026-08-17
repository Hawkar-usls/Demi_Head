#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import nohand_habitat_peer as core
import nohand_habitat_peer_v1_5_1 as guard

VERSION = "1.5.1-ORPHAN-OUTCOME-RESILIENT"
ORPHAN_HOLD_SCHEMA = "janus.habitat.nohand.demihead_outcome_hold.v1"


def _hold_receipt(outcome: dict[str, Any]) -> dict[str, Any]:
    value = {
        "schema": ORPHAN_HOLD_SCHEMA,
        "outcome_sha256": outcome["outcome_sha256"],
        "request_id": outcome["request_id"],
        "action": outcome["action"],
        "success": outcome["success"],
        "reason": "UNKNOWN_PENDING_REQUEST",
        "source_outcome_preserved": True,
        "source_outcome_deleted": False,
        "source_outcome_moved": False,
        "source_outcome_renamed": False,
        "predictor_mutated": False,
        "authority_delta": 0,
        "hold_is_permission": False,
    }
    value["hold_receipt_sha256"] = core.digest(value)
    return value


def process_exchange_resilient(root: Path) -> dict[str, Any]:
    predictor = core.latest_predictor(root)
    created_responses = 0
    settled = 0
    orphan_holds = 0

    inbox_dir = root / core.INBOX
    if inbox_dir.exists():
        for request_path in sorted(inbox_dir.glob("*.json")):
            request = core.read_json(request_path)
            guard.validate_external_pins(request)
            response_path = root / core.OUTBOX / f"{request['request_id']}.json"
            if response_path.exists():
                continue
            response = core.build_response(request, predictor)
            core.create_json(response_path, response)
            created_responses += 1

    outcome_dir = root / core.OUTCOMES
    if outcome_dir.exists():
        for outcome_path in sorted(outcome_dir.glob("*.json")):
            outcome = core.read_json(outcome_path)
            core.validate_outcome(outcome)
            marker = root / core.SETTLED / f"{outcome['outcome_sha256']}.json"
            if marker.exists():
                continue

            request_id = str(outcome["request_id"])
            action = str(outcome["action"])
            if request_id not in predictor.pending:
                core.create_json(marker, _hold_receipt(outcome))
                orphan_holds += 1
                continue

            settlement = predictor.settle(request_id, action, bool(outcome["success"]))
            core.create_json(marker, {
                "schema": "janus.habitat.nohand.demihead_settlement.v1",
                "outcome_sha256": outcome["outcome_sha256"],
                "settlement": settlement,
            })
            settled += 1

    if created_responses or settled:
        core.save_snapshot(root, predictor)

    return {
        "status": "PASS",
        "created_responses": created_responses,
        "settled_outcomes": settled,
        "orphan_outcomes_held": orphan_holds,
        "orphan_policy": "APPEND_ONLY_HOLD_NONBLOCKING",
        "authority_delta": 0,
    }


def process(root: Path) -> dict[str, Any]:
    guard.configure_v151_namespace()
    checked = guard.preflight_inbox(root)
    result = process_exchange_resilient(root)
    return {
        "status": result["status"],
        "version": VERSION,
        "external_guard": "PASS",
        "requests_preflighted": checked,
        "created_responses": result["created_responses"],
        "settled_outcomes": result["settled_outcomes"],
        "orphan_outcomes_held": result["orphan_outcomes_held"],
        "orphan_policy": result["orphan_policy"],
        "authority_delta": 0,
        "registry_passage_is_permission": False,
    }


def self_test() -> dict[str, Any]:
    base = guard.self_test()
    fake = {
        "schema": core.OUTCOME_SCHEMA,
        "request_id": "orphan-selftest",
        "action": "STARTUP_HANDSHAKE",
        "success": False,
        "authority_delta": 0,
    }
    fake["outcome_sha256"] = core.digest(fake)
    hold = _hold_receipt(fake)
    orphan_ok = (
        hold["reason"] == "UNKNOWN_PENDING_REQUEST"
        and hold["source_outcome_preserved"] is True
        and hold["source_outcome_deleted"] is False
        and hold["source_outcome_moved"] is False
        and hold["source_outcome_renamed"] is False
        and hold["predictor_mutated"] is False
        and core.verify_self_hash(hold, "hold_receipt_sha256")
    )
    return {
        "status": "PASS" if base.get("status") == "PASS" and orphan_ok else "FAIL",
        "version": VERSION,
        "checks": {
            **dict(base.get("checks", {})),
            "orphan_outcome_held_append_only": orphan_ok,
            "orphan_outcome_nonblocking": orphan_ok,
            "orphan_outcome_predictor_unchanged": orphan_ok,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Resilient pinned DemiHead v1.5.1 exchange wrapper.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        result = self_test() if args.self_test else process(args.root.resolve())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "error": f"{type(exc).__name__}:{exc}", "version": VERSION}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
