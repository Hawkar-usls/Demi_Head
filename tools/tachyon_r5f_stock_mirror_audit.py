"""TACHYON R5F-MIRROR: stock settings, mathematically transposed causal DAG.

Original: A -> B -> C (unique cause of observed C).
Mirrored: C -> B -> A (same graph edges transposed, fixed C source).

This changes the DIRECTION OF GRAPH SEARCH and synthetic layer coordinate,
not real UTC timestamps or physical causality. No model training or outside
witness inference. This is an isomorphism/invariance test using the original
600 R5F synthetic heldout cases and unchanged budget 500.
"""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import statistics
from collections import Counter
from time import perf_counter_ns
from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN, BUDGET, SCENARIOS, SOURCE_SHA, constraints, forward_only,
    reverse_only, reverse_then_forward, run_split, digest,
)

DEFAULT_BUDGET=500
STOCK_FORWARD_EDGE_COUNT=9
SCIENTIFIC_GATE="STOCK_SYNTHETIC_MIRROR_INVARIANCE_ONLY__EXTERNAL_GENERALIZATION_HOLD"


def transpose(edges:dict)->dict:
    """Turn u->v into v->u; stable de-duplicated adjacency lists."""
    result={}
    for u, vs in edges.items():
        for v in vs:
            result.setdefault(v, []).append(u)
    return {k:sorted(set(vs)) for k,vs in sorted(result.items())}


def mirror_case(original:dict)->dict:
    if not isinstance(original,dict) or original.get("synthetic_only") is not True:
        raise ValueError("only the frozen synthetic R5F input is admissible")
    if original.get("schema")!="janus.tachyon.r5f.synthetic_reverse_road_graph.v1":
        raise ValueError("unexpected input schema")
    src_ab=original["forward_edges"]["A_B"]
    src_bc=original["forward_edges"]["B_C"]
    actual={
        "A_B":transpose(src_bc),  # old C -> old B
        "B_C":transpose(src_ab),  # old B -> old A
    }
    # Proposals retain intentional decoy and incompleteness from original,
    # but are not elevated to ground truth.
    proposed={
        "A_B":copy.deepcopy(original["reverse_proposals"]["C_B"]),
        "B_C":copy.deepcopy(original["reverse_proposals"]["B_A"]),
        "complete_certified":bool(original["reverse_proposals"]["complete_certified"]),
    }
    mapped_reports=[]
    for w in original["witness_reports"]:
        w2=copy.deepcopy(w)
        w2["stage"]={"A":"C","B":"B"}[w["stage"]]
        # Preserve physical capture time verbatim: no fake reversed clocks.
        mapped_reports.append(w2)
    transformed={
        "schema":"janus.tachyon.r5f.stock_mirror_graph.v1",
        "case_ref":original["case_ref"],
        "anchor_source":original["terminal"],  # fixed former C
        "anchor_source_kind":original["terminal_kind"],
        "forward_edges":actual,
        "reverse_proposals":proposed,
        "witness_reports":mapped_reports,
        "witness_window_seconds":original["witness_window_seconds"],
        "graph_direction":"C_TO_B_TO_A",
        "mirror_stages":{"original_A":"mirrored_C","original_B":"mirrored_B","original_C":"mirrored_A"},
        "synthetic_time_layer_coordinates":{"A":2,"B":1,"C":0},
        "physical_utc_modified":False,
        "synthetic_only":True,
    }
    return transformed


def mirror_constraints(mirrored:dict):
    """Same corroboration checks but stages C/B, not original A/B."""
    if mirrored.get("synthetic_only") is not True or mirrored.get("anchor_source_kind")!="OBSERVED":
        return None
    rebuilt={
        "synthetic_only":True,
        "terminal_kind":mirrored["anchor_source_kind"],
        "witness_window_seconds":mirrored["witness_window_seconds"],
        "witness_reports":[{
            **w, "stage": {"C":"A","B":"B"}.get(w["stage"],"__invalid__")
        } for w in mirrored["witness_reports"]],
    }
    original=constraints(rebuilt)
    if original is None:return None
    return {"C":original["A"],"B":original["B"]} if "A" in original and "B" in original else {
        **({"C":original["A"]} if "A" in original else {}),
        **({"B":original["B"]} if "B" in original else {}),
    }


def eligible(path,cons:dict)->bool:
    # path is C, B, A; constrain mirrored C (original A) and mirrored B.
    c,b,a=path
    return all({"C":a,"B":b}[stage] == value for stage,value in cons.items())


