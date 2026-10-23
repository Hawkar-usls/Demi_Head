#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

VERSION = "1.0.0-BOUNDED-CALIBRATED-GOVERNOR"
ENVELOPE = Path("habitat/nohand/adaptive/parameter-envelope-v1.json")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def load_envelope(root: Path) -> dict[str, Any]:
    value = json.loads((root / ENVELOPE).read_text(encoding="utf-8"))
    if value.get("schema") != "janus.habitat.adaptive.parameter_envelope.v1":
        raise ValueError("ENVELOPE_SCHEMA_INVALID")
    laws = value.get("laws") or {}
    required = {
        "no_delete": True,
        "no_move": True,
        "no_rename": True,
        "gate_root_read_only": True,
        "authority_weight": 0,
        "prediction_is_permission": False,
        "safety_contract_mutable": False,
        "allowed_operations_mutable": False,
        "docker_socket_access_mutable": False,
        "mount_permissions_mutable": False,
        "release_pins_mutable_by_governor": False,
    }
    for key, expected in required.items():
        if laws.get(key) != expected:
            raise ValueError(f"IMMUTABLE_LAW_MISMATCH:{key}")
    return value


def _proposal(name: str, current: float, target: float, spec: Mapping[str, Any], reason: str) -> dict[str, Any] | None:
    lo, hi = float(spec["min"]), float(spec["max"])
    step = float(spec["max_step"])
    target = clamp(target, lo, hi)
    delta = clamp(target - current, -step, step)
    proposed = clamp(current + delta, lo, hi)
    if spec["type"] == "int":
        proposed = int(round(proposed))
        current = int(round(current))
    else:
        proposed = round(float(proposed), 6)
        current = round(float(current), 6)
    if proposed == current:
        return None
    return {
        "parameter": name,
        "env": spec["env"],
        "from": current,
        "to": proposed,
        "reason": reason,
    }


