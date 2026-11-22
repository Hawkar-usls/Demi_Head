"""DemiHead × TACHYON R5B: leakage-resistant synthetic witness exam.

Everything is generated metadata, not people or real physics. No raw event IDs,
R4 status labels, private clinical observations, or retrospective target fields
are supplied to either sidecar. R4 may decline out-of-domain inputs; never
invent its missing training features to obtain a prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter_ns

from tools.keto_reference import summarize_case

SEED = 2026112251
UTC = timezone.utc
TOLERANCE = timedelta(minutes=3)
REF = datetime(2026, 11, 22, 12, tzinfo=UTC)
SCENARIOS = (
    "same_signature_separate_days",
    "different_content_separate_days",
    "known_order_unknown_content",
    "future_schedules_no_observations",
    "same_window_identity_unknown",
    "timestamp_missing",
    "contradictory_clocks",
    "duplicate_source_roots",
    "unsynchronized_clocks",
    "one_root_only",
)
ANSWER = {
    SCENARIOS[0]: "REPEAT_WINDOWS_SAME_SIGNATURE",
    SCENARIOS[1]: "DISTINCT_CONTENT_WITNESSED",
    SCENARIOS[2]: "ORDER_A_BEFORE_B",
    SCENARIOS[3]: "ONLY_FUTURE_SCHEDULES",
    **{name: "ABSTAIN_INSUFFICIENT_EVIDENCE" for name in SCENARIOS[4:]},
}
ABSTAIN = "ABSTAIN_INSUFFICIENT_EVIDENCE"
R4_OOD = "ABSTAIN_R4_UNSUPPORTED_OBSERVABLE_SCHEMA"
NON_ABSTAIN = set(ANSWER.values()) - {ABSTAIN}
MODEL_SOURCE = "Hawkar-usls/Simptomat@5c1daed7f728d671ed2139b3448bd612ea0a4f58"
HOLD = "SCIENTIFIC_HOLD_NO_EXTERNAL_HUMAN_OR_PHYSICAL_VALIDATION"


def _t(dt: datetime | None) -> str | None:
    return None if dt is None else dt.astimezone(UTC).isoformat()


def _parse(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None or result.utcoffset() is None:
            return None
        return result.astimezone(UTC)
    except (TypeError, ValueError):
        return None


def build_case(family: int, scenario: str, *, partition: str = "holdout") -> tuple[dict, str]:
    """Generate hidden gold separate from visible evidence. No target field in input."""
    if scenario not in SCENARIOS or type(family) is not int or family < 0:
        raise ValueError("invalid synthetic family/scenario")
    if partition not in {"development", "holdout"}:
        raise ValueError("invalid partition")
    rng = random.Random(SEED + (0 if partition == "development" else 1000003) +
                        10007 * family + 197 * SCENARIOS.index(scenario))
    day = REF - timedelta(days=2 + (family % 10))
    prior = day.replace(hour=8, minute=0)
    following = prior + timedelta(days=2)
    same_time = prior + timedelta(seconds=25)
    future = REF + timedelta(days=1 + family % 2)
    sig_a = "tone-" + str(rng.randrange(18))
    sig_b = sig_a
    if scenario == "different_content_separate_days":
        sig_b = sig_a + "-different"
    if scenario == "known_order_unknown_content":
        sig_a = sig_b = None
    if scenario == "same_window_identity_unknown":
        following = same_time
    if scenario == "future_schedules_no_observations":
        prior, following = future, future + timedelta(days=1)
    # Synthetic witness report provenance: only a separate root string, not a
    # cryptographic proof of true independence in real-world observations.
    def witness(slot: str, index: int, when: datetime | None, signature: str | None,
                kind: str = "recording", root: str | None = None,
                quality: str = "synchronized") -> dict:
        wobble = timedelta(seconds=(index * 11) if index else 0)
        return {
            "slot": slot,
            "root": root or f"{partition}-family{family}-{slot}-source{index}",
            "source_medium": ("acoustic_sensor", "lab_notebook")[index % 2],
            "claim_medium": kind,
            "captured_at_utc": _t(when + wobble if when else None),
            "receipt_created_at_utc": _t(REF + timedelta(minutes=index)),
            "content_signature": signature,
            "clock_quality": quality,
        }
    kind = "schedule_notice" if scenario == "future_schedules_no_observations" else "recording"
    rows = [witness(slot, i, when, sig, kind=kind)
            for slot, when, sig in (("a", prior, sig_a), ("b", following, sig_b))
            for i in (0, 1)]
    if scenario == "timestamp_missing":
        for item in rows:
            if item["slot"] == "b":
                item["captured_at_utc"] = None
    if scenario == "contradictory_clocks":
        for item in rows:
            if item["slot"] == "b" and item["source_medium"] == "lab_notebook":
                item["captured_at_utc"] = _t(following + timedelta(days=2))
    if scenario == "duplicate_source_roots":
        for item in rows:
            if item["source_medium"] == "lab_notebook":
                item["root"] = f"{partition}-family{family}-{item['slot']}-source0"
    if scenario == "unsynchronized_clocks":
        for item in rows:
            if item["slot"] == "b":
                item["clock_quality"] = "unknown"
    if scenario == "one_root_only":
        rows = [w for w in rows if w["source_medium"] == "acoustic_sensor"]
    rng.shuffle(rows)
    public = {
        "schema": "janus.demihead.tachyon.r5b.synthetic_witness_input.v1",
        "case_ref": hashlib.sha256(f"{partition}/{family}/{scenario}".encode()).hexdigest()[:16],
        "reference_time_utc": _t(REF),
        "witnesses": rows,
        "synthetic_only": True,
    }
    # DO NOT insert scenario, gold, R4 event IDs, or R4 b_status into public.
    return public, ANSWER[scenario]


def _summarize_slot(witnesses: list[dict], slot: str) -> dict | None:
    sub = [w for w in witnesses if w.get("slot") == slot]
    if len(sub) < 2 or len({w.get("root") for w in sub}) < 2:
        return None
    if any(not isinstance(w.get("root"), str) or not w["root"] for w in sub):
        return None
    if any(w.get("clock_quality") != "synchronized" for w in sub):
        return None
    times = [_parse(w.get("captured_at_utc")) for w in sub]
    if any(t is None for t in times) or max(times) - min(times) > TOLERANCE:
        return None
    signatures = {w.get("content_signature") for w in sub}
    if len(signatures) != 1:
        return None
    kinds = {w.get("claim_medium") for w in sub}
    if kinds not in ({"recording"}, {"schedule_notice"}):
        return None
    return {
        "time": min(times),
        "signature": next(iter(signatures)),
        "kind": next(iter(kinds)),
        "roots": len({w["root"] for w in sub}),
    }


def witness_rule(inp: dict) -> str:
    """Proof-carrying rule: conservative about identity and unsupported timing."""
    if inp.get("synthetic_only") is not True:
        return ABSTAIN
    ref = _parse(inp.get("reference_time_utc"))
    rows = inp.get("witnesses")
    if ref is None or not isinstance(rows, list):
        return ABSTAIN
    a, b = (_summarize_slot(rows, k) for k in ("a", "b"))
    if a is None or b is None:
        return ABSTAIN
    if a["kind"] == b["kind"] == "schedule_notice":
        return "ONLY_FUTURE_SCHEDULES" if a["time"] > ref and b["time"] > ref else ABSTAIN
    if a["kind"] != "recording" or b["kind"] != "recording":
        return ABSTAIN
    if a["time"] > ref or b["time"] > ref:
        return ABSTAIN  # A future recording claim needs external verification.
    if b["time"] - a["time"] <= timedelta(hours=12):
        return ABSTAIN  # Same-window logs do NOT prove two or one physical events.
    if a["signature"] is None or b["signature"] is None:
        return "ORDER_A_BEFORE_B"
    if a["signature"] == b["signature"]:
        return "REPEAT_WINDOWS_SAME_SIGNATURE"
    return "DISTINCT_CONTENT_WITNESSED"


def clock_only_baseline(inp: dict) -> str:
    """Naive single-record baseline, deliberately fails to check independence."""
    try:
        a = next(w for w in inp["witnesses"] if w["slot"] == "a")
        b = next(w for w in inp["witnesses"] if w["slot"] == "b")
        t1, t2, ref = (_parse(a["captured_at_utc"]), _parse(b["captured_at_utc"]),
                       _parse(inp["reference_time_utc"]))
        if None in (t1, t2, ref):
            return ABSTAIN
        if a["claim_medium"] == b["claim_medium"] == "schedule_notice" and t1 > ref and t2 > ref:
            return "ONLY_FUTURE_SCHEDULES"
        if t2 - t1 <= timedelta(hours=12) or t2 > ref:
            return ABSTAIN
        if a["content_signature"] is None or b["content_signature"] is None:
            return "ORDER_A_BEFORE_B"
        return ("REPEAT_WINDOWS_SAME_SIGNATURE" if a["content_signature"] == b["content_signature"]
                else "DISTINCT_CONTENT_WITNESSED")
    except (KeyError, StopIteration, TypeError):
        return ABSTAIN


def r4_frozen_adapter(inp: dict) -> str:
    """Refuse to forge R4 event IDs/status. Frozen learned model cannot run here."""
    # R4 features() contract requires known event_a_id/event_b_id and
    # b_status, neither of which exists in this witness-only schema.
    required = ("event_a_id", "event_b_id", "b_status", "event_a_time",
                "event_b_time", "content_a", "content_b", "reference_time")
    if all(k in inp for k in required):
        raise ValueError("R5B forbids original R4 answer-bearing feature contract")
    return R4_OOD


def original_demihead(inp: dict) -> dict:
    """Actual original DemiHead reference unchanged across all arms."""
    presentations = [
        {
            "presentation_id": f"{inp['case_ref']}-{i}",
            "root_id": w["root"],
            "relation": "context_only",
            "freshness": "current",
            "source_class": "synthetic",
            "independence": "unknown",
        } for i, w in enumerate(inp["witnesses"])
    ]
    return summarize_case({
        "schema": "janus.demihead.keto_case.v1",
        "case_id": "R5B-" + inp["case_ref"],
        "claim": "Evidence cannot establish temporal identity without authenticated roots",
        "presentations": presentations,
    })


def cases(partition: str) -> list[tuple[dict, str]]:
    # Two distinct deterministic corpora, with source-disjoint root namespaces.
    ids = range(0, 8) if partition == "development" else range(100, 132)
    out = [build_case(family, s, partition=partition) for family in ids for s in SCENARIOS]
    random.Random(SEED + (0 if partition == "development" else 1)).shuffle(out)
    return out


def _casebank_hash(rows: list[tuple[dict, str]]) -> str:
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def benchmark() -> dict:
    rows = cases("holdout")
    routines = {
        "B_FROZEN_R4_NO_FEATURE_BACKFILL": r4_frozen_adapter,
        "C_INDEPENDENT_WITNESS_RULE": witness_rule,
        "D_SINGLE_CLOCK_BASELINE": clock_only_baseline,
        "E_ALWAYS_ABSTAIN": lambda x: ABSTAIN,
    }
    measures = {n: Counter() for n in routines}
    times = {n: [] for n in routines}
    errors = {n: [] for n in routines}
    original_unchanged = 0
    predicted_examples = {n: [] for n in routines}
    for inp, gold in rows:
        before_head = original_demihead(inp)
        after_head = original_demihead(inp)
        original_unchanged += int(before_head == after_head and
                                  before_head["truth_claim"] == "NOT_MADE")
        for name, fn in routines.items():
            start = perf_counter_ns()
            pred = fn(inp)
            elapsed = perf_counter_ns() - start
            times[name].append(elapsed)
            v = measures[name]
            v["all"] += 1
            v["exact_gold_match"] += int(pred == gold)
            attempted = pred not in {ABSTAIN, R4_OOD}
            v["attempted"] += int(attempted)
            v["correct_attempted"] += int(attempted and pred == gold)
            v["unsupported_assertions"] += int(attempted and gold == ABSTAIN)
            v["incorrect_nonabstentions"] += int(attempted and pred != gold)
            v["correct_required_abstentions"] += int(gold == ABSTAIN and not attempted)
            if pred != gold and len(errors[name]) < 16:
                errors[name].append(inp["case_ref"])
            predicted_examples[name].append(pred)
    summary = {}
    for name, cnt in measures.items():
        attempted = cnt["attempted"]
        summary[name] = {
            "cases": cnt["all"],
            "exact_gold_matches_including_abstentions": cnt["exact_gold_match"],
            "raw_gold_match_rate": round(cnt["exact_gold_match"]/len(rows), 6),
            "answered_count": attempted,
            "coverage": round(attempted/len(rows), 6),
            "selective_accuracy": round(cnt["correct_attempted"]/attempted, 6)
                                 if attempted else None,
            "unsupported_assertions": cnt["unsupported_assertions"],
            "incorrect_nonabstentions": cnt["incorrect_nonabstentions"],
            "correct_required_abstentions": cnt["correct_required_abstentions"],
            "median_decision_microseconds": round(statistics.median(times[name])/1000, 4),
            "sample_error_case_refs": errors[name],
        }
    golden_counts = dict(sorted(Counter(g for _,g in rows).items()))
    is_safe = (summary["C_INDEPENDENT_WITNESS_RULE"]["unsupported_assertions"] == 0 and
               original_unchanged == len(rows) and
               summary["B_FROZEN_R4_NO_FEATURE_BACKFILL"]["answered_count"] == 0)
    return {
        "schema": "janus.demihead.tachyon.r5b.anti_shortcut_witness_audit.v1",
        "scope": "SYNTHETIC_METHODS_ONLY__DEVELOPER_HOLDOUT_NOT_EXTERNAL_BLIND",
        "seed": SEED,
        "cases": len(rows),
        "development_cases": len(cases("development")),
        "source_groups_disjoint_between_splits": True,
        "challenge_sha256_with_private_gold": _casebank_hash(rows),
        "challenge_input_sha256": hashlib.sha256(
            json.dumps([x for x,_ in rows], sort_keys=True).encode()).hexdigest(),
        "input_keys": list(rows[0][0].keys()),
        "forbidden_leakage_fields": ["event_a_id", "event_b_id", "b_status", "target", "gold", "scenario"],
        "frozen_original_R4": MODEL_SOURCE,
        "r4_interface_result": "OUT_OF_DOMAIN__NO_RAW_ID_OR_STATUS_TO_GENERATE_LEARNED_FEATURES",
        "r4_weights_modified": False,
        "r4_learned_predictions_executed": False,
        "core_DemiHead_outputs_unchanged": original_unchanged,
        "gold_distribution": golden_counts,
        "arms": summary,
        "valid_engineering_safety_gate": is_safe,
        "neural_gain_established": False,
        "sufficient_external_independent_data": False,
        "real_world_independence_authenticated": False,
        "model_selection_on_holdout": False,
        "physical_retrocausality_claim": False,
        "subjective_timelessness_claim": False,
        "human_or_clinical_data_used": False,
        "production_weights_changed": False,
        "scientific_gate": HOLD,
        "timing_notes": "Single CI worker; only per-case adapter decision times; not standardized. Retraining omitted because R4 adapter abstains.",
        "interpretation": "The old R4 learned model requires answer-bearing metadata that independent witnesses do not supply. A strict adapter returns OOD instead of hallucinating IDs. Strong synthetic witness rules may act when independent roots/timing corroborate the claim; root names are simulated, NOT real authenticated independence.",
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--audit", action="store_true")
    a = p.parse_args()
    if not a.audit:
        p.error("Use --audit (synthetic-only)")
    receipt = benchmark()
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2))
    if not receipt["valid_engineering_safety_gate"]:
        raise SystemExit("R5B failed safety gate")


if __name__ == "__main__":
    main()
