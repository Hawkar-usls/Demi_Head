"""JANUS TACHYON-R1: fail-closed temporal evidence envelope.

All source provenance is *asserted* unless independently byte-verified.
A PASS here is structural, never an AIFC, TOPA or physical-world verdict.
No model execution, weights, trainer, network, secrets or mutable ledger.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = "janus.tachyon.temporal_evidence.v1"
RECEIPT_SCHEMA = "janus.tachyon.temporal_evidence_review.v1"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SAFE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REPO = re.compile(r"^Hawkar-usls/[A-Za-z0-9_.-]{1,80}$")
KINDS = {"FEATURE", "FORECAST", "RESOLUTION"}
TIMES = ("observed_at", "available_at", "feature_cutoff_at", "forecast_frozen_at", "target_at", "resolved_at")
MAX_BYTES = 64_000

class TemporalHold(ValueError):
    """Evidence is missing or causally inconsistent; fail closed."""

def require(ok: bool, reason: str) -> None:
    if not ok:
        raise TemporalHold(reason)

def canonical(value: object) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise TemporalHold("INVALID_CANONICAL_JSON") from exc

def digest(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()

def time_utc(value: str | None) -> datetime | None:
    if value is None:
        return None
    require(isinstance(value, str) and value.endswith("Z") and len(value) <= 36,
            "UTC_Z_TIMESTAMP_REQUIRED")
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise TemporalHold("INVALID_TIMESTAMP") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset().total_seconds() == 0,
            "TIMESTAMP_NOT_UTC")
    return parsed

def strict_object(value: object, keys: set[str], label: str) -> dict:
    require(isinstance(value, dict) and set(value) == keys, "BAD_" + label + "_FIELDS")
    return value

def check_source(source: object) -> dict:
    s = strict_object(source, {"repository", "commit_sha", "path", "content_sha256",
                                "source_family_id", "evidence_class"}, "SOURCE")
    require(bool(REPO.fullmatch(str(s["repository"]))), "SOURCE_REPO_NOT_ALLOWED")
    require(isinstance(s["commit_sha"], str) and HEX40.fullmatch(s["commit_sha"]), "COMMIT_SHA_REQUIRED")
    require(isinstance(s["content_sha256"], str) and HEX64.fullmatch(s["content_sha256"]), "SOURCE_DIGEST_REQUIRED")
    require(isinstance(s["path"], str) and 1 <= len(s["path"]) <= 256
            and not s["path"].startswith("/") and ".." not in s["path"].split("/")
            and "\\" not in s["path"], "UNSAFE_SOURCE_PATH")
    require(isinstance(s["source_family_id"], str) and SAFE_ID.fullmatch(s["source_family_id"]),
            "SOURCE_FAMILY_REQUIRED")
    require(s["evidence_class"] in {"PUBLISHED_MEASUREMENT", "INSTRUMENT_TELEMETRY",
                                    "FROZEN_FORECAST", "RESOLVED_OUTCOME", "SYNTHETIC_CONTROL"},
            "INVALID_EVIDENCE_CLASS")
    return s

def check_value(kind: str, value: object) -> None:
    v = strict_object(value, {"probability_1", "observed_label", "description"}, "VALUE")
    text = v["description"]
    require(isinstance(text, str) and len(text) <= 280, "DESCRIPTION_TOO_LONG")
    p, y = v["probability_1"], v["observed_label"]
    if kind == "FORECAST":
        require(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1
                and y is None, "FORECAST_PROBABILITY_OR_OUTCOME_LEAK")
    elif kind == "FEATURE":
        require(p is None and y is None, "FEATURE_HAS_FUTURE_LABEL")
    else:
        require(p is None and type(y) is int and y in (0, 1), "RESOLUTION_LABEL_REQUIRED")

def validate(record: object) -> dict:
    r = strict_object(record, {"schema", "record_id", "kind", "target_id", "source",
                               "times", "value", "controls", "content_sha256"}, "RECORD")
    require(r["schema"] == SCHEMA, "SCHEMA_MISMATCH")
    for key in ("record_id", "target_id"):
        require(isinstance(r[key], str) and SAFE_ID.fullmatch(r[key]), "INVALID_" + key.upper())
    kind = r["kind"]
    require(isinstance(kind, str) and kind in KINDS, "INVALID_RECORD_KIND")
    check_source(r["source"])
    check_value(kind, r["value"])
    controls = strict_object(r["controls"], {"provenance_checked_externally", "training_permitted",
                                            "automatic_deployment", "scientific_claim_promoted",
                                            "forecast_link_sha256"}, "CONTROLS")
    require(controls["provenance_checked_externally"] is False and
            controls["training_permitted"] is False and
            controls["automatic_deployment"] is False and
            controls["scientific_claim_promoted"] is False,
            "ASSERTED_AUTHORITY_NOT_ACCEPTED")
    link = controls["forecast_link_sha256"]
    require((kind == "RESOLUTION" and isinstance(link, str) and HEX64.fullmatch(link)) or
            (kind != "RESOLUTION" and link is None), "FORECAST_LINK_REQUIRED_OR_FORBIDDEN")
    t = strict_object(r["times"], set(TIMES), "TEMPORAL")
    v = {k: time_utc(t[k]) for k in TIMES}
    o, a, cutoff, freeze, target, resolve = (v[k] for k in TIMES)
    require(cutoff is not None and freeze is not None and target is not None,
            "FORECAST_TEMPORAL_BOUNDARIES_REQUIRED")
    require(cutoff <= freeze < target, "FORECAST_NOT_BEFORE_TARGET")
    if kind == "FEATURE":
        require(o is not None and a is not None and resolve is None,
                "FEATURE_TEMPORAL_FIELDS_MISSING")
        require(o <= a <= cutoff, "LATE_FEATURE_NOT_ADMISSIBLE")
    elif kind == "FORECAST":
        require(o is None and a is not None and resolve is None,
                "FORECAST_PHASE_FIELDS_INVALID")
        require(freeze <= a < target, "FORECAST_PUBLICATION_NOT_PRE_TARGET")
    else:
        require(o is not None and a is not None and resolve is not None,
                "RESOLUTION_TEMPORAL_FIELDS_MISSING")
        require(target <= o <= a <= resolve, "LATE_OUTCOME_TIMESTAMP_ORDER_INVALID")
    sha = r["content_sha256"]
    require(isinstance(sha, str) and HEX64.fullmatch(sha), "ENVELOPE_HASH_REQUIRED")
    unsigned = {k: val for k, val in r.items() if k != "content_sha256"}
    require(digest(unsigned) == sha, "ENVELOPE_DIGEST_MISMATCH")
    return {"schema": RECEIPT_SCHEMA, "record_id": r["record_id"],
            "kind": kind, "record_sha256": sha, "status": "STRUCTURAL_TIME_ORDER_PASS",
            "source_bytes_authenticated": False, "external_clock_witness_verified": False,
            "outcome_admitted_for_training": False, "scientific_claim_promoted": False,
            "authority_delta": 0}

def seal(unsigned: dict) -> dict:
    require(isinstance(unsigned, dict) and "content_sha256" not in unsigned,
            "SEAL_REQUIRES_UNSIGNED_ENVELOPE")
    signed = dict(unsigned)
    signed["content_sha256"] = digest(unsigned)
    validate(signed)
    return signed

def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--record", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    raw = a.record.read_bytes()
    require(len(raw) <= MAX_BYTES, "ENVELOPE_TOO_LARGE")
    def unique(pairs):
        out = {}
        for key, value in pairs:
            require(key not in out, "DUPLICATE_JSON_KEY")
            out[key] = value
        return out
    try:
        obj = json.loads(raw, object_pairs_hook=unique,
                         parse_constant=lambda _: (_ for _ in ()).throw(TemporalHold("NAN_FORBIDDEN")))
        result = validate(obj)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise TemporalHold("INVALID_JSON") from exc
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps(result, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
