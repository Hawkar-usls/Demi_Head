"""Research R5: benchmark integrity rather than promising a gain."""
from __future__ import annotations
import json
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from tools.tachyon_r5_paired_gain_audit import (
    HOLD, LABELS, SOURCE_COMMIT, SEED, benchmark, make_case, negative_cases,
    pairs, simple_rule, validate_provenance, real_demihead,
)

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / "_pinned_simptomat"

class R5PairedGainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = benchmark(UPSTREAM)

    def test_real_demihead_is_invoked_for_all_arms(self):
        self.assertEqual(self.receipt["unchanged_head_outcomes"],230)
        self.assertTrue(self.receipt["all_head_outcomes_preserved"])

    def test_actual_original_head_not_pretended_temporal(self):
        self.assertFalse(self.receipt["head_temporal_classification_supported_in_A"])
        self.assertTrue(self.receipt["head_A_cannot_be_scored_as_general_intelligence_accuracy"])

    def test_frozen_source_used_not_dynamic_latest(self):
        self.assertEqual(self.receipt["TACHYON_source_commit"], SOURCE_COMMIT)
        self.assertIn("PINNED_R4_CODE",self.receipt["weight_provenance"])

    def test_replay_is_real_learned_model(self):
        self.assertEqual(self.receipt["R4_replay_train_cases"],3360)
        self.assertGreater(self.receipt["R4_replay_train_cost_ms"],0)
        self.assertEqual(self.receipt["R4_replay_self_test_accuracy"],1.0)

    def test_32_independent_family_cases_each(self):
        self.assertEqual(self.receipt["challenge_count"],230)
        self.assertEqual(self.receipt["valid_case_count"],224)
        self.assertEqual(self.receipt["invalid_provenance_count"],6)
        self.assertEqual(len(pairs()),230)

    def test_clearly_disclosed_baseline_not_removed(self):
        a=self.receipt["comparisons"]
        self.assertIn("B_TACHYON",a)
        self.assertIn("C_SIMPLE_RULE",a)
        self.assertEqual(a["C_SIMPLE_RULE"]["valid_correct"],224)

    def test_performance_difference_not_forced_positive(self):
        self.assertIsInstance(self.receipt["B_minus_C_accuracy_points"],float)
        self.assertIn("NOT_ESTABLISHED",self.receipt["general_intelligence_gain_claim"])

    def test_no_false_accepts_on_negative_provenance(self):
        for row in self.receipt["comparisons"].values():
            self.assertEqual(row["invalid_provenance_false_accepts"],0)

    def test_no_claim_of_physical_timelessness(self):
        r=self.receipt
        self.assertFalse(r["human_memory_or_consciousness_validated"])
        self.assertFalse(r["physical_timelessness_proven"])
        self.assertFalse(r["clinical_data_used"])
        self.assertFalse(r["core_weights_changed"])
        self.assertFalse(r["trained_model_replaces_demihead"])
        self.assertEqual(r["scientific_gate"],HOLD)

    def test_all_seven_target_concepts_in_challenge(self):
        seen={r["target"] for r in pairs()}
        self.assertTrue(set(LABELS).issubset(seen))

    def test_equal_content_distinct_ids_cannot_collapse(self):
        case=make_case(0,"OBSERVED_REPEAT")
        self.assertEqual(case["content_a"],case["content_b"])
        self.assertNotEqual(case["event_a_id"],case["event_b_id"])
        self.assertEqual(simple_rule(case),"OBSERVED_REPEAT")

    def test_tomorrow_is_plan_not_observation(self):
        case=make_case(1,"FUTURE_PLAN")
        self.assertGreater(case["event_b_time"],case["reference_time"])
        self.assertEqual(simple_rule(case),"FUTURE_PLAN")

    def test_memory_reference_not_a_new_event(self):
        case=make_case(2,"MEMORY_OF_EVENT")
        self.assertEqual(case["event_a_id"],case["event_b_id"])
        self.assertEqual(simple_rule(case),"MEMORY_OF_EVENT")

    def test_indeterminate_identifiers_are_explicit(self):
        case=make_case(3,"AMBIGUOUS_REFERENCE")
        self.assertIsNone(case["event_a_id"])
        self.assertEqual(simple_rule(case),"AMBIGUOUS_REFERENCE")

    def test_invalid_forecast_or_provenance_abstains(self):
        for case in negative_cases():
            self.assertFalse(validate_provenance(case))
            self.assertEqual(simple_rule(case),"ABSTAIN_INVALID_PROVENANCE")

    def test_real_head_preserves_evidence_ceiling(self):
        case=make_case(2,"OBSERVED_REPEAT")
        head=real_demihead(case)
        self.assertEqual(head["truth_claim"],"NOT_MADE")
        self.assertEqual(head["mass_effect_budget"],0)
        self.assertEqual(head["evidence_state"],"UNRESOLVED")

    def test_challenge_checksum_is_repeatable(self):
        self.assertEqual(self.receipt["challenge_sha256"],benchmark(UPSTREAM)["challenge_sha256"])

    def test_timing_is_exploratory_not_clinical(self):
        self.assertEqual(set(self.receipt["paired_median_total_per_case_microseconds"]),
                         {"A_UNMODIFIED","B_TACHYON","C_SIMPLE_RULE"})
        self.assertIn("CI-runner",self.receipt["cost_warning"])

if __name__=="__main__":
    unittest.main()
