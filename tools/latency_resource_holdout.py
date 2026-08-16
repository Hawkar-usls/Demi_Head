from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import time
import tracemalloc
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from hemisphere_bridge import BRIDGE_CONTRACT, HEMISPHERE_RULES, combine_packets
from hemisphere_local_proposal import build_proposal, envelope


SCHEMA = "janus.demihead.latency_resource_holdout.v1"
FREEZE_SHA256 = "e92f2441825cf56c8876cc522e056e21bd93bc9ceff7434aedde4cd29879efa3"
RESULT_SCHEMA = "janus.demihead.latency_resource_result.v1"
ALLOWED_SCIENTIFIC_STATUSES = {
    "PERFORMANCE_CANDIDATE_ADMITTED",
    "NO_CANDIDATE_ADMITTED",
}


@dataclass(frozen=True)
class Config:
    config_id: str
    executor: str
    workers: int
    role: str


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def nearest_rank(values: Iterable[int], percentile: float) -> int:
    ordered = sorted(int(value) for value in values)
    if not ordered:
        raise ValueError("nearest_rank requires at least one value")
    if not 0 < percentile <= 1:
        raise ValueError("percentile must be in (0, 1]")
    rank = max(1, math.ceil(percentile * len(ordered)))
    return ordered[rank - 1]


def load_frozen_corpus(path: Path) -> dict[str, Any]:
    corpus = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(corpus, dict) or corpus.get("schema") != SCHEMA:
        raise ValueError("Unexpected latency/resource holdout schema")
    payload = corpus.get("freeze_payload")
    if not isinstance(payload, dict):
        raise ValueError("freeze_payload must be an object")
    actual = canonical_sha256(payload)
    if corpus.get("freeze_sha256") != FREEZE_SHA256 or actual != FREEZE_SHA256:
        raise ValueError(
            f"Frozen latency/resource corpus hash mismatch: declared={corpus.get('freeze_sha256')} actual={actual}"
        )
    if payload.get("frozen_before_first_execution") is not True:
        raise ValueError("Performance corpus was not frozen before first execution")
    return corpus


def _origin_for(index: int, hemisphere: str) -> str:
    if hemisphere == "LEFT_HRAIN":
        return ("USER", "SYSTEM", "LOCAL_FALLBACK")[index % 3]
    return ("SYSTEM", "LOCAL_FALLBACK", "REMOTE_AI")[index % 3]


def _node(hemisphere: str, node_id: int, label: str) -> dict[str, Any]:
    if hemisphere == "LEFT_HRAIN":
        return {
            "id": node_id,
            "label": label,
            "origin": _origin_for(node_id, hemisphere),
            "type": "default",
        }
    origin = _origin_for(node_id, hemisphere)
    return {
        "id": node_id,
        "label": f"🧩 {label}",
        "origin": origin,
        "is_ai": origin == "REMOTE_AI",
    }