def result(paths,ops,budget):
    matches=sorted(set(paths))
    value="|".join(reversed(matches[0])) if len(matches)==1 and ops<=budget else ABSTAIN
    return {"prediction":value, "compatible_paths":len(matches),
            "operations":ops,"budget_exceeded":ops>budget}


def mirrored_exact(mirrored:dict,budget:int=DEFAULT_BUDGET):
    cons=mirror_constraints(mirrored)
    if cons is None:return result([],0,budget)
    ans=[];ops=0
    fixed=mirrored["anchor_source"]
    for b in sorted(mirrored["forward_edges"]["A_B"].get(fixed,[])):
        ops+=1
        for a in sorted(mirrored["forward_edges"]["B_C"].get(b,[])):
            ops+=1
            candidate=(fixed,b,a)
            if eligible(candidate,cons):
                ans.append(candidate)
    return result(ans,ops,budget)


def mirrored_proposals(mirrored:dict,budget:int=DEFAULT_BUDGET,verify:bool=False):
    cons=mirror_constraints(mirrored)
    if cons is None:return result([],0,budget)
    proposals=mirrored["reverse_proposals"]
    if not proposals["complete_certified"]:
        return result([],0,budget)
    ans=[];ops=0
    fixed=mirrored["anchor_source"]
    for b in sorted(proposals["A_B"].get(fixed,[])):
        ops+=1
        for a in sorted(proposals["B_C"].get(b,[])):
            ops+=1
            candidate=(fixed,b,a)
            if not eligible(candidate,cons):continue
            if verify:
                ops+=2
                if (b not in mirrored["forward_edges"]["A_B"].get(fixed,[]) or
                    a not in mirrored["forward_edges"]["B_C"].get(b,[])):
                    continue
            ans.append(candidate)
    return result(ans,ops,budget)


def mirrored_proposals_only(mirrored:dict,budget:int=DEFAULT_BUDGET):
    return mirrored_proposals(mirrored,budget=budget,verify=False)


def mirrored_replay(mirrored:dict,budget:int=DEFAULT_BUDGET):
    return mirrored_proposals(mirrored,budget=budget,verify=True)


def mirrored_abstain(mirrored:dict,budget:int=DEFAULT_BUDGET):
    return result([],0,budget)


ARMS={
    "A_MIRROR_FORWARD_EXACT":mirrored_exact,
    "B_MIRROR_PROPOSALS_UNVERIFIED":mirrored_proposals_only,
    "C_MIRROR_PROPOSALS_PLUS_REPLAY":mirrored_replay,
    "D_STRONG_EXACT_MIRROR":mirrored_exact,
    "E_ALWAYS_ABSTAIN":mirrored_abstain,
}


def count_forward_edges(original:dict)->int:
    return sum(len(v) for block in original["forward_edges"].values() for v in block.values())


