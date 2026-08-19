from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping

SOURCE_REPOSITORY = "Hawkar-usls/janus-distributed-ai-swarm"
SOURCE_SHA = "43eb173e28f4a8b3e396efc1466db1da02b3c1c7"
CRITICAL_RULES_BLOB_SHA = "f2f1fbc38ff84856f7558ac86ac3b00c1c9f8916"
ARCHITECTURE_BLOB_SHA = "20585721b4e4b2db6fd6bbee25d9fec950b4cbce"
CURRENT_STATE_BLOB_SHA = "f7a05fdb2b8db78427c3f92b73a50a70c4f57cc7"
INPUT_SCHEMA = "janus.demihead.swarm_edge_summary.v1"
OUTPUT_SCHEMA = "janus.demihead.swarm_edge_telemetry_sample.v1"
PACKET_FAMILIES = {"JANUS", "S/S", "P/N"}
FRESHNESS = {"FRESH", "STALE", "ABSENT", "RECOVERING", "DEGRADED"}
PRESENCE_BASIS = {"CURRENT_PACKET", "MEMORY", "PREDICTION"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def verify_summary(summary: Mapping[str, Any]) -> bool:
    if not isinstance(summary, Mapping) or summary.get("schema") != INPUT_SCHEMA:
        return False
    for key in ("node_id", "node_kind", "firmware_version", "declared_identity"):
        if not isinstance(summary.get(key), str) or not summary[key].strip():
            return False
    if summary["declared_identity"] != f"{summary['node_id']}:{summary['node_kind']}":
        return False
    if summary.get("packet_family") not in PACKET_FAMILIES:
        return False
    if summary.get("freshness") not in FRESHNESS:
        return False
    if summary.get("presence_basis") not in PRESENCE_BASIS:
        return False
    if summary["freshness"] == "FRESH" and summary["presence_basis"] != "CURRENT_PACKET":
        return False
    if not isinstance(summary.get("observed_at_ms"), int) or isinstance(summary["observed_at_ms"], bool) or summary["observed_at_ms"] < 0:
        return False
    if not isinstance(summary.get("observer_only"), bool):
        return False
    if not _number(summary.get("submit_pressure")) or float(summary["submit_pressure"]) < 0:
        return False
    if summary["observer_only"] and float(summary["submit_pressure"]) != 0.0:
        return False

    radio = summary.get("radio")
    if not isinstance(radio, Mapping):
        return False
    for key in ("tx_ok", "tx_fail", "rescue_count", "rx_age_ms"):
        if not isinstance(radio.get(key), int) or isinstance(radio[key], bool) or radio[key] < 0:
            return False
    for key in ("channel", "peer_channel"):
        value = radio.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or not 1 <= value <= 14):
            return False

    work = summary.get("work")
    if not isinstance(work, Mapping):
        return False
    if not _number(work.get("hash_rate")) or float(work["hash_rate"]) < 0:
        return False
    for key in ("accepted", "rejected", "stale"):
        if not isinstance(work.get(key), int) or isinstance(work[key], bool) or work[key] < 0:
            return False
    for key in ("best_bits", "target_bits"):
        value = work.get(key)
        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
            return False

    sensors = summary.get("sensors")
    if not isinstance(sensors, Mapping):
        return False
    for name, reading in sensors.items():
        if not isinstance(name, str) or not name or not isinstance(reading, Mapping):
            return False
        state = reading.get("state")
        if state not in FRESHNESS:
            return False
        value = reading.get("value")
        if state == "FRESH":
            if not _number(value):
                return False
            if not isinstance(reading.get("unit"), str) or not reading["unit"]:
                return False
        else:
            if value is not None:
                return False
    return True


def build_sample(summary: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_summary(summary):
        raise ValueError("SWARM_EDGE_SUMMARY_INVALID")
    sample: dict[str, Any] = {
        "schema": OUTPUT_SCHEMA,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "source_sha": SOURCE_SHA,
            "critical_rules_blob_sha": CRITICAL_RULES_BLOB_SHA,
            "architecture_blob_sha": ARCHITECTURE_BLOB_SHA,
            "current_state_blob_sha": CURRENT_STATE_BLOB_SHA,
            "summary_sha256": digest(dict(summary)),
        },
        "node": {
            "node_id": summary["node_id"],
            "node_kind": summary["node_kind"],
            "firmware_version": summary["firmware_version"],
            "semantic_identity": summary["declared_identity"],
            "semantic_identity_sha256": digest({"identity": summary["declared_identity"], "source_sha": SOURCE_SHA}),
        },
        "presence": {
            "packet_family": summary["packet_family"],
            "freshness": summary["freshness"],
            "presence_basis": summary["presence_basis"],
            "observed_at_ms": summary["observed_at_ms"],
            "current_presence_established": summary["freshness"] == "FRESH" and summary["presence_basis"] == "CURRENT_PACKET",
            "stale_or_degraded_state_preserved": summary["freshness"] != "FRESH",
        },
        "radio": dict(summary["radio"]),
        "work": {
            **dict(summary["work"]),
            "sha_target_submit_semantics_reinterpreted": False,
        },
        "sensors": {name: dict(value) for name, value in summary["sensors"].items()},
        "observer": {
            "observer_only": summary["observer_only"],
            "submit_pressure": float(summary["submit_pressure"]),
            "command_authority": False,
        },
        "claim_ceiling": {
            "edge_telemetry_is_command": False,
            "stale_telemetry_is_current_truth": False,
            "prediction_or_memory_is_current_presence": False,
            "hash_integrity_is_source_truth": False,
            "pool_or_sha_truth_changed": False,
            "external_authority": False,
        },
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    sample["sample_sha256"] = digest(sample)
    return sample


def verify_sample(summary: Mapping[str, Any], sample: Mapping[str, Any]) -> bool:
    if not isinstance(sample, Mapping) or sample.get("schema") != OUTPUT_SCHEMA:
        return False
    try:
        expected = build_sample(summary)
    except ValueError:
        return False
    return dict(sample) == expected