def make_packet(
    hemisphere: str,
    *,
    node_count: int,
    shared_labels: int = 0,
    case_id: str,
) -> dict[str, Any]:
    if hemisphere not in HEMISPHERE_RULES:
        raise ValueError(f"Unknown hemisphere {hemisphere}")
    if node_count < 1:
        raise ValueError("node_count must be positive")
    if not 0 <= shared_labels <= node_count:
        raise ValueError("shared_labels must be between zero and node_count")

    rules = HEMISPHERE_RULES[hemisphere]
    nodes: list[dict[str, Any]] = []
    side = "Left" if hemisphere == "LEFT_HRAIN" else "Right"
    for index in range(node_count):
        if index < shared_labels:
            label = f"Shared Context {index:04d}"
        else:
            label = f"{side} Context {case_id} {index:04d}"
        nodes.append(_node(hemisphere, index + 1, label))

    links = [
        {"source": index, "target": index + 1}
        for index in range(1, node_count)
    ]
    return {
        "schema": "janus.demihead.hemisphere_packet.v1",
        "packet_id": f"perf-{case_id}-{hemisphere.lower()}",
        "hemisphere": hemisphere,
        "role": rules["role"],
        "captured_at": "2026-08-16T10:45:00Z",
        "source": {
            "repository": rules["repository"],
            "bridge_contract": BRIDGE_CONTRACT,
            "source_revision": "PERFORMANCE_SYNTHETIC_FIXTURE_V1",
            "workspace_mode": rules["workspace_mode"],
        },
        "graph": {"nodes": nodes, "links": links},
        "control": {
            "read_only_transfer": True,
            "direct_cross_hemisphere_mutation": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def execute_case(case: dict[str, Any], inner_loops: int) -> dict[str, Any]:
    kind = case["kind"]
    case_id = case["case_id"]
    output: dict[str, Any] | None = None
    for _ in range(inner_loops):
        if kind == "bridge":
            left = make_packet(
                "LEFT_HRAIN",
                node_count=int(case["left_nodes"]),
                shared_labels=int(case["shared_labels"]),
                case_id=case_id,
            )
            right = make_packet(
                "RIGHT_INAIHR",
                node_count=int(case["right_nodes"]),
                shared_labels=int(case["shared_labels"]),
                case_id=case_id,
            )
            output = combine_packets(left=left, right=right)
        elif kind == "proposal":
            hemisphere = str(case["hemisphere"])
            packet = make_packet(
                hemisphere,
                node_count=int(case["nodes"]),
                shared_labels=0,
                case_id=case_id,
            )
            safe_case_id = case_id.replace("-", ".").lower()
            proposal = build_proposal(
                packet,
                proposal_id=f"proposal.perf.{safe_case_id}",
                node_id=f"node.perf.{safe_case_id}",
                label=f"Performance candidate {case_id}",
                created_at="2026-08-16T10:45:00Z",
            )
            output = envelope(proposal)
        else:
            raise ValueError(f"Unknown workload kind: {kind}")
    assert output is not None
    return output


def protected_boundary(output: dict[str, Any]) -> dict[str, Any]:
    if output.get("schema") == "janus.demihead.bicameral_result.v1":
        routing = output["routing"]
        ceiling = output["claim_ceiling"]
        boundary = {
            "kind": "bridge",
            "external_effect_permitted": routing["external_effect_permitted"],
            "direct_cross_hemisphere_write_permitted": routing[
                "direct_cross_hemisphere_write_permitted"
            ],
            "truth_claim_made": ceiling["truth_claim_made"],
            "agreement_is_truth": ceiling["agreement_is_truth"],
            "hemisphere_count_is_authority": ceiling["hemisphere_count_is_authority"],
            "authority_delta": ceiling["authority_delta"],
            "mass_effect_budget_delta": ceiling["mass_effect_budget_delta"],
        }
        if boundary != {
            "kind": "bridge",
            "external_effect_permitted": False,
            "direct_cross_hemisphere_write_permitted": False,
            "truth_claim_made": False,
            "agreement_is_truth": False,
            "hemisphere_count_is_authority": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        }:
            raise ValueError("Bridge protected boundary drifted")
        return boundary

    if output.get("type") == "JANUS_DEMIHEAD_LOCAL_PROPOSAL_V1":
        control = output["proposal"]["control"]
        exact = {
            "auto_apply": False,
            "requires_explicit_local_accept": True,
            "direct_cross_hemisphere_write": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        }
        if control != exact:
            raise ValueError("Proposal protected control boundary drifted")
        return {"kind": "proposal", "proposal_control": control}

    raise ValueError("Unknown output kind while extracting protected boundary")


def _run_cases(
    cases: list[dict[str, Any]],
    config: Config,
    inner_loops: int,
    *,
    observer: bool = False,
) -> list[dict[str, Any]]:
    indexed = list(enumerate(cases))

    def task(item: tuple[int, dict[str, Any]]) -> tuple[int, dict[str, Any]]:
        index, case = item
        output = execute_case(case, inner_loops)
        if observer:
            # Bounded observer work. It is measured separately and never participates
            # in candidate selection, truth, authority, or semantic output.
            canonical_sha256(output)
            time.perf_counter_ns()
        return index, output

    if config.executor == "sequential":
        results = [task(item) for item in indexed]
    elif config.executor == "thread_pool":
        with ThreadPoolExecutor(max_workers=config.workers) as pool:
            futures = [pool.submit(task, item) for item in indexed]
            results = [future.result() for future in as_completed(futures)]
    else:
        raise ValueError(f"Unknown executor: {config.executor}")

    results.sort(key=lambda item: item[0])
    return [output for _, output in results]


def semantic_receipt(
    cases: list[dict[str, Any]], config: Config, inner_loops: int
) -> dict[str, Any]:
    outputs = _run_cases(cases, config, inner_loops)
    boundaries = [protected_boundary(output) for output in outputs]
    return {
        "output_digest": canonical_sha256(outputs),
        "protected_boundary_digest": canonical_sha256(boundaries),
        "protected_boundaries_valid": True,
    }


def _summarize_samples(samples: list[dict[str, int]], peak_memory_bytes: int) -> dict[str, Any]:
    wall = [sample["wall_ns"] for sample in samples]
    cpu = [sample["cpu_ns"] for sample in samples]
    timeouts = sum(sample["timeout"] for sample in samples)
    errors = sum(sample["error"] for sample in samples)
    return {
        "repeat_count": len(samples),
        "p50_wall_ns": nearest_rank(wall, 0.50),
        "p95_wall_ns": nearest_rank(wall, 0.95),
        "p99_wall_ns": nearest_rank(wall, 0.99),
        "p50_cpu_ns": nearest_rank(cpu, 0.50),
        "p95_cpu_ns": nearest_rank(cpu, 0.95),
        "p99_cpu_ns": nearest_rank(cpu, 0.99),
        "peak_memory_bytes": int(peak_memory_bytes),
        "timeout_count": int(timeouts),
        "error_count": int(errors),
        "timeout_rate": timeouts / len(samples),
        "error_rate": errors / len(samples),
    }


def benchmark_config(
    cases: list[dict[str, Any]],
    config: Config,
    *,
    warmup_repeats: int,
    repeats: int,
    inner_loops: int,
    timeout_ms: int,
) -> dict[str, Any]:
    for _ in range(warmup_repeats):
        _run_cases(cases, config, inner_loops)

    samples: list[dict[str, int]] = []
    for _ in range(repeats):
        wall_start = time.perf_counter_ns()
        cpu_start = time.process_time_ns()
        error = 0
        try:
            _run_cases(cases, config, inner_loops)
        except Exception:
            error = 1
        cpu_end = time.process_time_ns()
        wall_end = time.perf_counter_ns()
        wall_ns = wall_end - wall_start
        samples.append(
            {
                "wall_ns": wall_ns,
                "cpu_ns": cpu_end - cpu_start,
                "timeout": int(wall_ns > timeout_ms * 1_000_000),
                "error": error,
            }
        )

    tracemalloc.start()
    try:
        _run_cases(cases, config, inner_loops)
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    return _summarize_samples(samples, peak)


def select_candidate(calibration_metrics: dict[str, dict[str, Any]]) -> str:
    candidates = [config_id for config_id in calibration_metrics if config_id != "BASELINE_SEQ"]
    if not candidates:
        raise ValueError("No performance candidates available")
    return min(
        candidates,
        key=lambda config_id: (
            calibration_metrics[config_id]["p95_wall_ns"],
            calibration_metrics[config_id]["p50_wall_ns"],
            calibration_metrics[config_id]["p95_cpu_ns"],
            calibration_metrics[config_id]["peak_memory_bytes"],
            config_id,
        ),
    )


def admission_checks(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    thresholds: dict[str, Any],
    *,
    semantic_equal: bool,
    protected_equal: bool,
) -> dict[str, bool]:
    p95_wall_ratio = candidate["p95_wall_ns"] / baseline["p95_wall_ns"]
    p99_wall_ratio = candidate["p99_wall_ns"] / baseline["p99_wall_ns"]
    p95_cpu_ratio = candidate["p95_cpu_ns"] / baseline["p95_cpu_ns"]
    memory_ratio = candidate["peak_memory_bytes"] / baseline["peak_memory_bytes"]
    return {
        "minimum_p95_wall_improvement": p95_wall_ratio
        <= 1.0 - float(thresholds["minimum_p95_wall_improvement_fraction"]),
        "p99_wall_within_limit": p99_wall_ratio
        <= 1.0 + float(thresholds["maximum_p99_wall_regression_fraction"]),
        "p95_cpu_within_limit": p95_cpu_ratio
        <= 1.0 + float(thresholds["maximum_p95_cpu_regression_fraction"]),
        "peak_memory_within_limit": memory_ratio
        <= 1.0 + float(thresholds["maximum_peak_memory_regression_fraction"]),
        "zero_candidate_timeouts": candidate["timeout_rate"]
        <= float(thresholds["maximum_timeout_rate"]),
        "zero_candidate_errors": candidate["error_rate"]
        <= float(thresholds["maximum_error_rate"]),
        "exact_output_digest_equality": semantic_equal,
        "protected_boundary_equality": protected_equal,
    }


def measure_observer_overhead(
    cases: list[dict[str, Any]],
    config: Config,
    *,
    repeats: int,
    inner_loops: int,
) -> dict[str, Any]:
    pairs: list[dict[str, int]] = []
    for index in range(repeats):
        order = (False, True) if index % 2 == 0 else (True, False)
        measured: dict[bool, int] = {}
        for observer in order:
            start = time.perf_counter_ns()
            _run_cases(cases, config, inner_loops, observer=observer)
            measured[observer] = time.perf_counter_ns() - start
        pairs.append({"off_ns": measured[False], "on_ns": measured[True]})

    ratios = [pair["on_ns"] / pair["off_ns"] for pair in pairs]
    deltas = [pair["on_ns"] - pair["off_ns"] for pair in pairs]
    ordered_ratios = sorted(ratios)
    return {
        "paired_repeats": len(pairs),
        "alternating_order": True,
        "p50_ratio": ordered_ratios[len(ordered_ratios) // 2],
        "p50_delta_ns": nearest_rank(deltas, 0.50),
        "used_for_candidate_selection": False,
        "used_for_admission": False,
    }


def _config_objects(payload: dict[str, Any]) -> dict[str, Config]:
    result: dict[str, Config] = {}
    for value in payload["candidate_grid"]:
        config = Config(
            config_id=value["config_id"],
            executor=value["executor"],
            workers=int(value["workers"]),
            role=value["role"],
        )
        result[config.config_id] = config
    return result


def run_holdout(corpus_path: Path) -> dict[str, Any]:
    corpus = load_frozen_corpus(corpus_path)
    payload = corpus["freeze_payload"]
    measurement = payload["measurement"]
    configs = _config_objects(payload)
    calibration_cases = payload["calibration_cases"]
    holdout_cases = payload["holdout_cases"]
    inner_loops = int(measurement["inner_loops_per_case"])
    timeout_ms = int(measurement["timeout_ms_per_repeat"])

    calibration_metrics: dict[str, dict[str, Any]] = {}
    calibration_receipts: dict[str, dict[str, Any]] = {}
    for config_id in ("BASELINE_SEQ", "THREADS_2", "THREADS_4"):
        config = configs[config_id]
        calibration_receipts[config_id] = semantic_receipt(calibration_cases, config, inner_loops)
        calibration_metrics[config_id] = benchmark_config(
            calibration_cases,
            config,
            warmup_repeats=int(measurement["warmup_repeats"]),
            repeats=int(measurement["calibration_repeats"]),
            inner_loops=inner_loops,
            timeout_ms=timeout_ms,
        )

    selected = select_candidate(calibration_metrics)
    holdout_metrics: dict[str, dict[str, Any]] = {}
    holdout_receipts: dict[str, dict[str, Any]] = {}
    for config_id in ("BASELINE_SEQ", selected):
        config = configs[config_id]
        holdout_receipts[config_id] = semantic_receipt(holdout_cases, config, inner_loops)
        holdout_metrics[config_id] = benchmark_config(
            holdout_cases,
            config,
            warmup_repeats=int(measurement["warmup_repeats"]),
            repeats=int(measurement["holdout_repeats"]),
            inner_loops=inner_loops,
            timeout_ms=timeout_ms,
        )

    baseline_cal = calibration_receipts["BASELINE_SEQ"]
    selected_cal = calibration_receipts[selected]
    baseline_hold = holdout_receipts["BASELINE_SEQ"]
    selected_hold = holdout_receipts[selected]
    semantic_equal = (
        baseline_cal["output_digest"] == selected_cal["output_digest"]
        and baseline_hold["output_digest"] == selected_hold["output_digest"]
    )
    protected_equal = (
        baseline_cal["protected_boundary_digest"] == selected_cal["protected_boundary_digest"]
        and baseline_hold["protected_boundary_digest"] == selected_hold["protected_boundary_digest"]
        and all(receipt["protected_boundaries_valid"] for receipt in calibration_receipts.values())
        and all(receipt["protected_boundaries_valid"] for receipt in holdout_receipts.values())
    )

    baseline_metrics = holdout_metrics["BASELINE_SEQ"]
    selected_metrics = holdout_metrics[selected]
    checks = admission_checks(
        baseline_metrics,
        selected_metrics,
        payload["admission_thresholds"],
        semantic_equal=semantic_equal,
        protected_equal=protected_equal,
    )
    baseline_integrity = (
        baseline_metrics["timeout_rate"] == 0.0
        and baseline_metrics["error_rate"] == 0.0
        and baseline_cal["protected_boundaries_valid"]
        and baseline_hold["protected_boundaries_valid"]
    )
    benchmark_integrity = baseline_integrity and semantic_equal and protected_equal
    if not benchmark_integrity:
        status = "BENCHMARK_INTEGRITY_FAIL"
    elif all(checks.values()):
        status = "PERFORMANCE_CANDIDATE_ADMITTED"
    else:
        status = "NO_CANDIDATE_ADMITTED"

    observer = measure_observer_overhead(
        calibration_cases,
        configs["BASELINE_SEQ"],
        repeats=int(measurement["observer_overhead_repeats"]),
        inner_loops=inner_loops,
    )

    return {
        "schema": RESULT_SCHEMA,
        "status": status,
        "freeze_sha256": FREEZE_SHA256,
        "parent_demihead_sha": payload["parent_demihead_sha"],
        "environment": {
            "python": sys.version.split()[0],
            "implementation": platform.python_implementation(),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "github_actions": os.getenv("GITHUB_ACTIONS") == "true",
            "runner_os": os.getenv("RUNNER_OS"),
            "runner_arch": os.getenv("RUNNER_ARCH"),
        },
        "protocol": {
            "selection_uses_calibration_only": True,
            "holdout_may_not_change_selection": True,
            "calibration_repeats": measurement["calibration_repeats"],
            "holdout_repeats": measurement["holdout_repeats"],
            "inner_loops_per_case": inner_loops,
            "quantile_method": "nearest_rank",
        },
        "calibration": {
            "metrics": calibration_metrics,
            "semantic_receipts": calibration_receipts,
            "selected_candidate": selected,
            "selection_metric": "p95_wall_ns_min",
        },
        "holdout": {
            "executed_configs": ["BASELINE_SEQ", selected],
            "metrics": holdout_metrics,
            "semantic_receipts": holdout_receipts,
            "admission_checks": checks,
        },
        "observer_overhead": observer,
        "scientific_result": {
            "speed_improvement_established": status == "PERFORMANCE_CANDIDATE_ADMITTED",
            "negative_performance_certificate": status == "NO_CANDIDATE_ADMITTED",
            "failed_or_slower_candidates_preserved": True,
        },
        "integrity": {
            "benchmark_integrity_pass": benchmark_integrity,
            "exact_output_digest_equality": semantic_equal,
            "protected_boundary_equality": protected_equal,
            "baseline_errors": baseline_metrics["error_count"],
            "baseline_timeouts": baseline_metrics["timeout_count"],
        },
        "claim_ceiling": {
            "functional_correctness_implied_by_performance": False,
            "production_latency_established": False,
            "cross_machine_generalization_established": False,
            "production_readiness_established": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen DemiHead latency/resource holdout")
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    result = run_holdout(Path(args.corpus))
    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")

    if result["status"] == "BENCHMARK_INTEGRITY_FAIL":
        raise SystemExit(2)
    if result["status"] not in ALLOWED_SCIENTIFIC_STATUSES:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
