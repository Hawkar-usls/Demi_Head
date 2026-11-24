"""JANUS TACHYON R5E: 180-degree *reported* time-order reversal audit.

'180 degrees' is an operational METAPHOR for exact permutation reversal:
physical event sequence (A, B, C) vs reported temporal judgment (C, B, A).
This does not measure literal geometric rotation, conscious experience, a
disorder, reversed physics, or a retrocausal information channel.

Research-only synthetic witness metadata; no patient records or production
DemiHead weights.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

SEED = 20261122
UTC = timezone.utc
TOLERANCE_SECONDS = 120

REVERSED = "REPORTED_TEMPORAL_JUDGMENT_REVERSED_180"
ALIGNED = "REPORTED_TEMPORAL_JUDGMENT_ALIGNED"
NARRATIVE = "REVERSED_RECALL_NARRATIVE_ONLY"
PRESENTATION = "REVERSED_STIMULUS_PRESENTATION_ONLY"
OTHER = "OTHER_ORDER_MISMATCH_NOT_180"
ABSTAIN = "ABSTAIN_INSUFFICIENT_EVIDENCE"

SCENARIOS = (
    "reversed_three",
    "aligned_three",
    "recall_reverse",
    "presentation_reverse",
    "rotation_not_reversal",
    "partial_order_error",
    "identical_content_anchor_ids",
    "identical_content_no_ids",
    "future_plan_not_observed",
    "timestamp_missing",
    "clock_conflict",
    "duplicate_source_root",
    "unknown_report_mode",
    "two_events_reversed",
    "local_midnight",
    "duplicate_report_reference",
)
LABELS = {
    "reversed_three": REVERSED,
    "aligned_three": ALIGNED,
    "recall_reverse": NARRATIVE,
    "presentation_reverse": PRESENTATION,
    "rotation_not_reversal": OTHER,
    "partial_order_error": OTHER,
    "identical_content_anchor_ids": REVERSED,
    "identical_content_no_ids": ABSTAIN,
    "future_plan_not_observed": ABSTAIN,
    "timestamp_missing": ABSTAIN,
    "clock_conflict": ABSTAIN,
    "duplicate_source_root": ABSTAIN,
    "unknown_report_mode": ABSTAIN,
    "two_events_reversed": REVERSED,
    "local_midnight": REVERSED,
    "duplicate_report_reference": ABSTAIN,
}

def parse_time(value: str | None):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.utcoffset() is None:
            return None
        return dt.astimezone(UTC)
    except ValueError:
        return None

def _as_str(dt):
    return dt.isoformat() if dt is not None else None

def relative_day(event: str, reference: str, timezone_name: str = "Europe/Kyiv") -> str:
    """Civil-date relation does not modify the event's UTC instant."""
    e, r = parse_time(event), parse_time(reference)
    if e is None or r is None:
        raise ValueError("External-aware event and reference times required")
    tz = ZoneInfo(timezone_name)
    d = (e.astimezone(tz).date() - r.astimezone(tz).date()).days
    return "TODAY" if d == 0 else f"FUTURE_{d}" if d > 0 else f"PAST_{-d}"

