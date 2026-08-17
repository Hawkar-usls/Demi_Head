from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from goldprompt_handshake import build_upstream_fixture_receipt  # noqa: E402
from hemisphere_bridge import (  # noqa: E402
    BRIDGE_CONTRACT,
    HEMISPHERE_RULES,
    PACKET_SCHEMA,
    combine_packets,
    packet_sha256,
    semantic_key,
    self_test,
    validate_packet,
    verify_receipt_chain_result,
)

TEST_RUNTIME_SHA = "e" * 40


class HemisphereBridgeTests(unittest.TestCase):
    def setUp(self):
        self.previous_revision = os.environ.get("JANUS_SOURCE_REVISION")
        if not os.environ.get("GITHUB_SHA"):
            os.environ["JANUS_SOURCE_REVISION"] = TEST_RUNTIME_SHA

    def tearDown(self):
        if self.previous_revision is None:
            os.environ.pop("JANUS_SOURCE_REVISION", None)
        else:
            os.environ["JANUS_SOURCE_REVISION"] = self.previous_revision

    def packet(self, hemisphere: str, labels: list[tuple[str, str]]):
        rules = HEMISPHERE_RULES[hemisphere]
        nodes = [
            {"id": index + 1, "label": label, "origin": origin}
            for index, (label, origin) in enumerate(labels)
        ]
        links = [
            {"source": index + 1, "target": index + 2}
            for index in range(max(0, len(nodes) - 1))
        ]
        source_revision = ("a" if hemisphere == "LEFT_HRAIN" else "b") * 40
        upstream_receipt = build_upstream_fixture_receipt(hemisphere, source_revision)
        return {
            "schema": PACKET_SCHEMA,
            "packet_id": f"test-{hemisphere.lower()}",
            "hemisphere": hemisphere,
            "role": rules["role"],
            "captured_at": "2026-08-16T08:53:00Z",
            "source": {
                "repository": rules["repository"],
                "bridge_contract": BRIDGE_CONTRACT,
                "source_revision": source_revision,
                "goldprompt_receipt_sha256": upstream_receipt["receipt_sha256"],
                "workspace_mode": rules["workspace_mode"],
            },
            "goldprompt_receipt": upstream_receipt,
            "graph": {"nodes": nodes, "links": links},
            "control": {
                "read_only_transfer": True,
                "direct_cross_hemisphere_mutation": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }

    def test_bicameral_overlap_does_not_become_truth_or_authority(self):
        left = self.packet("LEFT_HRAIN", [("Context", "USER"), ("Evidence", "USER")])
        right = self.packet("RIGHT_INAIHR", [("🧩 Context", "SYSTEM"), ("Relation", "LOCAL_FALLBACK")])
        result = combine_packets(left=left, right=right)
        self.assertEqual(result["status"], "BICAMERAL_OVERLAP_PRESENT")
        self.assertEqual(result["comparison"]["shared_semantic_keys"], ["context"])
        self.assertFalse(result["comparison"]["automatic_graph_merge_performed"])
        self.assertFalse(result["routing"]["external_effect_permitted"])
        self.assertFalse(result["claim_ceiling"]["truth_claim_made"])
        self.assertFalse(result["claim_ceiling"]["agreement_is_truth"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)
        self.assertRegex(result["goldprompt_receipt"]["source_revision"], r"^[0-9a-f]{40}$")
        self.assertTrue(result["receipt_chain"]["canonical_bicameral_chain_complete"])
        self.assertTrue(result["receipt_chain"]["end_to_end_receipt_binding_established"])
        self.assertFalse(result["receipt_chain"]["origin_authentication_established"])
        self.assertTrue(verify_receipt_chain_result(result))

    def test_bicameral_divergence_is_preserved(self):
        left = self.packet("LEFT_HRAIN", [("Chronology", "USER")])
        right = self.packet("RIGHT_INAIHR", [("Metaphor", "REMOTE_AI")])
        result = combine_packets(left=left, right=right)
        self.assertEqual(result["status"], "BICAMERAL_DIVERGENCE_PRESERVED")
        self.assertEqual(result["comparison"]["shared_semantic_keys"], [])
        self.assertTrue(result["routing"]["disagreement_preserved"])

    def test_single_hemisphere_is_degraded_hold_and_not_canonical_chain(self):
        left = self.packet("LEFT_HRAIN", [("Context", "USER")])
        result = combine_packets(left=left)
        self.assertEqual(result["status"], "DEGRADED_SINGLE_HEMISPHERE")
        self.assertEqual(result["routing"]["mode"], "DEGRADED_SINGLE_HEMISPHERE_HOLD")
        self.assertFalse(result["routing"]["external_effect_permitted"])
        self.assertFalse(result["receipt_chain"]["end_to_end_receipt_binding_established"])

    def test_upstream_receipt_is_required_and_bound_to_packet(self):
        packet = self.packet("LEFT_HRAIN", [("Context", "USER")])
        missing = copy.deepcopy(packet)
        missing.pop("goldprompt_receipt")
        with self.assertRaises(ValueError):
            validate_packet(missing)
        drifted = copy.deepcopy(packet)
        drifted["source"]["goldprompt_receipt_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_packet(drifted)
        swapped = copy.deepcopy(packet)
        right = self.packet("RIGHT_INAIHR", [("Context", "SYSTEM")])
        swapped["goldprompt_receipt"] = right["goldprompt_receipt"]
        swapped["source"]["goldprompt_receipt_sha256"] = right["goldprompt_receipt"]["receipt_sha256"]
        with self.assertRaises(ValueError):
            validate_packet(swapped)

    def test_direct_cross_hemisphere_mutation_fails_closed(self):
        packet = self.packet("LEFT_HRAIN", [("Context", "USER")])
        packet["control"]["direct_cross_hemisphere_mutation"] = True
        with self.assertRaises(ValueError):
            validate_packet(packet)

    def test_wrong_repository_or_role_fails_closed(self):
        packet = self.packet("LEFT_HRAIN", [("Context", "USER")])
        wrong_repo = copy.deepcopy(packet)
        wrong_repo["source"]["repository"] = "Hawkar-usls/iNaiHR"
        with self.assertRaises(ValueError):
            validate_packet(wrong_repo)
        wrong_role = copy.deepcopy(packet)
        wrong_role["role"] = "ASSOCIATIVE_CONTEXT"
        with self.assertRaises(ValueError):
            validate_packet(wrong_role)

    def test_duplicate_or_dangling_topology_fails_closed(self):
        duplicate = self.packet("LEFT_HRAIN", [("A", "USER"), ("B", "USER")])
        duplicate["graph"]["nodes"][1]["id"] = 1
        with self.assertRaises(ValueError):
            validate_packet(duplicate)
        dangling = self.packet("RIGHT_INAIHR", [("A", "SYSTEM"), ("B", "LOCAL_FALLBACK")])
        dangling["graph"]["links"][0]["target"] = 999
        with self.assertRaises(ValueError):
            validate_packet(dangling)

    def test_origins_are_counted_separately(self):
        right = self.packet("RIGHT_INAIHR", [("A", "USER"), ("B", "REMOTE_AI"), ("C", "LOCAL_FALLBACK"), ("D", "LEGACY_UNKNOWN"), ("E", "SYSTEM")])
        result = combine_packets(right=right)
        counts = result["packet_receipts"]["RIGHT_INAIHR"]["origin_counts"]
        self.assertEqual(counts, {"USER": 1, "REMOTE_AI": 1, "LOCAL_FALLBACK": 1, "LEGACY_UNKNOWN": 1, "SYSTEM": 1})

    def test_packet_hash_is_canonical(self):
        packet = self.packet("LEFT_HRAIN", [("Context", "USER")])
        reordered = {key: packet[key] for key in reversed(list(packet.keys()))}
        self.assertEqual(packet_sha256(packet), packet_sha256(reordered))

    def test_chain_hash_tamper_fails_closed(self):
        result = combine_packets(left=self.packet("LEFT_HRAIN", [("Context", "USER")]), right=self.packet("RIGHT_INAIHR", [("Context", "SYSTEM")]))
        tampered = copy.deepcopy(result)
        tampered["receipt_chain"]["chain_sha256"] = "0" * 64
        self.assertFalse(verify_receipt_chain_result(tampered))

    def test_semantic_key_only_strips_leading_decoration(self):
        self.assertEqual(semantic_key("🧩 Context"), "context")
        self.assertEqual(semantic_key("  CONTEXT  "), "context")
        self.assertNotEqual(semantic_key("Contextual"), "context")

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
