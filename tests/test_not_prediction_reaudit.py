from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import not_prediction_reaudit as npr  # noqa: E402


class NotPredictionReauditTests(unittest.TestCase):
    def setUp(self) -> None:
        fixture = ROOT / "examples" / "not_prediction_reaudit_minimal.json"
        self.document = json.loads(fixture.read_text(encoding="utf-8"))

    def test_root_collapse_prevents_pseudoreplication(self) -> None:
        result = npr.audit(self.document)
        self.assertEqual(result["root_collapse"]["candidate_count"], 2)
        self.assertEqual(result["root_collapse"]["root_count"], 1)
        self.assertEqual(
            result["root_collapse"]["roots"][0]["candidate_ids"],
            ["NP-T001", "NP-T002"],
        )

    def test_authoritative_total_is_not_silently_promoted(self) -> None:
        result = npr.audit(self.document)
        self.assertEqual(result["authoritative_total_preserved"], 29)
        self.assertEqual(result["prediction_claim"], "NOT_PROMOTED")
        self.assertTrue(result["requires_matched_null"])

    def test_memory_blind_packet_removes_interpretive_labels(self) -> None:
        candidate = self.document["pre_snapshot_strong_omissions"][0]
        blinded = npr.blind_candidate(candidate)
        for key in npr.BLIND_REMOVE_KEYS:
            self.assertNotIn(key, blinded)
        self.assertEqual(blinded["raw_observation"], "Observed clock 04:40.")
        self.assertEqual(blinded["source_root"], "ROOT_CLOCK_0440")

    def test_ontology_blind_packet_neutralizes_project_terms(self) -> None:
        candidate = self.document["pre_snapshot_strong_omissions"][0]
        blinded = npr.blind_candidate(candidate, ontology_blind=True)
        rendered = json.dumps(blinded, ensure_ascii=False)
        self.assertNotIn("Janus", rendered)
        self.assertNotIn("threshold", rendered.casefold())
        self.assertNotIn(" sign", rendered.casefold())

    def test_forbidden_promotion_fails_closed(self) -> None:
        mutated = json.loads(json.dumps(self.document))
        mutated["final_boundary"]["prediction_promoted"] = True
        with self.assertRaises(ValueError):
            npr.audit(mutated)

    def test_authoritative_total_drift_fails_closed(self) -> None:
        mutated = json.loads(json.dumps(self.document))
        mutated["counting_state"]["authoritative_current_total"] = 31
        with self.assertRaises(ValueError):
            npr.audit(mutated)


if __name__ == "__main__":
    unittest.main()