def generate_case(family: int, scenario: str) -> tuple[dict, str]:
    if type(family) is not int or family < 0 or scenario not in SCENARIOS:
        raise ValueError("invalid case")
    # 3 *distinct* physical event IDs; some with identical content.
    n = 2 if scenario == "two_events_reversed" else 3
    base = datetime(2026, 11, 22, 10, 0, tzinfo=UTC) - timedelta(days=10 + family % 7)
    if scenario == "local_midnight":
        base = datetime(2026, 11, 20, 21, 40, tzinfo=UTC)
    timestamps = [base + timedelta(minutes=i*30) for i in range(n)]
    ref = datetime(2026, 11, 22, 12, tzinfo=UTC)
    event_ids = [f"synthetic-f{family}-{i}" for i in range(n)]
    same_content = scenario in ("identical_content_anchor_ids", "identical_content_no_ids")
    events = []
    for i, event_id in enumerate(event_ids):
        witnesses = [
            {
                "root": f"family{family}-event{i}-independent-source{j}",
                "captured_at_utc":_as_str(timestamps[i] + timedelta(seconds=13*j)),
                "clock_quality":"synchronized",
            }
            for j in range(2)
        ]
        events.append({
            "event_id": event_id,
            "content_signature": "repeated-same-content" if same_content else f"tone-{i}",
            "occurrence_status": "OBSERVED",
            "witnesses": witnesses,
        })
    report = list(reversed(event_ids))
    mode = "temporal_judgment"
    if scenario == "aligned_three":
        report = list(event_ids)
    elif scenario == "rotation_not_reversal":
        report = [event_ids[1],event_ids[2],event_ids[0]]
    elif scenario == "partial_order_error":
        report = [event_ids[1],event_ids[0],event_ids[2]]
    elif scenario == "recall_reverse":
        mode = "retelling_order"
    elif scenario == "presentation_reverse":
        mode = "stimulus_presentation_order"
    elif scenario == "unknown_report_mode":
        mode = "not_declared"
    elif scenario == "identical_content_no_ids":
        report = ["repeated-same-content"] * n
    elif scenario == "future_plan_not_observed":
        events[-1]["occurrence_status"] = "PLANNED"
        future = ref + timedelta(days=1)
        for j, witness in enumerate(events[-1]["witnesses"]):
            witness["captured_at_utc"] = _as_str(future + timedelta(seconds=13*j))
    elif scenario == "timestamp_missing":
        for witness in events[-1]["witnesses"]:
            witness["captured_at_utc"] = None
    elif scenario == "clock_conflict":
        events[-1]["witnesses"][1]["captured_at_utc"] = _as_str(timestamps[-1]+timedelta(hours=5))
    elif scenario == "duplicate_source_root":
        events[-1]["witnesses"][1]["root"] = events[-1]["witnesses"][0]["root"]
    elif scenario == "duplicate_report_reference":
        report = [event_ids[0],event_ids[0],event_ids[-1]]
    payload = {
        "schema":"janus.tachyon.r5e.synthetic_reported_order.v1",
        "case_ref":hashlib.sha256(f"r5e/{family}/{scenario}".encode()).hexdigest()[:16],
        "reference_time_utc":_as_str(ref),
        "timezone_name":"Europe/Kyiv",
        "physical_events":events,
        "subjective_report":{
            "mode":mode,
            "ordered_event_refs":report,
            "observation_type":"REPORTED_ORDER_NOT_DIRECT_PHENOMENOLOGY",
        },
        "synthetic_only":True,
    }
    return payload,LABELS[scenario]

def assess(payload: dict) -> str:
    """Compare reported order to fixed witness chronology, never reverse clocks."""
    if not isinstance(payload,dict) or payload.get("synthetic_only") is not True:
        return ABSTAIN
    events = payload.get("physical_events")
    report = payload.get("subjective_report")
    if not isinstance(events,list) or len(events)<2 or not isinstance(report,dict):
        return ABSTAIN
    ref = parse_time(payload.get("reference_time_utc"))
    if ref is None:
        return ABSTAIN
    anchor = []
    event_ids = set()
    for event in events:
        if not isinstance(event,dict):
            return ABSTAIN
        eid=event.get("event_id")
        if not isinstance(eid,str) or not eid or eid in event_ids:
            return ABSTAIN
        event_ids.add(eid)
        if event.get("occurrence_status")!="OBSERVED":
            return ABSTAIN
        witnesses=event.get("witnesses")
        if not isinstance(witnesses,list) or len(witnesses)<2:
            return ABSTAIN
        roots=[w.get("root") for w in witnesses if isinstance(w,dict)]
        if len(roots)!=len(witnesses) or any(not isinstance(root,str) or not root for root in roots):
            return ABSTAIN
        if len(set(roots))<2:
            return ABSTAIN
        if any(w.get("clock_quality")!="synchronized" for w in witnesses):
            return ABSTAIN
        times=[parse_time(w.get("captured_at_utc")) for w in witnesses]
        if any(t is None for t in times):
            return ABSTAIN
        if (max(times)-min(times)).total_seconds()>TOLERANCE_SECONDS:
            return ABSTAIN
        representative=min(times)
        if representative>ref:
            return ABSTAIN
        anchor.append((representative,eid))
    # Exact order requires non-overlapping time uncertainty intervals.
    anchor.sort(key=lambda x:(x[0],x[1]))
    for (start,_),(next_start,_) in zip(anchor,anchor[1:]):
        if (next_start-start).total_seconds()<=TOLERANCE_SECONDS:
            return ABSTAIN
    physical=[eid for _,eid in anchor]
    refs=report.get("ordered_event_refs")
    if not isinstance(refs,list) or len(refs)!=len(physical):
        return ABSTAIN
    if not all(isinstance(x,str) for x in refs):
        return ABSTAIN
    if set(refs)!=set(physical) or len(set(refs))!=len(refs):
        return ABSTAIN
    mode=report.get("mode")
    if refs==list(reversed(physical)):
        if mode=="temporal_judgment":
            return REVERSED
        if mode=="retelling_order":
            return NARRATIVE
        if mode=="stimulus_presentation_order":
            return PRESENTATION
        return ABSTAIN
    if mode!="temporal_judgment":
        return ABSTAIN
    if refs==physical:
        return ALIGNED
    return OTHER

