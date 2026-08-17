from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any

from goldprompt_handshake import assert_contract_integrity
from nohand_pair_protocol import (
    CONTRACT,
    DEMIHEAD_HEAD,
    NAS_HEAD,
    build_message,
    descriptive_selection_concentration,
    sha256,
    validate_message,
)

SAFE_EXTENSIONS = {".py", ".json", ".md", ".txt", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".html", ".css", ".js", ".ts", ".sql", ".csv"}
SAFE_PREFIXES = ("tools/", "docs/", "schemas/", ".janus/")
SECRET_MARKERS = ("secret", "token", "password", "credential", "private_key", ".env", ".pem", ".key")
MAX_OFFER_BYTES = 900 * 1024

SAFETY_CONTRACT = {
    "schema": "janus.demihead.nohand.guard.v1",
    "laws": [
        "NO_DELETE", "NO_MOVE", "NO_RENAME", "APPEND_ONLY_CHANNEL",
        "MESSAGE != COMMAND", "PREDICTION != TRUTH",
        "LEARNER_CANNOT_BYPASS_GUARD", "LEARNER_CANNOT_SELF_MODIFY_CODE",
        "AUTHORITY_WEIGHT = 0",
    ],
}
SAFETY_CONTRACT_SHA256 = sha256(SAFETY_CONTRACT)

def safe_candidate_path(path: str) -> bool:
    if not isinstance(path, str) or not path or path.startswith("/") or ".." in Path(path).parts:
        return False
    low = path.lower()
    if any(marker in low for marker in SECRET_MARKERS):
        return False
    if not any(path.startswith(prefix) for prefix in SAFE_PREFIXES):
        return False
    return Path(path).suffix.lower() in SAFE_EXTENSIONS

def guard_state() -> dict[str, Any]:
    if assert_contract_integrity() != "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8":
        raise ValueError("GoldPrompt contract mismatch")
    if sha256(SAFETY_CONTRACT) != SAFETY_CONTRACT_SHA256:
        raise ValueError("NOHAND safety contract digest mismatch")
    return {
        "safety_contract_sha256": SAFETY_CONTRACT_SHA256,
        "guardian_of_guardian": "PASS",
        "preservation_sentinel": "NOT_APPLICABLE_APPEND_ONLY_GIT",
        "mutation_frozen": False,
        "destructive_permissions": [],
    }

class Calibrator:
    """Append-only operational calibrator; repeated presentations of one action root count once."""

    def __init__(self, observations: list[dict[str, Any]] | None = None) -> None:
        self._seen_roots: set[str] = set()
        self._stats: dict[str, dict[str, float]] = defaultdict(lambda: {"n": 0.0, "success": 0.0, "brier_sum": 0.0, "latency_ewma_ms": 0.0})
        self._selection_roots: list[str] = []
        for observation in observations or []:
            self.observe(observation)

    @staticmethod
    def bucket(action: str, size: int) -> str:
        if size <= 64 * 1024:
            size_class = "XS"
        elif size <= 256 * 1024:
            size_class = "S"
        elif size <= 900 * 1024:
            size_class = "M"
        else:
            size_class = "L"
        return f"{action}|{size_class}"

    def predict(self, *, action: str, size: int, action_event_root: str, selection_process_root: str) -> dict[str, Any]:
        key = self.bucket(action, size)
        stats = self._stats[key]
        p_success = (stats["success"] + 2.0) / (stats["n"] + 4.0)
        total = sum(row["n"] for row in self._stats.values())
        return {
            "schema": "janus.nohand.operational_forecast.v1",
            "forecast_id": hashlib.sha256(f"{action_event_root}|{selection_process_root}|{key}".encode("utf-8")).hexdigest(),
            "action": action,
            "key": key,
            "p_success": round(p_success, 6),
            "expected_latency_ms": round(stats["latency_ewma_ms"], 3) if stats["n"] else None,
            "sample_count": int(stats["n"]),
            "selection_process_root": selection_process_root,
            "action_event_root": action_event_root,
            "mode": "SHADOW_CALIBRATING" if total < 20 else "ADAPTIVE_RANKING",
            "authority_weight": 0,
            "claim_ceiling": "OPERATIONAL_FORECAST_NOT_TRUTH",
        }

    def observe(self, observation: dict[str, Any]) -> bool:
        root = observation.get("action_event_root")
        if not isinstance(root, str) or not root or root in self._seen_roots:
            return False
        key = observation.get("key")
        p_success = observation.get("p_success")
        success = observation.get("success")
        selection_root = observation.get("selection_process_root")
        if not isinstance(key, str) or not isinstance(p_success, (int, float)) or success not in (True, False):
            return False
        if not isinstance(selection_root, str) or not selection_root:
            return False
        stats = self._stats[key]
        stats["n"] += 1.0
        stats["success"] += 1.0 if success else 0.0
        stats["brier_sum"] += (float(p_success) - (1.0 if success else 0.0)) ** 2
        latency = observation.get("latency_ms")
        if isinstance(latency, (int, float)) and latency >= 0:
            stats["latency_ewma_ms"] = float(latency) if stats["n"] == 1 else 0.8 * stats["latency_ewma_ms"] + 0.2 * float(latency)
        self._seen_roots.add(root)
        self._selection_roots.append(selection_root)
        return True

    def summary(self) -> dict[str, Any]:
        total_n = sum(row["n"] for row in self._stats.values())
        total_brier = sum(row["brier_sum"] for row in self._stats.values())
        return {
            "schema": "janus.demihead.nohand.calibration.v1",
            "event_root_count": len(self._seen_roots),
            "brier_mean": round(total_brier / total_n, 6) if total_n else None,
            "selection": descriptive_selection_concentration(self._selection_roots),
            "authority_weight": 0,
            "claim_ceiling": "OPERATIONAL_CALIBRATION_ONLY_NOT_TRUTH_AUTHORITY",
        }

