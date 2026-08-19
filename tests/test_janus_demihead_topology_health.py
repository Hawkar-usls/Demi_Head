import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "janus_demihead_topology_health.py"
spec = importlib.util.spec_from_file_location("topology_health", TOOL)
topology_health = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(topology_health)


class DemiHeadTopologyHealthTests(unittest.TestCase):
    def setUp(self):
        self.manifest_path = ROOT / "configs" / "janus_demihead_topology_health.v1.json"
        self.contract_path = ROOT / "contracts" / "JANUS_DEMIHEAD_TOPOLOGY_HEALTH_FROZEN_CONTRACT.json"
        self.nexus_path = ROOT / ".janus" / "NEXUS_LINK.json"
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.contract = json.loads(self.contract_path.read_text(encoding="utf-8"))

    def test_frozen_contract_precedes_implementation_and_binds_parent(self):
        self.assertTrue(self.contract["frozen_before_implementation"])
        self.assertEqual(
            self.contract["parent"]["sha"],
            "4e5624bc0fcc4bc196934c954e5aa8f0dca119fd",
        )
        self.assertFalse(self.contract["promotion_gate"]["merge_before_all_green"])

    def test_manifest_binds_exact_frozen_contract_blob(self):
        self.assertEqual(
            topology_health.git_blob_sha(self.contract_path),
            self.manifest["frozen_contract"]["blob_sha"],
        )

    def test_manifest_binds_unchanged_demihead_nexus_blob(self):
        self.assertEqual(
            topology_health.git_blob_sha(self.nexus_path),
            self.manifest["demihead"]["nexus_link_blob_sha"],
        )

    def test_required_edges_are_exact_and_ordered(self):
        edge_ids = [edge["edge_id"] for edge in self.manifest["edges"]]
        self.assertEqual(edge_ids, self.manifest["required_edge_ids"])
        self.assertEqual(edge_ids, self.contract["required_edges"])
        self.assertEqual(len(edge_ids), 5)

    def test_current_manifest_is_three_promoted_two_pending(self):
        promoted = [e for e in self.manifest["edges"] if e["status"] == "PROMOTED"]
        pending = [e for e in self.manifest["edges"] if e["status"] != "PROMOTED"]
        self.assertEqual(len(promoted), 3)
        self.assertEqual(len(pending), 2)
        self.assertEqual(
            {e["repository"] for e in pending},
            {"Hawkar-usls/SkinGPT", "Hawkar-usls/Janus_Genesis"},
        )

    def test_every_provider_marker_is_metadata_only_and_zero_authority(self):
        for edge in self.manifest["edges"]:
            self.assertEqual(edge["allowed_drift_paths"], [edge["marker_path"]])
            self.assertRegex(edge["source_baseline_sha"], r"^[0-9a-f]{40}$")
            self.assertRegex(edge["promotion_head_sha"], r"^[0-9a-f]{40}$")

    def test_route_search_is_exact_not_keyword_based(self):
        route = ["A", "B", "C"]
        tree = {"nested": {"routes": [["X"], route]}}
        self.assertTrue(topology_health.contains_exact_list(tree, route))
        self.assertFalse(topology_health.contains_exact_list(tree, ["A", "B"]))

    def test_git_blob_hash_is_content_sensitive(self):
        self.assertNotEqual(
            topology_health.git_blob_sha_bytes(b"alpha"),
            topology_health.git_blob_sha_bytes(b"alpha\n"),
        )

    def test_admission_claim_cannot_be_true_while_required_edges_pending(self):
        self.assertTrue(any(e["status"] != "PROMOTED" for e in self.manifest["edges"]))
        self.assertEqual(
            self.manifest["admission_law"],
            "ALL_REQUIRED_EDGES_PROMOTED_AND_VERIFIED_OR_HOLD",
        )


if __name__ == "__main__":
    unittest.main()
