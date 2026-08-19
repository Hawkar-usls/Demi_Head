from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import aifc_witness_adapter as aifc  # noqa: E402
import nexus_habitat_v2_2 as v22  # noqa: E402
import nexus_habitat_v2_3 as v23  # noqa: E402


def gates(state: str = "PASS") -> dict:
    return {name: state for name in aifc.MANDATORY_GATES}


def summary(grade: str = "FORWARD_NULL_COMPATIBLE") -> dict:
    base = {
        "schema": "janus.demihead.aifc_witness_package_summary.v1",
        "package_id": "AIFC-TRIAL-0001",
        "package_sha256": "a" * 64,
        "trial_state": "TERMINAL",
        "grade": grade,
        "mandatory_gates": gates(),
        "admitted": True,
        "statistical_threshold_crossed": False,
        "internal_adversarial_audit_pass": False,
        "independent_replications": 0,
        "mechanism_established": False,
        "physical_retrocausality_claimed": False,
    }
    if grade == "NOT_ADMITTED":
        base["admitted"] = False
        base["mandatory_gates"]["EXTERNAL_FRESHNESS"] = "MISSING"
    elif grade == "STRUCTURAL_MATCH_ONLY":
        base["admitted"] = False
        base["mandatory_gates"]["PROOF_CARRYING_ENTROPY_PROFILE"] = "UNKNOWN"
    elif grade == "FORWARD_NULL_INCOMPATIBILITY_CANDIDATE":
        base["statistical_threshold_crossed"] = True
    elif grade == "EXTERNAL_REPLICATION_REQUIRED":
        base["statistical_threshold_crossed"] = True
        base["internal_adversarial_audit_pass"] = True
        base["independent_replications"] = 1
    elif grade == "REPLICATED_FORWARD_NULL_INCOMPATIBILITY":
        base["statistical_threshold_crossed"] = True
        base["internal_adversarial_audit_pass"] = True
        base["independent_replications"] = 2
    elif grade == "PHYSICAL_MECHANISM_UNRESOLVED":
        base["statistical_threshold_crossed"] = True
        base["internal_adversarial_audit_pass"] = True
        base["independent_replications"] = 2
    return base


class AIFCWitnessEvidenceTests(unittest.TestCase):
    def test_v23_is_additive_and_v22_remains_parent(self) -> None:
        self.assertEqual(v23.CONTRACT, "JANUS_NEXUS_HABITAT_V2_3")
        self.assertEqual(v22.CONTRACT, "JANUS_NEXUS_HABITAT_V2_2")
        self.assertEqual(set(v23.HEADS) - set(v22.HEADS), {"AIFC_WITNESS"})
        self.assertEqual(set(v23.ROUTES) - set(v22.ROUTES), {("AIFC_WITNESS", "FUNDAMENTUM", "EVIDENCE_CANDIDATE")})

    def test_all_declared_grades_have_consistent_positive_fixture(self) -> None:
        for grade in sorted(aifc.GRADES):
            with self.subTest(grade=grade):
                s = summary(grade)
                self.assertTrue(aifc.verify_summary(s))
                candidate, envelope = v23.build_aifc_envelope(s)
                self.assertTrue(v23.verify_aifc_envelope(envelope, s, candidate))
                route = v23.route_receipt(envelope)
                self.assertFalse(route["routing"]["evidence_admission_performed"])
                self.assertFalse(route["claim_ceiling"]["aifc_grade_is_world_truth"])

    def test_invalid_package_hash_rejects(self) -> None:
        s = summary()
        s["package_sha256"] = "not-a-hash"
        self.assertFalse(aifc.verify_summary(s))

    def test_missing_or_unknown_gate_name_rejects(self) -> None:
        s = summary()
        del s["mandatory_gates"]["EXTERNAL_FRESHNESS"]
        self.assertFalse(aifc.verify_summary(s))
        s = summary()
        s["mandatory_gates"]["INVENTED_GATE"] = "PASS"
        self.assertFalse(aifc.verify_summary(s))

    def test_grade0_with_all_gates_pass_rejects(self) -> None:
        s = summary("NOT_ADMITTED")
        s["mandatory_gates"] = gates()
        self.assertFalse(aifc.verify_summary(s))

    def test_grade2_with_threshold_crossed_rejects(self) -> None:
        s = summary("FORWARD_NULL_COMPATIBLE")
        s["statistical_threshold_crossed"] = True
        self.assertFalse(aifc.verify_summary(s))

    def test_grade3_with_nonpass_gate_rejects(self) -> None:
        s = summary("FORWARD_NULL_INCOMPATIBILITY_CANDIDATE")
        s["mandatory_gates"]["CAUSAL_DAG" if "CAUSAL_DAG" in s["mandatory_gates"] else "MACHINE_READABLE_CAUSAL_DAG"] = "UNKNOWN"
        self.assertFalse(aifc.verify_summary(s))

    def test_grade4_without_internal_audit_rejects(self) -> None:
        s = summary("EXTERNAL_REPLICATION_REQUIRED")
        s["internal_adversarial_audit_pass"] = False
        self.assertFalse(aifc.verify_summary(s))

    def test_grade5_with_fewer_than_two_replicates_rejects(self) -> None:
        s = summary("REPLICATED_FORWARD_NULL_INCOMPATIBILITY")
        s["independent_replications"] = 1
        self.assertFalse(aifc.verify_summary(s))

    def test_grade6_cannot_claim_mechanism_established(self) -> None:
        s = summary("PHYSICAL_MECHANISM_UNRESOLVED")
        s["mechanism_established"] = True
        self.assertFalse(aifc.verify_summary(s))

    def test_retrocausality_claim_rejects_for_every_grade(self) -> None:
        for grade in sorted(aifc.GRADES):
            s = summary(grade)
            s["physical_retrocausality_claimed"] = True
            self.assertFalse(aifc.verify_summary(s))

    def test_candidate_cannot_be_relabelled_as_truth_or_admission(self) -> None:
        s = summary("FORWARD_NULL_INCOMPATIBILITY_CANDIDATE")
        candidate = aifc.build_candidate(s)
        bad = copy.deepcopy(candidate)
        bad["fundamentum_boundary"]["route_is_fundamentum_admission"] = True
        bad.pop("candidate_sha256")
        bad["candidate_sha256"] = aifc.digest(bad)
        self.assertFalse(aifc.verify_candidate(s, bad))

    def test_unadmitted_route_rejects(self) -> None:
        s = summary()
        _, envelope = v23.build_aifc_envelope(s)
        envelope["target_head"] = "REGISTRY"
        with self.assertRaises(ValueError):
            v23.validate_envelope(envelope)

    def test_authority_mass_effect_delivery_and_admission_escalation_reject(self) -> None:
        s = summary()
        _, envelope = v23.build_aifc_envelope(s)
        for field, value in (("authority_delta", 1), ("mass_effect_budget_delta", 1), ("delivery_claimed", True), ("admission_claimed", True)):
            bad = copy.deepcopy(envelope)
            bad["control"][field] = value
            with self.assertRaises(ValueError):
                v23.validate_envelope(bad)


if __name__ == "__main__":
    unittest.main()
