"""R5C observation-native synthetic model: split, leakage, safety, comparison."""
from __future__ import annotations

import copy
import math
import unittest

from tools.tachyon_r5b_witness_audit import (
    ABSTAIN, SCENARIOS, build_case, witness_rule,
)
from tools.tachyon_r5c_observation_native_train import (
    CONFIDENCE_CANDIDATES, DEV_FAMILIES, FEATURES, FORBIDDEN, LABELS,
    TEST_FAMILIES, VALIDATION_FAMILIES, _build, _hash_dataset, _prob,
    benchmark, extract_observation_features,
)


class R5CNativeLearningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = benchmark()

    def test_train_valid_test_are_separate(self):
        a, b, c = set(DEV_FAMILIES), set(VALIDATION_FAMILIES), set(TEST_FAMILIES)
        self.assertFalse(a & b or a & c or b & c)
        self.assertTrue(self.out["source_root_split_disjoint"])

    def test_train_valid_test_sizes(self):
        self.assertEqual((self.out["train_cases"], self.out["validation_cases"],
                          self.out["test_cases"]), (800,200,320))

    def test_model_really_learns_nonzero_parameters(self):
        self.assertEqual(self.out["learned_parameters"], len(FEATURES)*len(LABELS))
        self.assertTrue(any(abs(x) > 0.0001 for row in self.out["weights"] for x in row))
        self.assertEqual(self.out["epochs"],36)

    def test_only_observation_features_used(self):
        item, _ = build_case(3000,SCENARIOS[0],partition="holdout")
        self.assertFalse(FORBIDDEN & set(item))
        self.assertEqual(len(extract_observation_features(item)),len(FEATURES))

    def test_input_root_names_not_seen_as_raw_feature(self):
        item, _ = build_case(3000, SCENARIOS[0],partition="holdout")
        renamed=copy.deepcopy(item)
        for w in renamed["witnesses"]:
            w["root"]="completely-unrelated-" + w["root"]
        renamed["case_ref"]="altered-public-identifier"
        self.assertEqual(extract_observation_features(item),
                         extract_observation_features(renamed))

    def test_target_fields_prohibited(self):
        item, label=build_case(3000,SCENARIOS[0],partition="holdout")
        for key in ("target","scenario","gold","b_status","event_a_id","event_b_id"):
            candidate=copy.deepcopy(item)
            candidate[key]=label
            with self.assertRaises(ValueError):
                extract_observation_features(candidate)

    def test_non_synthetic_examples_rejected(self):
        item,_=build_case(3000,SCENARIOS[0],partition="holdout")
        item["synthetic_only"]=False
        with self.assertRaises(ValueError):
            extract_observation_features(item)

    def test_missing_witnesses_rejected(self):
        item,_=build_case(3000,SCENARIOS[0],partition="holdout")
        item.pop("witnesses")
        with self.assertRaises(ValueError):
            extract_observation_features(item)

    def test_missing_reference_rejected(self):
        item,_=build_case(3000,SCENARIOS[0],partition="holdout")
        item["reference_time_utc"]=None
        with self.assertRaises(ValueError):
            extract_observation_features(item)

    def test_reference_time_is_observation_not_receipt(self):
        item,_=build_case(3000,SCENARIOS[0],partition="holdout")
        edited=copy.deepcopy(item)
        for w in edited["witnesses"]:
            w["receipt_created_at_utc"]="2035-01-01T12:00:00+00:00"
        self.assertEqual(extract_observation_features(item),
                         extract_observation_features(edited))

    def test_plans_stay_plans(self):
        item, label=build_case(3000,"future_schedules_no_observations",partition="holdout")
        self.assertEqual(label,"ONLY_FUTURE_SCHEDULES")
        self.assertTrue(all(w["claim_medium"]=="schedule_notice"
                            for w in item["witnesses"]))

    def test_contradicting_clocks_are_distinct_from_normal(self):
        a,_=build_case(3000,"same_signature_separate_days",partition="holdout")
        b,_=build_case(3000,"contradictory_clocks",partition="holdout")
        self.assertNotEqual(extract_observation_features(a),
                            extract_observation_features(b))

    def test_future_as_observation_not_promoted(self):
        item,_=build_case(3000,"same_signature_separate_days",partition="holdout")
        for w in item["witnesses"]:
            if w["slot"]=="b":
                w["captured_at_utc"]="2026-12-02T08:00:00+00:00"
        self.assertEqual(witness_rule(item), ABSTAIN)

    def test_validation_threshold_predeclared(self):
        threshold=self.out["validation_only_selected_threshold"]
        self.assertIn(threshold,CONFIDENCE_CANDIDATES)
        self.assertEqual(len(self.out["validation_threshold_grid"]),
                         len(CONFIDENCE_CANDIDATES))

    def test_all_probs_finite_and_sum_one(self):
        w=self.out["weights"]
        item,_=build_case(3000,SCENARIOS[0],partition="holdout")
        p=_prob(w,extract_observation_features(item))
        self.assertEqual(len(p),len(LABELS))
        self.assertAlmostEqual(sum(p),1,places=6)
        self.assertTrue(all(math.isfinite(x) and 0 <= x <= 1 for x in p))

    def test_three_baselines_are_reported(self):
        self.assertEqual(set(self.out["arms"]),{
            "B_R5C_LEARNED_WITNESSES","C_FROZEN_R5B_STRONG_RULE",
            "D_WEAK_SINGLE_CLOCK","E_ALWAYS_ABSTAIN"
        })

    def test_strong_rule_controls_still_safe(self):
        c=self.out["arms"]["C_FROZEN_R5B_STRONG_RULE"]
        self.assertEqual(c["attempted"],128)
        self.assertEqual(c["unsupported_assertions"],0)
        self.assertEqual(c["selective_accuracy"],1.0)

    def test_learned_model_may_fail_without_false_pass(self):
        r=self.out
        b=r["arms"]["B_R5C_LEARNED_WITNESSES"]
        c=r["arms"]["C_FROZEN_R5B_STRONG_RULE"]
        self.assertEqual(r["model_vs_rule_coverage_delta"],
                         round(b["coverage"]-c["coverage"],6))
        if r["strict_positive_learned_gain_on_heldout"]:
            self.assertEqual(b["incorrect_attempted"],0)
            self.assertEqual(b["unsupported_assertions"],0)
            self.assertGreater(b["attempted"],c["attempted"])

    def test_zero_coverage_has_null_selective_accuracy(self):
        b=self.out["arms"]["E_ALWAYS_ABSTAIN"]
        self.assertEqual(b["attempted"],0)
        self.assertIsNone(b["selective_accuracy"])
        self.assertEqual(b["coverage"],0)

    def test_no_leak_of_test_labels_to_model_features(self):
        a,_=_build(TEST_FAMILIES,"holdout")[0]
        f=extract_observation_features(a)
        a=copy.deepcopy(a)
        a["case_ref"]="different-reference"
        self.assertEqual(f,extract_observation_features(a))

    def test_deterministic_challenge_hash(self):
        rows=_build(TEST_FAMILIES,"holdout")
        self.assertEqual(self.out["test_public_input_sha256"],
                         _hash_dataset(rows,labels=False))

    def test_actual_demihead_invariant(self):
        self.assertEqual(self.out["original_demihead_reference_outputs_preserved"],320)

    def test_trainable_model_is_not_production_neural_gain(self):
        r=self.out
        for prop in ("external_custodian","real_world_witnesses","human_or_clinical_data",
                     "physical_retrocausality_proven",
                     "subjective_time_phenomenology_measured",
                     "production_weights_changed","automatic_model_adoption"):
            self.assertFalse(r[prop])
        self.assertIn("HOLD",r["scientific_gate"])

    def test_not_reusing_old_r5b_holdout_family_range(self):
        self.assertGreater(min(TEST_FAMILIES),131)
        self.assertFalse(set(range(100,132)) & set(TEST_FAMILIES))

    def test_model_weights_observe_only_aggregate_evidence(self):
        self.assertNotIn("scenario",FEATURES)
        self.assertNotIn("root",FEATURES)
        self.assertNotIn("case_ref",FEATURES)
        self.assertNotIn("b_status",FEATURES)
        self.assertNotIn("event_id",FEATURES)


if __name__=="__main__":
    unittest.main()
