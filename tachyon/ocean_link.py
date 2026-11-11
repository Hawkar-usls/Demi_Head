"""JANUS Tachyon × JANUS Ocean 009B: read-only, phase-separated audit.

Neither Tachyon's narrative classifier nor its numeric Lorentz classifier predicts
Ocean drand results. This bridge preserves early/late provenance and emits a
bounded TOPA-compatible research envelope. Its output is not a training label.
"""
from __future__ import annotations

import argparse
from datetime import datetime, date, timezone
import hashlib
import json
import math
from pathlib import Path
import re

SCHEMA = "janus.ocean.open_future_009b.v1"
OUTPUT_SCHEMA = "janus.tachyon.ocean_shadow_bridge.v1"
FEEDBACK_SCHEMA = "janus.ocean.tachyon_research_feedback.v1"
CHAIN = "52db9ba70e0cc0f6eaf7803dd07447a1f5477735fd3f661792ba94600c84e971"
GENESIS = 1692803367
PERIOD = 3
N = 128
WINDOW_START = date(2026, 11, 12)
WINDOW_END = date(2026, 11, 19)
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
HEX40 = re.compile(r"[a-f0-9]{40}\Z")
MAX_BYTES = 250_000


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def load(path):
    raw = Path(path).read_bytes()
    if len(raw) > MAX_BYTES:
        raise ValueError("OVERSIZED_UNTRUSTED_SOURCE")
    return json.loads(raw), hashlib.sha256(raw).hexdigest()


def utc(value):
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("UTC_Z_REQUIRED")
    try:
        t = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("INVALID_UTC_TIMESTAMP") from exc
    if t.utcoffset().total_seconds() != 0:
        raise ValueError("UTC_REQUIRED")
    return t


