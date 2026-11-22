"""JANUS TACHYON R5F — Causal Memory Reconstruction (offline synthetic research).

Direct method lineage: JANUS-DOUGAN-FREESTYLER-REVERSE-ROAD-CAUSAL-TRACE
v1.4: FREEZE_C -> ASK_PREDECESSOR -> WALK_TO_B -> FREEZE_RULES ->
FORWARD_REPLAY -> CONTROL.

This is *reverse inference* at a later physical time, never reverse causation.
All data are generated DAGs with synthetic witness roots. Real independence,
human memories, clinical diagnosis and retrocausality are not tested.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import random
import statistics
from collections import Counter
from datetime import datetime, timedelta, timezone
from time import perf_counter_ns

SEED=20261122
ABSTAIN="ABSTAIN_NOT_IDENTIFIABLE"
BUDGET=500
SCENARIOS=(
 "unique_A_and_B","unique_B_only","unique_A_only",
 "ambiguous_terminal","collider_shared_B",
 "duplicate_witness_root","conflicting_reports","missing_timestamps",
 "unsynchronized_clock","decoy_reverse_edge",
 "incomplete_reverse_index","future_plan","single_source",
 "identical_content_ambiguity","unsynchronized_terminal",
)
SPLITS={"development":range(0,20),"validation":range(50,60),
        "heldout":range(100,140)}
SOURCE_SHA="4b21b5abc6e2741bcbea562d80f3079b8ab2ce22"
RESEARCH_GATE="ENGINEERING_SYNTHETIC_ONLY__EXTERNAL_CAUSAL_GAIN_UNPROVEN__SCIENCE_HOLD"

def node(family,stage,index):
    return f"w{family}-{stage}{index}"

def build_case(family:int,scenario:str)->dict:
    if type(family) is not int or family<0 or scenario not in SCENARIOS:
        raise ValueError("invalid synthetic family or scenario")
    a=[node(family,"a",i) for i in range(5)]
    b=[node(family,"b",i) for i in range(4)]
    c=[node(family,"c",i) for i in range(2)]
    # Two causes can lead through the same B: source/collider ambiguity.
    forward_A={a[0]:[b[0]],a[1]:[b[1]],a[2]:[b[1]],a[3]:[b[2]],a[4]:[b[3]]}
    forward_B={b[0]:[c[0]],b[1]:[c[0]],b[2]:[c[0]],b[3]:[c[1]]}
    reverse_C={c[0]:[b[0],b[1],b[2]],c[1]:[b[3]]}
    reverse_B={b[0]:[a[0]],b[1]:[a[1],a[2]],b[2]:[a[3]],b[3]:[a[4]]}
    complete=True
    if scenario=="decoy_reverse_edge":
        # One ghost proposal is not a real edge: forward replay must reject it.
        reverse_B[b[0]].append(a[4])
    if scenario=="incomplete_reverse_index":
        reverse_B[b[0]].remove(a[0])
        complete=False
    rng=random.Random(SEED+family*1009+SCENARIOS.index(scenario)*10007)
    origin=datetime(2026,10,1,tzinfo=timezone.utc)+timedelta(days=family%23)
    def witness(stage,actual,index):
        return {
            "stage":stage,
            "observed_node":actual,
            "root":f"sim-root-{family}-{stage}-{index}",
            "capture_utc":(origin+timedelta(hours={"A":0,"B":1}[stage],
                                seconds=index*11)).isoformat(),
            "clock_quality":"calibrated",
            "kind":"recording",
        }
    evidence=[]
    if scenario in ("unique_A_and_B","unique_A_only","decoy_reverse_edge"):
        if scenario!="decoy_reverse_edge":
            evidence += [witness("A",a[0],i) for i in range(2)]
    if scenario in ("unique_A_and_B","unique_B_only","decoy_reverse_edge",
                     "incomplete_reverse_index"):
        evidence += [witness("B",b[0],i) for i in range(2)]
    if scenario=="collider_shared_B":
        evidence += [witness("B",b[1],i) for i in range(2)]
    if scenario=="duplicate_witness_root":
        evidence += [witness("B",b[1],i) for i in range(2)]
        evidence[-1]["root"]=evidence[-2]["root"]
    if scenario=="conflicting_reports":
        evidence += [witness("A",a[0],0),witness("A",a[1],1)]
    if scenario=="missing_timestamps":
        evidence += [witness("A",a[0],i) for i in range(2)]
        evidence[-1]["capture_utc"]=None
    if scenario=="unsynchronized_clock":
        evidence += [witness("A",a[0],i) for i in range(2)]
        evidence[-1]["clock_quality"]="unknown"
    if scenario=="single_source":
        evidence.append(witness("A",a[0],0))
    rng.shuffle(evidence)
    terminal_kind="OBSERVED"
    terminal=c[0]
    if scenario=="future_plan":
        terminal_kind="PLANNED"
    if scenario=="unsynchronized_terminal":
        terminal_kind="OBSERVED_WITH_UNCALIBRATED_CLOCK"
    # No solution label, true hidden route or scenario name inside public input.
    public={
        "schema":"janus.tachyon.r5f.synthetic_reverse_road_graph.v1",
        "case_ref":hashlib.sha256(f"{family}:{scenario}:r5f".encode()).hexdigest()[:16],
        "terminal":terminal,
        "terminal_kind":terminal_kind,
        "forward_edges":{"A_B":forward_A,"B_C":forward_B},
        "reverse_proposals":{"C_B":reverse_C,"B_A":reverse_B,
                             "complete_certified":complete},
        "witness_reports":evidence,
        "witness_window_seconds":120,
        "synthetic_only":True,
    }
    return public

def _safe_time(v):
    if not isinstance(v,str):return None
    try:
        d=datetime.fromisoformat(v)
        return d.astimezone(timezone.utc) if d.utcoffset() is not None else None
    except ValueError:return None

def constraints(inp):
    """Return corroborated node constraints; unreliable evidence is ignored."""
    if inp.get("synthetic_only") is not True or inp.get("terminal_kind")!="OBSERVED":
        return None
    reports=inp.get("witness_reports")
    if not isinstance(reports,list):return None
    out={}
    for stage in ("A","B"):
        rows=[r for r in reports if isinstance(r,dict) and r.get("stage")==stage]
        if len(rows)<2:continue
        roots=[r.get("root") for r in rows]
        times=[_safe_time(r.get("capture_utc")) for r in rows]
        nodes=[r.get("observed_node") for r in rows]
        if (len(set(roots))<2 or any(not isinstance(x,str) or not x for x in roots)
             or any(t is None for t in times)
             or any(r.get("clock_quality")!="calibrated" or r.get("kind")!="recording" for r in rows)
             or len(set(nodes))!=1 or
             (max(times)-min(times)).total_seconds()>inp.get("witness_window_seconds",120)):
            continue
        if not isinstance(nodes[0],str):continue
        out[stage]=nodes[0]
    return out

def accepts(path, constraints_):
    return all(path[0 if stage=="A" else 1]==node_id
               for stage,node_id in constraints_.items())

def pack_result(paths,operations,budget=BUDGET):
    unique=sorted(set(paths))
    predicted="|".join(unique[0]) if len(unique)==1 and operations<=budget else ABSTAIN
    return {"prediction":predicted,"compatible_paths":len(unique),
            "operations":operations,"budget_exceeded":operations>budget}

def forward_only(inp,budget=BUDGET):
    cons=constraints(inp)
    if cons is None:return pack_result([],0,budget)
    ops=0
    eligible=[]
    ab=inp["forward_edges"]["A_B"];bc=inp["forward_edges"]["B_C"]
    for a,bs in sorted(ab.items()):
        for b in sorted(bs):
            ops+=1
            for c in sorted(bc.get(b,[])):
                ops+=1
                if c==inp["terminal"] and accepts((a,b,c),cons):
                    eligible.append((a,b,c))
    return pack_result(eligible,ops,budget)

def reverse_only(inp,budget=BUDGET):
    cons=constraints(inp)
    if cons is None:return pack_result([],0,budget)
    # A missing reverse index cannot justify a uniqueness claim.
    if not inp["reverse_proposals"].get("complete_certified"):
        return pack_result([],0,budget)
    back=inp["reverse_proposals"]
    ops=0
    paths=[]
    for b in sorted(back["C_B"].get(inp["terminal"],[])):
        ops+=1
        for a in sorted(back["B_A"].get(b,[])):
            ops+=1
            if accepts((a,b,inp["terminal"]),cons):
                paths.append((a,b,inp["terminal"]))
    return pack_result(paths,ops,budget)

def reverse_then_forward(inp,budget=BUDGET):
    """C→B→A proposals followed by exact A→B→C frozen replay."""
    cons=constraints(inp)
    if cons is None:return pack_result([],0,budget)
    if not inp["reverse_proposals"].get("complete_certified"):
        return pack_result([],0,budget)
    back=inp["reverse_proposals"];ab=inp["forward_edges"]["A_B"]
    bc=inp["forward_edges"]["B_C"]
    ops=0
    paths=[]
    for b in sorted(back["C_B"].get(inp["terminal"],[])):
        ops+=1
        for a in sorted(back["B_A"].get(b,[])):
            ops+=1
            if not accepts((a,b,inp["terminal"]),cons):continue
            # Replay using fixed authoritative forward edges; not generated from gold.
            ops+=2
            if b in ab.get(a,[]) and inp["terminal"] in bc.get(b,[]):
                paths.append((a,b,inp["terminal"]))
    return pack_result(paths,ops,budget)

def always_abstain(inp,budget=BUDGET):
    return pack_result([],0,budget)

def gold_reference(inp):
    """Separate exhaustive graph identifiability oracle, not hidden true history."""
    ref=forward_only(inp)
    return ref["prediction"]

def run_split(name):
    if name not in SPLITS:raise ValueError("unknown split")
    # Paired arms see exact same visible input; no one is trained on test gold.
    rows=[(build_case(fid,scenario),scenario,fid) for fid in SPLITS[name]
          for scenario in SCENARIOS]
    random.Random(SEED+len(rows)+len(name)).shuffle(rows)
    return rows

def digest(rows,include_gold=False):
    data=rows if include_gold else [item for item,_,_ in rows]
    return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def audit():
    test=run_split("heldout")
    arms={
        "A_FORWARD_ONLY_EXHAUSTIVE":forward_only,
        "B_REVERSE_ONLY_UNVERIFIED":reverse_only,
        "C_REVERSE_PLUS_FORWARD_REPLAY":reverse_then_forward,
        "D_STRONG_EXHAUSTIVE_PROVENANCE":forward_only,
        "E_ALWAYS_ABSTAIN":always_abstain,
    }
    measurements={n:Counter() for n in arms}
    durations={n:[] for n in arms}
    sample_wrong={n:[] for n in arms}
    paired_disagreements=Counter()
    for visible,_,_ in test:
        truth=gold_reference(visible)
        each={}
        for name,fn in arms.items():
            begin=perf_counter_ns()
            ans=fn(visible)
            durations[name].append((perf_counter_ns()-begin)/1000)
            prediction=ans["prediction"]
            each[name]=prediction
            c=measurements[name]
            answered=prediction!=ABSTAIN
            c["total"]+=1
            c["answered"]+=int(answered)
            c["right_attempted"]+=int(answered and prediction==truth)
            c["wrong_attempted"]+=int(answered and prediction!=truth)
            c["unsupported_assertions"]+=int(answered and truth==ABSTAIN)
            c["exact"]+=int(prediction==truth)
            c["abstain_correct"]+=int(not answered and truth==ABSTAIN)
            c["operations"]+=ans["operations"]
            c["over_budget"]+=int(ans["budget_exceeded"])
            if prediction!=truth and len(sample_wrong[name])<12:
                sample_wrong[name].append(visible["case_ref"])
        paired_disagreements[(each["C_REVERSE_PLUS_FORWARD_REPLAY"],
                               each["D_STRONG_EXHAUSTIVE_PROVENANCE"])]+=1
    scores={}
    for n,c in measurements.items():
        scores[n]={
            "total":c["total"],
            "answered":c["answered"],
            "coverage":round(c["answered"]/c["total"],6),
            "selective_accuracy":round(c["right_attempted"]/c["answered"],6) if c["answered"] else None,
            "wrong_attempted":c["wrong_attempted"],
            "unsupported_assertions":c["unsupported_assertions"],
            "correct_abstentions":c["abstain_correct"],
            "exact_matches":c["exact"],
            "mean_operations_per_case":round(c["operations"]/c["total"],4),
            "over_budget_cases":c["over_budget"],
            "median_decision_us":round(statistics.median(durations[n]),4),
            "error_case_refs":sample_wrong[n],
        }
    c=scores["C_REVERSE_PLUS_FORWARD_REPLAY"]
    d=scores["D_STRONG_EXHAUSTIVE_PROVENANCE"]
    gain=c["coverage"]>d["coverage"] and c["unsupported_assertions"]<=d["unsupported_assertions"]
    return {
        "schema":"janus.demihead.tachyon.r5f.causal_memory_reconstruction_audit.v1",
        "status":"RESEARCH_SYNTHETIC_ENGINEERING_ONLY__SCIENCE_HOLD",
        "source_method":"Hawkar-usls/janus-meta-registry@main/data/JANUS-DOUGAN-FREESTYLER-REVERSE-ROAD-CAUSAL-TRACE-2026-08-18-v1.4.json",
        "source_blob_sha1":SOURCE_SHA,
        "seed":SEED,"operation_budget_per_case":BUDGET,
        "split_families":{"development":20,"validation":10,"heldout":40},
        "development_cases":len(run_split("development")),
        "validation_cases":len(run_split("validation")),
        "heldout_cases":len(test),
        "challenge_sha256":digest(test),
        "model_selection_on_test":False,
        "all_arms_receive_identical_input":True,
        "synthetic_source_independence_only":True,
        "gold_definition":"Uniquely identifiable route under corroborated visible witness constraints and authoritative causal DAG, not latent physical truth.",
        "potential_history_multiplicity":"A1→B1→C and A2→B1→C possible; do not assert unique when provenance insufficient.",
        "arms":scores,
        "gain_vs_strong_baseline_established":gain,
        "statistical_science_gain_established":False,
        "human_memory_measured":False,"physical_reverse_time_measured":False,
        "production_weights_changed":False,"independent_external_custodian":False,
        "scientific_gate":RESEARCH_GATE,
        "timing_limit":"Uncalibrated single CI-runner Python timings; operation count is defined proxy, not wall-clock standardized latency or full energy.",
        "comparison_limit":"Strong forward/provenance baseline uses exhaustive path verification; identity of results is not meaningful neural uplift. Source roots are synthetic strings, not authenticated instruments.",
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--audit",action="store_true")
    o=ap.parse_args()
    if not o.audit:ap.error("--audit required")
    result=audit()
    print(json.dumps(result,sort_keys=True,indent=2,ensure_ascii=False))
    c=result["arms"]["C_REVERSE_PLUS_FORWARD_REPLAY"]
    if c["unsupported_assertions"] or c["over_budget_cases"]:
        raise SystemExit("R5F_UNSUPPORTED_ASSERTION_OR_BUDGET")

if __name__=="__main__":
    main()
