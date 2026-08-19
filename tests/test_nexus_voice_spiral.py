from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_voice_spiral import prepare_spiral_bundle, self_test  # noqa: E402


class NexusVoiceSpiralTests(unittest.TestCase):
    def test_frozen_two_layer_spiral(self) -> None:
        bundle = prepare_spiral_bundle()
        self.assertEqual(bundle["status"], "PREPARED_NOT_RENDERED")
        self.assertEqual(len(bundle["layers"]), 2)
        self.assertEqual([layer["speaker"] for layer in bundle["layers"]], ["aidar", "eugene"])
        self.assertTrue(bundle["spiral"]["preserve_all_layers"])
        self.assertFalse(bundle["spiral"]["automatic_winner_selection"])

    def test_language_and_source_identical(self) -> None:
        bundle = prepare_spiral_bundle()
        first = bundle["layers"][0]["request"]
        second = bundle["layers"][1]["request"]
        self.assertEqual(first["source"], second["source"])
        self.assertEqual(first["language"], second["language"])
        self.assertNotEqual(first["larynx"]["speaker"], second["larynx"]["speaker"])
        self.assertEqual(first["language"]["anchor_band_hz"], [117.0, 121.0])
        self.assertFalse(first["control"]["audio_rendered"])
        self.assertFalse(second["control"]["audio_rendered"])

    def test_self_test(self) -> None:
        result = self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["layer_count"], 2)
        self.assertFalse(result["audio_rendered"])


if __name__ == "__main__":
    unittest.main()
