from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from third_wish_catalog import catalog_status, inspect_request, load_config, self_test  # noqa: E402


class ThirdWishCatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = load_config()

    def test_catalog_activation_binds_32_of_32_receipt(self) -> None:
        status = catalog_status(self.config)
        self.assertEqual(status["genesis_signature"], "0:0 = JANUS")
        self.assertEqual(status["frozen_capability_ids"], 32)
        self.assertEqual(status["typed_reference_handler_contracts"], 32)
        self.assertEqual(status["adapter_ownership_overlap"], 0)
        self.assertEqual(status["catalog_completion"], "ESTABLISHED")

    def test_catalog_completion_does_not_imply_provider_completion(self) -> None:
        status = catalog_status(self.config)
        self.assertFalse(status["provider_universal_completion"])
        self.assertEqual(status["external_effect_authority"], "NOT_INHERITED_FROM_CATALOG_COMPLETION")

    def test_activation_does_not_execute_ordinary_request(self) -> None:
        result = inspect_request("GITHUB.REPOSITORY.READ", self.config)
        self.assertFalse(result["effect_executed"])
        self.assertFalse(result["provider_call_entered"])
        self.assertEqual(result["authority_delta"], 0)

    def test_high_impact_request_is_held(self) -> None:
        result = inspect_request("GITHUB.DESTRUCTIVE", self.config)
        self.assertTrue(result["high_impact_class"])
        self.assertTrue(result["fresh_verified_human_reauthorization_required"])
        self.assertEqual(
            result["decision"],
            "HELD_FOR_FRESH_VERIFIED_HUMAN_REAUTH_AND_PROVIDER_GATE",
        )
        self.assertFalse(result["effect_executed"])

    def test_mass_effect_budget_does_not_grow(self) -> None:
        status = catalog_status(self.config)
        self.assertEqual(status["mass_effect_budget_delta"], 0)

    def test_embedded_self_test(self) -> None:
        self.assertTrue(all(value == "PASS" for value in self_test().values()))


if __name__ == "__main__":
    unittest.main()
