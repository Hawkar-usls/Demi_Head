"""DemiHead × TACHYON R5: paired, research-only synthetic capability ablation.

This imports the REAL current DemiHead KETO reference head and, when enabled,
deterministically replays the pinned Simptomat R4 source as an isolated sidecar.
It is NOT a production integration and CANNOT measure general intelligence.
Three arms: original DemiHead (no temporal classifier), a simple transparent
rule sidecar, and a TACHYON trained sidecar. No clinical, human or live data.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import random
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter_ns

from tools.keto_reference import summarize_case

LABELS = (
    "AMBIGUOUS_REFERENCE", "CONTINUING_EVENT", "DISTINCT_CONTENT",
    "FUTURE_PLAN", "MEMORY_OF_EVENT", "OBSERVED_REPEAT", "SAME_EVENT",
)
SOURCE_REPOSITORY = "Hawkar-usls/Simptomat"
SOURCE_COMMIT = "5c1daed7f728d671ed2139b3448bd612ea0a4f58"
SOURCE_PATH = "tools/temporal_recurrence_r4_train.py"
SEED = 20261122 + 5
HOLD = "HOLD_NO_INDEPENDENT_REAL_WORLD_DEMIHEAD_GAIN_EVIDENCE"

def _dt(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("R5 requires timezone-aware datetimes")
    return value.astimezone(timezone.utc)

def make_case(family: int, target: str) -> dict:
    """Independent synthetic authoring, NOT Simptomat generate_case()."""
    if type(family) is not int or not 0 <= family < 32 or target not in LABELS:
        raise ValueError("unknown frozen synthetic case")
    rng = random.Random(SEED + family * 10007 + LABELS.index(target)*131)
    start = datetime(2026, 7, 1, 12, tzinfo=timezone.utc) + timedelta(days=family*3)
    when_a = start - timedelta(days=rng.choice((2, 5, 9)))
    when_b = start - timedelta(days=rng.choice((1, 2, 4)))
    cid = f"fixture-repeated-tone-{family%5}"
    a = f"review-{family}-episode-a"
    b = f"review-{family}-episode-b"
    item = dict(
        family_id=family, event_a_id=a, event_b_id=b,
        content_a=cid, content_b=cid, b_status="OBSERVED",
        event_a_time=when_a, event_b_time=when_b, reference_time=start,
        synthetic_only=True, target=target
    )
    if target == "SAME_EVENT":
        item["event_b_id"] = a
        item["event_b_time"] = when_a
    elif target == "CONTINUING_EVENT":
        item["event_b_id"] = a
        item["b_status"] = "CONTINUATION"
        item["event_b_time"] = when_a + timedelta(days=1)
    elif target == "DISTINCT_CONTENT":
        item["content_b"] = f"other-distinct-tone-{family}"
    elif target == "FUTURE_PLAN":
        item["b_status"] = "PLANNED"
        item["event_b_time"] = start + timedelta(days=rng.choice((1, 2)))
    elif target == "MEMORY_OF_EVENT":
        item["b_status"] = "MEMORY_REFERENCE"
        item["event_b_id"] = a
        item["event_b_time"] = start
    elif target == "AMBIGUOUS_REFERENCE":
        item["b_status"] = "UNCERTAIN"
        item["event_a_id"] = item["event_b_id"] = None
    return item

def negative_cases() -> list[dict]:
    """Predeclared contradictions; the shared provenance guard must abstain."""
    def modified(fam: int, label: str, **overrides) -> dict:
        original = make_case(fam, label)
        return {**original, **overrides, "target": "ABSTAIN_INVALID_PROVENANCE"}
    ref_plan = make_case(1, "FUTURE_PLAN")["reference_time"]
    ref_observed = make_case(2, "OBSERVED_REPEAT")["reference_time"]
    return [
        modified(1, "FUTURE_PLAN", event_b_time=ref_plan-timedelta(days=1)),
        modified(2, "OBSERVED_REPEAT", event_b_time=ref_observed+timedelta(days=1)),
        modified(3, "MEMORY_OF_EVENT", event_b_id="unrelated-episode"),
        modified(4, "CONTINUING_EVENT", event_b_id="unrelated-episode"),
        modified(5, "SAME_EVENT", content_b="impossible-other-content"),
        modified(6, "OBSERVED_REPEAT", event_a_id=None),
    ]

def validate_provenance(item: dict) -> bool:
    """Validator applied symmetrically to both temporal sidecars."""
    if item.get("synthetic_only") is not True:
        return False
    if item.get("b_status") not in {
        "OBSERVED", "PLANNED", "MEMORY_REFERENCE", "CONTINUATION", "UNCERTAIN"
    }:
        return False
    try:
        a = _dt(item["event_a_time"])
        b = _dt(item["event_b_time"])
        ref = _dt(item["reference_time"])
    except (KeyError, ValueError, TypeError):
        return False
    if (item["b_status"] == "PLANNED" and b <= ref) or (
        item["b_status"] == "OBSERVED" and b > ref
    ):
        return False
    if item["b_status"] in {"CONTINUATION", "MEMORY_REFERENCE"} and (
        item.get("event_a_id") is None or item.get("event_a_id") != item.get("event_b_id")
    ):
        return False
    if item["b_status"] == "UNCERTAIN":
        return item.get("event_a_id") is None and item.get("event_b_id") is None
    if item.get("event_a_id") is None or item.get("event_b_id") is None:
        return False
    if (item["event_a_id"] == item["event_b_id"]
            and item["content_a"] != item["content_b"]):
        return False
    if (item["b_status"] == "OBSERVED" and
            item["event_a_id"] == item["event_b_id"] and a != b):
        return False
    return True

def simple_rule(item: dict) -> str:
    """Clearly stated transparent alternative to trained TACHYON."""
    if not validate_provenance(item):
        return "ABSTAIN_INVALID_PROVENANCE"
    kind = item["b_status"]
    if kind == "UNCERTAIN":
        return "AMBIGUOUS_REFERENCE"
    if kind == "PLANNED":
        return "FUTURE_PLAN"
    if kind == "CONTINUATION":
        return "CONTINUING_EVENT"
    if kind == "MEMORY_REFERENCE":
        return "MEMORY_OF_EVENT"
    if item["content_a"] != item["content_b"]:
        return "DISTINCT_CONTENT"
    if item["event_a_id"] == item["event_b_id"]:
        return "SAME_EVENT"
    return "OBSERVED_REPEAT"

def import_pinned_r4(upstream: Path):
    file = upstream / SOURCE_PATH
    if not file.is_file():
        raise FileNotFoundError("Pinned Simptomat R4 source not checked out")
    spec = importlib.util.spec_from_file_location("pinned_simptomat_tachyon_r4", file)
    if spec is None or spec.loader is None:
        raise RuntimeError("Simptomat R4 source unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if tuple(module.CLASSES) != LABELS or module.ROOT_SEED != 20261122:
        raise ValueError("Pinned R4 contract mismatch")
    return module

def real_demihead(case: dict) -> dict:
    """Use actual unmodified DemiHead main reference, not mock predictions."""
    f = case["family_id"]
    bundle = {
        "schema": "janus.demihead.keto_case.v1",
        "case_id": f"R5-DEV-{f}-{case['target']}",
        "claim": "Check event-time relation only where independent sources permit",
        "presentations": [
            {
                "presentation_id": f"presentation-{f}",
                "root_id": f"source-{f}",
                "relation": "context_only",
                "freshness": "current",
                "source_class": "synthetic",
                "independence": "unknown",
            }
        ],
    }
    return summarize_case(bundle)

def pairs() -> list[dict]:
    cases = [make_case(f, lab) for f in range(32) for lab in LABELS]
    cases += negative_cases()
    random.Random(SEED).shuffle(cases)
    return cases

def _hash_casebank(cases: list[dict]) -> str:
    def conv(v):
        if isinstance(v, datetime):
            return v.astimezone(timezone.utc).isoformat()
        if isinstance(v, dict):
            return {k: conv(x) for k, x in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    payload=json.dumps(conv(cases),sort_keys=True,separators=(",",":"),ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()

def benchmark(upstream: Path) -> dict:
    """Perform same-head A/B/C benchmark with explicit coverage and cost."""
    upstream_r4=import_pinned_r4(upstream)
    before=perf_counter_ns()
    replay=upstream_r4.train_and_evaluate()
    training_ns=perf_counter_ns()-before
    if not replay["training_qualified_synthetic"]:
        raise RuntimeError("Original R4 retrain did not qualify")
    weights=replay["weights"]
    tasks=pairs()
    samples={a:[] for a in ("A_UNMODIFIED", "B_TACHYON", "C_SIMPLE_RULE")}
    labels={a:[] for a in ("B_TACHYON", "C_SIMPLE_RULE")}
    same_heads=0
    for task in tasks:
        actual=task["target"]
        # Interleave arm order cyclically to reduce run-order artifacts. Each
        # call runs exact DemiHead reference; all inputs are identical.
        arm_order=("A_UNMODIFIED","C_SIMPLE_RULE","B_TACHYON")
        outputs={}
        for arm in arm_order:
            begin=perf_counter_ns()
            head=real_demihead(task)
            if arm=="A_UNMODIFIED":
                prediction=None  # No temporal output exists in main DemiHead.
            elif arm=="C_SIMPLE_RULE":
                prediction=simple_rule(task)
            elif not validate_provenance(task):
                prediction="ABSTAIN_INVALID_PROVENANCE"
            else:
                prediction=LABELS[upstream_r4._predict(weights,upstream_r4.features(task))]
            duration=perf_counter_ns()-begin
            samples[arm].append(duration)
            outputs[arm]=(head,prediction)
        same_heads+=int(outputs["A_UNMODIFIED"][0]==outputs["B_TACHYON"][0]==outputs["C_SIMPLE_RULE"][0])
        for arm in ("B_TACHYON","C_SIMPLE_RULE"):
            labels[arm].append((actual, outputs[arm][1]))

    valid_count=sum(t["target"]!="ABSTAIN_INVALID_PROVENANCE" for t in tasks)
    test_totals={}
    for arm in ("B_TACHYON","C_SIMPLE_RULE"):
        seen=labels[arm]
        correct=sum(t==pred for t,pred in seen if t!="ABSTAIN_INVALID_PROVENANCE")
        unsafe=sum(t=="ABSTAIN_INVALID_PROVENANCE" and pred!="ABSTAIN_INVALID_PROVENANCE"
                   for t,pred in seen)
        test_totals[arm]={
            "valid_correct":correct,
            "valid_total":valid_count,
            "valid_accuracy":round(correct/valid_count,6),
            "invalid_provenance_false_accepts":unsafe,
            "unmatched_valid_examples":[i for i,(t,pred) in enumerate(seen)
                                        if t!="ABSTAIN_INVALID_PROVENANCE" and pred!=t][:30],
        }

    medians={a:round(statistics.median(v)/1e3,3) for a,v in samples.items()}
    advantage=test_totals["B_TACHYON"]["valid_accuracy"]-test_totals["C_SIMPLE_RULE"]["valid_accuracy"]
    return {
        "schema":"janus.demihead.tachyon.r5.paired_reference_ablation.v1",
        "date":"2026-11-22",
        "scope":"DEV_ONLY_SYNTHETIC_PAIRED_REFERENCE_HEAD",
        "baseline_head":"tools.keto_reference.summarize_case from Demi_Head main",
        "TACHYON_source_repository":SOURCE_REPOSITORY,
        "TACHYON_source_commit":SOURCE_COMMIT,
        "weight_provenance":"REPLAY_DETERMINISTIC_FROM_PINNED_R4_CODE__NOT_SIGNED_ORIGINAL_WEIGHTS",
        "R4_replay_self_test_accuracy":replay["heldout_accuracy"],
        "R4_replay_train_cases":replay["train_cases"],
        "R4_replay_train_cost_ms":round(training_ns/1e6,3),
        "challenge_generation":"INDEPENDENT_METHOD_AUTHOR_32_FAMILIES_X_7_CLASSES_PLUS_6_NEGATIVE_CONTROLS",
        "challenge_sha256":_hash_casebank(tasks),
        "challenge_count":len(tasks),
        "valid_case_count":valid_count,
        "invalid_provenance_count":len(tasks)-valid_count,
        "unchanged_head_outcomes":same_heads,
        "all_head_outcomes_preserved":same_heads==len(tasks),
        "head_temporal_classification_supported_in_A":False,
        "head_A_cannot_be_scored_as_general_intelligence_accuracy":True,
        "comparisons":test_totals,
        "B_minus_C_accuracy_points":round(100*advantage,3),
        "paired_median_total_per_case_microseconds":medians,
        "cost_warning":"CI-runner exploratory timing only; B replays model training once (reported separately). Not reliable product latency.",
        "adoption_recommendation":"HOLD_NO_AUTOMATIC_ADOPTION",
        "scientific_gate":HOLD,
        "true_independent_blind_test":False,
        "trained_model_replaces_demihead":False,
        "human_memory_or_consciousness_validated":False,
        "physical_timelessness_proven":False,
        "clinical_data_used":False,
        "core_weights_changed":False,
        "network_or_publication_effect":False,
        "general_intelligence_gain_claim":"NOT_ESTABLISHED",
    }

def main():
    parser=argparse.ArgumentParser(description="DemiHead R5 synthetic paired ablation")
    parser.add_argument("--audit",action="store_true")
    parser.add_argument("--simptomat-root",type=Path,default=None)
    args=parser.parse_args()
    if not args.audit or args.simptomat_root is None:
        parser.error("--audit --simptomat-root <pinned checkout> required")
    result=benchmark(args.simptomat_root)
    print(json.dumps(result,sort_keys=True,indent=2))
    if not result["all_head_outcomes_preserved"]:
        raise SystemExit("DemiHead reference outputs changed across arms")
    if any(v["invalid_provenance_false_accepts"]
           for v in result["comparisons"].values()):
        raise SystemExit("Invalid temporal provenance was accepted")

if __name__=="__main__":
    main()
