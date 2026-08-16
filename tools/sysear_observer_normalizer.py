from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any


WINDOW_SCHEMA = "janus.demihead.sysear_aggregate_window.v1"
OBSERVATION_SCHEMA = "janus.demihead.observation_signal.v1"
NORMALIZER_CONTRACT = "JANUS_SYSEAR_OBSERVER_NORMALIZER_V1"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def rounded(value: float) -> float:
    return round(float(value), 6)


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite")
    return number


def validate_window(window: dict[str, Any]) -> None:
    if not isinstance(window, dict) or window.get("schema") != WINDOW_SCHEMA:
        raise ValueError("Unexpected SysEar aggregate-window schema")
    source = window.get("source")
    if not isinstance(source, dict):
        raise ValueError("source object is required")
    if source.get("adapter") != "SYSEAR":
        raise ValueError("source.adapter must be SYSEAR")
    if source.get("sanitized_aggregate_only") is not True:
        raise ValueError("SysEar Nexus ingress requires sanitized aggregate input")
    for field in (
        "raw_syslog_included",
        "raw_ip_included",
        "raw_mac_included",
        "credentials_included",
    ):
        if source.get(field) is not False:
            raise ValueError(f"{field} must be false")

    metrics = window.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError("metrics object is required")

    sample_count = metrics.get("sample_count")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int) or sample_count < 1:
        raise ValueError("sample_count must be an integer >= 1")

    jitter = _finite_number(metrics.get("interarrival_jitter_us"), "interarrival_jitter_us")
    freshness = _finite_number(metrics.get("source_freshness_seconds"), "source_freshness_seconds")
    if jitter < 0 or freshness < 0:
        raise ValueError("jitter and freshness must be non-negative")

    for field in (
        "firewall_drop_ratio",
        "known_device_ack_ratio",
        "parser_error_ratio",
    ):
        value = _finite_number(metrics.get(field), field)
        if not 0.0 <= value <= 1.0:
            raise ValueError(f"{field} must be in [0, 1]")

    claims = window.get("claims")
    if not isinstance(claims, dict):
        raise ValueError("claims object is required")
    if claims.get("quantum_randomness_established") is not False:
        raise ValueError("SysEar window cannot establish quantum randomness")
    if claims.get("cryptographic_entropy_source") is not False:
        raise ValueError("SysEar window cannot claim cryptographic entropy")
    if claims.get("hardware_entropy_validated") is not False:
        raise ValueError("v1 normalizer requires hardware_entropy_validated=false")


