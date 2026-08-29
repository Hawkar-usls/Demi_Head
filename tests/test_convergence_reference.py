from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

SPEC = importlib.util.spec_from_file_location("convergence_reference", TOOLS / "convergence_reference.py")
assert SPEC and SPEC.loader
convergence = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(convergence)


class ConvergenceReferenceTests(unittest.TestCase):
    def test_internal_candidate_routing_has_no_authority(self) -> None:
        inventory = {
            "self_repository": "Hawkar-usls/Demi_Head",
            "source": "test",
            "authenticated_inventory": True,
            "repositories": [
                {"name":"Demi_Head","full_name":"Hawkar-usls/Demi_Head","default_branch":"main","visibility":"public","archived":False},
                {"name":"Hrain","full_name":"Hawkar-usls/Hrain","default_branch":"main","visibility":"public","archived":False,"description":"knowledge graph semantic memory"},
                {"name":"Other","full_name":"Hawkar-usls/Other","default_branch":"main","visibility":"private","archived":False,"description":"unrelated"},
            ],
        }
        result = convergence.build_proposal("semantic knowledge graph memory", inventory)
        names = {row["candidate_repository"] for row in result["candidates"]}
        self.assertIn("Hawkar-usls/Hrain", names)
        self.assertNotIn("Hawkar-usls/Demi_Head", names)
        self.assertFalse(result["claim_ceiling"]["cross_repository_write_permission"])
        self.assertFalse(result["claim_ceiling"]["novelty_established"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)

    def test_overlap_is_not_promoted_to_plagiarism(self) -> None:
        inventory = {
            "self_repository": "Hawkar-usls/Demi_Head",
            "repositories": [
                {"name":"GraphMind","full_name":"Hawkar-usls/GraphMind","default_branch":"main","visibility":"public","archived":False,"description":"graph memory"}
            ],
        }
        result = convergence.build_proposal("graph memory", inventory)
        self.assertIn("OVERLAP != PLAGIARISM", result["invariants"])
        self.assertFalse(result["claim_ceiling"]["plagiarism_established"])

    def test_third_thing_requires_explicit_delta(self) -> None:
        result = convergence.build_proposal("nothing matching", {"self_repository":"x/y","repositories":[]})
        self.assertIn("THIRD_THING_REQUIRES_EXPLICIT_INTERACTION_DELTA", result["invariants"])


if __name__ == "__main__":
    unittest.main()
