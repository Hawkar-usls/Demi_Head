"""TACHYON × DemiHead R5C: observation-native, synthetic-only learned witness inference.

Explicit epistemic boundary:
* Development and validation families do not overlap heldout families.
* R5B source code is the frozen strong rule baseline, not a source of labels.
* Inputs contain witness reports, never event_id/b_status/target/scenario.
* A validation-only confidence threshold permits refusal; zero validation
  false assertions cannot certify safe real-world generalization.
* This experiment is NOT an independent external blind exam.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import statistics
from collections import Counter
from datetime import datetime, timezone
from time import perf_counter_ns

from tools.tachyon_r5b_witness_audit import (
    ABSTAIN, ANSWER, SCENARIOS, build_case, clock_only_baseline,
    original_demihead, witness_rule,
)

SEED = 2026112252
LABELS = tuple(sorted(set(ANSWER.values())))
DEV_FAMILIES = range(500, 580)
VALIDATION_FAMILIES = range(900, 920)
TEST_FAMILIES = range(3000, 3032)
EPOCHS = 36
LR = 0.085
CONFIDENCE_CANDIDATES = (0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98, 0.995, 1.01)
SOURCE_SHA = "5f462b79177ca5fcb86f4e8c14266e0ead3078a8"
HOLD = "HOLD_NO_INDEPENDENT_OBSERVATION_NATIVE_REAL_WORLD_MODEL_GAIN"
FORBIDDEN = {"event_a_id", "event_b_id", "b_status", "gold", "target", "scenario"}
FEATURES = (
    "bias",
    "n_witness_a_scaled", "n_witness_b_scaled",
    "unique_root_a_scaled", "unique_root_b_scaled",
    "unique_source_media_a_scaled", "unique_source_media_b_scaled",
    "fraction_parseable_clock_a", "fraction_parseable_clock_b",
    "time_spread_hours_a", "time_spread_hours_b",
    "synced_fraction_a", "synced_fraction_b",
    "recording_fraction_a", "recording_fraction_b",
    "schedule_fraction_a", "schedule_fraction_b",
    "signature_known_fraction_a", "signature_known_fraction_b",
    "signature_consistency_a", "signature_consistency_b",
    "content_equal_when_known", "content_distinct_when_known",
    "mean_time_gap_days_signed", "gap_over_12h", "same_time_window",
    "fraction_past_a", "fraction_past_b",
    "fraction_future_a", "fraction_future_b",
    "all_time_missing_a", "all_time_missing_b",
)


def _parse(value):
    if not isinstance(value, str):
        return None
    try:
        value = datetime.fromisoformat(value)
        if value.tzinfo is None or value.utcoffset() is None:
            return None
        return value.astimezone(timezone.utc)
    except ValueError:
        return None


def _slot(rows, name, ref):
    witnesses = [r for r in rows if r.get("slot") == name]
    n = len(witnesses)
    if not n:
        return {"n": 0, "roots": 0, "media": 0, "parse_fraction": 0,
                "spread": 1.0, "synced": 0, "recording": 0, "schedule": 0,
                "sig_known": 0, "sig_consistency": 0, "signature": None,
                "time": None, "past_fraction": 0, "future_fraction": 0,
                "all_missing": 1}
    times = [_parse(x.get("captured_at_utc")) for x in witnesses]
    valid = [t for t in times if t is not None]
    sigs = [w.get("content_signature") for w in witnesses
            if isinstance(w.get("content_signature"), str)]
    mean = (sum(x.timestamp() for x in valid)/len(valid)) if valid else None
    return {
        "n": n,
        "roots": len({w.get("root") for w in witnesses if w.get("root")}),
        "media": len({w.get("source_medium") for w in witnesses if w.get("source_medium")}),
        "parse_fraction": len(valid)/n,
        "spread": min(1.0, (max(valid)-min(valid)).total_seconds()/3600)
                  if valid else 1.0,
        "synced": sum(w.get("clock_quality") == "synchronized" for w in witnesses)/n,
        "recording": sum(w.get("claim_medium") == "recording" for w in witnesses)/n,
        "schedule": sum(w.get("claim_medium") == "schedule_notice" for w in witnesses)/n,
        "sig_known": len(sigs)/n,
        "sig_consistency": float(len(set(sigs)) == 1) if sigs else 0.0,
        "signature": sigs[0] if sigs and len(set(sigs)) == 1 else None,
        "time": mean,
        "past_fraction": sum(t <= ref for t in valid)/n,
        "future_fraction": sum(t > ref for t in valid)/n,
        "all_missing": float(not valid),
    }


def extract_observation_features(inp: dict) -> list[float]:
    """Only aggregate independent visible witness evidence, no strings as IDs."""
    if not isinstance(inp, dict) or inp.get("synthetic_only") is not True:
        raise ValueError("R5C forbids non-synthetic/real inputs")
    if any(name in inp for name in FORBIDDEN):
        raise ValueError("R5C input contains answer-bearing fields")
    ref = _parse(inp.get("reference_time_utc"))
    rows = inp.get("witnesses")
    if ref is None or not isinstance(rows, list):
        raise ValueError("R5C requires visible witness records and reference time")
    a, b = _slot(rows, "a", ref), _slot(rows, "b", ref)
    signed_gap = ((b["time"]-a["time"])/(24*3600)
                  if a["time"] is not None and b["time"] is not None else 0.0)
    same_sig = a["signature"] is not None and b["signature"] is not None
    feats = [
        1.0,
        min(a["n"], 4)/4, min(b["n"], 4)/4,
        min(a["roots"], 4)/4, min(b["roots"], 4)/4,
        min(a["media"], 3)/3, min(b["media"], 3)/3,
        a["parse_fraction"], b["parse_fraction"],
        a["spread"], b["spread"],
        a["synced"], b["synced"],
        a["recording"], b["recording"],
        a["schedule"], b["schedule"],
        a["sig_known"], b["sig_known"],
        a["sig_consistency"], b["sig_consistency"],
        float(same_sig and a["signature"] == b["signature"]),
        float(same_sig and a["signature"] != b["signature"]),
        max(-1.0, min(1.0, signed_gap/7)),
        float(signed_gap > 0.5),
        float(abs(signed_gap) <= 0.5) if a["time"] is not None and b["time"] is not None else 0.0,
        a["past_fraction"], b["past_fraction"],
        a["future_fraction"], b["future_fraction"],
        a["all_missing"], b["all_missing"],
    ]
    if len(feats) != len(FEATURES):
        raise AssertionError("feature contract mismatch")
    return feats


def _softmax(logits):
    maximum = max(logits)
    weights = [math.exp(z-maximum) for z in logits]
    total = sum(weights)
    return [z/total for z in weights]


def _prob(weights, x):
    return _softmax([sum(wi*xi for wi,xi in zip(row,x)) for row in weights])


def _build(families, partition):
    out = []
    for family in families:
        for scenario in SCENARIOS:
            evidence, label = build_case(family, scenario, partition=partition)
            assert not (FORBIDDEN & set(evidence))
            out.append((evidence, label))
    random.Random(SEED + len(out)).shuffle(out)
    return out


def _hash_dataset(rows, *, labels):
    values = rows if labels else [r[0] for r in rows]
    return hashlib.sha256(json.dumps(values, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _train(train):
    weights = [[0.0]*len(FEATURES) for _ in LABELS]
    rng = random.Random(SEED)
    ex = [(extract_observation_features(x), LABELS.index(y)) for x,y in train]
    start = perf_counter_ns()
    for _ in range(EPOCHS):
        order = list(range(len(ex)))
        rng.shuffle(order)
        for i in order:
            x, truth = ex[i]
            probs = _prob(weights,x)
            for c, row in enumerate(weights):
                delta = (float(truth == c) - probs[c])*LR
                for k in range(len(x)):
                    row[k] += delta*x[k]
    return weights, (perf_counter_ns()-start)/1e6


def _predict(weights, inp, threshold):
    x = extract_observation_features(inp)
    probabilities = _prob(weights,x)
    choice = max(range(len(probabilities)),key=probabilities.__getitem__)
    label = LABELS[choice]
    if probabilities[choice] < threshold:
        return ABSTAIN
    return label


def _measure(rows, predict, *, latency=True):
    count = Counter()
    errors = []
    elapsed = []
    for evidence,gold in rows:
        start = perf_counter_ns()
        prediction = predict(evidence)
        if latency:
            elapsed.append((perf_counter_ns()-start)/1000)
        answered = prediction != ABSTAIN
        count["n"] += 1
        count["attempted"] += int(answered)
        count["attempted_correct"] += int(answered and prediction == gold)
        count["incorrect_attempted"] += int(answered and prediction != gold)
        count["unsupported_assertions"] += int(answered and gold == ABSTAIN)
        count["correct_abstentions"] += int(not answered and gold == ABSTAIN)
        count["exact_label_matches"] += int(prediction == gold)
        if prediction != gold and len(errors)<10:
            errors.append(evidence["case_ref"])
    return {
        "cases":count["n"],
        "attempted":count["attempted"],
        "coverage":round(count["attempted"]/count["n"],6),
        "selective_accuracy":round(count["attempted_correct"]/count["attempted"],6)
                             if count["attempted"] else None,
        "incorrect_attempted":count["incorrect_attempted"],
        "unsupported_assertions":count["unsupported_assertions"],
        "correct_abstentions":count["correct_abstentions"],
        "exact_label_matches":count["exact_label_matches"],
        "full_match_fraction":round(count["exact_label_matches"]/count["n"],6),
        "median_decision_us":round(statistics.median(elapsed),4) if elapsed else None,
        "sample_errors":errors,
    }


def _choose_threshold(weights, validation):
    """Selection uses validation only; aim zero unsupported and >=.98 precision."""
    evaluations=[]
    for threshold in CONFIDENCE_CANDIDATES:
        stats = _measure(validation, lambda x:_predict(weights,x,threshold),latency=False)
        evaluations.append((threshold,stats))
    eligible=[(t,s) for t,s in evaluations
              if s["unsupported_assertions"]==0 and
              (s["selective_accuracy"] is None or s["selective_accuracy"]>=0.98)]
    if not eligible:
        return 1.01,evaluations
    threshold,_=max(eligible,key=lambda x:(x[1]["attempted"],-x[0]))
    return threshold,evaluations


def benchmark():
    train=_build(DEV_FAMILIES,"development")
    validation=_build(VALIDATION_FAMILIES,"development")
    test=_build(TEST_FAMILIES,"holdout")
    train_sources={w["root"] for e,_ in train for w in e["witnesses"]}
    val_sources={w["root"] for e,_ in validation for w in e["witnesses"]}
    test_sources={w["root"] for e,_ in test for w in e["witnesses"]}
    if train_sources & val_sources or train_sources & test_sources or val_sources & test_sources:
        raise AssertionError("leaked source root into heldout")
    weights,train_ms=_train(train)
    threshold,choices=_choose_threshold(weights,validation)
    arms={
        "B_R5C_LEARNED_WITNESSES":lambda x:_predict(weights,x,threshold),
        "C_FROZEN_R5B_STRONG_RULE":witness_rule,
        "D_WEAK_SINGLE_CLOCK":clock_only_baseline,
        "E_ALWAYS_ABSTAIN":lambda x:ABSTAIN,
    }
    score={key:_measure(test,fn) for key,fn in arms.items()}
    normal=[original_demihead(x) for x,_ in test]
    if any(x["truth_claim"]!="NOT_MADE" for x in normal):
        raise AssertionError("Original DemiHead made truth claim")
    confidence_model=score["B_R5C_LEARNED_WITNESSES"]
    rule=score["C_FROZEN_R5B_STRONG_RULE"]
    clear_gain=(confidence_model["unsupported_assertions"]==0 and
                confidence_model["incorrect_attempted"]==0 and
                confidence_model["attempted"]>rule["attempted"])
    return {
        "schema":"janus.demihead.tachyon.r5c.observation_native_training.v1",
        "scope":"SYNTHETIC_DEVELOPMENT_WITH_SEPARATE_DEVELOPER_HOLDOUT_NOT_EXTERNAL",
        "model":"5_CLASS_LINEAR_SOFTMAX_SGD",
        "root_seed":SEED,
        "labels":list(LABELS),
        "feature_names":list(FEATURES),
        "train_families":len(DEV_FAMILIES),"validation_families":len(VALIDATION_FAMILIES),
        "test_families":len(TEST_FAMILIES),
        "train_cases":len(train),"validation_cases":len(validation),"test_cases":len(test),
        "train_dataset_sha256":_hash_dataset(train,labels=True),
        "validation_dataset_sha256":_hash_dataset(validation,labels=True),
        "test_public_input_sha256":_hash_dataset(test,labels=False),
        "test_with_labels_sha256":_hash_dataset(test,labels=True),
        "source_root_split_disjoint":True,
        "r5b_rule_baseline_blob_sha":SOURCE_SHA,
        "hidden_fields_prohibited":sorted(FORBIDDEN),
        "weights":[[round(v,8) for v in w] for w in weights],
        "learned_parameters":len(LABELS)*len(FEATURES),
        "epochs":EPOCHS,"learning_rate":LR,
        "training_wall_cpu_approx_ms":round(train_ms,3),
        "validation_only_selected_threshold":threshold,
        "validation_threshold_grid":[{"threshold":t,"attempted":s["attempted"],
                         "unsupported_assertions":s["unsupported_assertions"],
                         "selective_accuracy":s["selective_accuracy"]} for t,s in choices],
        "arms":score,
        "model_vs_rule_coverage_delta":round(confidence_model["coverage"]-rule["coverage"],6),
        "strict_positive_learned_gain_on_heldout":clear_gain,
        "original_demihead_reference_outputs_preserved":len(normal),
        "external_custodian":False,
        "real_world_witnesses":False,
        "human_or_clinical_data":False,
        "physical_retrocausality_proven":False,
        "subjective_time_phenomenology_measured":False,
        "production_weights_changed":False,
        "automatic_model_adoption":False,
        "scientific_gate":HOLD,
        "limits":"Labels derive from developer-authored synthetic scenario contract; test is source-name-disjoint but not independent external. Model cannot establish event identity or human/physical retrocausality. Performance does not validate superiority for real-world use.",
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--train-and-audit",action="store_true")
    args=p.parse_args()
    if not args.train_and_audit:
        p.error("--train-and-audit is required")
    result=benchmark()
    print(json.dumps(result,indent=2,sort_keys=True))
    if result["original_demihead_reference_outputs_preserved"]!=result["test_cases"]:
        raise SystemExit("DEMIHEAD_HEAD_CHANGED")
    if not result["source_root_split_disjoint"]:
        raise SystemExit("SOURCE_SPLIT_FAILURE")


if __name__=="__main__":
    main()
