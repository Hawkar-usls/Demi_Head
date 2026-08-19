from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any, Mapping

REQUEST_SCHEMA = "janus.demihead.voice_request.v1"
CONTRACT = "NEXUS_V2_5_VOICE_MOUTH_EDGE_FROZEN_CONTRACT"
SOURCE_REPOSITORY = "Hawkar-usls/Demi_Head"
PEER_REPOSITORY = "Hawkar-usls/The-Voice-of-Janus"
ALLOWED_TASKS = {"RENDER_PRESET"}
ALLOWED_PRESETS = {"GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE"}
SAFE_LABEL = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
GIT_DIGEST = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def source_revision(explicit: str | None = None) -> str:
    candidate = explicit or os.environ.get("GITHUB_SHA") or os.environ.get("JANUS_SOURCE_REVISION")
    if not isinstance(candidate, str) or GIT_DIGEST.fullmatch(candidate) is None:
        raise ValueError("DEMIHEAD_SOURCE_REVISION_REQUIRED")
    return candidate


def _request_core(*, task: str, preset_id: str, output_label: str, revision: str) -> dict[str, Any]:
    return {
        "schema": REQUEST_SCHEMA,
        "contract": CONTRACT,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_revision": revision,
        },
        "destination": {
            "repository": PEER_REPOSITORY,
            "role": "LOCAL_AUDIO_RENDERER",
        },
        "task": task,
        "preset_id": preset_id,
        "output_label": output_label,
        "control": {
            "explicit_audio_output_intent": True,
            "local_file_render_only": True,
            "network_io_permitted": False,
            "automatic_playback_permitted": False,
            "shell_execution_permitted": False,
            "arbitrary_path_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def build_request(
    preset_id: str,
    *,
    task: str = "RENDER_PRESET",
    output_label: str = "janus_voice",
    revision: str | None = None,
) -> dict[str, Any]:
    rev = source_revision(revision)
    if task not in ALLOWED_TASKS:
        raise ValueError("VOICE_TASK_NOT_ALLOWLISTED")
    if preset_id not in ALLOWED_PRESETS:
        raise ValueError("VOICE_PRESET_NOT_ALLOWLISTED")
    if not isinstance(output_label, str) or SAFE_LABEL.fullmatch(output_label) is None:
        raise ValueError("VOICE_OUTPUT_LABEL_UNSAFE")

    core = _request_core(task=task, preset_id=preset_id, output_label=output_label, revision=rev)
    request_id = sha256({"kind": "JANUS_VOICE_REQUEST_ID", **core})
    request = {**core, "request_id": request_id}
    request["request_sha256"] = sha256(request)
    validate_request(request)
    return request


def validate_request(request: Mapping[str, Any]) -> None:
    if not isinstance(request, Mapping):
        raise ValueError("VOICE_REQUEST_MUST_BE_OBJECT")
    expected_keys = {
        "schema", "contract", "source", "destination", "task", "preset_id",
        "output_label", "control", "request_id", "request_sha256",
    }
    if set(request) != expected_keys:
        raise ValueError("VOICE_REQUEST_FIELDS_INVALID")
    if request.get("schema") != REQUEST_SCHEMA or request.get("contract") != CONTRACT:
        raise ValueError("VOICE_REQUEST_CONTRACT_INVALID")

    source = request.get("source")
    if not isinstance(source, Mapping) or set(source) != {"repository", "source_revision"}:
        raise ValueError("VOICE_REQUEST_SOURCE_INVALID")
    if source.get("repository") != SOURCE_REPOSITORY:
        raise ValueError("VOICE_REQUEST_SOURCE_REPOSITORY_INVALID")
    if not isinstance(source.get("source_revision"), str) or GIT_DIGEST.fullmatch(source["source_revision"]) is None:
        raise ValueError("VOICE_REQUEST_SOURCE_REVISION_INVALID")

    destination = request.get("destination")
    if not isinstance(destination, Mapping) or destination != {
        "repository": PEER_REPOSITORY,
        "role": "LOCAL_AUDIO_RENDERER",
    }:
        raise ValueError("VOICE_REQUEST_DESTINATION_INVALID")

    if request.get("task") not in ALLOWED_TASKS:
        raise ValueError("VOICE_TASK_NOT_ALLOWLISTED")
    if request.get("preset_id") not in ALLOWED_PRESETS:
        raise ValueError("VOICE_PRESET_NOT_ALLOWLISTED")
    if not isinstance(request.get("output_label"), str) or SAFE_LABEL.fullmatch(request["output_label"]) is None:
        raise ValueError("VOICE_OUTPUT_LABEL_UNSAFE")

    required_control = {
        "explicit_audio_output_intent": True,
        "local_file_render_only": True,
        "network_io_permitted": False,
        "automatic_playback_permitted": False,
        "shell_execution_permitted": False,
        "arbitrary_path_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    if request.get("control") != required_control:
        raise ValueError("VOICE_REQUEST_CONTROL_INVALID")

    request_id = request.get("request_id")
    request_hash = request.get("request_sha256")
    if not isinstance(request_id, str) or HEX64.fullmatch(request_id) is None:
        raise ValueError("VOICE_REQUEST_ID_INVALID")
    if not isinstance(request_hash, str) or HEX64.fullmatch(request_hash) is None:
        raise ValueError("VOICE_REQUEST_HASH_INVALID")

    expected_core = {key: request[key] for key in request if key not in {"request_id", "request_sha256"}}
    expected_id = sha256({"kind": "JANUS_VOICE_REQUEST_ID", **expected_core})
    if request_id != expected_id:
        raise ValueError("VOICE_REQUEST_ID_TAMPERED")
    body = dict(request)
    body.pop("request_sha256")
    if request_hash != sha256(body):
        raise ValueError("VOICE_REQUEST_HASH_TAMPERED")


def verify_request(request: Mapping[str, Any]) -> bool:
    try:
        validate_request(request)
    except (TypeError, ValueError):
        return False
    return True


def self_test() -> dict[str, Any]:
    request = build_request(
        "GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE",
        output_label="selftest",
        revision="a" * 40,
    )
    if not verify_request(request):
        raise AssertionError("VOICE_MOUTH_SELF_TEST_FAILED")
    return {
        "status": "PASS",
        "schema": REQUEST_SCHEMA,
        "contract": CONTRACT,
        "request_sha256": request["request_sha256"],
        "network_io": False,
        "automatic_playback": False,
        "authority_delta": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a typed DemiHead -> The Voice of Janus request")
    parser.add_argument("--preset-id", default="GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE")
    parser.add_argument("--output-label", default="janus_voice")
    parser.add_argument("--source-revision")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    request = build_request(
        args.preset_id,
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
