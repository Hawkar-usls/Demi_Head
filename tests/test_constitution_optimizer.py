import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "constitution_optimizer.py"
SPEC = importlib.util.spec_from_file_location("constitution_optimizer", MODULE_PATH)
optimizer = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(optimizer)


class ConstitutionOptimizerTests(unittest.TestCase):
    def base_spec(self):
        return {
            "schema": optimizer.SPEC_SCHEMA,
            "experiment_id": "test",
            "objective_order": ["p95_latency_ms", "cpu_time_ms"],
            "trials": [
                {
                    "candidate_id": "safe",
                    "config": {"flow_gate_quota": 2},
                    "metrics": {"p95_latency_ms": 20, "cpu_time_ms": 10},
                    "constraints": {},
                }
            ],
        }

    def test_safe_operational_trial_is_admitted(self):
        result = optimizer.evaluate_trials(self.base_spec())
        self.assertEqual(result["accounting"]["admitted_count"], 1)
        self.assertEqual(result["best_candidate"]["candidate_id"], "safe")

    def test_belief_or_engagement_objective_fails_closed(self):
        spec = self.base_spec()
        spec["trials"].append(
            {
                "candidate_id": "bad",
                "config": {"flow_gate_quota": 8},
                "metrics": {"p95_latency_ms": 1, "cpu_time_ms": 1, "belief_change": 1.0},
                "constraints": {},
            }
        )
        result = optimizer.evaluate_trials(spec)
        bad = next(row for row in result["history"] if row["candidate_id"] == "bad")
        self.assertEqual(bad["admission"], "REJECTED")
        self.assertTrue(any(reason.startswith("FORBIDDEN_OBJECTIVES:") for reason in bad["reasons"]))
        self.assertEqual(result["best_candidate"]["candidate_id"], "safe")

    def test_authority_mutation_fails_closed(self):
        spec = self.base_spec()
        spec["trials"].append(
            {
                "candidate_id": "authority",
                "config": {"flow_gate_quota": 8},
                "metrics": {"p95_latency_ms": 1, "cpu_time_ms": 1},
                "constraints": {"authority_delta_nonzero": True},
            }
        )
        result = optimizer.evaluate_trials(spec)
        row = next(row for row in result["history"] if row["candidate_id"] == "authority")
        self.assertEqual(row["admission"], "REJECTED")

    def test_rejected_trials_are_preserved(self):
        spec = self.base_spec()
        spec["trials"].append(
            {
                "candidate_id": "unknown_metric",
                "config": {"flow_gate_quota": 4},
                "metrics": {"p95_latency_ms": 2, "cpu_time_ms": 2, "mystery": 0},
                "constraints": {},
            }
        )
        result = optimizer.evaluate_trials(spec)
        self.assertEqual(result["accounting"]["trial_count"], 2)
        self.assertEqual(result["accounting"]["rejected_count"], 1)
        self.assertTrue(result["invariants"]["failed_trials_preserved"])

    def test_forbidden_objective_cannot_be_declared_as_rank_target(self):
        spec = self.base_spec()
        spec["objective_order"] = ["engagement"]
        with self.assertRaises(ValueError):
            optimizer.evaluate_trials(spec)

    def test_self_test(self):
        self.assertEqual(optimizer.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
