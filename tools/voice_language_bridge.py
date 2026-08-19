from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

REQUEST_SCHEMA = "janus.demihead.voice_language_request.v1"
CONTRACT = "NEXUS_V2_6_PYRAMID_LANGUAGE_JSON_EDGE_FROZEN_CONTRACT"
SOURCE_REPOSITORY = "Hawkar-usls/Demi_Head"
PEER_REPOSITORY = "Hawkar-usls/The-Voice-of-Janus"
TASK = "SONIFY_INLINE_JSON"
ALLOWED_PRESETS = {"GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE"}
SAFE_LABEL = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
GIT_DIGEST = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MAX_CANONICAL_JSON_BYTES = 65536


def canonical_json_bytes(value: Any) -> bytes:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("INLINE_JSON_NOT_CANONICALIZABLE") from exc
    return text.encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_json(value: Any) -> str:
    return sha256_bytes(canonical_json_bytes(value))


def source_revision(explicit: str | None = None) -> str:
    candidate = explicit or os.environ.get("GITHUB_SHA") or os.environ.get("JANUS_SOURCE_REVISION")
    if not isinstance(candidate, str) or GIT_DIGEST.fullmatch(candidate) is None:
        raise ValueError("DEMIHEAD_SOURCE_REVISION_REQUIRED")
    return candidate


def build_request(
    value: Any,
    *,
    preset_id: str = "GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE",
    output_label: str = "janus_json_record",
    revision: str | None = None,
) -> dict[str, Any]:
    if preset_id not in ALLOWED_PRESETS:
        raise ValueError("VOICE_PRESET_NOT_ALLOWLISTED")
    if not isinstance(output_label, str) or SAFE_LABEL.fullmatch(output_label) is None:
        raise ValueError("VOICE_OUTPUT_LABEL_UNSAFE")

    payload = canonical_json_bytes(value)
    if len(payload) > MAX_CANONICAL_JSON_BYTES:
        raise ValueError("INLINE_JSON_TOO_LARGE")
    rev = source_revision(revision)
    core = {
        "schema": REQUEST_SCHEMA,
        "contract": CONTRACT,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_revision": rev,
        },
        "destination": {
            "repository": PEER_REPOSITORY,
            "role": "PYRAMID_LANGUAGE_AUDIO_RENDERER",
        },
        "task": TASK,
        "preset_id": preset_id,
        "output_label": output_label,
        "inline_json": value,
        "canonical_json_sha256": sha256_bytes(payload),
        "canonical_json_bytes": len(payload),
        "control": {
            "explicit_audio_output_intent": True,
            "local_file_render_only": True,
            "network_io_permitted": False,
            "automatic_playback_permitted": False,
            "microphone_start_permitted": False,
            "shell_execution_permitted": False,
            "arbitrary_path_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    request_id = sha256_json({"kind": "JANUS_PYRAMID_LANGUAGE_REQUEST_ID", **core})
    request = {**core, "request_id": request_id}
    request["request_sha256"] = sha256_json(request)
    validate_request(request)
    return request


def validate_request(request: Mapping[str, Any]) -> None:
    expected_keys = {
        "schema", "contract", "source", "destination", "task", "preset_id",
        "output_label", "inline_json", "canonical_json_sha256", "canonical_json_bytes",
        "control", "request_id", "request_sha256",
    }
    if not isinstance(request, Mapping) or set(request) != expected_keys:
        raise ValueError("VOICE_LANGUAGE_REQUEST_FIELDS_INVALID")
    if request.get("schema") != REQUEST_SCHEMA or request.get("contract") != CONTRACT:
        raise ValueError("VOICE_LANGUAGE_CONTRACT_INVALID")
    if request.get("task") != TASK:
        raise ValueError("VOICE_LANGUAGE_TASK_INVALID")
    if request.get("preset_id") not in ALLOWED_PRESETS:
        raise ValueError("VOICE_PRESET_NOT_ALLOWLISTED")
    if not isinstance(request.get("output_label"), str) or SAFE_LABEL.fullmatch(request["output_label"]) is None:
        raise ValueError("VOICE_OUTPUT_LABEL_UNSAFE")

    source = request.get("source")
    if not isinstance(source, Mapping) or set(source) != {"repository", "source_revision"}:
        raise ValueError("VOICE_LANGUAGE_SOURCE_INVALID")
    if source.get("repository") != SOURCE_REPOSITORY:
        raise ValueError("VOICE_LANGUAGE_SOURCE_REPOSITORY_INVALID")
    if not isinstance(source.get("source_revision"), str) or GIT_DIGEST.fullmatch(source["source_revision"]) is None:
        raise ValueError("VOICE_LANGUAGE_SOURCE_REVISION_INVALID")

    destination = request.get("destination")
    if not isinstance(destination, Mapping) or destination != {
        "repository": PEER_REPOSITORY,
        "role": "PYRAMID_LANGUAGE_AUDIO_RENDERER",
    }:
        raise ValueError("VOICE_LANGUAGE_DESTINATION_INVALID")

    payload = canonical_json_bytes(request.get("inline_json"))
    if len(payload) > MAX_CANONICAL_JSON_BYTES:
        raise ValueError("INLINE_JSON_TOO_LARGE")
    if request.get("canonical_json_bytes") != len(payload):
        raise ValueError("CANONICAL_JSON_SIZE_TAMPERED")
    if request.get("canonical_json_sha256") != sha256_bytes(payload):
        raise ValueError("CANONICAL_JSON_HASH_TAMPERED")

    required_control = {
        "explicit_audio_output_intent": True,
        "local_file_render_only": True,
        "network_io_permitted": False,
        "automatic_playback_permitted": False,
        "microphone_start_permitted": False,
        "shell_execution_permitted": False,
        "arbitrary_path_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    if request.get("control") != required_control:
        raise ValueError("VOICE_LANGUAGE_CONTROL_INVALID")

    request_id = request.get("request_id")
    request_hash = request.get("request_sha256")
    if not isinstance(request_id, str) or HEX64.fullmatch(request_id) is None:
        raise ValueError("VOICE_LANGUAGE_REQUEST_ID_INVALID")
    if not isinstance(request_hash, str) or HEX64.fullmatch(request_hash) is None:
        raise ValueError("VOICE_LANGUAGE_REQUEST_HASH_INVALID")

    core = {key: request[key] for key in request if key not in {"request_id", "request_sha256"}}
    if request_id != sha256_json({"kind": "JANUS_PYRAMID_LANGUAGE_REQUEST_ID", **core}):
        raise ValueError("VOICE_LANGUAGE_REQUEST_ID_TAMPERED")
    body = dict(request)
    body.pop("request_sha256")
    if request_hash != sha256_json(body):
        raise ValueError("VOICE_LANGUAGE_REQUEST_HASH_TAMPERED")


def verify_request(request: Mapping[str, Any]) -> bool:
    try:
        validate_request(request)
    except (TypeError, ValueError):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a typed DemiHead -> Pyramid Language inline JSON request")
    parser.add_argument("json_file", type=Path)
    parser.add_argument("--preset-id", default="GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE")
    parser.add_argument("--output-label", default="janus_json_record")
    parser.add_argument("--source-revision")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    value = json.loads(args.json_file.read_text(encoding="utf-8"))
    request = build_request(
        value,
        preset_id=args.preset_id,
        output_label=args.output_label,
        revision=args.source_revision,
    )
    text = json.dumps(request, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out is None:
        print(text, end="")
    else:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