class DemiHeadNohandAgent:
    def __init__(self, source_revision: str, observations: list[dict[str, Any]] | None = None) -> None:
        if not source_revision:
            raise ValueError("source_revision required")
        self.source_revision = source_revision
        self.calibrator = Calibrator(observations)

    def offer_local(self, *, path: str, content: bytes, selection_process_root: str = "DEMIHEAD_REPO_SCAN_V1") -> dict[str, Any]:
        if not safe_candidate_path(path):
            raise ValueError("candidate path is outside bounded DemiHead offer scope")
        if len(content) > MAX_OFFER_BYTES:
            raise ValueError("candidate too large for Git control/data path")
        digest = hashlib.sha256(content).hexdigest()
        action_root = f"offer:{self.source_revision}:{path}:{digest}"
        prediction = self.calibrator.predict(action="OFFER_TO_NAS", size=len(content), action_event_root=action_root, selection_process_root=selection_process_root)
        object_ref = {
            "origin_kind": "GIT_REPOSITORY",
            "sha256": digest,
            "size": len(content),
            "locator": {"repository": "Hawkar-usls/Demi_Head", "ref": self.source_revision, "path": path},
        }
        return build_message(
            message_id=hashlib.sha256(action_root.encode()).hexdigest()[:32],
            sender=DEMIHEAD_HEAD,
            target=NAS_HEAD,
            kind="OFFER",
            source_revision=self.source_revision,
            object_ref=object_ref,
            prediction=prediction,
            guard=guard_state(),
            references={"parent_face_id": "DEMIHEAD_ARBITER", "pair_contract": CONTRACT},
        )

    def evaluate_nas_offer(self, offer: dict[str, Any]) -> dict[str, Any]:
        validate_message(offer)
        if offer["sender"] != NAS_HEAD or offer["target"] != DEMIHEAD_HEAD or offer["kind"] != "OFFER":
            raise ValueError("expected NAS_NOHAND OFFER")
        object_ref = offer["object_ref"]
        path = str((object_ref.get("locator") or {}).get("path", ""))
        size = int(object_ref["size"])
        action_root = f"request:{offer['message_sha256']}"
        prediction = self.calibrator.predict(action="REQUEST_FROM_NAS", size=size, action_event_root=action_root, selection_process_root="DEMIHEAD_NAS_OFFER_REVIEW_V1")
        if size > MAX_OFFER_BYTES:
            state, reason = "HOLD", "PAYLOAD_TOO_LARGE_USE_TRANSFER_NODE"
        elif not path or any(marker in path.lower() for marker in SECRET_MARKERS):
            state, reason = "REJECT", "SECRET_OR_UNSAFE_PATH"
        elif Path(path).suffix.lower() not in SAFE_EXTENSIONS:
            state, reason = "HOLD", "UNSUPPORTED_ARTIFACT_TYPE"
        else:
            state, reason = "REQUEST_COPY", None
        decision = {"state": state}
        if reason:
            decision["reason"] = reason
        return build_message(
            message_id=hashlib.sha256(action_root.encode()).hexdigest()[:32],
            sender=DEMIHEAD_HEAD,
            target=NAS_HEAD,
            kind="DECISION" if state == "REQUEST_COPY" else "HOLD",
            source_revision=self.source_revision,
            object_ref=object_ref,
            decision=decision,
            prediction=prediction,
            guard=guard_state(),
            references={"in_reply_to": offer["message_sha256"], "parent_face_id": "DEMIHEAD_ARBITER"},
        )

def load_observations(path: Path | None) -> list[dict[str, Any]]:
    if path is None or not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows

def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded DemiHead peer for JANUS NOHAND.")
    parser.add_argument("--source-revision", default=os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"))
    parser.add_argument("--observations", type=Path)
    parser.add_argument("--evaluate-offer", type=Path)
    parser.add_argument("--offer-path", type=Path)
    args = parser.parse_args()
    agent = DemiHeadNohandAgent(args.source_revision, load_observations(args.observations))
    if args.evaluate_offer:
        offer = json.loads(args.evaluate_offer.read_text(encoding="utf-8"))
        print(json.dumps(agent.evaluate_nas_offer(offer), ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    if args.offer_path:
        message = agent.offer_local(path=args.offer_path.as_posix(), content=args.offer_path.read_bytes())
        print(json.dumps(message, ensure_ascii=False, indent=2, sort_keys=True))
        return 0
    print(json.dumps({
        "status": "READY_ADVISORY_ONLY",
        "source_revision": args.source_revision,
        "guard": guard_state(),
        "calibration": agent.calibrator.summary(),
        "authority_weight": 0,
        "live_nas_effect_authority": False,
    }, ensure_ascii=False, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