def fixed_rounds(target_day):
    if not WINDOW_START <= target_day <= WINDOW_END:
        raise ValueError("OUTSIDE_PREREGISTERED_OCEAN_WINDOW")
    start = int(datetime(target_day.year, target_day.month, target_day.day, 8,
                         tzinfo=timezone.utc).timestamp())
    first = max(1, (start - GENESIS + PERIOD - 1) // PERIOD + 1)
    return [first + 20 * i for i in range(N)]


def release(round_number):
    return GENESIS + (round_number - 1) * PERIOD


def validate_early(wrapper, github_created_at=None):
    if not isinstance(wrapper, dict) or not isinstance(wrapper.get("payload"), dict):
        raise ValueError("OCEAN_PRECOMMIT_WRAPPER_REQUIRED")
    p = wrapper["payload"]
    if wrapper.get("sha256") != digest(p):
        raise ValueError("OCEAN_CANONICAL_PRECOMMIT_SHA_MISMATCH")
    if (p.get("schema") != SCHEMA or p.get("lane") != "OPEN-FUTURE-009B"
            or p.get("phase") != "EARLY_PRECOMMIT"):
        raise ValueError("OCEAN_SCHEMA_OR_PHASE_REJECTED")
    try:
        target = date.fromisoformat(p["target_date"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("INVALID_TARGET_DATE") from exc
    rounds = fixed_rounds(target)
    if (p.get("n_distinct_rounds") != N or p.get("target_rounds") != rounds
            or p.get("quicknet_hash") != CHAIN
            or p.get("quicknet_genesis_unix") != GENESIS
            or p.get("quicknet_period_seconds") != PERIOD
            or p.get("first_release_unix") != release(rounds[0])
            or p.get("last_release_unix") != release(rounds[-1])):
        raise ValueError("OCEAN_ROUNDS_OR_CHAIN_CHANGED")
    if (p.get("future_results_seen") is not False
            or p.get("postselection_allowed") is not False
            or p.get("training_after_precommit") is not False
            or p.get("no_physical_receiver") is not True
            or p.get("retrocausality_proven") is not False
            or p.get("forecast_encoding") != "MODEL_PUBLIC_ROUND_AND_POSITION_ONLY"):
        raise ValueError("EARLY_FUTURE_LEAKAGE_OR_AUTHORITY_REJECTED")
    if (p.get("forecast_model") != "HISTORIC_FROZEN_JANUS_TINY_TRANSFORMER_004_BORN_TRAINED_NOT_DRAND_TRAINED"
            or not isinstance(p.get("frozen_checkpoint_sha256"), str)
            or not HEX64.fullmatch(p["frozen_checkpoint_sha256"])
            or not isinstance(p.get("frozen_training_report_sha256"), str)
            or not HEX64.fullmatch(p["frozen_training_report_sha256"])):
        raise ValueError("MODEL_LINEAGE_NOT_FROZEN")
    prior = p.get("latest_bls_verified_round_at_preparation")
    if type(prior) is not int or not 0 < prior < rounds[0]:
        raise ValueError("EARLY_PRIOR_NOT_PRE_TARGET")
    probabilities = p.get("probability_1")
    bits = p.get("bits")
    if (not isinstance(probabilities, list) or len(probabilities) != N
            or not isinstance(bits, list) or len(bits) != N
            or any(type(x) not in (int, float) or not math.isfinite(x) or not 0 <= x <= 1
                   for x in probabilities)
            or bits != ["1" if x >= 0.5 else "0" for x in probabilities]):
        raise ValueError("PREDICTION_BIT_OR_PROBABILITY_MISMATCH")
    # Self-reported time is NOT an independent GitHub timestamp.
    claimed = p.get("timestamp_self_reported")
    if not isinstance(claimed, str):
        raise ValueError("MISSING_SELF_REPORTED_TIME")
    try:
        claimed_time = datetime.fromisoformat(claimed.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("INVALID_SELF_REPORTED_TIME") from exc
    if claimed_time.tzinfo is None or claimed_time.utcoffset().total_seconds() != 0:
        raise ValueError("SELF_REPORTED_TIME_NOT_UTC")
    if claimed_time.timestamp() >= release(rounds[0]) - 60:
        raise ValueError("LATE_PRECOMMIT_SELF_TIME")
    witnessed = False
    if github_created_at is not None:
        t = utc(github_created_at)
        if t.timestamp() >= release(rounds[0]) - 60:
            raise ValueError("GITHUB_WITNESS_TOO_LATE")
        witnessed = True  # still supplied by caller; verify with GitHub API in workflow
    return {"target_date": str(target), "precommit_sha256": wrapper["sha256"],
            "first_release_unix": release(rounds[0]),
            "last_release_unix": release(rounds[-1]),
            "witness_timestamp_supplied": witnessed,
            "github_created_at": github_created_at,
            "mean_model_probability": round(sum(probabilities) / N, 8),
            "probabilities": probabilities, "bits": bits, "rounds": rounds}


def independently_recompute_late(early, assessment, signed_beacons=None):
    if assessment is None:
        return {"status": "PENDING_FUTURE_OUTCOMES", "scored": False}
    p = early
    a = assessment
    if not p["witness_timestamp_supplied"]:
        raise ValueError("LATE_ASSESSMENT_NEEDS_EXTERNAL_PRECOMMIT_WITNESS")
    if (not isinstance(a, dict) or a.get("schema") != SCHEMA
            or a.get("lane") != "OPEN-FUTURE-009B"
            or a.get("status") != "ALL_SIGNED_INDEPENDENT_DRAND_ROUNDS_SCORED"
            or a.get("precommitted_sha256") != p["precommit_sha256"]
            or a.get("target_date") != p["target_date"]
            or a.get("n_distinct_rounds") != N
            or a.get("time_separation_externally_timestamped") is not True
            or a.get("randomness_bls_verified") is not True
            or a.get("no_late_outcomes_filtered") is not True
            or a.get("real_physical_early_receiver") is not False
            or a.get("retrocausality_proven") is not False
            or a.get("github_server_artifact_timestamp") != p["github_created_at"]):
        raise ValueError("LATE_OCEAN_CLAIM_OR_LINEAGE_REJECTED")
    if (type(a.get("matches")) is not int or not 0 <= a["matches"] <= N
            or type(a.get("accuracy")) not in (float, int)
            or abs(a["accuracy"] - a["matches"] / N) > 0.00000002
            or type(a.get("brier")) not in (float, int)
            or not math.isfinite(a["brier"]) or not 0 <= a["brier"] <= 1
            or a.get("fair_baseline_brier") != 0.25
            or a.get("better_brier_than_fair") is not (a["brier"] < 0.25)):
        raise ValueError("LATE_METRIC_INTEGRITY_REJECTED")
    if (type(a.get("exact_two_sided_binomial_p")) not in (int, float)
            or not math.isfinite(a["exact_two_sided_binomial_p"])
            or not 0 <= a["exact_two_sided_binomial_p"] <= 1):
        raise ValueError("INVALID_EXACT_BINOMIAL_P")
    small = min(a["matches"], N - a["matches"])
    computed_p = min(1.0, 2 * sum(math.comb(N, k) for k in range(small + 1)) / (2 ** N))
    if abs(a["exact_two_sided_binomial_p"] - computed_p) > 1e-10:
        raise ValueError("LATE_BINOMIAL_P_DISAGREES")
    if signed_beacons is None:
        return {"status": "UPSTREAM_REPORT_ONLY_NO_INDEPENDENT_RECALC", "scored": True,
                "measured_matches_reported": a["matches"],
                "brier_reported": a["brier"], "labels_recomputed": False}
    b = signed_beacons
    if not isinstance(b, dict):
        raise ValueError("SIGNED_BEACON_OBJECT_REQUIRED")
    rows = b.get("beacons")
    if a.get("beacon_receipt_sha256") != digest(b):
        raise ValueError("LATE_SIGNED_BEACON_RECEIPT_CHANGED")
    if (b.get("target_rounds") != p["rounds"] or b.get("chain_hash") != CHAIN
            or b.get("signature_verification") != "DRAND_CLIENT_BLS_PINNED"
            or b.get("verifier_package") != "drand-client@1.4.2"
            or not isinstance(rows, list) or len(rows) != N):
        raise ValueError("INCOMPLETE_OR_UNVERIFIED_SIGNED_BEACONS")
    labels = []
    for rnd, row in zip(p["rounds"], rows):
        if (not isinstance(row, dict) or row.get("round") != rnd
                or row.get("signature_verified_by_pinned_client") is not True):
            raise ValueError("MISSING_OR_WRONG_SIGNED_ROUND")
        sig = row.get("signature")
        try:
            raw = bytes.fromhex(sig)
        except (TypeError, ValueError) as exc:
            raise ValueError("INVALID_SIGNATURE_ENCODING") from exc
        if len(raw) != 96 or hashlib.sha256(raw).hexdigest() != row.get("randomness"):
            raise ValueError("SIGNATURE_RANDOMNESS_HASH_MISMATCH")
        labels.append(int(row["randomness"][0], 16) >> 3)
    hits = sum(int(bit) == label for bit, label in zip(p["bits"], labels))
    brier = sum((prob - label) ** 2 for prob, label in zip(p["probabilities"], labels)) / N
    if hits != a["matches"] or abs(brier - a["brier"]) > 0.00000002:
        raise ValueError("LATE_INDEPENDENT_ARITHMETIC_DISAGREES")
    return {"status": "SIGNATURE_DIGESTS_AND_SCORE_RECOMPUTED", "scored": True,
            "measured_matches": hits, "brier": round(brier, 8),
            "fair_baseline_brier": 0.25,
            "labels_recomputed": True,
            "bls_pairing_reverified_here": False,
            "upstream_bls_verification_reported": True,
            "retrocausality_proven": False}


def bridge(early_wrapper, *, ocean_commit, github_created_at=None,
           late_assessment=None, signed_beacons=None, topa_router=None):
    if not isinstance(ocean_commit, str) or not HEX40.fullmatch(ocean_commit):
        raise ValueError("PINNED_OCEAN_COMMIT_REQUIRED")
    e = validate_early(early_wrapper, github_created_at)
    late = independently_recompute_late(e, late_assessment, signed_beacons)
    from .research_bridge import make_topa_claim, canonical_topa_assessment
    statement = ("JANUS Ocean 009B precommits 128 predictions from public round metadata; "
                 "Tachyon proposes testing whether any observed advantage remains "
                 "after independent controls for randomness, selection and time provenance.")
    envelope = make_topa_claim(
        claim_id="TACHYON-OCEAN-009B-" + e["target_date"].replace("-", ""),
        statement=statement,
        source_urls=["https://github.com/Hawkar-usls/Janus-Demiurge/blob/" + ocean_commit
                     + "/experiments/ocean_transformer/open_causality_009/future_009b.py"],
        alternative="Ordinary chance variation or selection effects; no physical backwards channel",
        falsifier="Freeze all target rounds, prove external early timestamp, verify all BLS signatures and compare Brier/p-values against chance across all eight prespecified dates")
    topa = {"envelope": envelope, "provider_admission": "NOT_EXECUTED"}
    if topa_router is not None:
        topa["assessment"] = canonical_topa_assessment(envelope, Path(topa_router))
        topa["provider_admission"] = "HYPOTHESIS_ONLY_ACCEPTED"
    result = {
        "schema": OUTPUT_SCHEMA,
        "role": "TACHYON_TIME_AND_CAUSALITY_SHADOW_AUDITOR",
        "ocean_source": {"repository": "Hawkar-usls/Janus-Demiurge",
                         "commit": ocean_commit,
                         "model": "JanusTinyTransformer", "lane": "OPEN-FUTURE-009B"},
        "early": {k: v for k, v in e.items() if k not in ("probabilities", "bits", "rounds")},
        "late": late,
        "tachyon": {"model_version": "v0.3",
                    "semantic_classifier_used_for_truth": False,
                    "semantic_generalization_gate": "HOLD_NO_TEXT_GENERALIZATION_GAIN",
                    "numeric_lorentz_head_used_on_drand": False,
                    "reason": "drand round identifiers have no spacetime q,beta features",
                    "learned_training_signal": False},
        "topa": topa,
        "feedback": {"schema": FEEDBACK_SCHEMA, "consumer": "JANUS_OCEAN_RESEARCH_ONLY",
                     "candidate_questions": ["Is an apparent gain above the fair-coin baseline reproducible across all frozen target dates?",
                                             "Does independent timestamp verification withstand an adversarial audit?"],
                     "eligible_as_gradient_label": False,
                     "may_revise_frozen_early_forecast": False,
                     "may_trigger_automatic_training": False,
                     "authority_delta": 0},
        "postselection_allowed": False,
        "independent_external_timestamp_verified_by_this_program": False,
        "physical_retrocausality_established": False,
        "automatic_deployment": False,
        "authority_delta": 0,
    }
    result["receipt_sha256"] = digest(result)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--precommit", type=Path, required=True)
    ap.add_argument("--ocean-commit", required=True)
    ap.add_argument("--github-created-at")
    ap.add_argument("--late", type=Path)
    ap.add_argument("--beacons", type=Path)
    ap.add_argument("--topa-router", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    if a.beacons and not a.late:
        ap.error("beacons require scored assessment")
    early, _ = load(a.precommit)
    late = load(a.late)[0] if a.late else None
    beacons = load(a.beacons)[0] if a.beacons else None
    record = bridge(early, ocean_commit=a.ocean_commit,
                    github_created_at=a.github_created_at,
                    late_assessment=late, signed_beacons=beacons,
                    topa_router=a.topa_router)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    with a.output.open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False)
        f.write("\n")
    print(json.dumps({"status": record["late"]["status"],
                      "receipt_sha256": record["receipt_sha256"],
                      "auto_deployed": False}, sort_keys=True))


if __name__ == "__main__":
    main()
