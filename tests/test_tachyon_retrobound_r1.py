"""Prepared (NOT YET EXECUTED) checks for TACHYON/RETROBOUND R1.

Run only in the next authorized test phase:
    python -m unittest discover -s tests -p test_tachyon_retrobound_r1.py -v
"""
import math
import unittest
from itertools import product

from tools import tachyon_retrobound_r1 as retro
from tools import tachyon_experiment_router as router


class RetroboundAnalyticTests(unittest.TestCase):
    def test_normalization(self):
        for b in retro.SPINS:
            for rho, eta in ((0.0, 0.0), (0.85, 0.9), (0.999, 0.999)):
                p = sum(retro.path_probability(path, b, rho, eta)
                        for path in product(retro.SPINS, repeat=5))
                self.assertAlmostEqual(p, 1.0, places=10)

    def test_transfer_hidden_correlation(self):
        for t in range(9):
            x = retro.hidden_mean(8, 0.85, 0.9, 1, t)
            self.assertAlmostEqual(x, 0.9 * 0.85 ** (8 - t), places=10)

    def test_full_accessible_parity_record_has_zero_tv(self):
        for n in (1, 2, 4, 8):
            self.assertLess(retro.exact_tv(
                n, 0.85, 0.9, retro.accessible_record), 1e-10)

    def test_hidden_observable_does_depend_on_boundary(self):
        n = 7
        private_tv = retro.exact_tv(n, 0.85, 0.9, lambda path: path[0])
        self.assertAlmostEqual(private_tv, 0.9 * 0.85 ** n, places=10)
        self.assertGreater(private_tv, 0)

    def test_forward_postselection_same_conditional_law(self):
        n, rho, eta = 5, 0.65, 0.7
        acceptance = 1 / (1 + eta)
        for b in retro.SPINS:
            for path in product(retro.SPINS, repeat=n + 1):
                forward = 0.5 * math.prod(
                    retro.transition(x, y, rho)
                    for x, y in zip(path, path[1:])
                )
                keep = retro.boundary_likelihood(path[-1], b, eta) / (1 + eta)
                conditioned = forward * keep / acceptance
                self.assertAlmostEqual(
                    conditioned, retro.path_probability(path, b, rho, eta), places=12
                )

    def test_malformed_parameters_refused(self):
        for args in ((0, 0.85, 0.9), (9, -0.1, 0.9),
                     (9, 0.85, 1.0), (9, float("nan"), 0.9),
                     (True, 0.5, 0.5)):
            with self.assertRaises(ValueError):
                retro.validate(*args)

    def test_science_gate_fails_closed_on_fake_external_future(self):
        receipt = {
            "schema": retro.SCHEMA,
            "classification": "SYNTHETIC_OFFLINE_MODEL_ONLY",
            "checks": {"analytical": True},
            "scientific_boundary": {
                "late_choice_created_independently_after_frozen_early_record": True
            },
        }
        with self.assertRaises(ValueError):
            retro.gated_research_receipt(receipt)

    def test_router_description_does_not_execute(self):
        metadata = router.describe()
        self.assertTrue(metadata["lanes"]["retrobound-r1"]["requires_explicit_run"])
        self.assertFalse(metadata["deployed_models_changed"])
        self.assertEqual(metadata["scientific_claim"], "NONE")

    def test_paired_monte_carlo_smoke_proposed(self):
        # This test is prepared but intentionally NOT run during integration.
        result = router.dispatch(
            "retrobound-r1", steps=4, rho=0.75, eta=0.7,
            trials=2000, seed=20261123
        )
        self.assertTrue(result["all_checks_passed"])
        self.assertEqual(result["tachyon_gate"]["physical_retrocausality"],
                         "NOT_TESTED_NOT_ESTABLISHED")
        self.assertFalse(result["scientific_boundary"][
            "late_choice_created_independently_after_frozen_early_record"])


if __name__ == "__main__":
    unittest.main()
