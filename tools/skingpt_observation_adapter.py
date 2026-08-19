from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SOURCE_REPOSITORY = "Hawkar-usls/SkinGPT"
SOURCE_SHA = "1efd61a17bb24f63b8d92788acec9909bdda76c8"
SOURCE_SCHEMA = "skingpt.frame.v0.3"
SOURCE_SCHEMA_BLOB_SHA = "d1e36072e917ba32ffdeba8552064d3a526d00b4"
OUTPUT_SCHEMA = "janus.demihead.skingpt_telemetry_sample.v1"
EVENTS = {"idle", "warm_touch", "hot_contact", "vibration", "impact", "warm_impact"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def verify_frame(frame: Mapping[str, Any]) -> bool:
    if not isinstance(frame, Mapping) or frame.get("schema") != SOURCE_SCHEMA:
        return False
    for key in ("device_id", "boot_id"):
        if not isinstance(frame.get(key), str) or not frame[key]:
            return False
    for key in ("seq", "uptime_ms"):
        if not isinstance(frame.get(key), int) or isinstance(frame[key], bool) or frame[key] < 0:
            return False
    for key in ("system_operational", "experiment_baseline_valid"):
        if not isinstance(frame.get(key), bool):
            return False

    event = frame.get("event")
    if not isinstance(event, Mapping):
        return False
    if event.get("type") not in EVENTS:
        return False
    if event.get("classifier") != "rule_based_heuristic":
        return False
    if event.get("score_semantics") != "heuristic_not_probability":
        return False
    for key in ("confidence", "severity_score"):
        if not _number(event.get(key)) or not 0 <= float(event[key]) <= 1:
            return False

    piezo = frame.get("piezo")
    if not isinstance(piezo, Mapping):
        return False
    for key in ("peak", "rms", "effective_hz"):
        if not _number(piezo.get(key)) or float(piezo[key]) < 0:
            return False
    if not isinstance(piezo.get("samples"), int) or isinstance(piezo["samples"], bool) or piezo["samples"] < 0:
        return False
    if not isinstance(piezo.get("bias_adc"), int) or isinstance(piezo["bias_adc"], bool) or not 0 <= piezo["bias_adc"] <= 4095:
        return False

    thermal = frame.get("thermal")
    if not isinstance(thermal, Mapping):
        return False
    for key in ("zones_c", "baseline_c", "baseline_ready_by_zone"):
        if not isinstance(thermal.get(key), list) or len(thermal[key]) != 8:
            return False
    if not all(value is None or _number(value) for value in thermal["zones_c"]):
        return False
    if not all(value is None or _number(value) for value in thermal["baseline_c"]):
        return False
    if not all(isinstance(value, bool) for value in thermal["baseline_ready_by_zone"]):
        return False
    if "baseline_ready" in frame and frame["baseline_ready"] != frame["experiment_baseline_valid"]:
        return False
    return True


def build_sample(frame: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_frame(frame):
        raise ValueError("SKINGPT_FRAME_V0_3_INVALID")
    event = frame["event"]
    thermal = frame["thermal"]
    piezo = frame["piezo"]
    source_identity = {
        "repository": SOURCE_REPOSITORY,
        "source_sha": SOURCE_SHA,
        "device_id": frame["device_id"],
        "boot_id": frame["boot_id"],
    }
    calibration = frame.get("calibration") if isinstance(frame.get("calibration"), Mapping) else {}
    threshold_hash = calibration.get("threshold_source_log_sha256")
    if threshold_hash is not None and not _hex64(threshold_hash):
        threshold_hash = None

    sample: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_sha": SOURCE_SHA,
            "frame_schema": SOURCE_SCHEMA,
            "frame_schema_blob_sha": SOURCE_SCHEMA_BLOB_SHA,
            "frame_sha256": digest(dict(frame)),
            "source_identity_sha256": digest(source_identity),
        },
        "sequence": {"seq": frame["seq"], "uptime_ms": frame["uptime_ms"]},
        "operational_state": {
            "system_operational": frame["system_operational"],
            "experiment_baseline_valid": frame["experiment_baseline_valid"],
        },
        "event": {
            "type": event["type"],
            "confidence": float(event["confidence"]),
            "confidence_semantics": "internal_rule_confidence_not_calibrated_posterior_probability",
            "severity_score": float(event["severity_score"]),
            "severity_semantics": "relative_heuristic_not_damage_injury_failure_or_safety_probability",
            "classifier": "rule_based_heuristic",
            "score_semantics": "heuristic_not_probability",
        },
        "measurements": {
            "piezo": {
                "peak": piezo["peak"],
                "rms": piezo["rms"],
                "samples": piezo["samples"],
                "effective_hz": piezo["effective_hz"],
                "bias_adc": piezo["bias_adc"],
            },
            "thermal": {
                "zones_c": list(thermal["zones_c"]),
                "baseline_c": list(thermal["baseline_c"]),
                "baseline_ready_by_zone": list(thermal["baseline_ready_by_zone"]),
                "warmest_zone": thermal.get("warmest_zone"),
                "warmest_c": thermal.get("warmest_c"),
                "warmest_delta_c": thermal.get("warmest_delta_c"),
                "spread_c": thermal.get("spread_c"),
                "traceable_calibration_established": False,
            },
        },
        "calibration": {
            "threshold_source_log_sha256": threshold_hash,
            "threshold_label_source": calibration.get("threshold_label_source") if isinstance(calibration.get("threshold_label_source"), str) else None,
            "thresholds_are_validated_safety_limits": False,
        },
        "privacy": {
            "raw_device_id_forwarded": False,
            "raw_boot_id_forwarded": False,
            "raw_source_ip_forwarded": False,
            "source_identity_bound_by_hash": True,
        },
        "claim_ceiling": {
            "telemetry_sample_is_truth": False,
            "physical_sensor_validation_established": False,
            "material_validation_established": False,
            "medical_or_safety_authority": False,
            "damage_probability_established": False,
            "calibrated_posterior_probability_established": False,
            "hash_integrity_is_sensor_truth": False,
        },
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    sample["sample_sha256"] = digest(sample)
    return sample


def verify_sample(frame: Mapping[str, Any], sample: Mapping[str, Any]) -> bool:
    if not isinstance(sample, Mapping) or sample.get("schema") != OUTPUT_SCHEMA:
        return False
    try:
        expected = build_sample(frame)
    except ValueError:
        return False
    return dict(sample) == expected
