from __future__ import annotations

import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from latency_resource_holdout import (  # noqa: E402
    ALLOWED_SCIENTIFIC_STATUSES,
    Config,
    FREEZE_SHA256,
    admission_checks,
    canonical_sha256,
    load_frozen_corpus,
    make_packet,
    nearest_rank,
    protected_boundary,
    select_candidate,
    semantic_receipt,
)
from hemisphere_bridge import combine_packets  # noqa: E402
from hemisphere_local_proposal import build_proposal, envelope  # noqa: E402


class LatencyResourceHoldoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.corpus_path = ROOT / "holdout" / "latency_resource_v1" / "frozen_corpus.json"

    def test_frozen_hash_is_exact_and_mutation_is_rejected(self) -> None:
        corpus = load_frozen_corpus(self.corpus_path)
        self.assertEqual(corpus["freeze_sha256"], FREEZE_SHA256)
        self.assertEqual(canonical_sha256(corpus["freeze_payload"]), FREEZE_SHA256)

        mutated = deepcopy(corpus)
        mutated["freeze_payload"]["measurement"]["calibration_repeats"] = 22
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mutated.json"
            path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_frozen_corpus(path)

    def test_nearest_rank(self) -> None:
        values = [9, 1, 5, 3, 7]
        self.assertEqual(nearest_rank(values, 0.50), 5)
        self.assertEqual(nearest_rank(values, 0.95), 9)
        self.assertEqual(nearest_rank(values, 0.99), 9)
        with self.assertRaises(ValueError):
            nearest_rank([], 0.50)
        with self.assertRaises(ValueError):
            nearest_rank(values, 0.0)

    def test_packet_generator_is_deterministic(self) -> None:
        first = make_packet(
            "LEFT_HRAIN", node_count=12, shared_labels=3, case_id="TEST-B-012"
        )
        second = make_packet(
            "LEFT_HRAIN", node_count=12, shared_labels=3, case_id="TEST-B-012"
        )
        self.assertEqual(first, second)
        self.assertEqual(canonical_sha256(first), canonical_sha256(second))
        self.assertEqual(len(first["graph"]["nodes"]), 12)
        self.assertEqual(len(first["graph"]["links"]), 11)

    def test_real_bridge_protected_boundary(self) -> None:
        left = make_packet(
            "LEFT_HRAIN", node_count=8, shared_labels=4, case_id="TEST-BRIDGE"
        )
        right = make_packet(
            "RIGHT_INAIHR", node_count=8, shared_labels=4, case_id="TEST-BRIDGE"
        )
        result = combine_packets(left=left, right=right)
        boundary = protected_boundary(result)
        self.assertFalse(boundary["external_effect_permitted"])
        self.assertFalse(boundary["truth_claim_made"])
        self.assertEqual(boundary["authority_delta"], 0)
        self.assertEqual(boundary["mass_effect_budget_delta"], 0)

    def test_real_proposal_protected_boundary(self) -> None:
        packet = make_packet(
            "RIGHT_INAIHR", node_count=8, shared_labels=0, case_id="TEST-PROPOSAL"
        )
        proposal = build_proposal(
            packet,
            proposal_id="proposal.test.0001",
            node_id="node.test.0001",
            label="Candidate context",
            created_at="2026-08-16T10:45:00Z",
        )
        wrapped = envelope(proposal)
        boundary = protected_boundary(wrapped)
        control = boundary["proposal_control"]
        self.assertFalse(control["auto_apply"])
        self.assertTrue(control["requires_explicit_local_accept"])
        self.assertFalse(control["external_effect_permitted"])
        self.assertEqual(control["authority_delta"], 0)

    def test_sequential_and_threaded_semantic_receipts_match(self) -> None:
        cases = [
            {
                "case_id": "TEST-B-008",
                "kind": "bridge",
                "left_nodes": 8,
                "right_nodes": 8,
                "shared_labels": 4,
            },
            {
                "case_id": "TEST-P-L-008",
                "kind": "proposal",
                "hemisphere": "LEFT_HRAIN",
                "nodes": 8,
            },
            {
                "case_id": "TEST-P-R-008",
                "kind": "proposal",
                "hemisphere": "RIGHT_INAIHR",
                "nodes": 8,
            },
        ]
        baseline = semantic_receipt(
            cases, Config("BASELINE_SEQ", "sequential", 1, "baseline"), 1
        )
        threaded = semantic_receipt(
            cases, Config("THREADS_2", "thread_pool", 2, "candidate"), 1
        )
        self.assertEqual(baseline["output_digest"], threaded["output_digest"])
        self.assertEqual(
            baseline["protected_boundary_digest"], threaded["protected_boundary_digest"]
        )
        self.assertTrue(threaded["protected_boundaries_valid"])

    def test_selection_uses_only_supplied_calibration_metrics(self) -> None:
        calibration = {
            "BASELINE_SEQ": {
                "p95_wall_ns": 1000,
                "p50_wall_ns": 900,
                "p95_cpu_ns": 950,
                "peak_memory_bytes": 100,
            },
            "THREADS_2": {
                "p95_wall_ns": 800,
                "p50_wall_ns": 700,
                "p95_cpu_ns": 900,
                "peak_memory_bytes": 120,
            },
            "THREADS_4": {
                "p95_wall_ns": 850,
                "p50_wall_ns": 650,
                "p95_cpu_ns": 800,
                "peak_memory_bytes": 110,
            },
        }
        self.assertEqual(select_candidate(calibration), "THREADS_2")

    def test_faster_but_semantically_mutated_candidate_is_rejected(self) -> None:
        baseline = {
            "p95_wall_ns": 1000,
            "p99_wall_ns": 1100,
            "p95_cpu_ns": 1000,
            "peak_memory_bytes": 1000,
            "timeout_rate": 0.0,
            "error_rate": 0.0,
        }
        candidate = {
            "p95_wall_ns": 800,
            "p99_wall_ns": 900,
            "p95_cpu_ns": 900,
            "peak_memory_bytes": 900,
            "timeout_rate": 0.0,
            "error_rate": 0.0,
        }
        thresholds = {
            "minimum_p95_wall_improvement_fraction": 0.05,
            "maximum_p99_wall_regression_fraction": 0.05,
            "maximum_p95_cpu_regression_fraction": 0.05,
            "maximum_peak_memory_regression_fraction": 0.10,
            "maximum_timeout_rate": 0.0,
            "maximum_error_rate": 0.0,
        }
        checks = admission_checks(
            baseline,
            candidate,
            thresholds,
            semantic_equal=False,
            protected_equal=True,
        )
        self.assertTrue(checks["minimum_p95_wall_improvement"])
        self.assertFalse(checks["exact_output_digest_equality"])
        self.assertFalse(all(checks.values()))

    def test_no_candidate_is_a_valid_scientific_status(self) -> None:
        self.assertIn("NO_CANDIDATE_ADMITTED", ALLOWED_SCIENTIFIC_STATUSES)
        self.assertIn("PERFORMANCE_CANDIDATE_ADMITTED", ALLOWED_SCIENTIFIC_STATUSES)
        self.assertNotIn("BENCHMARK_INTEGRITY_FAIL", ALLOWED_SCIENTIFIC_STATUSES)


if __name__ == "__main__":
    unittest.main()
