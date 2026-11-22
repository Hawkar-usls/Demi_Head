"""TACHYON × DemiHead R5B witness-only, anti-shortcut, abstention tests."""
from __future__ import annotations

import copy
import unittest

from tools.tachyon_r5b_witness_audit import (
    ABSTAIN, ANSWER, R4_OOD, SCENARIOS, benchmark, build_case, cases,
    clock_only_baseline, original_demihead, r4_frozen_adapter, witness_rule,
)


class R5BAntiShortcutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = benchmark()

    def test_heldout_challenge_has_balanced_scenarios(self):
        self.assertEqual(self.receipt["cases"], 320)
        self.assertEqual(self.receipt["development_cases"], 80)
        self.assertEqual(len(cases("holdout")), 32 * len(SCENARIOS))

    def test_no_gold_or_shortcut_fields_in_visible_challenge(self):
        for obj, _ in cases("holdout"):
            assert not (set(obj) & {"gold", "target", "scenario", "b_status",
                                    "event_a_id", "event_b_id"})
            self.assertEqual(set(obj), {"schema", "case_ref", "reference_time_utc",
                                        "witnesses", "synthetic_only"})

    def test_heldout_and_development_sources_are_disjoint(self):
        def roots(partition):
            return {w["root"] for inp, _ in cases(partition) for w in inp["witnesses"]}
        self.assertTrue(roots("development").isdisjoint(roots("holdout")))
        self.assertTrue(self.receipt["source_groups_disjoint_between_splits"])

    def test_repeat_preserves_distinct_source_window_not_event_identity(self):
        obj, gold = build_case(111, "same_signature_separate_days")
        self.assertEqual(gold, "REPEAT_WINDOWS_SAME_SIGNATURE")
        self.assertEqual(witness_rule(obj), gold)
        self.assertNotIn("event_a_id", obj)
        self.assertNotIn("event_b_id", obj)

    def test_near_simultaneous_logs_do_not_prove_one_event(self):
        obj, gold = build_case(111, "same_window_identity_unknown")
        self.assertEqual(gold, ABSTAIN)
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_different_signatures_in_distinct_time_windows(self):
        obj, gold = build_case(111, "different_content_separate_days")
        self.assertEqual(witness_rule(obj), gold)

    def test_order_without_content_can_be_observed(self):
        obj, gold = build_case(111, "known_order_unknown_content")
        self.assertEqual(gold, "ORDER_A_BEFORE_B")
        self.assertEqual(witness_rule(obj), gold)

    def test_future_schedule_is_not_future_observation(self):
        obj, gold = build_case(111, "future_schedules_no_observations")
        self.assertEqual(gold, "ONLY_FUTURE_SCHEDULES")
        self.assertEqual(witness_rule(obj), gold)
        self.assertTrue(all(w["claim_medium"]=="schedule_notice" for w in obj["witnesses"]))

    def test_missing_timestamps_abstain(self):
        obj, _ = build_case(111, "timestamp_missing")
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_disagreeing_witness_clocks_abstain(self):
        obj, _ = build_case(111, "contradictory_clocks")
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_duplicate_root_not_independent(self):
        obj, _ = build_case(111, "duplicate_source_roots")
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_unknown_clock_quality_abstains(self):
        obj, _ = build_case(111, "unsynchronized_clocks")
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_one_source_cannot_prove_two_independent_witnesses(self):
        obj, _ = build_case(111, "one_root_only")
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_forged_future_recording_cannot_promote(self):
        obj, _ = build_case(111, "same_signature_separate_days")
        for w in obj["witnesses"]:
            if w["slot"] == "b":
                w["captured_at_utc"] = "2026-12-01T10:00:00+00:00"
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_mixed_future_observation_and_schedule_abstain(self):
        obj, _ = build_case(111, "future_schedules_no_observations")
        obj["witnesses"][0]["claim_medium"] = "recording"
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_bad_time_format_and_naive_utc_abstain(self):
        obj, _ = build_case(111, "same_signature_separate_days")
        for w in obj["witnesses"]:
            if w["slot"]=="a":
                w["captured_at_utc"] = "2026-11-20T12:00:00"
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_real_data_prohibited_by_inference(self):
        obj, _ = build_case(111, "same_signature_separate_days")
        obj["synthetic_only"] = False
        self.assertEqual(witness_rule(obj), ABSTAIN)

    def test_r4_adapter_refuses_to_hallucinate_frozen_features(self):
        for scenario in SCENARIOS:
            obj, _ = build_case(111, scenario)
            self.assertEqual(r4_frozen_adapter(obj), R4_OOD)
        self.assertFalse(self.receipt["r4_learned_predictions_executed"])

    def test_r4_metadata_backfill_is_not_permitted(self):
        obj, _ = build_case(111, "same_signature_separate_days")
        obj.update({
            "event_a_id":"fabricated", "event_b_id":"fabricated2", "b_status":"PLANNED",
            "event_a_time":0, "event_b_time":1, "content_a":"x", "content_b":"x",
            "reference_time":2,
        })
        with self.assertRaises(ValueError):
            r4_frozen_adapter(obj)

    def test_head_original_results_are_preserved(self):
        for obj, _ in cases("development"):
            a = original_demihead(obj)
            self.assertEqual(a["truth_claim"], "NOT_MADE")
            self.assertEqual(a["mass_effect_budget"], 0)
        self.assertEqual(self.receipt["core_DemiHead_outputs_unchanged"], 320)

    def test_strong_baseline_has_no_unsupported_assertions(self):
        a = self.receipt["arms"]["C_INDEPENDENT_WITNESS_RULE"]
        self.assertEqual(a["unsupported_assertions"], 0)
        self.assertEqual(a["incorrect_nonabstentions"], 0)
        self.assertEqual(a["answered_count"], 128)

    def test_r4_has_no_eligible_coverage_or_accuracy_gain(self):
        b = self.receipt["arms"]["B_FROZEN_R4_NO_FEATURE_BACKFILL"]
        self.assertEqual(b["answered_count"], 0)
        self.assertIsNone(b["selective_accuracy"])
        self.assertFalse(self.receipt["neural_gain_established"])

    def test_always_abstain_does_not_score_as_perfect(self):
        e = self.receipt["arms"]["E_ALWAYS_ABSTAIN"]
        self.assertEqual(e["answered_count"], 0)
        self.assertLess(e["raw_gold_match_rate"], 1.0)

    def test_precision_and_abstention_report_separate_metrics(self):
        a = self.receipt["arms"]["C_INDEPENDENT_WITNESS_RULE"]
        self.assertEqual(a["coverage"], 0.4)
        self.assertEqual(a["selective_accuracy"], 1.0)
        self.assertEqual(a["correct_required_abstentions"], 192)

    def test_reproducible_synthetic_casebank_checksum(self):
        self.assertEqual(benchmark()["challenge_input_sha256"],
                         self.receipt["challenge_input_sha256"])

    def test_scientific_hold_and_no_production_mutation(self):
        r = self.receipt
        for name in ("neural_gain_established","sufficient_external_independent_data",
                     "real_world_independence_authenticated","physical_retrocausality_claim",
                     "subjective_timelessness_claim","human_or_clinical_data_used",
                     "production_weights_changed","r4_weights_modified"):
            self.assertIs(r[name], False)
        self.assertTrue(r["valid_engineering_safety_gate"])
        self.assertIn("HOLD", r["scientific_gate"])

if __name__=="__main__":
    unittest.main()