def audit():
    if BUDGET!=DEFAULT_BUDGET:
        raise ValueError("R5F stock budget drift detected")
    rows=run_split("heldout")
    if len(rows)!=600:raise ValueError("stock R5F heldout changed")
    cumulative={k:Counter() for k in ARMS}
    times={k:[] for k in ARMS}
    original_scores={k:Counter() for k in ("forward","reverse_only","reverse_replay")}
    exact_mirror_matches=0; replay_mirror_matches=0; report_utc_preserved=0
    input_sha=hashlib.sha256()
    baseline_edge_counts=set()
    for inp,scenario,family in rows:
        m=mirror_case(inp)
        baseline_edge_counts.add(count_forward_edges(inp))
        if (sum(len(v) for block in m["forward_edges"].values()
                 for v in block.values()) != count_forward_edges(inp)):
            raise ValueError("mirror lost edge multiplicity")
        if [r["capture_utc"] for r in m["witness_reports"]] != [r["capture_utc"] for r in inp["witness_reports"]]:
            raise ValueError("physical timestamps modified")
        report_utc_preserved+=1
        input_sha.update(json.dumps(m,sort_keys=True,separators=(",",":")).encode())
        # Gold defined by original exact graph. Never interpret as real past.
        reference=forward_only(inp,budget=BUDGET)["prediction"]
        stock_rev=reverse_only(inp,budget=BUDGET)["prediction"]
        stock_replay=reverse_then_forward(inp,budget=BUDGET)["prediction"]
        for n,pred in [("forward",reference),("reverse_only",stock_rev),
                       ("reverse_replay",stock_replay)]:
            original_scores[n]["answered"]+=int(pred!=ABSTAIN)
        for name,fn in ARMS.items():
            t0=perf_counter_ns()
            out=fn(m,budget=DEFAULT_BUDGET)
            times[name].append((perf_counter_ns()-t0)/1000)
            p=out["prediction"]
            s=cumulative[name]
            s["total"]+=1
            s["answered"]+=int(p!=ABSTAIN)
            s["correct_answers"]+=int(p==reference and p!=ABSTAIN)
            s["incorrect_answers"]+=int(p!=reference and p!=ABSTAIN)
            s["unsupported_claims"]+=int(p!=ABSTAIN and reference==ABSTAIN)
            s["exact_matches"]+=int(p==reference)
            s["operations"]+=out["operations"]
            s["over_budget"]+=int(out["budget_exceeded"])
        exact_mirror_matches+=int(mirrored_exact(m)["prediction"]==reference)
        replay_mirror_matches+=int(mirrored_replay(m)["prediction"]==stock_replay)
    if baseline_edge_counts!={STOCK_FORWARD_EDGE_COUNT}:
        raise ValueError("not 9-edge stock workload")
    metrics={}
    for name,s in cumulative.items():
        coverage=s["answered"]/s["total"]
        metrics[name]={
            "cases":s["total"],
            "answered":s["answered"],
            "coverage":round(coverage,6),
            "selective_accuracy":round(s["correct_answers"]/s["answered"],6) if s["answered"] else None,
            "incorrect_nonabstentions":s["incorrect_answers"],
            "unsupported_claims":s["unsupported_claims"],
            "exact_matches":s["exact_matches"],
            "mean_counted_operations_per_case":round(s["operations"]/s["total"],4),
            "budget_exceeded_cases":s["over_budget"],
            "median_runtime_microseconds_single_runner":round(statistics.median(times[name]),4),
        }
    strong=metrics["D_STRONG_EXACT_MIRROR"];trial=metrics["C_MIRROR_PROPOSALS_PLUS_REPLAY"]
    return {
        "schema":"janus.demihead.tachyon.r5f_stock_mirror_reversal_audit.v1",
        "status":"RESEARCH_SYNTHETIC_MIRROR_CONSISTENCY_ONLY__SCIENCE_HOLD",
        "stock_budget_operations_per_case":DEFAULT_BUDGET,
        "stock_graph_edges_per_case":STOCK_FORWARD_EDGE_COUNT,
        "challenge_cases":len(rows),
        "scenario_count":len(SCENARIOS),
        "prior_negative999_gate_not_applied":True,
        "prior_x100_expansion_not_applied":True,
        "same_original_heldout_input_sha256":digest(rows),
        "mirrored_graph_input_sha256":input_sha.hexdigest(),
        "mirror_direction":"C_TO_B_TO_A",
        "synthetic_coordinate_inversion":"original abstract levels A=0 B=1 C=2 map to C=0 B=1 A=2",
        "physical_UTC_unchanged_cases":report_utc_preserved,
        "original_stock_answers":{n:x["answered"] for n,x in original_scores.items()},
        "original_forward_vs_exact_mirror_predictions_equal_cases":exact_mirror_matches,
        "original_reverse_replay_vs_mirror_replay_predictions_equal_cases":replay_mirror_matches,
        "arms":metrics,
        "mirror_replay_gain_vs_strong_exact":trial["coverage"]>strong["coverage"] and trial["unsupported_claims"]<=strong["unsupported_claims"],
        "total_nonabstention_unsafe":sum(v["unsupported_claims"] for v in metrics.values()),
        "gold_scope":"Unique path under the original authoritative causal DAG and simulated witness constraints; exact mirror is algebraically isomorphic by construction",
        "workload_scope":"Same generator and same 600 cases; reverse represented by DAG transpose, NOT a new external dataset.",
        "no_causal_conclusion_from_negative_time":True,
        "external_custodian":False,
        "real_physical_time_reversal":False,
        "human_memory_measured":False,
        "neural_training_or_production_weights_changed":False,
        "science_gate":SCIENTIFIC_GATE,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--audit",action="store_true")
    args=ap.parse_args()
    if not args.audit:ap.error("--audit required")
    r=audit()
    print(json.dumps(r,sort_keys=True,indent=2,ensure_ascii=False))
    assert r["original_forward_vs_exact_mirror_predictions_equal_cases"]==600
    assert r["original_reverse_replay_vs_mirror_replay_predictions_equal_cases"]==600
    assert r["total_nonabstention_unsafe"]==0


if __name__=="__main__":
    main()
