#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping

from goldprompt_handshake import assert_contract_integrity

REQUEST_SCHEMA = "janus.habitat.nohand.demihead_request.v1"
RESPONSE_SCHEMA = "janus.habitat.nohand.demihead_response.v1"
OUTCOME_SCHEMA = "janus.habitat.nohand.demihead_outcome.v1"
STATE_SCHEMA = "janus.habitat.nohand.demihead_predictor_state.v1"

FACE_ID = "DEMIHEAD_ARBITER"
FACE_ROLE = "BICAMERAL_ARBITER"
AUTHORITY_WEIGHT = 0
GOLDPROMPT_VERSION = "0.9.2"
GOLDPROMPT_CONTRACT_DIGEST = "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8"
GOLDPROMPT_PARENT_MAIN_REVISION = "f2074ca833692f4c2a9f1cb1f5cf723c873d3211"

INBOX = Path("habitat/nohand/inbox")
OUTBOX = Path("habitat/nohand/outbox")
OUTCOMES = Path("habitat/nohand/outcomes")
SETTLED = Path("habitat/nohand/settled")
SNAPSHOTS = Path("habitat/nohand/state/snapshots")

CALIBRATION_BINS = 10
MIN_BIN_CALIBRATION = 5
SAFE_HEX = re.compile(r"^[0-9a-f]{64}$")
SOURCE_REV = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
ALLOWED_ACTIONS = {
    "STARTUP_HANDSHAKE",
    "LOCAL_TO_GIT",
    "GIT_TO_LOCAL_CREATE",
    "GIT_TO_LOCAL_OVERWRITE",
}


