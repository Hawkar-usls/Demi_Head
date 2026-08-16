from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_guardian_ingress import guardian_ingest, release_control  # noqa: E402
from nexus_habitat import sha256  # noqa: E402
from sysear_observer_normalizer import normalize  # noqa: E402


class SysEarObserverNormalizerTests(unittest.TestCase):
    def load(self, relative: str):
        return json.loads((ROOT / relative).read_text(encoding="utf-8"))

    def test_sanitized_window_replays_exact_observation(self):
        window = self.load("examples/sysear_aggregate_window_v1.json")
        expected = self.load("examples/sysear_normalized_observation_v1.json")
        observed = normalize(window)
        self.assertEqual(observed, expected)
        self.assertEqual(
            sha256(window),
            "24b2bb811ecde6f26cdda540c4285745eb22f1635eb8c7a9b7c259d46683c2c2",
        )
        self.assertEqual(
            sha256(expected),
            "5881444b0d041f5ba167e8272aef8d23f29b61b2a14a01654cf31b2eabd54c2e",
        )
        self.assertEqual(expected["quality"]["quality_state"], "PASS")
        self.assertFalse(expected["normalization"]["entropy_hint_eligible"])
        self.assertEqual(expected["normalization"]["entropy_hint_delta"], 0.0)
        self.assertFalse(expected["control"]["direct_model_temperature_control"])
        self.assertFalse(expected["control"]["cryptographic_entropy_source"])

    def test_observation_enters_guardian_as_advisory_not_truth(self):
        observation = self.load("examples/sysear_normalized_observation_v1.json")
        guardian = guardian_ingest("OBSERVATION_SIGNAL", observation)
        self.assertEqual(guardian["status"], "OBSERVATION_ACCEPTED_ADVISORY")
        self.assertEqual(guardian["bounded_result"]["evidence_state"], "OBSERVATION_ONLY_NOT_TRUTH")
        self.assertFalse(guardian["bounded_result"]["definitive_claim_permitted"])
        self.assertFalse(guardian["bounded_result"]["automatic_escalation_permitted"])
        self.assertFalse(guardian["control"]["automatic_retry_permitted"])
        self.assertEqual(
            sha256(guardian),
            "11eeb8bf0dc735c12e63f151640810dc9648de90555d27a4ed23f95ee1e986e6",
        )

        release = release_control(guardian)
        self.assertEqual(release["status"], "RELEASE_TO_HUMAN")
        self.assertTrue(release["control"]["return_control_to_human"])
        self.assertFalse(release["control"]["automatic_external_effect_permitted"])
        self.assertEqual(
            sha256(release),
            "95f2cf566960071097849186d39bf2bb9114f79d657573403164f239e027d350",
        )

    def test_raw_identifiers_fail_closed(self):
        window = self.load("examples/sysear_aggregate_window_v1.json")
        window["source"]["raw_mac_included"] = True
        with self.assertRaises(ValueError):
            normalize(window)

    def test_quantum_upgrade_fails_closed(self):
        window = self.load("examples/sysear_aggregate_window_v1.json")
        window["claims"]["quantum_randomness_established"] = True
        with self.assertRaises(ValueError):
            normalize(window)

    def test_entropy_validation_claim_fails_closed_in_v1(self):
        window = self.load("examples/sysear_aggregate_window_v1.json")
        window["claims"]["hardware_entropy_validated"] = True
        with self.assertRaises(ValueError):
            normalize(window)


if __name__ == "__main__":
    unittest.main()
