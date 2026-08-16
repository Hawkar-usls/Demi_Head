import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "correction_propagator.py"
SPEC = importlib.util.spec_from_file_location("correction_propagator", MODULE_PATH)
correction = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(correction)


class CorrectionPropagatorTests(unittest.TestCase):
    def base_graph(self):
        return {
            "schema": correction.INPUT_SCHEMA,
            "graph_id": "test",
            "roots": [{"root_id": "root-A", "current_revision_id": "r3"}],
            "corrections": [
                {
                    "correction_id": "c1",
                    "root_id": "root-A",
                    "superseded_revision_id": "r1",
                    "replacement_revision_id": "r2",
                },
                {
                    "correction_id": "c2",
                    "root_id": "root-A",
                    "superseded_revision_id": "r2",
                    "replacement_revision_id": "r3",
                },
            ],
            "presentations": [
                {"presentation_id": "old", "root_id": "root-A", "bound_revision_id": "r1"},
                {"presentation_id": "new", "root_id": "root-A", "bound_revision_id": "r3"},
                {"presentation_id": "unknown", "root_id": None, "bound_revision_id": None},
            ],
        }

    def test_known_descendant_gets_full_correction_chain(self):
        result = correction.propagate_corrections(self.base_graph())
        by_id = {row["presentation_id"]: row for row in result["presentations"]}
        self.assertEqual(by_id["old"]["status"], "AFFECTED_BY_CORRECTION")
        self.assertEqual(by_id["old"]["correction_chain"], ["c1", "c2"])

    def test_current_descendant_remains_current(self):
        result = correction.propagate_corrections(self.base_graph())
        row = next(row for row in result["presentations"] if row["presentation_id"] == "new")
        self.assertEqual(row["status"], "CURRENT")
        self.assertEqual(row["correction_chain"], [])

    def test_unknown_lineage_is_not_guessed(self):
        result = correction.propagate_corrections(self.base_graph())
        row = next(row for row in result["presentations"] if row["presentation_id"] == "unknown")
        self.assertEqual(row["status"], "UNKNOWN_LINEAGE")
        self.assertFalse(result["invariants"]["unknown_lineage_invented"])

    def test_history_is_preserved(self):
        graph = self.base_graph()
        result = correction.propagate_corrections(graph)
        self.assertEqual(result["history"]["roots"], graph["roots"])
        self.assertEqual(result["history"]["presentations"], graph["presentations"])
        self.assertEqual(result["history"]["corrections"], graph["corrections"])
        self.assertFalse(result["invariants"]["history_deleted"])

    def test_correction_unknown_root_fails_closed(self):
        graph = self.base_graph()
        graph["corrections"][0]["root_id"] = "missing-root"
        with self.assertRaises(correction.CorrectionGraphError):
            correction.propagate_corrections(graph)

    def test_duplicate_correction_id_fails_closed(self):
        graph = self.base_graph()
        graph["corrections"][1]["correction_id"] = "c1"
        with self.assertRaises(correction.CorrectionGraphError):
            correction.propagate_corrections(graph)

    def test_ambiguous_branch_fails_closed(self):
        graph = self.base_graph()
        graph["corrections"].append(
            {
                "correction_id": "c3",
                "root_id": "root-A",
                "superseded_revision_id": "r1",
                "replacement_revision_id": "r3",
            }
        )
        with self.assertRaises(correction.CorrectionGraphError):
            correction.propagate_corrections(graph)

    def test_chain_must_terminate_at_declared_current_revision(self):
        graph = self.base_graph()
        graph["roots"][0]["current_revision_id"] = "r4"
        with self.assertRaises(correction.CorrectionGraphError):
            correction.propagate_corrections(graph)

    def test_correction_does_not_create_truth_or_authority(self):
        result = correction.propagate_corrections(self.base_graph())
        inv = result["invariants"]
        self.assertFalse(inv["correction_is_truth_proof"])
        self.assertEqual(inv["evidence_authority_delta"], 0)
        self.assertEqual(inv["mass_effect_budget_delta"], 0)

    def test_self_test(self):
        self.assertEqual(correction.self_test()["self_test"], "PASS")


if __name__ == "__main__":
    unittest.main()
