"""Read-only Proof-of-Observation/AIFC eligibility audit for frozen Ocean 009B.

The output is NOT full AIFC verification or an experimental retrocausality result.
"""
from __future__ import annotations
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re

IO_REPO = "Hawkar-usls/janus-io-public"
AIFC_REPO = "Hawkar-usls/AIFC"
EARLY_RUN = 42878578752
EARLY_ARTIFACT = 13793425503
HEX = re.compile(r"^[0-9a-f]{64}$")
MISSING_AIFC = [
    "certified_trial_created_before_candidate",
    "complete_global_trial_ledger_and_visible_aborts",
    "external_witness_quorum_and_key_lifecycle",
    "complete_pre_target_conditioning_view",
    "historywise_entropy_bound_with_evidence",
    "candidate_multiplicity_and_selection_audit",
    "target_derivation_and_d_separation",
    "independent_full_aifc_verifier_admission",
]

def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def read_obj(path):
    raw = Path(path).read_bytes()
    if len(raw) > 150000:
        raise ValueError("INPUT_TOO_LARGE")
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError("OBJECT_REQUIRED")
    return obj, raw

def check_policy(io, aifc):
    if (io.get("schema") != "JANUS/proof-of-observation-origin-record/v1"
            or io.get("repository") != IO_REPO
            or io.get("claim_level") != "telemetry_and_methodology_only"):
        raise ValueError("IO_POLICY_IDENTITY_CHANGED")
    layers = {"facts", "derived_metrics", "claims", "source_provenance",
              "deterministic_integrity", "uncertainty", "comparability",
              "independent_repetition", "holdout_discipline", "fail_closed_claims"}
    if not layers.issubset(set(io.get("required_layers", []))):
        raise ValueError("IO_REQUIRED_LAYERS_MISSING")
    if "Unknown is not zero." not in io.get("canonical_principles", []):
        raise ValueError("IO_UNKNOWN_NOT_ZERO_MISSING")
    for grade in ["NOT_ADMITTED", "STRUCTURAL_MATCH_ONLY", "FORWARD_NULL_COMPATIBLE",
                  "FORWARD_NULL_INCOMPATIBILITY_CANDIDATE"]:
        if grade not in aifc:
            raise ValueError("AIFC_GRADES_CHANGED")

def check_witness(w):
    if w.get("schema") != "janus.tachyon.ocean_009b.real_early_witness.v1":
        raise ValueError("WRAPPER_SCHEMA_CHANGED")
    review = w.get("tachyon_shadow_review")
    if not isinstance(review, dict) or review.get("schema") != "janus.tachyon.ocean_shadow_bridge.v1":
        raise ValueError("REVIEW_MISSING")
    body = dict(review)
    receipt = body.pop("receipt_sha256", None)
    if not isinstance(receipt, str) or not HEX.fullmatch(receipt) or sha(canonical(body)) != receipt:
        raise ValueError("REVIEW_HASH_INVALID")
    if (w.get("source_workflow_run_id") != EARLY_RUN
            or w.get("github_artifact_id") != EARLY_ARTIFACT
            or w.get("source_repository") != "Hawkar-usls/Janus-Demiurge"
            or w.get("source_workflow_conclusion") != "success"
            or w.get("n_distinct_future_rounds") != 128
            or w.get("precommit_target_date_utc") != "2026-11-12"
            or w.get("github_artifact_server_digest_matches_download") is not True):
        raise ValueError("ORIGINAL_OCEAN_WITNESS_IDENTITY_CHANGED")
    early = review.get("early", {})
    limits = w.get("limits", {})
    feedback = review.get("feedback", {})
    topa = review.get("topa", {})
    if (early.get("target_date") != "2026-11-12"
            or early.get("precommit_sha256") != w.get("ocean_canonical_precommit_sha256")
            or early.get("github_created_at") != w.get("github_artifact_created_at_utc")
            or early.get("witness_timestamp_supplied") is not True
            or limits.get("future_target_outcomes_known") is not False
            or limits.get("late_scoring_executed") is not False
            or limits.get("physical_retrocausality_proven") is not False
            or review.get("physical_retrocausality_established") is not False
            or review.get("automatic_deployment") is not False
            or review.get("authority_delta") != 0
            or feedback.get("eligible_as_gradient_label") is not False
            or topa.get("envelope", {}).get("status") != "HYPOTHESIS_ONLY"):
        raise ValueError("UNFROZEN_OUTCOME_OR_AUTHORITY_ESCALATION")
    if (not isinstance(w.get("github_artifact_zip_sha256"), str)
            or not HEX.fullmatch(w["github_artifact_zip_sha256"])):
        raise ValueError("ARTIFACT_DIGEST_INVALID")
    published = datetime.fromisoformat(early["github_created_at"].replace("Z", "+00:00"))
    if published.timestamp() >= early["first_release_unix"] - 60:
        raise ValueError("WITNESS_AFTER_TARGET")
    return receipt

