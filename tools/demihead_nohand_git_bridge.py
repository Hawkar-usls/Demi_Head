from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

from demihead_nohand_agent import DemiHeadNohandAgent, guard_state
from nohand_pair_protocol import DEMIHEAD_HEAD, NAS_HEAD, build_message, validate_message

CHANNEL_ROOT = Path("nohand/channel")
INBOUND_ROOT = CHANNEL_ROOT / "nas_to_demihead"
OUTBOUND_ROOT = CHANNEL_ROOT / "demihead_to_nas"
PAYLOAD_ROOT = CHANNEL_ROOT / "payloads"


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("message must be a JSON object")
    return value


def _sha256_file(path: Path) -> tuple[str, int]:
    h = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            h.update(chunk)
    return h.hexdigest(), size


def _safe_payload_path(locator: dict[str, Any]) -> Path:
    raw = locator.get("path")
    if not isinstance(raw, str) or not raw:
        raise ValueError("payload locator.path required")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("unsafe payload path")
    try:
        path.relative_to(PAYLOAD_ROOT)
    except ValueError as exc:
        raise ValueError("payload must live under nohand/channel/payloads") from exc
    return path


def handle(message: dict[str, Any], *, source_revision: str) -> dict[str, Any]:
    validate_message(message)
    if message["sender"] != NAS_HEAD or message["target"] != DEMIHEAD_HEAD:
        raise ValueError("bridge accepts NAS_NOHAND -> DEMIHEAD_NOHAND only")

    agent = DemiHeadNohandAgent(source_revision)
    kind = message["kind"]
    if kind == "OFFER":
        return agent.evaluate_nas_offer(message)

    if kind == "RECEIPT":
        obj = message.get("object_ref") or {}
        locator = obj.get("locator")
        if not isinstance(locator, dict):
            raise ValueError("RECEIPT payload locator required")
        payload_path = _safe_payload_path(locator)
        if not payload_path.is_file() or payload_path.is_symlink():
            raise ValueError("RECEIPT payload missing or symlinked")
        digest, size = _sha256_file(payload_path)
        if digest != obj.get("sha256") or size != obj.get("size"):
            raise ValueError("RECEIPT payload hash/size mismatch")
        action_root = f"accept:{message['message_sha256']}:{digest}"
        return build_message(
            message_id=hashlib.sha256(action_root.encode("utf-8")).hexdigest()[:32],
            sender=DEMIHEAD_HEAD,
            target=NAS_HEAD,
            kind="RECEIPT",
            source_revision=source_revision,
            object_ref=obj,
            decision={"state": "ACCEPT"},
            guard=guard_state(),
            references={
                "in_reply_to": message["message_sha256"],
                "payload_verified_in_demihead_checkout": True,
                "parent_face_id": "DEMIHEAD_ARBITER",
            },
        )

    return build_message(
        message_id=hashlib.sha256(f"hold:{message['message_sha256']}".encode("utf-8")).hexdigest()[:32],
        sender=DEMIHEAD_HEAD,
        target=NAS_HEAD,
        kind="HOLD",
        source_revision=source_revision,
        object_ref=message.get("object_ref"),
        decision={"state": "HOLD", "reason": f"UNSUPPORTED_INBOUND_KIND:{kind}"},
        guard=guard_state(),
        references={"in_reply_to": message["message_sha256"], "parent_face_id": "DEMIHEAD_ARBITER"},
    )


def write_create_only(path: Path, value: dict[str, Any]) -> None:
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_text(encoding="utf-8") != raw:
            raise ValueError("response path already exists with different content")
        return
    path.write_text(raw, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead side of the append-only JANUS NOHAND Git channel.")
    parser.add_argument("message", type=Path)
    parser.add_argument("--source-revision", default=os.environ.get("GITHUB_SHA", "LOCAL_UNBOUND"))
    parser.add_argument("--output-root", type=Path, default=OUTBOUND_ROOT)
    args = parser.parse_args()
    inbound = _load(args.message)
    response = handle(inbound, source_revision=args.source_revision)
    output = args.output_root / f"{inbound['message_id']}-response.json"
    write_create_only(output, response)
    print(output.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
