from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_registry_ingress import ingest  # noqa: E402
from nexus_habitat import sha256  # noqa: E402


class NexusRegistryIngressTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_release_receipt_replays_to_local_registry_receipt(self):
        release = self.load("examples/nexus_release_wait_receipt.json")
        expected = self.load("examples/nexus_registry_local_receipt.json")
        observed = ingest("RELEASE_RECEIPT", release)
        self.assertEqual(observed, expected)
        self.assertEqual(
            sha256(expected),
            "ab961fd55a9f3cdc4c248a9d2e0f3ff63c3ce0c0954f6e6ddd8c1c4c29d1d3de",
        )
        self.assertFalse(expected["effect_boundary"]["meta_registry_write_performed"])
        self.assertFalse(expected["effect_boundary"]["git_commit_performed"])
        self.assertFalse(expected["claim_ceiling"]["receipt_proves_payload_truth"])
        self.assertFalse(expected["claim_ceiling"]["receipt_is_archive_commit"])

    def test_effect_escalation_is_rejected(self):
        release = self.load("examples/nexus_release_wait_receipt.json")
        release["control"]["automatic_external_effect_permitted"] = True
        with self.assertRaises(ValueError):
            ingest("RELEASE_RECEIPT", release)

    def test_nonzero_authority_is_rejected(self):
        release = self.load("examples/nexus_release_wait_receipt.json")
        release["control"]["authority_delta"] = 1
        with self.assertRaises(ValueError):
            ingest("RELEASE_RECEIPT", release)


if __name__ == "__main__":
    unittest.main()
