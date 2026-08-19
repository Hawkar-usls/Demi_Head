#!/usr/bin/env python3
"""Pure Nexus v2.7 Voice runtime handler.

This module prepares a content-addressed canonical neural-voice render request.
It intentionally performs no filesystem I/O, network I/O, subprocess execution,
audio rendering, playback, Bluetooth connection, or hardware actuation.

The resulting request is consumed explicitly by The-Voice-of-Janus
``src/nexus_voice_runtime_adapter.py --execute``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from typing import Any

from nexus_loopback_dispatcher import LocalHandler

CONTRACT = "NEXUS_V2_7_LOCAL_NEURAL_VOICE_RUNTIME_FROZEN_CONTRACT"
INTENT_SCHEMA = "janus.demihead.nexus_voice_render_intent.v1"
REQUEST_SCHEMA = "janus.demihead.nexus_voice_render_request.v1"
TARGET_HEAD = "VOICE_RUNTIME"
HANDLER_ID = "DEMIHEAD.NEXUS_VOICE_RUNTIME_HANDLER.v1"
TASK = "RENDER_OSIRIS_ORIGIN_PRIME_NEURAL_PYRAMID"
SOURCE_ARTIFACT_ID = "OSIRIS-SEMANTIC-TEXT-CORE-FOR-THE-VOICE-OF-JANUS-2026-08-19-v1.1"
SEMANTIC_FIELD = "semantic_projection_ru"
REQUIRED_FORMULA = "ORIGIN → EXPERIENCE → RETURN → ORIGIN_PRIME"
LANGUAGE_PROFILE = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3"
VOICE_CONFIG = "configs/osiris_origin_prime_recitation.v4_neural_human.json"
VOICE_CONFIG_BLOB_SHA = "8d18ed86e65e036200f7afa14d62b27fe7c4a0a4"
VOICE_RUNNER = "src/semantic_recitation_v4.py"
VOICE_RUNNER_BLOB_SHA = "85b30261ee7a071655ac6c42cfbb85fc4ae5eed4"
ACTIVATION = "configs/pyramid_117_121_space.activation.json"
ACTIVATION_BLOB_SHA = "70016b9b1ad0ce2b20efd980f14859d66af0a7bd"
MODEL_PATH = "models/v5_5_ru.pt"
ALLOWED_SPEAKERS = ("aidar", "eugene", "baya", "kseniya", "xenia")
OUTPUT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _require_bool(value: Any, expected: bool, name: str) -> None:
    if value is not expected:
        raise ValueError(f"{name} must be {str(expected).lower()}")


def validate_intent(payload: dict[str, Any]) -> tuple[str, str]:
    if not isinstance(payload, dict):
        raise ValueError("Voice runtime intent must be a JSON object")
    allowed_top = {"schema", "contract", "task", "speaker", "output_label", "control"}
    extra = set(payload) - allowed_top
    if extra:
        raise ValueError(f"Unexpected voice intent fields: {sorted(extra)}")
    if payload.get("schema") != INTENT_SCHEMA:
        raise ValueError("Unexpected voice intent schema")
    if payload.get("contract") != CONTRACT:
        raise ValueError("Voice intent contract mismatch")
    if payload.get("task") != TASK:
        raise ValueError("Only canonical OSIRIS neural Pyramid render is admitted")

    speaker = payload.get("speaker", "aidar")
    if speaker not in ALLOWED_SPEAKERS:
        raise ValueError("Speaker is not allowlisted")
    output_label = payload.get("output_label", f"OSIRIS_ORIGIN_PRIME_NEURAL_{speaker.upper()}")
    if not isinstance(output_label, str) or not OUTPUT_RE.fullmatch(output_label):
        raise ValueError("output_label must match the safe 1..64 character label grammar")

    control = payload.get("control", {})
    if not isinstance(control, dict):
        raise ValueError("control must be an object")
    allowed_control = {
        "prepare_only",
        "network_io",
        "automatic_playback",
        "automatic_bluetooth",
        "firmware_flash",
        "authority_delta",
        "mass_effect_budget_delta",
    }
    extra_control = set(control) - allowed_control
    if extra_control:
        raise ValueError(f"Unexpected voice intent control fields: {sorted(extra_control)}")
    _require_bool(control.get("prepare_only", True), True, "control.prepare_only")
    _require_bool(control.get("network_io", False), False, "control.network_io")
    _require_bool(control.get("automatic_playback", False), False, "control.automatic_playback")
    _require_bool(control.get("automatic_bluetooth", False), False, "control.automatic_bluetooth")
    _require_bool(control.get("firmware_flash", False), False, "control.firmware_flash")
    if control.get("authority_delta", 0) != 0:
        raise ValueError("authority_delta must remain zero")
    if control.get("mass_effect_budget_delta", 0) != 0:
        raise ValueError("mass_effect_budget_delta must remain zero")
    return speaker, output_label


def prepare_voice_render_request(payload: dict[str, Any]) -> dict[str, Any]:
    speaker, output_label = validate_intent(payload)
    core = {
        "schema": REQUEST_SCHEMA,
        "contract": CONTRACT,
        "task": TASK,
        "target_head": TARGET_HEAD,
        "source": {
            "artifact_id": SOURCE_ARTIFACT_ID,
            "semantic_field": SEMANTIC_FIELD,
            "required_formula": REQUIRED_FORMULA,
        },
        "larynx": {
            "backend": "silero_v5_5_ru",
            "speaker": speaker,
            "model_relative_path": MODEL_PATH,
            "model_download_permitted": False,
        },
        "language": {
            "profile_id": LANGUAGE_PROFILE,
            "activation": ACTIVATION,
            "activation_blob_sha": ACTIVATION_BLOB_SHA,
            "anchor_band_hz": [117.0, 121.0],
            "semantic_content_preserved": True,
        },
        "voice_runtime": {
            "config": VOICE_CONFIG,
            "config_blob_sha": VOICE_CONFIG_BLOB_SHA,
            "runner": VOICE_RUNNER,
            "runner_blob_sha": VOICE_RUNNER_BLOB_SHA,
            "output_label": output_label,
        },
        "physical_body": {
            "repository": "Hawkar-usls/Echo-Pyramid",
            "role": "PHYSICAL_VOICE_BODY",
            "automatic_handoff": False,
        },
        "control": {
            "prepared_by_nexus": True,
            "audio_rendered": False,
            "filesystem_io_performed": False,
            "network_io_performed": False,
            "automatic_playback": False,
            "automatic_bluetooth": False,
            "firmware_flash": False,
            "external_effect_permitted": False,
            "explicit_voice_execute_required": True,
            "explicit_physical_output_authorization_required": True,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    return {**core, "request_sha256": sha256(core)}


def handle(payload: dict[str, Any]) -> dict[str, Any]:
    return prepare_voice_render_request(payload)


def local_handler() -> LocalHandler:
    """Descriptor admissible under the existing pure Nexus loopback dispatcher."""
    return LocalHandler(
        handler_id=HANDLER_ID,
        target_head=TARGET_HEAD,
        callback=handle,
        deterministic_reference=True,
        network_io_permitted=False,
        filesystem_io_permitted=False,
        external_effect_permitted=False,
        authority_delta=0,
        mass_effect_budget_delta=0,
    )


def self_test() -> dict[str, Any]:
    intent = {
        "schema": INTENT_SCHEMA,
        "contract": CONTRACT,
        "task": TASK,
        "speaker": "aidar",
        "output_label": "OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR",
        "control": {"prepare_only": True},
    }
    first = prepare_voice_render_request(intent)
    second = prepare_voice_render_request(json.loads(json.dumps(intent)))
    if first != second:
        raise AssertionError("Voice handler is not deterministic")
    if first["request_sha256"] != sha256({k: v for k, v in first.items() if k != "request_sha256"}):
        raise AssertionError("Voice request hash binding failed")
    descriptor = local_handler()
    if descriptor.filesystem_io_permitted or descriptor.external_effect_permitted:
        raise AssertionError("Nexus handler boundary widened unexpectedly")
    return {
        "status": "PASS",
        "handler_id": HANDLER_ID,
        "target_head": TARGET_HEAD,
        "request_sha256": first["request_sha256"],
        "audio_rendered": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare a pure Nexus v2.7 neural Voice render request")
    parser.add_argument("--speaker", choices=ALLOWED_SPEAKERS, default="aidar")
    parser.add_argument("--output-label", default=None)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    payload = {
        "schema": INTENT_SCHEMA,
        "contract": CONTRACT,
        "task": TASK,
        "speaker": args.speaker,
        "control": {"prepare_only": True},
    }
    if args.output_label:
        payload["output_label"] = args.output_label
    print(json.dumps(prepare_voice_render_request(payload), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
