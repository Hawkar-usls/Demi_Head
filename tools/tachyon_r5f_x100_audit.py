"""TACHYON R5F-X100: real graph-work expansion + 100x operation allowance.

Two separate interventions:
1. BUDGET_ONLY: old graph with 500 -> 50,000 operations.
2. GRAPH_X100: 100 disjoint copies of the base A/B causal fan-in,
   all pointing to the same observed C, at budget=50,000.

This actually expands candidate causal work; it does NOT multiply a counter,
repeat the same evaluation 100 times, or insert fake source confirmations.
Old source code and reference weights remain unchanged. Gold is the unique
history under the authoritative complete DAG (NOT real physical history).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import statistics
from collections import Counter
from time import perf_counter_ns

from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN,
    BUDGET as ORIGINAL_BUDGET,
    SCENARIOS,
    build_case,
    forward_only,
    reverse_only,
    reverse_then_forward,
    always_abstain,
    run_split,
)

SCALE = 100
BUDGET = ORIGINAL_BUDGET * SCALE
ARMS = {
    "A_FORWARD_ONLY_EXHAUSTIVE": forward_only,
    "B_REVERSE_ONLY_UNVERIFIED": reverse_only,
    "C_REVERSE_PLUS_FORWARD_REPLAY": reverse_then_forward,
    "D_STRONG_EXHAUSTIVE_PROVENANCE": forward_only,
    "E_ALWAYS_ABSTAIN": always_abstain,
}
RESEARCH_GATE = "SYNTHETIC_X100_ENGINEERING_ONLY__CAUSAL_GAIN_UNPROVEN__SCIENCE_HOLD"


def expand_graph_x100(original: dict, replicas: int = SCALE) -> dict:
    """Embed original graph and (replicas-1) competitor causal subgraphs.

    No new witness reports are generated. Each new subgraph supplies extra
    alternative causes of observed C; other terminal C1 remains unobserved.
    Completeness status and original decoy/incomplete reverse pointers retain
    their meaning. All graphs remain acyclic A->B->C.
    """
    if not isinstance(replicas, int) or replicas < 1:
        raise ValueError("replicas must be a positive integer")
    if original.get("synthetic_only") is not True:
        raise ValueError("only synthetic graphs supported")
    o = json.loads(json.dumps(original))
    ab = o["forward_edges"]["A_B"]
    bc = o["forward_edges"]["B_C"]
    rev_cb = o["reverse_proposals"]["C_B"]
    rev_ba = o["reverse_proposals"]["B_A"]
    base_ab = {a: list(bs) for a, bs in ab.items()}
    base_bc = {b: list(cs) for b, cs in bc.items()}
    terminal = o["terminal"]
    for replica in range(1, replicas):
        prefix = f"__copy{replica}__"
        for a, bs in base_ab.items():
            ab[prefix + a] = [prefix + b for b in bs]
        for b, cs in base_bc.items():
            bc[prefix + b] = [terminal if c == terminal else prefix + c for c in cs]
        for b, cs in base_bc.items():
            for c in cs:
                out_c = terminal if c == terminal else prefix + c
                rev_cb.setdefault(out_c, []).append(prefix + b)
        for a, bs in base_ab.items():
            for b in bs:
                rev_ba.setdefault(prefix + b, []).append(prefix + a)
    o["schema"] = "janus.tachyon.r5f_x100.expanded_graph.v1"
    o["case_ref"] = hashlib.sha256((o["case_ref"] + "/" + str(replicas)).encode()).hexdigest()[:16]
    o["graph_replicas"] = replicas
    o["expansion_kind"] = "100_DISTINCT_CAUSAL_FANIN_SUBGRAPHS__NO_NEW_WITNESS_REPORTS"
    return o


def count_graph_edges(inp: dict) -> int:
    return (sum(map(len, inp["forward_edges"]["A_B"].values())) +
            sum(map(len, inp["forward_edges"]["B_C"].values())))


def _run_one_case(inp: dict, budget: int) -> dict:
    # The full exhaustive semantic oracle intentionally shares the graph
    # semantics with the strong exact baseline. This is NOT hidden real gold.
    truth = forward_only(inp, budget=budget)["prediction"]
    outputs = {}
    for name, fn in ARMS.items():
        start = perf_counter_ns()
        out = fn(inp, budget=budget)
        elapsed = (perf_counter_ns() - start) / 1000
        out["decision_us"] = elapsed
        outputs[name] = out
    return {"gold": truth, "outputs": outputs}


def _evaluate(rows: list, transform, budget: int, *, take_samples: bool) -> dict:
    summaries = {name: Counter() for name in ARMS}
    time_us = {name: [] for name in ARMS}
    example_errors = {name: [] for name in ARMS}
    graph_edges = []
    input_hash = hashlib.sha256()
    case_count = 0
    for original, scenario, family in rows:
        inp = transform(original)
        # Pure verification: no gold, status label or scenario leaked into input.
        assert "gold" not in inp and "scenario" not in inp
        assert "true_history" not in inp and "latent_cause" not in inp
        source_roots = [w["root"] for w in inp["witness_reports"]]
        if len(source_roots) != len([w["root"] for w in original["witness_reports"]]):
            raise AssertionError("expansion changed source witness count")
        graph_edges.append(count_graph_edges(inp))
        input_hash.update(json.dumps(inp, sort_keys=True, separators=(",", ":")).encode())
        res = _run_one_case(inp, budget)
        truth = res["gold"]
        case_count += 1
        for name, out in res["outputs"].items():
            pred = out["prediction"]
            attempted = pred != ABSTAIN
            s = summaries[name]
            s["cases"] += 1
            s["answered"] += int(attempted)
            s["correct_answers"] += int(attempted and pred == truth)
            s["unsupported_answers"] += int(attempted and truth == ABSTAIN)
            s["incorrect_nonabstentions"] += int(attempted and pred != truth)
            s["correct_abstentions"] += int(pred == truth == ABSTAIN)
            s["exact"] += int(pred == truth)
            s["counted_operations"] += out["operations"]
            s["budget_exceeded"] += int(out["budget_exceeded"])
            time_us[name].append(out["decision_us"])
            if take_samples and pred != truth and len(example_errors[name]) < 8:
                example_errors[name].append(inp["case_ref"])
    arms = {}
    for name, s in summaries.items():
        attempted = s["answered"]
        arms[name] = {
            "cases": case_count,
            "answered": attempted,
            "coverage": round(attempted/case_count, 6),
            "selective_accuracy": round(s["correct_answers"]/attempted, 6) if attempted else None,
            "unsupported_assertions": s["unsupported_answers"],
            "incorrect_nonabstentions": s["incorrect_nonabstentions"],
            "correct_abstentions": s["correct_abstentions"],
            "exact_matches": s["exact"],
            "mean_counted_operations_per_case": round(s["counted_operations"]/case_count, 4),
            "budget_exceeded_cases": s["budget_exceeded"],
            "median_decision_microseconds_uncontrolled": round(statistics.median(time_us[name]),4),
            "sample_errors": example_errors[name],
        }
    return {
        "cases": case_count,
        "budget_per_case": budget,
        "average_graph_edges": round(sum(graph_edges)/len(graph_edges), 4),
        "input_stream_sha256": input_hash.hexdigest(),
        "arms": arms,
    }


def audit() -> dict:
    cases = run_split("heldout")
    if len(cases) != 600:
        raise AssertionError("expected unchanged R5F heldout families (600 cases)")
    original = _evaluate(cases, lambda x: x, ORIGINAL_BUDGET, take_samples=False)
    budget_only = _evaluate(cases, lambda x: x, BUDGET, take_samples=False)
    expanded = _evaluate(cases, expand_graph_x100, BUDGET, take_samples=True)
    if original["average_graph_edges"] * SCALE != expanded["average_graph_edges"]:
        raise AssertionError("physical graph edge count not exactly 100x")
    if original["input_stream_sha256"] != budget_only["input_stream_sha256"]:
        raise AssertionError("budget-only changed input data")
    required = ["A_FORWARD_ONLY_EXHAUSTIVE","B_REVERSE_ONLY_UNVERIFIED",
                "C_REVERSE_PLUS_FORWARD_REPLAY","D_STRONG_EXHAUSTIVE_PROVENANCE"]
    result = {
        "schema": "janus.demihead.tachyon.r5f_x100.causal_memory_expansion.v1",
        "status": "X100_GRAPH_AND_BUDGET_CI_RESEARCH_ONLY__SCIENCE_HOLD",
        "scale_graph_edges": SCALE,
        "scale_budget": BUDGET / ORIGINAL_BUDGET,
        "source_r5f_main": "tools/tachyon_r5f_causal_memory_audit.py",
        "synthetic_external_custodian": False,
        "heldout_cases": len(cases),
        "scenarios": len(SCENARIOS),
        "budget_only_intervention": budget_only,
        "original_replayed_control": original,
        "expanded_graph_x100": expanded,
        "operation_ratios_expanded_over_original": {
            name: (round(expanded["arms"][name]["mean_counted_operations_per_case"] /
                         original["arms"][name]["mean_counted_operations_per_case"], 4)
                   if original["arms"][name]["mean_counted_operations_per_case"] else None)
            for name in ARMS
        },
        "original_vs_budget_only_predictions_identical": all(
            all(original["arms"][name][k] == budget_only["arms"][name][k]
                for k in ("answered","incorrect_nonabstentions","exact_matches","unsupported_assertions"))
            for name in ARMS
        ),
        "expanded_zero_unsupported_assertions": all(
            expanded["arms"][name]["unsupported_assertions"] == 0 for name in required),
        "expanded_strong_baseline_exact": expanded["arms"]["D_STRONG_EXHAUSTIVE_PROVENANCE"]["exact_matches"] == len(cases),
        "reverse_plus_replay_superior_to_strong_exact_baseline": (
            expanded["arms"]["C_REVERSE_PLUS_FORWARD_REPLAY"]["coverage"] >
            expanded["arms"]["D_STRONG_EXHAUSTIVE_PROVENANCE"]["coverage"] and
            expanded["arms"]["C_REVERSE_PLUS_FORWARD_REPLAY"]["unsupported_assertions"] <=
            expanded["arms"]["D_STRONG_EXHAUSTIVE_PROVENANCE"]["unsupported_assertions"]
        ),
        "timing_limit": "Same GitHub Actions runner, Python interleaved arms, one measurement; not calibrated, cost proxy is graph-edge/candidate traversals only.",
        "workload_limit": "99 additional replicas create distinct alternative paths, not new genuine physical witnesses. Original DAG semantics and original 600 scenario/instance families reused; no external blind generalization.",
        "semantic_gold_limit": "Uniquely identifiable from the supplied authoritative synthetic graph, so strong exact baseline equals gold by construction.",
        "physical_reverse_time_proven": False,
        "human_memory_measured": False,
        "model_or_production_weights_changed": False,
        "scientific_gate": RESEARCH_GATE,
    }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true")
    args = parser.parse_args()
    if not args.audit: parser.error("--audit required")
    output = audit()
    print(json.dumps(output, indent=2, ensure_ascii=False, sort_keys=True))
    if not output["expanded_zero_unsupported_assertions"]:
        raise SystemExit("UNSUPPORTED_CAUSAL_CLAIMS")
    if not output["expanded_strong_baseline_exact"]:
        raise SystemExit("STRONG_REFERENCE_MISMATCH")


if __name__ == "__main__":
    main()
