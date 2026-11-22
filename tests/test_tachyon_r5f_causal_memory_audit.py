"""R5F reverse-road causal memory synthetic peer controls."""
import copy
import unittest

from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN,BUDGET,SCENARIOS,SPLITS,
    build_case,constraints,forward_only,reverse_only,reverse_then_forward,
    always_abstain,gold_reference,run_split,digest,audit,
)

class R5FCausalMemoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=audit()

    def test_original_reverse_road_semantics(self):
        x=build_case(100,"unique_B_only")
        self.assertEqual(x["terminal_kind"],"OBSERVED")
        self.assertIn("forward_edges",x)
        self.assertIn("reverse_proposals",x)
        self.assertTrue(x["synthetic_only"])

    def test_all_scenarios_declared(self):
        self.assertEqual(len(SCENARIOS),15)

    def test_disjoint_family_partitions(self):
        a,b,c=map(lambda n:set(SPLITS[n]),("development","validation","heldout"))
        self.assertFalse(a&b or a&c or b&c)
        self.assertEqual((len(a),len(b),len(c)),(20,10,40))

    def test_no_gold_or_scenario_label_in_visible_input(self):
        for x,scenario,family in run_split("heldout"):
            self.assertNotIn("gold",x)
            self.assertNotIn("scenario",x)
            self.assertNotIn("target",x)
            self.assertNotIn("actual_history",x)
            self.assertNotIn("b_status",x)
            self.assertNotIn("event_a_id",x)

    def test_unique_two_witnesses_reconstructable(self):
        x=build_case(100,"unique_A_and_B")
        self.assertEqual(len(constraints(x)),2)
        self.assertEqual(reverse_then_forward(x)["prediction"],gold_reference(x))
        self.assertNotEqual(gold_reference(x),ABSTAIN)

    def test_unique_A_reconstructable(self):
        x=build_case(101,"unique_A_only")
        self.assertNotEqual(gold_reference(x),ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],gold_reference(x))

    def test_unique_B_reconstructable(self):
        x=build_case(101,"unique_B_only")
        self.assertNotEqual(gold_reference(x),ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],gold_reference(x))

    def test_shared_terminal_not_unique(self):
        x=build_case(101,"ambiguous_terminal")
        self.assertEqual(gold_reference(x),ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],ABSTAIN)

    def test_collider_B_does_not_identify_A(self):
        x=build_case(101,"collider_shared_B")
        self.assertEqual(len(constraints(x)),1)
        self.assertIn("B",constraints(x))
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_duplicate_source_roots_not_independent(self):
        x=build_case(101,"duplicate_witness_root")
        self.assertEqual(constraints(x),{})
        self.assertEqual(reverse_then_forward(x)["prediction"],ABSTAIN)

    def test_conflicting_witnesses_abstain(self):
        x=build_case(101,"conflicting_reports")
        self.assertEqual(constraints(x),{})
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_missing_timestamp_not_evidence(self):
        x=build_case(101,"missing_timestamps")
        self.assertEqual(constraints(x),{})
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_unsynced_clock_not_evidence(self):
        x=build_case(101,"unsynchronized_clock")
        self.assertEqual(constraints(x),{})
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_one_source_not_automatically_corrob(self):
        x=build_case(101,"single_source")
        self.assertEqual(constraints(x),{})
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_ghost_reverse_proposal_must_fail_forward_replay(self):
        x=build_case(101,"decoy_reverse_edge")
        self.assertEqual(reverse_only(x)["prediction"],ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],gold_reference(x))
        self.assertNotEqual(gold_reference(x),ABSTAIN)

    def test_incomplete_reverse_index_forces_abstention(self):
        x=build_case(101,"incomplete_reverse_index")
        self.assertFalse(x["reverse_proposals"]["complete_certified"])
        self.assertNotEqual(gold_reference(x),ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],ABSTAIN)

    def test_future_plan_is_not_observed_terminal(self):
        x=build_case(101,"future_plan")
        self.assertEqual(constraints(x),None)
        self.assertEqual(gold_reference(x),ABSTAIN)
        self.assertEqual(reverse_then_forward(x)["prediction"],ABSTAIN)

    def test_uncalibrated_terminal_is_not_proof(self):
        x=build_case(101,"unsynchronized_terminal")
        self.assertIsNone(constraints(x))
        self.assertEqual(reverse_then_forward(x)["prediction"],ABSTAIN)

    def test_matching_signatures_do_not_create_single_history(self):
        x=build_case(101,"identical_content_ambiguity")
        self.assertEqual(gold_reference(x),ABSTAIN)

    def test_no_mutation_of_physical_graph_or_sources(self):
        x=build_case(101,"decoy_reverse_edge")
        a=copy.deepcopy(x)
        reverse_then_forward(x)
        self.assertEqual(x,a)

    def test_forward_replay_only_uses_authoritative_forward_edges(self):
        x=build_case(101,"decoy_reverse_edge")
        untrusted=reverse_only(x)
        verified=reverse_then_forward(x)
        self.assertGreater(untrusted["compatible_paths"],verified["compatible_paths"])

    def test_no_unsafe_unique_claim_on_holdout(self):
        arm=self.report["arms"]["C_REVERSE_PLUS_FORWARD_REPLAY"]
        self.assertEqual(arm["unsupported_assertions"],0)
        self.assertEqual(arm["wrong_attempted"],0)

    def test_strong_baseline_has_correct_reference_labels(self):
        a=self.report["arms"]["A_FORWARD_ONLY_EXHAUSTIVE"]
        d=self.report["arms"]["D_STRONG_EXHAUSTIVE_PROVENANCE"]
        self.assertEqual({k:v for k,v in a.items() if k!="median_decision_us"},
                         {k:v for k,v in d.items() if k!="median_decision_us"})
        self.assertEqual(d["exact_matches"],self.report["heldout_cases"])

    def test_tiny_budget_fails_closed(self):
        x=build_case(101,"unique_B_only")
        r=reverse_then_forward(x,budget=1)
        self.assertTrue(r["budget_exceeded"])
        self.assertEqual(r["prediction"],ABSTAIN)

    def test_all_budget_limits_respected(self):
        for x in self.report["arms"].values():
            self.assertEqual(x["over_budget_cases"],0)

    def test_always_abstain_has_no_claim_to_generalization(self):
        arm=self.report["arms"]["E_ALWAYS_ABSTAIN"]
        self.assertEqual(arm["answered"],0)
        self.assertIsNone(arm["selective_accuracy"])

    def test_generator_is_reproducible(self):
        self.assertEqual(build_case(111,"unique_B_only"),build_case(111,"unique_B_only"))
        self.assertEqual(digest(run_split("heldout")),self.report["challenge_sha256"])

    def test_report_has_no_physical_or_clinical_approval(self):
        r=self.report
        self.assertFalse(r["physical_reverse_time_measured"])
        self.assertFalse(r["human_memory_measured"])
        self.assertFalse(r["production_weights_changed"])
        self.assertFalse(r["independent_external_custodian"])
        self.assertFalse(r["statistical_science_gain_established"])
        self.assertIn("SCIENCE_HOLD",r["scientific_gate"])

    def test_case_counts(self):
        r=self.report
        self.assertEqual((r["development_cases"],r["validation_cases"],r["heldout_cases"]),(300,150,600))

if __name__=="__main__":
    unittest.main()