def naive_reverse_detector(payload: dict) -> str:
    """Control: calls all reverse reports perception reversal, ignoring mode."""
    events=payload.get("physical_events",[])
    ordered=[e.get("event_id") for e in events]
    refs=payload.get("subjective_report",{}).get("ordered_event_refs")
    if isinstance(refs,list) and refs==list(reversed(ordered)):
        return REVERSED
    return ALIGNED

def score() -> dict:
    counts=Counter()
    matrices={"verified":Counter(),"naive":Counter(),"always_abstain":Counter()}
    false_reversal_claims={"verified":0,"naive":0,"always_abstain":0}
    examples=0
    for family in range(100,124):
        for scenario in SCENARIOS:
            payload,gold=generate_case(family,scenario)
            result={"verified":assess(payload),"naive":naive_reverse_detector(payload),
                    "always_abstain":ABSTAIN}
            examples+=1
            counts[gold]+=1
            for name,pred in result.items():
                matrices[name][(gold,pred)]+=1
                false_reversal_claims[name]+=int(pred==REVERSED and gold!=REVERSED)
    arms={}
    for name,mat in matrices.items():
        correct=sum(num for (gold,pred),num in mat.items() if gold==pred)
        answered=sum(num for (gold,pred),num in mat.items() if pred!=ABSTAIN)
        conditional_correct=sum(num for (gold,pred),num in mat.items()
                                if pred==gold and pred!=ABSTAIN)
        arms[name]={
            "exact_correct":correct,
            "exact_accuracy":round(correct/examples,6),
            "answered_count":answered,
            "coverage":round(answered/examples,6),
            "selective_accuracy":round(conditional_correct/answered,6) if answered else None,
            "false_180_reversal_claims":false_reversal_claims[name],
        }
    return {
        "schema":"janus.tachyon.r5e.order_180_audit.v1",
        "seed":SEED,
        "cases":examples,
        "scenario_names":list(SCENARIOS),
        "gold_distribution":dict(counts),
        "arms":arms,
        "scientific_gate":"ENGINEERING_SYNTHETIC_ONLY__SUBJECTIVE_EXPERIENCE_UNMEASURED__SCIENCE_HOLD",
        "180_definition":"Reverse *reported temporal judgment permutation* relative to independently timestamped physical event order",
        "not_reversed_physical_history":True,
        "not_phenomenal_experience_proven":True,
        "independent_real_witnesses_authenticated":False,
        "no_human_or_clinical_data":True,
        "production_models_changed":False,
        "baseline_scope":"Report-reversal detector is intentionally weak; no neural gain or external validation inference.",
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--audit",action="store_true")
    a=p.parse_args()
    if not a.audit:
        p.error("Use --audit for offline synthetic-only check")
    receipt=score()
    print(json.dumps(receipt,indent=2,ensure_ascii=False,sort_keys=True))
    if receipt["arms"]["verified"]["false_180_reversal_claims"]:
        raise SystemExit("UNSUPPORTED_SUBJECTIVE_REVERSAL_ASSERTION")

if __name__=="__main__":
    main()