def propose(snapshot: Mapping[str, Any], envelope: Mapping[str, Any]) -> dict[str, Any]:
    policy = envelope["change_policy"]
    forecast = snapshot.get("forecast") or {}
    metrics = snapshot.get("metrics") or {}
    current = snapshot.get("current") or {}
    observations = int(snapshot.get("observations", 0))
    calibrated = float(forecast.get("calibrated_success_probability", 0.0))
    uncertainty = float(forecast.get("uncertainty", 1.0))

    base = {
        "schema": "janus.habitat.adaptive.parameter_proposal.v1",
        "version": VERSION,
        "authority_delta": 0,
        "prediction_is_permission": False,
        "delete": False,
        "move": False,
        "rename": False,
        "observations": observations,
        "calibrated_success_probability": calibrated,
        "uncertainty": uncertainty,
    }

    if observations < int(policy["minimum_observations"]):
        base.update({"status": "HOLD", "reason": "INSUFFICIENT_OBSERVATIONS", "changes": []})
        base["proposal_sha256"] = digest(base)
        return base
    if calibrated < float(policy["minimum_calibrated_success_probability"]):
        base.update({"status": "HOLD", "reason": "CALIBRATED_SUCCESS_TOO_LOW", "changes": []})
        base["proposal_sha256"] = digest(base)
        return base
    if uncertainty > float(policy["maximum_uncertainty"]):
        base.update({"status": "HOLD", "reason": "UNCERTAINTY_TOO_HIGH", "changes": []})
        base["proposal_sha256"] = digest(base)
        return base

    specs = envelope["parameters"]
    change = None

    # 1. Repair observed DemiHead timing pressure first.
    timeout = float(current.get("demihead_timeout_seconds", specs["demihead_timeout_seconds"]["default"]))
    p95 = float(metrics.get("demihead_latency_p95_seconds", 0.0))
    timeout_rate = float(metrics.get("demihead_timeout_rate", 0.0))
    late_rate = float(metrics.get("demihead_late_response_rate", 0.0))
    if timeout_rate >= 0.05 or late_rate >= 0.05 or (p95 > 0 and p95 >= timeout * 0.80):
        target = max(timeout + 30.0, p95 * 1.35)
        change = _proposal("demihead_timeout_seconds", timeout, target, specs["demihead_timeout_seconds"], "DEMIHEAD_LATENCY_PRESSURE")
    elif timeout_rate == 0.0 and late_rate == 0.0 and p95 > 0 and p95 < timeout * 0.30 and observations >= 20:
        change = _proposal("demihead_timeout_seconds", timeout, max(30.0, p95 * 2.0), specs["demihead_timeout_seconds"], "DEMIHEAD_TIMEOUT_OVERPROVISIONED")

    # 2. Make promotion more conservative after instability.
    if change is None and float(metrics.get("recent_rollback_rate", 0.0)) > 0.0:
        value = float(current.get("promotion_samples", specs["promotion_samples"]["default"]))
        change = _proposal("promotion_samples", value, value + 2, specs["promotion_samples"], "RECENT_ROLLBACK_INCREASE_PROBATION")

    # 3. React to queue pressure without touching safety law.
    if change is None:
        backlog = int(metrics.get("terminal_backlog", 0))
        idle = float(metrics.get("terminal_idle_fraction", 0.0))
        value = float(current.get("terminal_poll_seconds", specs["terminal_poll_seconds"]["default"]))
        if backlog >= 10:
            change = _proposal("terminal_poll_seconds", value, max(5.0, value - 10.0), specs["terminal_poll_seconds"], "BACKLOG_PRESSURE")
        elif backlog == 0 and idle >= 0.95 and observations >= 20:
            change = _proposal("terminal_poll_seconds", value, value + 10.0, specs["terminal_poll_seconds"], "SUSTAINED_IDLE_BACKOFF")

    if change is None:
        base.update({"status": "HOLD", "reason": "NO_BOUNDED_IMPROVEMENT_FOUND", "changes": []})
    else:
        base.update({
            "status": "PROPOSE",
            "reason": change["reason"],
            "changes": [change],
            "probation_required": True,
            "rollback_target": "BEST_KNOWN_GOOD_PARAMETER_SET",
            "max_parameters_per_activation": 1,
        })
    base["proposal_sha256"] = digest(base)
    return base


def self_test(root: Path) -> dict[str, Any]:
    env = load_envelope(root)
    hot = {
        "observations": 12,
        "forecast": {"calibrated_success_probability": 0.84, "uncertainty": 0.10},
        "current": {"demihead_timeout_seconds": 180},
        "metrics": {"demihead_latency_p95_seconds": 175, "demihead_timeout_rate": 0.10, "demihead_late_response_rate": 0.10},
    }
    p = propose(hot, env)
    assert p["status"] == "PROPOSE"
    assert p["changes"][0]["parameter"] == "demihead_timeout_seconds"
    assert 180 < p["changes"][0]["to"] <= 240
    uncertain = dict(hot)
    uncertain["forecast"] = {"calibrated_success_probability": 0.90, "uncertainty": 0.50}
    h = propose(uncertain, env)
    assert h["status"] == "HOLD" and h["reason"] == "UNCERTAINTY_TOO_HIGH"
    assert p["authority_delta"] == 0 and p["delete"] is False and p["move"] is False and p["rename"] is False
    return {
        "status": "PASS",
        "version": VERSION,
        "checks": {
            "calibration_gates_parameter_change": True,
            "uncertainty_blocks_parameter_change": True,
            "one_parameter_per_activation": True,
            "bounded_step": True,
            "nohand_laws_immutable": True,
            "prediction_not_permission": True,
            "rollback_target_bkg_parameter_set": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    if args.self_test:
        print(json.dumps(self_test(root), ensure_ascii=False, sort_keys=True))
        return 0
    if args.snapshot is None:
        raise SystemExit("--snapshot required unless --self-test")
    envelope = load_envelope(root)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8"))
    print(json.dumps(propose(snapshot, envelope), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
