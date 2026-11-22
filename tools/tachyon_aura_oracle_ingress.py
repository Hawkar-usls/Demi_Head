#!/usr/bin/env python3
"""TACHYON -> AURA -> TACHYON closed-loop research receipt ingress.

This consumes a fixed AURA advisory generated from the validated RETROBOUND R1
synthetic summary. It does NOT alter TACHYON's existing tools, model weights,
CI scientific gates, production runtime or physical experiment scheduling.
The AURA packet SHA256 is a content fingerprint, NOT a digital signature and
NOT independently authenticated evidence of physical future information.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

AURA_SCHEMA = "janus.aura.tachyon.retrobound_r1.advisory.v1"
INGRESS_SCHEMA = "janus.demihead.tachyon.aura_advisory_ingress.v1"
RECEIVED_PACKET_DIGEST = "f52e09096c07ea3a4e1fb0f98a5f19f5b1b6d366792c79fcfc0046c62103e20e"
EXPECTED_SOURCE_COMMIT = "a6f84e3707828f59946be3848e0bc128d9e2b8cc"
EXPECTED_SOURCE_GIT_BLOB = "44f422bd450e1a29d4927235502868c49955002c"
EXPECTED_SOURCE_RAW_SHA256 = "5c5b2496d8240e7c01cc532c2548d3d70703b6a6f1c51a5f148891a1ef7704e7"
MAX_SOURCE_BYTES = 64000
FORBIDDEN_TRUE_FIELDS = (
    "may_assign_world_forecast_probability",
    "may_autoseal_or_publish_forecast",
    "may_change_tachyon_weights",
    "may_override_DemiHead_gate",
    "may_promote_production",
    "may_resolve_own_forecast",
    "may_submit_physical_experiment",
    "may_train_predictive_head",
    "external_effect_authorized",
)
EXPECTED_HYPOTHESES = frozenset({
    "H_CAUSAL_NULL", "H_FORWARD_POSTSELECTION", "H_RETROCAUSAL_PHYSICAL", "H_LEAKAGE_OR_SELECTION"
})


def canonical(obj: object) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(obj: object) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def load_packet(path: Path) -> dict:
    raw = path.read_bytes()
    if not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise ValueError("AURA_PACKET_SIZE_REJECT")
    obj = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(obj, dict):
        raise ValueError("AURA_PACKET_MUST_BE_OBJECT")
    return obj


def validate_packet(packet: dict) -> None:
    if not isinstance(packet, dict) or packet.get("schema") != AURA_SCHEMA or packet.get("mode") != "OFFLINE_READ_ONLY_ADVISORY":
        raise ValueError("AURA_ADVISORY_SCHEMA_OR_MODE_REJECT")
    if packet.get("peer") != "AURA_ORACLE__HYPOTHESIS_DISCRIMINATION":
        raise ValueError("AURA_PEER_MISMATCH")
    claimed = packet.get("packet_digest_sha256")
    if claimed != RECEIVED_PACKET_DIGEST:
        raise ValueError("UNRECOGNIZED_AURA_PACKET_DIGEST")
    signed = dict(packet)
    signed.pop("packet_digest_sha256", None)
    if digest(signed) != claimed:
        raise ValueError("AURA_PACKET_CONTENT_TAMPERING")
    source = packet.get("source")
    if not isinstance(source, dict) or (
        source.get("repository"), source.get("commit_sha"), source.get("git_blob_sha1"),
        source.get("raw_sha256"), source.get("external_physical_witness")
    ) != (
        "Hawkar-usls/Demi_Head", EXPECTED_SOURCE_COMMIT,
        EXPECTED_SOURCE_GIT_BLOB, EXPECTED_SOURCE_RAW_SHA256, False
    ):
        raise ValueError("UNPINNED_TACHYON_SOURCE_OR_FAKE_EXTERNAL_WITNESS")
    if source.get("path") != "research/tachyon/retrobound_r1_validation_result_20261123.json":
        raise ValueError("UNEXPECTED_RESEARCH_INPUT")
    meta = packet.get("five_axis_spiral")
    if not isinstance(meta, dict) or meta.get("real_physical_spacetime_dimensions_measured") is not False or meta.get("origin_prime_claim") is not False:
        raise ValueError("MISLEADING_5D_OR_STATE_ASCENT")
    if meta.get("D5_EVIDENCE_ASCENT") != "PLATEAU_NO_NEW_PHYSICAL_IDENTIFIABILITY":
        raise ValueError("FALSE_EVIDENCE_ASCENT")
    governance = packet.get("governance")
    if not isinstance(governance, dict) or governance.get("scientific_verdict") != "R1_SYNTHETIC_VALIDATION_PASS__PHYSICAL_RETROCAUSALITY_HOLD":
        raise ValueError("MISSING_TACHYON_PHYSICAL_HOLD")
    if any(governance.get(k) is not False for k in FORBIDDEN_TRUE_FIELDS):
        raise ValueError("ADVISORY_ATTEMPTED_TO_GAIN_AUTHORITY")
    hypotheses = packet.get("hypotheses")
    if not isinstance(hypotheses, list) or len(hypotheses) != 4 or set(h.get("id") for h in hypotheses if isinstance(h, dict)) != EXPECTED_HYPOTHESES:
        raise ValueError("HYPOTHESES_MISSING_OR_RELABELED")
    if any(not isinstance(h, dict) or h.get("physical_truth_probability") is not None for h in hypotheses):
        raise ValueError("AURA_CANNOT_ASSIGN_PHYSICAL_FORECAST_PROBABILITY")
    question = packet.get("hypothesis_discrimination")
    if not isinstance(question, dict) or (
        question.get("question_id") != "R2_FREEZE_BEFORE_LATE_ENTROPY"
        or question.get("R1_identifiability") != "TWO_BOUNDARY_VS_POSTSELECTION_NOT_IDENTIFIABLE"
        or question.get("calibrated_forecast_probability") is not None
    ):
        raise ValueError("NO_REAL_DISTINGUISHABILITY_CLAIM_ALLOWED")
    controls = question.get("prospective_controls")
    required = {"SPECIFY_PHYSICAL_READOUT_PREDICTION_DIFFERENT_FROM_FORWARD_POSTSELECTION",
                "INDEPENDENTLY_FREEZE_AND_TIMESTAMP_EARLY_READOUT_BEFORE_LATE_CHOICE",
                "GENUINELY_LATE_INDEPENDENT_PHYSICAL_ENTROPY",
                "APPEND_ONLY_ALL_TRIALS_LEDGER_INCLUDE_ABORTS",
                "PRECOMMITTED_FORWARD_AND_LEAKAGE_NULLS_WITH_MULTIPLICITY",
                "INDEPENDENT_BLINDED_EXTERNAL_CUSTODIAN"}
    if not isinstance(controls, list) or set(controls) != required:
        raise ValueError("R2_REQUIRED_CONTROLS_NOT_PRESERVED")
    metrics = packet.get("evidence_metrics")
    if not isinstance(metrics, dict) or metrics.get("physical_signal_evidence") is not False or metrics.get("real_future_forecast_skill_established") is not False:
        raise ValueError("AURA_FORECAST_PROMOTION_REJECT")
    default = metrics.get("reference_default")
    if not isinstance(default, dict):
        raise ValueError("MISSING_NUMERIC_REFERENCE")
    if default.get("n") != 40000 or default.get("steps") != 8:
        raise ValueError("REFERENCE_CONTRACT_CHANGED")
    if not math.isclose(float(default.get("theory")), 0.9 * (0.85 ** 8), abs_tol=1e-10):
        raise ValueError("BOUNDARY_THEORY_MISMATCH")


def ingest_advisory(packet: dict) -> dict:
    validate_packet(packet)
    req = packet["hypothesis_discrimination"]
    return {
        "schema": INGRESS_SCHEMA,
        "status": "AURA_TACHYON_R1_READONLY_PEER_ACCEPTED__SCIENTIFIC_HOLD",
        "aura_packet_sha256": packet["packet_digest_sha256"],
        "source_tachyon_commit": EXPECTED_SOURCE_COMMIT,
        "source_tachyon_blob": EXPECTED_SOURCE_GIT_BLOB,
        "received_discrimination_question": {
            "id": req["question_id"],
            "question": req["question"],
            "controls": list(req["prospective_controls"]),
            "priority_is_empirical_probability": False,
            "eligible_for_R2_design_review": True,
            "eligible_for_autonomous_experiment": False,
        },
        "hypothesis_ids": sorted(EXPECTED_HYPOTHESES),
        "epistemic_status": "R1_CLASSICAL_CONDITIONAL_PATHS_NOT_PHYSICAL_RETROCAUSAL_EVIDENCE",
        "verified_packet_identity_is_external_physics": False,
        "evidence_state_upgrade": False,
        "physical_retrocausality": "NOT_ESTABLISHED",
        "model_weights_changed": False,
        "production_activated": False,
        "automated_future_random_choice": False,
        "forecast_resolved_by_aura": False,
        "new_simulations_run": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description="TACHYON read-only admission of source-bound AURA R1 advisory")
    p.add_argument("--input", required=True, type=Path)
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    try:
        packet = load_packet(args.input)
        result = ingest_advisory(packet)
        raw = json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(raw, encoding="utf-8")
        else:
            sys.stdout.write(raw)
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("TACHYON_AURA_PACKET_HOLD:" + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
