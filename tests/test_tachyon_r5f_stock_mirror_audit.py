"""R5F mirrored default-parameter causal graph: no physical time reversal."""
from __future__ import annotations
import copy
import unittest
from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN,BUDGET,SCENARIOS,build_case,forward_only,
    reverse_only,reverse_then_forward,run_split,digest,
)
from tools.tachyon_r5f_stock_mirror_audit import (
    ARMS,DEFAULT_BUDGET,STOCK_FORWARD_EDGE_COUNT,
    mirror_case,transpose,mirror_constraints,mirrored_exact,
    mirrored_proposals_only,mirrored_replay,mirrored_abstain,
    count_forward_edges,audit
)

class R5FStockMirrorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=audit()

    def test_stock_budget_reinstated(self):
        self.assertEqual(DEFAULT_BUDGET,500)
        self.assertEqual(BUDGET,500)

    def test_stock_graph_edges_not_x100(self):
        x=build_case(101,"unique_A_and_B")
        y=mirror_case(x)
        self.assertEqual(count_forward_edges(x),9)
        self.assertEqual(sum(map(len,y["forward_edges"]["A_B"].values()))
                        +sum(map(len,y["forward_edges"]["B_C"].values())),9)

    def test_old_negative_999_not_applied(self):
        self.assertTrue(self.report["prior_negative999_gate_not_applied"])
        self.assertEqual(self.report["stock_budget_operations_per_case"],500)

    def test_old_x100_not_applied(self):
        self.assertTrue(self.report["prior_x100_expansion_not_applied"])
        self.assertEqual(self.report["stock_graph_edges_per_case"],9)

    def test_transposition_round_trip(self):
        x={"u1":["v1","v2"],"u2":["v2"]}
        self.assertEqual(transpose(transpose(x)),
                         {"u1":["v1","v2"],"u2":["v2"]})

    def test_direction_is_reversed(self):
        x=build_case(100,"unique_B_only")
        y=mirror_case(x)
        self.assertEqual(y["graph_direction"],"C_TO_B_TO_A")
        self.assertEqual(y["forward_edges"]["A_B"],transpose(x["forward_edges"]["B_C"]))
        self.assertEqual(y["forward_edges"]["B_C"],transpose(x["forward_edges"]["A_B"]))

    def test_reverse_is_not_a_change_to_utc(self):
        x=build_case(101,"unique_B_only")
        y=mirror_case(x)
        self.assertEqual([w["capture_utc"] for w in x["witness_reports"]],
                         [w["capture_utc"] for w in y["witness_reports"]])
        self.assertFalse(y["physical_utc_modified"])

    def test_mirror_input_is_pure_no_mutation(self):
        x=build_case(101,"decoy_reverse_edge")
        old=copy.deepcopy(x)
        mirror_case(x)
        self.assertEqual(x,old)

    def test_source_anchor_is_original_observed_end(self):
        x=build_case(101,"unique_A_and_B")
        y=mirror_case(x)
        self.assertEqual(y["anchor_source"],x["terminal"])
        self.assertEqual(y["anchor_source_kind"],x["terminal_kind"])

    def test_stage_A_reports_mirror_to_C(self):
        x=build_case(101,"unique_A_and_B")
        y=mirror_case(x)
        self.assertEqual([w["stage"] for w in y["witness_reports"]],
                         ["C" if w["stage"]=="A" else "B" for w in x["witness_reports"]])

    def test_synthetic_mirror_layer_coordinates(self):
        x=mirror_case(build_case(101,"unique_A_and_B"))
        self.assertEqual(x["synthetic_time_layer_coordinates"],{"A":2,"B":1,"C":0})

    def test_all_scenarios_exact_mirror_invariance(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                x=build_case(101,scenario)
                y=mirror_case(x)
                self.assertEqual(mirrored_exact(y)["prediction"],forward_only(x)["prediction"])

    def test_all_scenarios_proposal_mirror_invariance(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                x=build_case(101,scenario)
                y=mirror_case(x)
                self.assertEqual(mirrored_proposals_only(y)["prediction"],reverse_only(x)["prediction"])

    def test_all_scenarios_replay_mirror_invariance(self):
        for scenario in SCENARIOS:
            with self.subTest(scenario=scenario):
                x=build_case(101,scenario)
                y=mirror_case(x)
                self.assertEqual(mirrored_replay(y)["prediction"],reverse_then_forward(x)["prediction"])

    def test_many_histories_remain_ambiguous(self):
        x=mirror_case(build_case(101,"collider_shared_B"))
        self.assertEqual(mirrored_exact(x)["prediction"],ABSTAIN)

    def test_conflicting_witnesses_do_not_infer_unique_past(self):
        x=mirror_case(build_case(101,"conflicting_reports"))
        self.assertEqual(mirrored_exact(x)["prediction"],ABSTAIN)

    def test_duplicate_roots_are_not_independent(self):
        x=mirror_case(build_case(101,"duplicate_witness_root"))
        self.assertEqual(mirror_constraints(x),{})
        self.assertEqual(mirrored_exact(x)["prediction"],ABSTAIN)

    def test_missing_timestamp_unusable(self):
        x=mirror_case(build_case(101,"missing_timestamps"))
        self.assertEqual(mirror_constraints(x),{})

    def test_future_plan_not_observation(self):
        x=mirror_case(build_case(101,"future_plan"))
        self.assertEqual(mirror_constraints(x),None)
        self.assertEqual(mirrored_exact(x)["prediction"],ABSTAIN)

    def test_unsynchronized_terminal_not_observed(self):
        x=mirror_case(build_case(101,"unsynchronized_terminal"))
        self.assertEqual(mirrored_exact(x)["prediction"],ABSTAIN)

    def test_incomplete_reverse_proposals_require_abstention(self):
        x=mirror_case(build_case(101,"incomplete_reverse_index"))
        self.assertFalse(x["reverse_proposals"]["complete_certified"])
        self.assertEqual(mirrored_replay(x)["prediction"],ABSTAIN)

    def test_decoy_rejected_by_forward_replay(self):
        x=mirror_case(build_case(101,"decoy_reverse_edge"))
        self.assertEqual(mirrored_proposals_only(x)["prediction"],ABSTAIN)
        self.assertNotEqual(mirrored_replay(x)["prediction"],ABSTAIN)

    def test_no_synthetic_mirror_fabrication_from_real_input(self):
        x=build_case(101,"unique_A_and_B")
        x["synthetic_only"]=False
        with self.assertRaises(ValueError):mirror_case(x)

    def test_fail_closed_when_budget_tiny(self):
        x=mirror_case(build_case(101,"unique_A_and_B"))
        self.assertTrue(mirrored_exact(x,budget=1)["budget_exceeded"])
        self.assertEqual(mirrored_exact(x,budget=1)["prediction"],ABSTAIN)

    def test_only_stock_600_heldout(self):
        self.assertEqual(self.report["challenge_cases"],600)
        self.assertEqual(self.report["scenario_count"],15)
        self.assertEqual(self.report["same_original_heldout_input_sha256"],digest(run_split("heldout")))

    def test_mirror_predictions_exact_match_600(self):
        self.assertEqual(self.report["original_forward_vs_exact_mirror_predictions_equal_cases"],600)

    def test_replay_predictions_exact_match_600(self):
        self.assertEqual(self.report["original_reverse_replay_vs_mirror_replay_predictions_equal_cases"],600)

    def test_all_mirror_replays_at_500_budget(self):
        self.assertEqual(self.report["stock_budget_operations_per_case"],500)
        for arm in self.report["arms"].values():
            self.assertEqual(arm["budget_exceeded_cases"],0)

    def test_scientific_hold_no_physical_causality_claim(self):
        r=self.report
        self.assertFalse(r["real_physical_time_reversal"])
        self.assertFalse(r["external_custodian"])
        self.assertFalse(r["neural_training_or_production_weights_changed"])
        self.assertFalse(r["human_memory_measured"])
        self.assertIn("HOLD",r["science_gate"])

    def test_report_is_deterministic_without_runtime_comparison(self):
        a=self.report
        b=audit()
        for name in ARMS:
            for key in ("answered","exact_matches","mean_counted_operations_per_case",
                        "incorrect_nonabstentions","unsupported_claims"):
                self.assertEqual(a["arms"][name][key],b["arms"][name][key])

    def test_source_rows_and_mirror_are_separate(self):
        o=build_case(101,"unique_B_only")
        m=mirror_case(o)
        self.assertNotEqual(o["schema"],m["schema"])
        self.assertEqual(o["case_ref"],m["case_ref"])

    def test_no_unsafe_answers(self):
        self.assertEqual(self.report["total_nonabstention_unsafe"],0)

    def test_strong_mirror_identical_to_mirror_exact(self):
        a=self.report["arms"]["A_MIRROR_FORWARD_EXACT"]
        b=self.report["arms"]["D_STRONG_EXACT_MIRROR"]
        for key in ("answered","exact_matches","mean_counted_operations_per_case","unsupported_claims"):
            self.assertEqual(a[key],b[key])

if __name__=="__main__":
    unittest.main()
