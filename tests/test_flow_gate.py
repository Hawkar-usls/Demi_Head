import importlib.util
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "flow_gate.py"
SPEC = importlib.util.spec_from_file_location("flow_gate", MODULE_PATH)
flow_gate = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(flow_gate)
sys.modules["flow_gate"] = flow_gate


class FlowGateTests(unittest.TestCase):
    def test_quota_and_deferred_preserved(self):
        trace = {
            "schema": flow_gate.TRACE_SCHEMA,
            "trace_id": "quota",
            "config": {"quota": 2, "max_waves": 1},
            "work": [
                {"work_id": "a", "observed_outcome": "completed"},
                {"work_id": "b", "observed_outcome": "unknown"},
                {"work_id": "c", "observed_outcome": "failed"},
            ],
        }
        result = flow_gate.run_flow_gate(trace)
        self.assertEqual(result["accounting"]["admitted_count"], 2)
        self.assertEqual(result["accounting"]["deferred_count"], 1)
        self.assertLessEqual(result["accounting"]["max_wave_size"], 2)
        self.assertEqual(result["deferred"][0]["work_id"], "c")

    def test_unknown_is_not_promoted(self):
        trace = {
            "schema": flow_gate.TRACE_SCHEMA,
            "config": {"quota": 1, "max_waves": 1},
            "work": [{"work_id": "u", "observed_outcome": "unknown"}],
        }
        result = flow_gate.run_flow_gate(trace)
        self.assertEqual(result["accounting"]["unknown_observed_count"], 1)
        self.assertEqual(result["accounting"]["completed_observed_count"], 0)

    def test_scheduling_cannot_mutate_evidence_or_authority(self):
        trace = {
            "schema": flow_gate.TRACE_SCHEMA,
            "config": {"quota": 1, "max_waves": 1},
            "work": [{"work_id": "x", "observed_outcome": "completed"}],
        }
        inv = flow_gate.run_flow_gate(trace)["invariants"]
        self.assertFalse(inv["evidence_state_mutated"])
        self.assertFalse(inv["source_roots_mutated"])
        self.assertFalse(inv["provenance_mutated"])
        self.assertEqual(inv["authority_delta"], 0)
        self.assertEqual(inv["mass_effect_budget_delta"], 0)

    def test_duplicate_work_ids_fail_closed(self):
        trace = {
            "schema": flow_gate.TRACE_SCHEMA,
            "config": {"quota": 2, "max_waves": 1},
            "work": [
                {"work_id": "dup", "observed_outcome": "completed"},
                {"work_id": "dup", "observed_outcome": "failed"},
            ],
        }
        with self.assertRaises(ValueError):
            flow_gate.run_flow_gate(trace)

    def test_self_test(self):
        self.assertEqual(flow_gate.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
