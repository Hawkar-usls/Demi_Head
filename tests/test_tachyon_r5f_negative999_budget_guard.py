"""R5F negative budget -999: no graph search, no causal claims, no silent normalization."""
import copy
import unittest

from tools.tachyon_r5f_causal_memory_audit import (
    ABSTAIN, BUDGET, SCENARIOS, build_case, forward_only,
)
from tools.tachyon_r5f_negative999_budget_guard import (
    ARMS, INVALID_NEGATIVE_BUDGET, INVALID_BUDGET_TYPE,
    REQUESTED_AVAILABLE_OPERATIONS, guarded_call, run_negative_budget_audit,
)


class R5FNegative999Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result=run_negative_budget_audit()

    def test_exact_requested_negative_budget(self):
        self.assertEqual(REQUESTED_AVAILABLE_OPERATIONS,-999)

    def test_n999_is_invalid(self):
        obj=guarded_call(forward_only,build_case(100,"unique_A_and_B"),-999)
        self.assertEqual(obj["status"],INVALID_NEGATIVE_BUDGET)
        self.assertEqual(obj["requested_available_operations"],-999)

    def test_never_normalizes_negative_budget(self):
        self.assertFalse(self.result["negative_budget_normalized_to_positive_or_zero"])

    def test_no_invocation_on_negative(self):
        called=[]
        def forbidden(*args,**kwargs):
            called.append((args,kwargs))
            raise AssertionError("graph search must not be invoked")
        ans=guarded_call(forbidden,object(),-999)
        self.assertFalse(called)
        self.assertFalse(ans["algorithm_invoked"])

    def test_no_input_access_on_negative(self):
        class ForbiddenInput:
            def __getitem__(self,key):
                raise AssertionError("No graph input access")
            def get(self,key,default=None):
                raise AssertionError("No graph input access")
        ans=guarded_call(lambda *_: None,ForbiddenInput(),-999)
        self.assertEqual(ans["graph_operations_performed"],0)

    def test_zero_operation_accounting(self):
        self.assertEqual(self.result["total_graph_operations_performed"],0)

    def test_zero_causal_claims(self):
        self.assertEqual(self.result["total_causal_claims_issued"],0)

    def test_n999_returns_abstention(self):
        r=guarded_call(forward_only,build_case(100,"unique_A_and_B"),-999)
        self.assertEqual(r["prediction"],ABSTAIN)

    def test_invalid_budget_not_confused_with_exhaustion(self):
        r=guarded_call(forward_only,build_case(100,"unique_A_and_B"),-999)
        self.assertIsNone(r["budget_exceeded"])
        self.assertEqual(r["status"],INVALID_NEGATIVE_BUDGET)

    def test_all_five_arms_used(self):
        self.assertEqual(len(ARMS),5)
        self.assertEqual(self.result["arms_count"],5)

    def test_600_cases_per_arm(self):
        for row in self.result["arms"].values():
            self.assertEqual(row["attempted_cases"],600)
            self.assertEqual(row["rejected_before_dispatch"],600)

    def test_3000_attempts_rejected(self):
        self.assertEqual(self.result["total_algorithm_dispatch_attempts"],3000)
        self.assertTrue(self.result["all_requests_rejected_before_graph_search"])

    def test_zero_invocations_across_all_arms(self):
        self.assertEqual(self.result["total_algorithm_invocations"],0)
        for row in self.result["arms"].values():
            self.assertEqual(row["actually_invoked_algorithms"],0)

    def test_zero_graph_operations_every_arm(self):
        for row in self.result["arms"].values():
            self.assertEqual(row["graph_operations_performed"],0)

    def test_3000_abstentions_without_accuracy_score(self):
        self.assertEqual(self.result["total_abstentions"],3000)
        self.assertTrue(self.result["no_scored_accuracy"])
        for row in self.result["arms"].values():
            self.assertIsNone(row["accuracy"])

    def test_no_hidden_gold_examination(self):
        self.assertFalse(self.result["inference_ground_truth_inspected"])

    def test_original_r5f_default_untouched(self):
        self.assertEqual(BUDGET,500)

    def test_input_unchanged_under_guard(self):
        inp=build_case(100,"unique_B_only")
        prev=copy.deepcopy(inp)
        guarded_call(forward_only,inp,-999)
        self.assertEqual(inp,prev)

    def test_reject_other_negative_integer(self):
        for budget in (-1,-10,-9999):
            with self.subTest(budget=budget):
                ans=guarded_call(lambda *_: 1,object(),budget)
                self.assertEqual(ans["status"],INVALID_NEGATIVE_BUDGET)
                self.assertEqual(ans["graph_operations_performed"],0)

    def test_invalid_type_bool_not_integer_capacity(self):
        r=guarded_call(lambda *_: 1,object(),True)
        self.assertEqual(r["status"],INVALID_BUDGET_TYPE)

    def test_invalid_type_float_not_integer_capacity(self):
        r=guarded_call(lambda *_: 1,object(),-999.0)
        self.assertEqual(r["status"],INVALID_BUDGET_TYPE)

    def test_invalid_type_string_not_integer_capacity(self):
        r=guarded_call(lambda *_: 1,object(),"-999")
        self.assertEqual(r["status"],INVALID_BUDGET_TYPE)

    def test_nonnegative_budget_still_delegates(self):
        inp=build_case(100,"unique_B_only")
        r=guarded_call(forward_only,inp,500)
        self.assertEqual(r["status"],"ALGORITHM_DISPATCHED")
        self.assertTrue(r["algorithm_invoked"])
        self.assertGreater(r["graph_operations_performed"],0)

    def test_scenarios_preserved(self):
        self.assertEqual(len(SCENARIOS),15)

    def test_no_production_modification(self):
        s=self.result["science_limits"]
        self.assertFalse(s["production_weights_changed"])
        self.assertTrue(s["source_R5F_unchanged"])
        self.assertTrue(s["source_R5F_X100_unchanged"])

    def test_no_retrocause_or_cognition_claim(self):
        s=self.result["science_limits"]
        self.assertFalse(s["physical_reverse_time_proven"])
        self.assertFalse(s["human_memory_measured"])
        self.assertFalse(s["neural_gain_established"])
        self.assertIn("HOLD",s["scientific_gate"])

    def test_no_independent_real_world_claim(self):
        s=self.result["science_limits"]
        self.assertFalse(s["external_custodian"])
        self.assertFalse(s["real_witness_data_used"])

    def test_status_is_invalid_budget_guard(self):
        self.assertEqual(self.result["status"],"INVALID_BUDGET_CORRECTLY_REJECTED__ENGINEERING_GUARD_PASS__SCIENCE_HOLD")


if __name__=="__main__":
    unittest.main()