def normalize(window: dict[str, Any]) -> dict[str, Any]:
    validate_window(window)
    metrics = window["metrics"]

    sample_count = int(metrics["sample_count"])
    jitter_us = float(metrics["interarrival_jitter_us"])
    drop_ratio = float(metrics["firewall_drop_ratio"])
    ack_ratio = float(metrics["known_device_ack_ratio"])
    parser_error_ratio = float(metrics["parser_error_ratio"])
    freshness_seconds = float(metrics["source_freshness_seconds"])

    # Bounded descriptive transforms. They are engineering scales, not physical constants.
    turbulence = clamp01(math.log1p(jitter_us) / math.log1p(5000.0))
    security_pressure = clamp01(drop_ratio / 0.20)
    freshness_penalty = clamp01(freshness_seconds / 300.0)
    sample_penalty = clamp01((20.0 - min(sample_count, 20)) / 20.0)
    quality = clamp01(1.0 - 0.60 * parser_error_ratio - 0.25 * freshness_penalty - 0.15 * sample_penalty)
    known_presence = clamp01(ack_ratio * quality)

    if freshness_seconds > 300.0:
        quality_state = "STALE"
    elif sample_count < 20 or parser_error_ratio > 0.10 or freshness_seconds > 60.0:
        quality_state = "DEGRADED"
    else:
        quality_state = "PASS"

    # No automatic creativity/temperature routing in v1. Network conditions are spoofable.
    entropy_hint_eligible = False

    return {
        "schema": OBSERVATION_SCHEMA,
        "fixture_id": window.get("window_id", "UNNAMED_WINDOW"),
        "fixture": bool(window.get("fixture", False)),
        "source": {
            "adapter": "SYSEAR",
            "class": "LOCAL_ROUTER_TELEMETRY_SANITIZED_AGGREGATE",
            "raw_identifiers_included": False,
            "raw_syslog_included": False,
        },
        "quality": {
            "freshness": quality_state,
            "quality_state": quality_state,
            "quality_score": rounded(quality),
            "spoofability": "PRESENT_NOT_ZERO",
            "quantum_randomness_claim": False,
        },
        "signals": [
            {
                "name": "network_turbulence",
                "value": rounded(turbulence),
                "unit": "normalized_0_1",
                "confidence": rounded(quality),
            },
            {
                "name": "security_pressure",
                "value": rounded(security_pressure),
                "unit": "normalized_0_1",
                "confidence": rounded(quality),
            },
            {
                "name": "known_presence_confidence",
                "value": rounded(known_presence),
                "unit": "normalized_0_1",
                "confidence": rounded(quality),
            },
        ],
        "normalization": {
            "contract": NORMALIZER_CONTRACT,
            "jitter_reference_us": 5000.0,
            "drop_ratio_full_scale": 0.20,
            "minimum_full_quality_sample_count": 20,
            "stale_after_seconds": 300.0,
            "entropy_hint_eligible": entropy_hint_eligible,
            "entropy_hint_delta": 0.0,
            "reason_entropy_hint_disabled": "Network timing and event rates are spoofable and are not a validated hardware entropy source.",
        },
        "control": {
            "advisory_only": True,
            "direct_model_temperature_control": False,
            "cryptographic_entropy_source": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def self_test() -> dict[str, Any]:
    fixture = {
        "schema": WINDOW_SCHEMA,
        "window_id": "SELFTEST",
        "fixture": True,
        "source": {
            "adapter": "SYSEAR",
            "sanitized_aggregate_only": True,
            "raw_syslog_included": False,
            "raw_ip_included": False,
            "raw_mac_included": False,
            "credentials_included": False,
        },
        "metrics": {
            "sample_count": 40,
            "interarrival_jitter_us": 120.0,
            "firewall_drop_ratio": 0.02,
            "known_device_ack_ratio": 0.80,
            "parser_error_ratio": 0.01,
            "source_freshness_seconds": 5.0,
        },
        "claims": {
            "quantum_randomness_established": False,
            "cryptographic_entropy_source": False,
            "hardware_entropy_validated": False,
        },
    }
    observation = normalize(fixture)
    checks = {
        "quality_pass": observation["quality"]["quality_state"] == "PASS",
        "three_bounded_signals": len(observation["signals"]) == 3 and all(0.0 <= row["value"] <= 1.0 for row in observation["signals"]),
        "entropy_hint_disabled": observation["normalization"]["entropy_hint_eligible"] is False,
        "direct_temperature_disabled": observation["control"]["direct_model_temperature_control"] is False,
        "crypto_entropy_disabled": observation["control"]["cryptographic_entropy_source"] is False,
        "authority_zero": observation["control"]["authority_delta"] == 0,
    }

    forged = json.loads(json.dumps(fixture))
    forged["source"]["raw_ip_included"] = True
    try:
        normalize(forged)
    except ValueError:
        checks["raw_identifier_input_fails_closed"] = True
    else:
        checks["raw_identifier_input_fails_closed"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "observation": observation,
    }


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected a top-level JSON object")
    return value


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Normalize sanitized SysEar aggregate windows for DemiHead Observer ingress.")
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1
        if args.input is None:
            parser.error("provide --input or --self-test")
        write_json(normalize(load_json(args.input)), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"sysear_observer_normalizer: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