class PeerError(ValueError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_self_hash(value: Mapping[str, Any], key: str) -> bool:
    claimed = value.get(key)
    if not isinstance(claimed, str) or SAFE_HEX.fullmatch(claimed) is None:
        return False
    unsigned = dict(value)
    unsigned.pop(key, None)
    return digest(unsigned) == claimed


def runtime_revision() -> str:
    github = os.environ.get("GITHUB_SHA", "").strip().lower()
    fallback = os.environ.get("JANUS_PEER_SOURCE_REVISION", "").strip().lower()
    if os.environ.get("GITHUB_ACTIONS") == "true":
        if SOURCE_REV.fullmatch(github) is None:
            raise PeerError("GITHUB_SHA_REQUIRED")
        if fallback and fallback != github:
            raise PeerError("SOURCE_REVISION_ENV_CONFLICT")
        return github
    value = fallback or github
    if SOURCE_REV.fullmatch(value) is None:
        raise PeerError("TRUSTED_SOURCE_REVISION_REQUIRED")
    return value


def _probability(value: float) -> float:
    return min(1.0 - 1e-12, max(1e-12, float(value)))


class PeerPredictor:
    """Authority-neutral Beacon-style success predictor/calibrator.

    The equations mirror the JANUS Beacon policy: hierarchical Beta-like
    success backoff, Dirichlet-like action counts, and ten-bin prequential
    calibration. The model can rank or warn; it cannot grant permission.
    """

    def __init__(self) -> None:
        self.sequence = 0
        self.global_success = {"successes": 0, "total": 0}
        self.action_success: dict[str, dict[str, int]] = {}
        self.context_action_success: dict[str, dict[str, int]] = {}
        self.action_counts: dict[str, int] = {}
        self.context_action_counts: dict[str, dict[str, int]] = {}
        self.bins = [{"successes": 0, "total": 0, "sum_p": 0.0} for _ in range(CALIBRATION_BINS)]
        self.pending: dict[str, dict[str, Any]] = {}
        self.metric_sums = {"n": 0, "raw_brier": 0.0, "cal_brier": 0.0, "logloss": 0.0}

    def _raw_success(self, ctx: str, action: str) -> tuple[float, float]:
        g = self.global_success
        a = self.action_success.get(action, {"successes": 0, "total": 0})
        c = self.context_action_success.get(f"{ctx}|{action}", {"successes": 0, "total": 0})
        successes = 1.0 + c["successes"] + 0.5 * a["successes"] + 0.1 * g["successes"]
        total = 2.0 + c["total"] + 0.5 * a["total"] + 0.1 * g["total"]
        raw = successes / total
        effective_n = c["total"] + 0.5 * a["total"] + 0.1 * g["total"]
        uncertainty = math.sqrt(max(raw * (1.0 - raw), 0.0) / (effective_n + 2.0))
        return raw, uncertainty

    def _calibrate(self, raw: float) -> float:
        idx = min(CALIBRATION_BINS - 1, int(raw * CALIBRATION_BINS))
        row = self.bins[idx]
        if row["total"] < MIN_BIN_CALIBRATION:
            return raw
        empirical = (row["successes"] + 1.0) / (row["total"] + 2.0)
        weight = row["total"] / (row["total"] + 10.0)
        return (1.0 - weight) * raw + weight * empirical

    def forecast(self, request_id: str, context_sha256: str, action: str) -> dict[str, Any]:
        if action not in ALLOWED_ACTIONS:
            raise PeerError("ACTION_NOT_ALLOWED")
        if SAFE_HEX.fullmatch(context_sha256) is None:
            raise PeerError("CONTEXT_SHA256_INVALID")
        prior = self.pending.get(request_id)
        if prior is not None:
            if prior["context_sha256"] != context_sha256 or prior["action"] != action:
                raise PeerError("REQUEST_ID_REBOUND")
            return dict(prior)
        raw, uncertainty = self._raw_success(context_sha256, action)
        calibrated = self._calibrate(raw)
        local = self.context_action_counts.get(context_sha256, {})
        action_score = 1.0 + local.get(action, 0) + 0.25 * self.action_counts.get(action, 0)
        denom = sum(1.0 + local.get(a, 0) + 0.25 * self.action_counts.get(a, 0) for a in sorted(ALLOWED_ACTIONS))
        self.sequence += 1
        result = {
            "request_id": request_id,
            "context_sha256": context_sha256,
            "action": action,
            "raw_success_probability": raw,
            "calibrated_success_probability": calibrated,
            "uncertainty": uncertainty,
            "next_action_probability": action_score / denom,
            "state_sequence": self.sequence,
            "prediction_is_command": False,
            "prediction_is_permission": False,
            "prediction_is_truth": False,
        }
        result["forecast_sha256"] = digest(result)
        self.pending[request_id] = dict(result)
        return result

    def settle(self, request_id: str, action: str, success: bool) -> dict[str, Any]:
        forecast = self.pending.get(request_id)
        if forecast is None:
            raise PeerError("UNKNOWN_PENDING_REQUEST")
        if action != forecast["action"]:
            raise PeerError("OUTCOME_ACTION_MISMATCH")
        if not isinstance(success, bool):
            raise PeerError("OUTCOME_SUCCESS_INVALID")
        ctx = forecast["context_sha256"]
        y = 1.0 if success else 0.0
        raw = _probability(forecast["raw_success_probability"])
        cal = _probability(forecast["calibrated_success_probability"])
        raw_brier = (raw - y) ** 2
        cal_brier = (cal - y) ** 2
        logloss = -(y * math.log(cal) + (1.0 - y) * math.log(1.0 - cal))

        self.global_success["total"] += 1
        self.global_success["successes"] += int(success)
        ac = self.action_success.setdefault(action, {"successes": 0, "total": 0})
        ac["total"] += 1
        ac["successes"] += int(success)
        cc = self.context_action_success.setdefault(f"{ctx}|{action}", {"successes": 0, "total": 0})
        cc["total"] += 1
        cc["successes"] += int(success)
        self.action_counts[action] = self.action_counts.get(action, 0) + 1
        lc = self.context_action_counts.setdefault(ctx, {})
        lc[action] = lc.get(action, 0) + 1
        idx = min(CALIBRATION_BINS - 1, int(raw * CALIBRATION_BINS))
        row = self.bins[idx]
        row["total"] += 1
        row["successes"] += int(success)
        row["sum_p"] += raw
        self.metric_sums["n"] += 1
        self.metric_sums["raw_brier"] += raw_brier
        self.metric_sums["cal_brier"] += cal_brier
        self.metric_sums["logloss"] += logloss
        self.sequence += 1
        self.pending.pop(request_id, None)
        result = {
            "request_id": request_id,
            "action": action,
            "success": success,
            "raw_brier": raw_brier,
            "calibrated_brier": cal_brier,
            "success_logloss": logloss,
            "state_sequence": self.sequence,
            "outcome_grants_authority": False,
        }
        result["settlement_sha256"] = digest(result)
        return result

    def export(self) -> dict[str, Any]:
        state = {
            "schema": STATE_SCHEMA,
            "sequence": self.sequence,
            "global_success": self.global_success,
            "action_success": self.action_success,
            "context_action_success": self.context_action_success,
            "action_counts": self.action_counts,
            "context_action_counts": self.context_action_counts,
            "bins": self.bins,
            "pending": self.pending,
            "metric_sums": self.metric_sums,
            "raw_context_persisted": False,
            "authority_delta": 0,
        }
        state["state_sha256"] = digest(state)
        return state

    @classmethod
    def load(cls, state: Mapping[str, Any]) -> "PeerPredictor":
        if not isinstance(state, Mapping) or state.get("schema") != STATE_SCHEMA or not verify_self_hash(state, "state_sha256"):
            raise PeerError("STATE_INVALID")
        if state.get("raw_context_persisted") is not False or state.get("authority_delta") != 0:
            raise PeerError("STATE_AUTHORITY_OR_CONTEXT_INVALID")
        obj = cls()
        obj.sequence = int(state["sequence"])
        obj.global_success = dict(state["global_success"])
        obj.action_success = {str(k): dict(v) for k, v in dict(state["action_success"]).items()}
        obj.context_action_success = {str(k): dict(v) for k, v in dict(state["context_action_success"]).items()}
        obj.action_counts = {str(k): int(v) for k, v in dict(state["action_counts"]).items()}
        obj.context_action_counts = {str(k): {str(a): int(n) for a, n in dict(v).items()} for k, v in dict(state["context_action_counts"]).items()}
        obj.bins = [dict(row) for row in list(state["bins"])]
        obj.pending = {str(k): dict(v) for k, v in dict(state["pending"]).items()}
        obj.metric_sums = dict(state["metric_sums"])
        return obj


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PeerError(f"{path}: top level must be object")
    return value


def create_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(data)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != data:
            raise PeerError(f"CREATE_ONLY_COLLISION:{path}")


def latest_predictor(root: Path) -> PeerPredictor:
    folder = root / SNAPSHOTS
    if not folder.exists():
        return PeerPredictor()
    paths = sorted(folder.glob("*.json"))
    if not paths:
        return PeerPredictor()
    return PeerPredictor.load(read_json(paths[-1]))


def validate_request(value: Mapping[str, Any]) -> None:
    if value.get("schema") != REQUEST_SCHEMA or not verify_self_hash(value, "request_sha256"):
        raise PeerError("REQUEST_SCHEMA_OR_HASH_INVALID")
    if value.get("action") not in ALLOWED_ACTIONS:
        raise PeerError("REQUEST_ACTION_INVALID")
    if SAFE_HEX.fullmatch(str(value.get("context_sha256", ""))) is None:
        raise PeerError("REQUEST_CONTEXT_INVALID")
    if value.get("goldprompt_version") != GOLDPROMPT_VERSION or value.get("goldprompt_contract_digest") != GOLDPROMPT_CONTRACT_DIGEST:
        raise PeerError("REQUEST_GOLDPROMPT_MISMATCH")
    if value.get("expected_demihead_parent_main_revision") != GOLDPROMPT_PARENT_MAIN_REVISION:
        raise PeerError("REQUEST_DEMIHEAD_PARENT_PIN_MISMATCH")
    guard = value.get("guard")
    if not isinstance(guard, Mapping):
        raise PeerError("REQUEST_GUARD_MISSING")
    if guard.get("no_delete") is not True or guard.get("no_move") is not True or guard.get("no_rename") is not True:
        raise PeerError("REQUEST_PRESERVATION_LAWS_MISSING")
    if value.get("authority_requested") not in (None, False):
        raise PeerError("REQUEST_AUTHORITY_ESCALATION_FORBIDDEN")


def deterministic_advice(request: Mapping[str, Any]) -> tuple[str, list[str]]:
    action = request["action"]
    guard = request["guard"]
    notes: list[str] = []
    if guard.get("guardian_of_guardian_ok") is not True or guard.get("preservation_sentinel_ok") is not True:
        return "HOLD", ["GUARD_CHAIN_NOT_PROVEN"]
    if request.get("secret_like") is True:
        return "HOLD", ["SECRET_LIKE_CONTENT"]
    if action == "STARTUP_HANDSHAKE":
        return "ACK_CONTRACT_BOUNDARY", ["LIVE_NAS_RECEIPT_IS_NOT_GITHUB_CI_RECEIPT"]
    if action == "GIT_TO_LOCAL_OVERWRITE":
        if guard.get("verified_preimage_backup_required") is not True:
            return "HOLD", ["PREIMAGE_BACKUP_REQUIREMENT_MISSING"]
        notes.append("OVERWRITE_REMAINS_LOCAL_POLICY_DECISION")
    return "PROCEED_IF_LOCAL_POLICY_ALLOWS", notes


def build_response(request: Mapping[str, Any], predictor: PeerPredictor) -> dict[str, Any]:
    validate_request(request)
    contract_digest = assert_contract_integrity()
    if contract_digest != GOLDPROMPT_CONTRACT_DIGEST:
        raise PeerError("LOCAL_GOLDPROMPT_CONTRACT_MISMATCH")
    revision = runtime_revision()
    forecast = predictor.forecast(str(request["request_id"]), str(request["context_sha256"]), str(request["action"]))
    advice, notes = deterministic_advice(request)
    response: dict[str, Any] = {
        "schema": RESPONSE_SCHEMA,
        "request_id": request["request_id"],
        "request_sha256": request["request_sha256"],
        "face_id": FACE_ID,
        "face_role": FACE_ROLE,
        "authority_weight": AUTHORITY_WEIGHT,
        "advice": advice,
        "advice_is_permission": False,
        "prediction_is_permission": False,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "goldprompt_contract_digest": contract_digest,
        "goldprompt_parent_main_revision": GOLDPROMPT_PARENT_MAIN_REVISION,
        "peer_module_source_revision": revision,
        "forecast": forecast,
        "notes": notes,
        "claim_boundaries": [
            "PEER_ADVICE != NAS_PERMISSION",
            "PREDICTION != COMMAND",
            "CALIBRATION != TRUTH",
            "SHA256_RECEIPT != DIGITAL_SIGNATURE",
            "GITHUB_PEER_INVOCATION != LIVE_DEMIHEAD_PROCESS_ATTESTATION",
        ],
    }
    response["response_sha256"] = digest(response)
    return response


def validate_outcome(value: Mapping[str, Any]) -> None:
    if value.get("schema") != OUTCOME_SCHEMA or not verify_self_hash(value, "outcome_sha256"):
        raise PeerError("OUTCOME_SCHEMA_OR_HASH_INVALID")
    if value.get("action") not in ALLOWED_ACTIONS or not isinstance(value.get("success"), bool):
        raise PeerError("OUTCOME_VALUE_INVALID")


def save_snapshot(root: Path, predictor: PeerPredictor) -> Path:
    state = predictor.export()
    name = f"{int(state['sequence']):020d}-{state['state_sha256']}.json"
    path = root / SNAPSHOTS / name
    create_json(path, state)
    return path


def process_exchange(root: Path) -> dict[str, Any]:
    predictor = latest_predictor(root)
    created_responses = 0
    settled = 0

    inbox_dir = root / INBOX
    if inbox_dir.exists():
        for request_path in sorted(inbox_dir.glob("*.json")):
            request = read_json(request_path)
            validate_request(request)
            response_path = root / OUTBOX / f"{request['request_id']}.json"
            if response_path.exists():
                continue
            response = build_response(request, predictor)
            create_json(response_path, response)
            created_responses += 1

    outcome_dir = root / OUTCOMES
    if outcome_dir.exists():
        for outcome_path in sorted(outcome_dir.glob("*.json")):
            outcome = read_json(outcome_path)
            validate_outcome(outcome)
            marker = root / SETTLED / f"{outcome['outcome_sha256']}.json"
            if marker.exists():
                continue
            settlement = predictor.settle(str(outcome["request_id"]), str(outcome["action"]), bool(outcome["success"]))
            create_json(marker, {
                "schema": "janus.habitat.nohand.demihead_settlement.v1",
                "outcome_sha256": outcome["outcome_sha256"],
                "settlement": settlement,
            })
            settled += 1

    if created_responses or settled:
        save_snapshot(root, predictor)

    return {
        "status": "PASS",
        "created_responses": created_responses,
        "settled_outcomes": settled,
        "authority_delta": 0,
    }


def self_test() -> dict[str, Any]:
    revision = "a" * 40
    old = os.environ.get("JANUS_PEER_SOURCE_REVISION")
    os.environ["JANUS_PEER_SOURCE_REVISION"] = revision
    try:
        predictor = PeerPredictor()
        request: dict[str, Any] = {
            "schema": REQUEST_SCHEMA,
            "request_id": "selftest-1",
            "action": "GIT_TO_LOCAL_OVERWRITE",
            "context_sha256": "b" * 64,
            "goldprompt_version": GOLDPROMPT_VERSION,
            "goldprompt_contract_digest": GOLDPROMPT_CONTRACT_DIGEST,
            "expected_demihead_parent_main_revision": GOLDPROMPT_PARENT_MAIN_REVISION,
            "authority_requested": False,
            "secret_like": False,
            "guard": {
                "no_delete": True,
                "no_move": True,
                "no_rename": True,
                "guardian_of_guardian_ok": True,
                "preservation_sentinel_ok": True,
                "verified_preimage_backup_required": True,
            },
        }
        request["request_sha256"] = digest(request)
        response = build_response(request, predictor)
        ok = (
            response["authority_weight"] == 0
            and response["advice"] == "PROCEED_IF_LOCAL_POLICY_ALLOWS"
            and response["advice_is_permission"] is False
            and verify_self_hash(response, "response_sha256")
        )
        bad = dict(request)
        bad["guard"] = dict(request["guard"])
        bad["guard"]["guardian_of_guardian_ok"] = False
        bad.pop("request_sha256", None)
        bad["request_sha256"] = digest(bad)
        hold = build_response(bad, PeerPredictor())["advice"] == "HOLD"
        return {"status": "PASS" if ok and hold else "FAIL", "checks": {"bound_response": ok, "guard_failure_holds": hold}}
    finally:
        if old is None:
            os.environ.pop("JANUS_PEER_SOURCE_REVISION", None)
        else:
            os.environ["JANUS_PEER_SOURCE_REVISION"] = old


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead peer for JANUS NOHAND Habitat terminal.")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        result = self_test() if args.self_test else process_exchange(args.root.resolve())
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0 if result.get("status") == "PASS" else 1
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "error": f"{type(exc).__name__}:{exc}"}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
