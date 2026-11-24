"""R5F ×100 audit: real expanded graph work, unmodified baselines, no synthetic promotion."""
import copy
import unittest

from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN, build_case, forward_only, reverse_only, reverse_then_forward
)
from tools.tachyon_r5f_x100_audit import (
    BUDGET, ORIGINAL_BUDGET, SCALE, audit, count_graph_edges, expand_graph_x100
)


class R5FX100Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = audit()

    def test_budget_is_100x_not_a_counter_multiplier(self):
        self.assertEqual(ORIGINAL_BUDGET, 500)
        self.assertEqual(BUDGET, 50000)
        self.assertEqual(SCALE,100)

    def test_exactly_100x_graph_edges(self):
        inp = build_case(100,"ambiguous_terminal")
        large = expand_graph_x100(inp)
        self.assertEqual(count_graph_edges(large),100*count_graph_edges(inp))
        self.assertEqual(count_graph_edges(large),900)

    def test_graph_expansion_preserves_original_input(self):
        x = build_case(100,"unique_B_only")
        saved = copy.deepcopy(x)
        expand_graph_x100(x)
        self.assertEqual(x,saved)

    def test_expanded_graph_has_distinct_alternatives_not_rescoring(self):
        x=build_case(100,"ambiguous_terminal")
        y=expand_graph_x100(x)
        a=y["forward_edges"]["A_B"]
        self.assertEqual(len(a),500)
        self.assertEqual(len(set(a)),500)
        self.assertEqual(len(y["forward_edges"]["B_C"]),400)

    def test_source_witnesses_not_fabricated_in_x100(self):
        for scenario in ("unique_A_and_B","unique_B_only","duplicate_witness_root"):
            inp=build_case(100,scenario)
            large=expand_graph_x100(inp)
            self.assertEqual(inp["witness_reports"],large["witness_reports"])

    def test_original_causal_path_still_present(self):
        x=build_case(100,"unique_A_and_B")
        y=expand_graph_x100(x)
        self.assertEqual(
            forward_only(x,budget=ORIGINAL_BUDGET)["prediction"],
            forward_only(y,budget=BUDGET)["prediction"]
        )

    def test_no_new_unique_answers_without_witness(self):
        x=expand_graph_x100(build_case(100,"ambiguous_terminal"))
        self.assertEqual(forward_only(x,budget=BUDGET)["prediction"],ABSTAIN)

    def test_shared_intermediate_stays_ambiguous(self):
        x=expand_graph_x100(build_case(100,"collider_shared_B"))
        self.assertEqual(forward_only(x,budget=BUDGET)["prediction"],ABSTAIN)

    def test_incomplete_reverse_index_fail_closed(self):
        x=expand_graph_x100(build_case(100,"incomplete_reverse_index"))
        self.assertEqual(reverse_then_forward(x,budget=BUDGET)["prediction"],ABSTAIN)

    def test_decoy_reverse_edge_still_rejected(self):
        x=expand_graph_x100(build_case(100,"decoy_reverse_edge"))
        self.assertEqual(reverse_only(x,budget=BUDGET)["prediction"],ABSTAIN)
        self.assertEqual(reverse_then_forward(x,budget=BUDGET)["prediction"],
                         forward_only(x,budget=BUDGET)["prediction"])

    def test_hard_original_budget_really_too_small(self):
        x=expand_graph_x100(build_case(100,"unique_A_and_B"))
        out=forward_only(x,budget=ORIGINAL_BUDGET)
        self.assertTrue(out["budget_exceeded"])
        self.assertEqual(out["prediction"],ABSTAIN)

    def test_50000_budget_completes_graph(self):
        x=expand_graph_x100(build_case(100,"unique_A_and_B"))
        out=forward_only(x,budget=BUDGET)
        self.assertFalse(out["budget_exceeded"])
        self.assertNotEqual(out["prediction"],ABSTAIN)

    def test_budget_only_not_change_case_content(self):
        r=self.receipt
        self.assertEqual(r["original_replayed_control"]["input_stream_sha256"],
                         r["budget_only_intervention"]["input_stream_sha256"])

    def test_original_and_budget_only_predictions_equal(self):
        self.assertTrue(self.receipt["original_vs_budget_only_predictions_identical"])

    def test_actual_graph_x100_in_receipt(self):
        r=self.receipt
        self.assertEqual(r["expanded_graph_x100"]["average_graph_edges"],
                         100*r["original_replayed_control"]["average_graph_edges"])
        self.assertEqual(r["expanded_graph_x100"]["average_graph_edges"],900)

    def test_actual_operation_count_scaled(self):
        r=self.receipt
        for name in ("A_FORWARD_ONLY_EXHAUSTIVE","B_REVERSE_ONLY_UNVERIFIED",
                     "C_REVERSE_PLUS_FORWARD_REPLAY","D_STRONG_EXHAUSTIVE_PROVENANCE"):
            self.assertGreater(r["operation_ratios_expanded_over_original"][name],50)

    def test_all_arms_same_heldout(self):
        r=self.receipt
        self.assertEqual(r["heldout_cases"],600)
        self.assertEqual(len(r["expanded_graph_x100"]["arms"]),5)
        for stats in r["expanded_graph_x100"]["arms"].values():
            self.assertEqual(stats["cases"],600)

    def test_zero_unsupported_claims(self):
        self.assertTrue(self.receipt["expanded_zero_unsupported_assertions"])

    def test_strong_exact_reference_unchanged(self):
        self.assertTrue(self.receipt["expanded_strong_baseline_exact"])

    def test_correctly_abstains_on_future(self):
        x=expand_graph_x100(build_case(100,"future_plan"))
        self.assertEqual(forward_only(x,budget=BUDGET)["prediction"],ABSTAIN)
        self.assertEqual(reverse_then_forward(x,budget=BUDGET)["prediction"],ABSTAIN)

    def test_not_external_blind_or_physical_reversal(self):
        r=self.receipt
        self.assertFalse(r["synthetic_external_custodian"])
        self.assertFalse(r["physical_reverse_time_proven"])
        self.assertFalse(r["human_memory_measured"])
        self.assertFalse(r["model_or_production_weights_changed"])
        self.assertIn("SCIENCE_HOLD",r["scientific_gate"])

    def test_no_counting_fake_repeated_operations(self):
        x=expand_graph_x100(build_case(100,"ambiguous_terminal"))
        n=forward_only(x,budget=BUDGET)["operations"]
        original = build_case(100,"ambiguous_terminal")
        original_walks = forward_only(original,budget=ORIGINAL_BUDGET)["operations"]
        self.assertEqual(original_walks,10)
        self.assertEqual(n,SCALE*original_walks)
        self.assertEqual(n,1000)


if __name__=="__main__":
    unittest.main()