def check_live(w, run, listing):
    if not isinstance(run, dict) or not isinstance(listing, dict):
        raise ValueError("LIVE_GITHUB_PAIR_REQUIRED")
    if (run.get("id") != EARLY_RUN or run.get("conclusion") != "success"
            or run.get("name") != "JANUS Ocean / 009B Future drand 128bit Early"
            or run.get("path") != ".github/workflows/janus-ocean-open-future-009b-precommit.yml"
            or run.get("head_sha") != w.get("original_source_commit")):
        raise ValueError("LIVE_RUN_SOURCE_MISMATCH")
    matches = [a for a in listing.get("artifacts", []) if
               a.get("id") == EARLY_ARTIFACT
               and a.get("name") == "janus-open-future-009b-2026-11-12"
               and a.get("expired") is False
               and a.get("workflow_run", {}).get("id") == EARLY_RUN]
    if len(matches) != 1:
        raise ValueError("LIVE_ARTIFACT_UNIQUE_REQUIRED")
    art = matches[0]
    if (art.get("created_at") != w.get("github_artifact_created_at_utc")
            or art.get("digest") != "sha256:" + w.get("github_artifact_zip_sha256")):
        raise ValueError("LIVE_ARTIFACT_HASH_OR_TIME_MISMATCH")
    return True

def assess(w, io, io_raw, aifc_text, aifc_raw, run=None, listing=None):
    check_policy(io, aifc_text)
    receipt = check_witness(w)
    live = run is not None or listing is not None
    if live:
        check_live(w, run, listing)
    result = {
        "schema": "janus.tachyon.io_aifc_observation_gate.v1",
        "input": {"ocean_run_id": EARLY_RUN, "ocean_artifact_id": EARLY_ARTIFACT,
                  "tachyon_review_sha256": receipt,
                  "frozen_precommit_sha256": w["ocean_canonical_precommit_sha256"]},
        "proof_of_observation": {
            "source_repo": IO_REPO, "source_sha256": sha(io_raw),
            "status": "OBSERVATION_ONLY_PARTIAL_CHAIN",
            "live_github_artifact_binding_pass": live,
            "independent_source_truth_verified": False,
            "full_independent_observation_chain": False,
            "future_outcomes_not_available_to_this_audit": True},
        "aifc": {"source_repo": AIFC_REPO, "grades_source_sha256": sha(aifc_raw),
                 "scope": "ELIGIBILITY_SCREEN_NOT_FULL_AIFC_VERIFIER",
                 "grade": "NOT_ADMITTED",
                 "missing_or_unverified": MISSING_AIFC,
                 "physical_retrocausality_established": False},
        "topa": {"claim_status": "HYPOTHESIS_ONLY", "promoted": False},
        "weights_changed": False,
        "eligible_as_gradient_label": False,
        "authority_delta": 0}
    result["receipt_sha256"] = sha(canonical(result))
    return result

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--witness",required=True)
    p.add_argument("--io-origin",required=True)
    p.add_argument("--aifc-grades",required=True)
    p.add_argument("--live-run")
    p.add_argument("--live-artifacts")
    p.add_argument("--out",required=True)
    a=p.parse_args()
    w,_=read_obj(a.witness)
    io,ioraw=read_obj(a.io_origin)
    grades=Path(a.aifc_grades).read_bytes()
    if len(grades)>150000:
        raise ValueError("AIFC_GRADES_OVERSIZED")
    run=read_obj(a.live_run)[0] if a.live_run else None
    listing=read_obj(a.live_artifacts)[0] if a.live_artifacts else None
    result=assess(w,io,ioraw,grades.decode("utf8"),grades,run,listing)
    dst=Path(a.out)
    dst.parent.mkdir(parents=True,exist_ok=True)
    with dst.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,sort_keys=True,ensure_ascii=False)
        f.write("\n")
    print(json.dumps({"gate":result["proof_of_observation"]["status"],
                      "aifc_grade":result["aifc"]["grade"],
                      "receipt_sha256":result["receipt_sha256"]}))
if __name__=="__main__":
    main()
