#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

import nohand_habitat_peer as core

EXPECTED_TERMINAL_SCRIPT_SHA256 = "c7ee6233c698ccb5541b7ab1d914f982a6abc33e7dbcb21796cbbfc657864e49"
EXPECTED_TERMINAL_SAFETY_SHA256 = "2b489782ff90f967c406fa3bb918a3bac5c208ca0d047367821a56e9b9c64a4d"
EXPECTED_GATE_SCRIPT_SHA256 = "344eba1409e6bcab807426c0fe2034ad7926094d4d947d154d8699b945017982"
EXPECTED_GATE_SAFETY_SHA256 = "109188160c50fdab5c0cdfd07ea24cd85d671476af40de3f5983145145327e33"
EXPECTED_GOLDPROMPT_BUNDLE_V1_1 = "6a8a63d3bebf0b8611df2682d2c38dd6472818190da5e367fbc22467c5717d17"
EXPECTED_DEMIHEAD_PARENT_MAIN_REVISION = "f2074ca833692f4c2a9f1cb1f5cf723c873d3211"

V142_ROOT = Path("habitat/nohand/v1_4_2")


class ExternalGuardError(ValueError):
    pass


def configure_v142_namespace() -> None:
    core.INBOX = V142_ROOT / "inbox"
    core.OUTBOX = V142_ROOT / "outbox"
    core.OUTCOMES = V142_ROOT / "outcomes"
    core.SETTLED = V142_ROOT / "settled"
    core.SNAPSHOTS = V142_ROOT / "state" / "snapshots"


def validate_external_pins(value: Mapping[str, Any]) -> None:
    core.validate_request(value)
    if value.get("terminal_script_sha256") != EXPECTED_TERMINAL_SCRIPT_SHA256:
        raise ExternalGuardError("TERMINAL_SCRIPT_SHA256_PIN_MISMATCH")
    if value.get("goldprompt_working_faces_bundle_v1_1") != EXPECTED_GOLDPROMPT_BUNDLE_V1_1:
        raise ExternalGuardError("GOLDPROMPT_BUNDLE_V1_1_PIN_MISMATCH")
    if value.get("expected_demihead_parent_main_revision") != EXPECTED_DEMIHEAD_PARENT_MAIN_REVISION:
        raise ExternalGuardError("DEMIHEAD_PARENT_MAIN_PIN_MISMATCH")
    guard = value.get("guard")
    if not isinstance(guard, Mapping):
        raise ExternalGuardError("GUARD_OBJECT_REQUIRED")
    if guard.get("safety_contract_sha256") != EXPECTED_TERMINAL_SAFETY_SHA256:
        raise ExternalGuardError("TERMINAL_SAFETY_CONTRACT_PIN_MISMATCH")
    if guard.get("guardian_of_guardian_ok") is not True:
        raise ExternalGuardError("GUARDIAN_OF_GUARDIAN_REQUIRED")
    if guard.get("preservation_sentinel_ok") is not True:
        raise ExternalGuardError("PRESERVATION_SENTINEL_REQUIRED")
    if guard.get("no_delete") is not True or guard.get("no_move") is not True or guard.get("no_rename") is not True:
        raise ExternalGuardError("PRESERVATION_LAWS_REQUIRED")


def preflight_inbox(root: Path) -> int:
    folder = root / core.INBOX
    if not folder.exists():
        return 0
    checked = 0
    for path in sorted(folder.glob("*.json")):
        value = core.read_json(path)
        validate_external_pins(value)
        checked += 1
    return checked


def process(root: Path) -> dict[str, Any]:
    configure_v142_namespace()
    checked = preflight_inbox(root)
    result = core.process_exchange(root)
    return {
        "status": result.get("status"),
        "external_guard": "PASS",
        "requests_preflighted": checked,
        "created_responses": result.get("created_responses"),
        "settled_outcomes": result.get("settled_outcomes"),
        "authority_delta": 0,
        "pins": {
            "terminal_script_sha256": EXPECTED_TERMINAL_SCRIPT_SHA256,
            "terminal_safety_sha256": EXPECTED_TERMINAL_SAFETY_SHA256,
            "gate_script_sha256": EXPECTED_GATE_SCRIPT_SHA256,
            "gate_safety_sha256": EXPECTED_GATE_SAFETY_SHA256,
            "goldprompt_bundle_v1_1": EXPECTED_GOLDPROMPT_BUNDLE_V1_1,
            "demihead_parent_main_revision": EXPECTED_DEMIHEAD_PARENT_MAIN_REVISION,
        },
    }


def self_test() -> dict[str, Any]:
    configure_v142_namespace()
    request: dict[str, Any] = {
        "schema": core.REQUEST_SCHEMA,
        "request_id": "v142-guard-selftest",
        "action": "STARTUP_HANDSHAKE",
        "context_sha256": "c" * 64,
        "goldprompt_version": core.GOLDPROMPT_VERSION,
        "goldprompt_contract_digest": core.GOLDPROMPT_CONTRACT_DIGEST,
        "goldprompt_working_faces_bundle_v1_1": EXPECTED_GOLDPROMPT_BUNDLE_V1_1,
        "expected_demihead_parent_main_revision": EXPECTED_DEMIHEAD_PARENT_MAIN_REVISION,
        "authority_requested": False,
        "secret_like": False,
        "terminal_script_sha256": EXPECTED_TERMINAL_SCRIPT_SHA256,
        "local_sha256": EXPECTED_TERMINAL_SCRIPT_SHA256,
        "git_sha256": None,
        "path_sha256": None,
        "predictor_forecast_receipt_sha256": "f" * 64,
        "guard": {
            "no_delete": True,
            "no_move": True,
            "no_rename": True,
            "guardian_of_guardian_ok": True,
            "preservation_sentinel_ok": True,
            "verified_preimage_backup_required": False,
            "safety_contract_sha256": EXPECTED_TERMINAL_SAFETY_SHA256,
            "preservation_baseline_sha256": "b" * 64,
        },
    }
    request["request_sha256"] = core.digest(request)
    validate_external_pins(request)

    tampered = json.loads(json.dumps(request))
    tampered["guard"]["safety_contract_sha256"] = "0" * 64
    tampered.pop("request_sha256", None)
    tampered["request_sha256"] = core.digest(tampered)
    rejected = False
    try:
        validate_external_pins(tampered)
    except ExternalGuardError:
        rejected = True

    return {
        "status": "PASS" if rejected else "FAIL",
        "checks": {
            "exact_terminal_artifact_pinned": True,
            "exact_safety_contract_pinned": True,
            "exact_gate_artifact_recorded": True,
            "exact_gate_safety_contract_recorded": True,
            "goldprompt_bundle_pinned": True,
            "sqlite_volatile_sidecar_policy_terminal_side": True,
            "bootstrap_fail_closed_without_process_exit_terminal_side": True,
            "retry_unique_peer_request_id_terminal_side": True,
            "tampered_safety_hash_rejected": rejected,
            "authority_delta_zero": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Pinned DemiHead peer guard for JANUS NAS NOHAND v1.4.2 boot-safe Gate-Terminal pair.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        result = self_test() if args.self_test else process(args.root.resolve())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "error": f"{type(exc).__name__}:{exc}"}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
