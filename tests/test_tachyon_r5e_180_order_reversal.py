"""R5E 180° subjective reported order vs externally anchored clock."""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timezone

from tools.tachyon_r5e_180_order_reversal import (
    ABSTAIN, ALIGNED, NARRATIVE, OTHER, PRESENTATION, REVERSED,
    SCENARIOS, LABELS, assess, generate_case, naive_reverse_detector,
    relative_day, score,
)


class R5E180TimeReversalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=score()

    def test_all_synthetic_scenarios_are_handled(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                payload,gold=generate_case(21,scenario)
                self.assertEqual(assess(payload),gold)

    def test_no_physical_clock_mutation(self):
        p,_=generate_case(2,"reversed_three")
        before=copy.deepcopy(p["physical_events"])
        self.assertEqual(assess(p),REVERSED)
        self.assertEqual(p["physical_events"],before)

    def test_reversed_narration_is_not_temporal_perception(self):
        p,_=generate_case(2,"recall_reverse")
        self.assertEqual(assess(p),NARRATIVE)
        self.assertNotEqual(assess(p),REVERSED)

    def test_reversed_presentation_not_temporal_perception(self):
        p,_=generate_case(2,"presentation_reverse")
        self.assertEqual(assess(p),PRESENTATION)

    def test_full_order_reversed_exactly_180(self):
        p,_=generate_case(2,"reversed_three")
        ref=[e["event_id"] for e in p["physical_events"]]
        self.assertEqual(p["subjective_report"]["ordered_event_refs"],list(reversed(ref)))
        self.assertEqual(assess(p),REVERSED)

    def test_not_180_circular_rotation(self):
        p,_=generate_case(2,"rotation_not_reversal")
        self.assertEqual(assess(p),OTHER)

    def test_not_180_adjacent_swap(self):
        p,_=generate_case(2,"partial_order_error")
        self.assertEqual(assess(p),OTHER)

    def test_identical_content_with_distinct_anchored_ids(self):
        p,_=generate_case(2,"identical_content_anchor_ids")
        self.assertEqual(len({e["content_signature"] for e in p["physical_events"]}),1)
        self.assertEqual(len({e["event_id"] for e in p["physical_events"]}),3)
        self.assertEqual(assess(p),REVERSED)

    def test_identical_content_without_event_identity_abstains(self):
        p,_=generate_case(2,"identical_content_no_ids")
        self.assertEqual(assess(p),ABSTAIN)

    def test_planned_future_not_past_observation(self):
        p,_=generate_case(2,"future_plan_not_observed")
        self.assertEqual(p["physical_events"][-1]["occurrence_status"],"PLANNED")
        self.assertEqual(assess(p),ABSTAIN)

    def test_missing_timestamp_abstains(self):
        p,_=generate_case(2,"timestamp_missing")
        self.assertEqual(assess(p),ABSTAIN)

    def test_conflicting_clocks_abstain(self):
        p,_=generate_case(2,"clock_conflict")
        self.assertEqual(assess(p),ABSTAIN)

    def test_duplicate_source_is_not_independent(self):
        p,_=generate_case(2,"duplicate_source_root")
        self.assertEqual(assess(p),ABSTAIN)

    def test_unknown_reporting_mode_abstains(self):
        p,_=generate_case(2,"unknown_report_mode")
        self.assertEqual(assess(p),ABSTAIN)

    def test_two_event_reversal(self):
        p,_=generate_case(2,"two_events_reversed")
        self.assertEqual(len(p["physical_events"]),2)
        self.assertEqual(assess(p),REVERSED)

    def test_local_midnight_relative_label_without_reverse_physics(self):
        p,_=generate_case(2,"local_midnight")
        witness_times=[event["witnesses"][0]["captured_at_utc"]
                       for event in p["physical_events"]]
        self.assertEqual(relative_day(witness_times[0],witness_times[1]),"PAST_1")
        self.assertEqual(assess(p),REVERSED)

    def test_duplicate_report_ids_abstain(self):
        p,_=generate_case(2,"duplicate_report_reference")
        self.assertEqual(assess(p),ABSTAIN)

    def test_unsupported_non_synthetic_data_refused(self):
        p,_=generate_case(2,"reversed_three")
        p["synthetic_only"]=False
        self.assertEqual(assess(p),ABSTAIN)

    def test_future_recording_refused_even_if_status_observed(self):
        p,_=generate_case(2,"reversed_three")
        p["physical_events"][-1]["witnesses"][0]["captured_at_utc"]="2027-01-01T00:00:00+00:00"
        p["physical_events"][-1]["witnesses"][1]["captured_at_utc"]="2027-01-01T00:00:13+00:00"
        self.assertEqual(assess(p),ABSTAIN)

    def test_unsynced_clock_refused(self):
        p,_=generate_case(2,"reversed_three")
        p["physical_events"][0]["witnesses"][0]["clock_quality"]="unknown"
        self.assertEqual(assess(p),ABSTAIN)

    def test_colliding_time_windows_refused(self):
        p,_=generate_case(2,"reversed_three")
        p["physical_events"][1]["witnesses"]=[copy.deepcopy(w)
                                              for w in p["physical_events"][0]["witnesses"]]
        self.assertEqual(assess(p),ABSTAIN)

    def test_relative_day_never_modifies_physical_instant(self):
        t="2026-11-22T12:00:00+00:00"
        a="2026-11-22T12:30:00+00:00"
        b="2026-11-23T12:30:00+00:00"
        self.assertEqual(relative_day(t,a),"TODAY")
        self.assertEqual(relative_day(t,b),"PAST_1")

    def test_naive_timezone_rejected(self):
        with self.assertRaises(ValueError):
            relative_day("2026-11-22T12:00:00","2026-11-23T12:00:00+00:00")

    def test_scores_have_no_false_180_labels_in_guarded_arm(self):
        r=self.report
        self.assertEqual(r["cases"],24*len(SCENARIOS))
        self.assertEqual(r["arms"]["verified"]["false_180_reversal_claims"],0)
        self.assertEqual(r["arms"]["verified"]["exact_correct"],r["cases"])

    def test_naive_reverse_detector_incorrectly_promotes_reports(self):
        p,_=generate_case(2,"recall_reverse")
        self.assertEqual(naive_reverse_detector(p),REVERSED)
        self.assertGreater(self.report["arms"]["naive"]["false_180_reversal_claims"],0)

    def test_no_scientific_or_medical_promotion(self):
        r=self.report
        self.assertTrue(r["not_reversed_physical_history"])
        self.assertTrue(r["not_phenomenal_experience_proven"])
        self.assertFalse(r["independent_real_witnesses_authenticated"])
        self.assertTrue(r["no_human_or_clinical_data"])
        self.assertFalse(r["production_models_changed"])
        self.assertIn("SCIENCE_HOLD",r["scientific_gate"])

    def test_generator_is_deterministic(self):
        self.assertEqual(generate_case(4,"local_midnight"),
                         generate_case(4,"local_midnight"))

    def test_result_is_deterministic(self):
        self.assertEqual(score(),self.report)

    def test_experiment_not_general_intelligence_gain(self):
        self.assertIn("no neural gain",self.report["baseline_scope"])


if __name__=="__main__":
    unittest.main()
