"""TACHYON R4.0: finite negative/positive controls, never a physical CTC test."""
import unittest

from research.time_physics.tachyon_r40_hawking_causality import (
    I, X, P0, P1, RESET1, a_z_probabilities, bell_phi_plus_density,
    finite_ctc_fixed_points, is_cptp_kraus, local_b_map, scalar_dispersion_diagnostic,
    screen_claim, QFT_FIELDS, PROSPECTIVE_FIELDS,
)


class CausalGuardTests(unittest.TestCase):
    def test_unconditioned_entangled_marginal_unchanged(self):
        rho = bell_phi_plus_density()
        for channel in ([I], [X], [P0, P1], [P0, RESET1]):
            with self.subTest(channel=len(channel)):
                out = local_b_map(rho, channel)
                self.assertEqual(a_z_probabilities(out["rho_a"]), (0.5, 0.5))
                self.assertAlmostEqual(out["branch_probability"], 1.0)
                self.assertFalse(out["requires_late_herald"])

    def test_postselection_changes_conditional_not_early_marginal(self):
        rho = bell_phi_plus_density()
        early = local_b_map(rho, [P0, P1])
        later_selected = local_b_map(rho, [P0], conditioned=True)
        self.assertEqual(a_z_probabilities(early["rho_a"]), (0.5, 0.5))
        self.assertEqual(a_z_probabilities(later_selected["rho_a"]), (1.0, 0.0))
        self.assertAlmostEqual(later_selected["branch_probability"], 0.5)
        self.assertTrue(later_selected["requires_late_herald"])

    def test_incomplete_channel_forbidden_as_unconditional(self):
        self.assertFalse(is_cptp_kraus([P0]))
        with self.assertRaises(ValueError):
            local_b_map(bell_phi_plus_density(), [P0])

    def test_toy_classical_fixed_points(self):
        self.assertEqual(finite_ctc_fixed_points([0, 1]), [0, 1])
        self.assertEqual(finite_ctc_fixed_points([1, 0]), [])

    def test_bad_closed_map_rejected(self):
        with self.assertRaises(ValueError):
            finite_ctc_fixed_points([2, 0])

    def test_negative_mass_square_is_instability_not_signal(self):
        low = scalar_dispersion_diagnostic(k=1.0, mass_squared=-4.0)
        high = scalar_dispersion_diagnostic(k=3.0, mass_squared=-4.0)
        self.assertEqual(low["regime"], "EXPONENTIAL_INSTABILITY")
        self.assertGreater(high["group_velocity_formal"], 1.0)
        self.assertFalse(high["front_velocity_inferred"])
        self.assertFalse(high["physical_superluminal_channel_proven"])

    def test_qft_missing_is_hold(self):
        out = screen_claim({"kind": "ctc_spacetime", "metric_and_geometry": "toy"})
        self.assertEqual(out["verdict"], "HOLD_QFT_GEOMETRY_OR_BACKREACTION_INCOMPLETE")
        self.assertIn("semiclassical_backreaction", out["missing"])

    def test_qft_complete_manifest_is_still_not_proof(self):
        out = screen_claim({"kind": "ctc_spacetime",
                            **{k: "unverified user claim" for k in QFT_FIELDS}})
        self.assertEqual(out["verdict"], "HUMAN_QFT_REVIEW_REQUIRED__NOT_PHYSICAL_PROOF")

    def test_postselection_rejected_for_signaling_claim(self):
        self.assertEqual(screen_claim({"kind": "postselection",
                                       "claims_operational_backward_signaling": True})["verdict"],
                         "CONDITIONAL_ONLY__NO_BACKWARD_SIGNAL")

    def test_deutsch_is_hypothetical(self):
        self.assertIn("UNVERIFIED", screen_claim({"kind": "deutsch_ctc"})["verdict"])

    def test_prospective_requires_independent_future(self):
        out = screen_claim({"kind": "prospective_backward_signal",
                            "early_immutable_commit": True})
        self.assertIn("late_independent_entropy", out["missing"])

    def test_complete_prospective_checklist_still_not_result(self):
        out = screen_claim({"kind": "prospective_backward_signal",
                            **{k: True for k in PROSPECTIVE_FIELDS}})
        self.assertEqual(out["verdict"], "READY_FOR_EXTERNAL_EXAM__NO_RETROCAUSAL_RESULT")

    def test_unknown_model_abstains(self):
        self.assertIn("ABSTAIN", screen_claim({"kind": "warp_telepathy"})["verdict"])


if __name__ == "__main__":
    unittest.main()
