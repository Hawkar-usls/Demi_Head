#!/usr/bin/env python3
"""Prepare the frozen Aidar <-> Eugene OSIRIS Voice Spiral bundle.

Pure preparation only: no filesystem writes (apart from optional CLI stdout),
no network I/O, no model loading, no audio rendering, no playback, no hardware.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from typing import Any

from nexus_voice_handler import (
    CONTRACT as VOICE_RUNTIME_CONTRACT,
    INTENT_SCHEMA,
    TASK,
    prepare_voice_render_request,
)

CONTRACT = "NEXUS_V2_8_AIDAR_EUGENE_VOICE_SPIRAL_FROZEN_CONTRACT"
SCHEMA = "janus.demihead.nexus_voice_spiral_bundle.v1"
LAYERS = (
    ("LAYER_A_AIDAR", "aidar", "OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR"),
    ("LAYER_B_EUGENE", "eugene", "OSIRIS_ORIGIN_PRIME_NEURAL_EUGENE"),
)


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


def _intent(speaker: str, output_label: str) -> dict[str, Any]:
    return {
        "schema": INTENT_SCHEMA,
        "contract": VOICE_RUNTIME_CONTRACT,
        "task": TASK,
        "speaker": speaker,
        "output_label": output_label,
        "control": {
            "prepare_only": True,
            "network_io": False,
            "automatic_playback": False,
            "automatic_bluetooth": False,
            "firmware_flash": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def _comparable_core(request: dict[str, Any]) -> dict[str, Any]:
    core = json.loads(json.dumps(request, ensure_ascii=False))
    core.pop("request_sha256", None)
    core["larynx"]["speaker"] = "<SPEAKER>"
    core["voice_runtime"]["output_label"] = "<OUTPUT_LABEL>"
    return core


def prepare_spiral_bundle() -> dict[str, Any]:
    layers = []
    for layer_id, speaker, output_label in LAYERS:
        request = prepare_voice_render_request(_intent(speaker, output_label))
        layers.append({
            "layer_id": layer_id,
            "speaker": speaker,
            "request": request,
        })

    a = layers[0]["request"]
    b = layers[1]["request"]
    if _comparable_core(a) != _comparable_core(b):
        raise AssertionError("Spiral requests drift outside the allowed larynx/output-label difference")
    if a["language"] != b["language"]:
        raise AssertionError("Pyramid Language differs between Spiral layers")
    if a["source"] != b["source"]:
        raise AssertionError("Semantic source differs between Spiral layers")
    if a["larynx"]["speaker"] == b["larynx"]["speaker"]:
        raise AssertionError("Spiral layers must use different speakers")

    core = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "status": "PREPARED_NOT_RENDERED",
        "spiral": {
            "order": [layer["layer_id"] for layer in layers],
            "preserve_all_layers": True,
            "automatic_winner_selection": False,
        },
        "layers": layers,
        "invariants": {
            "same_source": True,
            "same_language": True,
            "same_anchor_band_hz": a["language"]["anchor_band_hz"],
            "only_larynx_speaker_and_output_label_change": True,
            "audio_rendered": False,
            "network_io": False,
            "external_effect": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    return {**core, "spiral_sha256": sha256(core)}


def self_test() -> dict[str, Any]:
    first = prepare_spiral_bundle()
    second = prepare_spiral_bundle()
    if first != second:
        raise AssertionError("Spiral preparation must be deterministic")
    if first["spiral_sha256"] != sha256({k: v for k, v in first.items() if k != "spiral_sha256"}):
        raise AssertionError("Spiral SHA binding failed")
    return {
        "status": "PASS",
        "spiral_sha256": first["spiral_sha256"],
        "layer_count": len(first["layers"]),
        "audio_rendered": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare Aidar <-> Eugene OSIRIS Voice Spiral")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    result = self_test() if args.self_test else prepare_spiral_bundle()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
