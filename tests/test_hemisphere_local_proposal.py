from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from hemisphere_local_proposal import (  # noqa: E402
    build_proposal,
    envelope,
    self_test,
    sha256_json,
    validate_envelope,
    validate_proposal,
)


class HemisphereLocalProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.left = json.loads((ROOT / "examples" / "hemisphere_left_hrain.json").read_text(encoding="utf-8"))
        cls.right = json.loads((ROOT / "examples" / "hemisphere_right_inaihr.json").read_text(encoding="utf-8"))
        cls.schema = json.loads((ROOT / "schemas" / "hemisphere-local-proposal.schema.json").read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema, format_checker=FormatChecker())

    def make(self, packet: dict, suffix: str = "left") -> dict:
        proposal = build_proposal(
            packet,
            proposal_id=f"proposal-{suffix}-test-0001",
            node_id=f"dh-node-{suffix}-test-0001",
            label="Candidate context",
            created_at="2026-08-16T10:10:00Z",
        )
        self.validator.validate(proposal)
        return envelope(proposal)

    def test_left_and_right_targets_are_exact(self) -> None:
        left = self.make(self.left, "left")
        right = self.make(self.right, "right")
        self.assertEqual(left["proposal"]["target"], {"hemisphere": "LEFT_HRAIN", "repository": "Hawkar-usls/Hrain"})
        self.assertEqual(right["proposal"]["target"], {"hemisphere": "RIGHT_INAIHR", "repository": "Hawkar-usls/iNaiHR"})

    def test_base_hash_binds_normalized_graph_only(self) -> None:
        wrapped = self.make(self.left)
        self.assertEqual(wrapped["proposal"]["base_graph_sha256"], sha256_json(self.left["graph"]))

    def test_operation_is_add_node_only_and_system_provenance(self) -> None:
        wrapped = self.make(self.left)
        operation = wrapped["proposal"]["operation"]
        self.assertEqual(operation["type"], "ADD_NODE")
        self.assertEqual(operation["node"]["origin"], "SYSTEM")
        self.assertFalse(wrapped["proposal"]["control"]["auto_apply"])
        self.assertTrue(wrapped["proposal"]["control"]["requires_explicit_local_accept"])
        self.assertFalse(wrapped["proposal"]["control"]["direct_cross_hemisphere_write"])
        self.assertFalse(wrapped["proposal"]["control"]["external_effect_permitted"])
        self.assertEqual(wrapped["proposal"]["control"]["authority_delta"], 0)
        self.assertEqual(wrapped["proposal"]["control"]["mass_effect_budget_delta"], 0)

    def test_envelope_hash_rejects_tampering(self) -> None:
        wrapped = self.make(self.left)
        tampered = copy.deepcopy(wrapped)
        tampered["proposal"]["operation"]["node"]["label"] = "Tampered"
        with self.assertRaisesRegex(ValueError, "proposal hash mismatch"):
            validate_envelope(tampered)

    def test_auto_apply_and_cross_write_are_refused(self) -> None:
        wrapped = self.make(self.left)
        auto_apply = copy.deepcopy(wrapped["proposal"])
        auto_apply["control"]["auto_apply"] = True
        with self.assertRaisesRegex(ValueError, "control boundary drifted"):
            validate_proposal(auto_apply)

        direct_write = copy.deepcopy(wrapped["proposal"])
        direct_write["control"]["direct_cross_hemisphere_write"] = True
        with self.assertRaisesRegex(ValueError, "control boundary drifted"):
            validate_proposal(direct_write)

    def test_target_mismatch_is_refused(self) -> None:
        proposal = self.make(self.left)["proposal"]
        proposal["target"] = {"hemisphere": "LEFT_HRAIN", "repository": "Hawkar-usls/iNaiHR"}
        with self.assertRaisesRegex(ValueError, "target hemisphere/repository mismatch"):
            validate_proposal(proposal)

    def test_extra_fields_are_refused(self) -> None:
        proposal = self.make(self.left)["proposal"]
        proposal["authority_override"] = True
        with self.assertRaisesRegex(ValueError, "fields must match"):
            validate_proposal(proposal)

    def test_self_test(self) -> None:
        result = self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(result["checks"]["tamper_refused"])
        self.assertTrue(result["checks"]["auto_apply_refused"])
        self.assertFalse(result["checks"]["proposal_is_mutation"])
        self.assertFalse(result["claim_ceiling"]["sha256_binding_is_signature"])
        self.assertFalse(result["claim_ceiling"]["ui_accept_event_is_verified_human_identity"])


if __name__ == "__main__":
    unittest.main()
