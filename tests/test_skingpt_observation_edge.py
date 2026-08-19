from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import nexus_habitat_v2 as v2  # noqa: E402
import nexus_habitat_v2_1 as v21  # noqa: E402
import skingpt_observation_adapter as skin  # noqa: E402


def frame() -> dict:
    return {
        "schema": "skingpt.frame.v0.3",
        "device_id": "skingpt-node-01",
        "boot_id": "boot-abcdef01",
        "seq": 42,
        "uptime_ms": 123456,
        "system_operational": True,
        "experiment_baseline_valid": False,
        "baseline_ready": False,
        "event": {
            "type": "warm_touch",
            "confidence": 0.71,
            "severity_score": 0.23,
            "classifier": "rule_based_heuristic",
            "score_semantics": "heuristic_not_probability",
        },
        "piezo": {"peak": 120.0, "rms": 15.5, "samples": 64, "effective_hz": 980.0, "bias_adc": 2047},
        "thermal": {
            "zones_c": [24.1, 24.2, 24.3, 24.5, 24.4, 24.2, 24.1, None],
            "baseline_c": [23.9, 23.9, 24.0, 24.0, 24.0, 23.9, 23.9, None],
            "baseline_ready_by_zone": [True, True, True, True, True, True, True, False],
            "warmest_zone": 3,
            "warmest_c": 24.5,
            "warmest_delta_c": 0.5,
            "spread_c": 0.4,
        },
        "calibration": {
            "threshold_source_log_sha256": "a" * 64,
            "threshold_label_source": "controlled_idle_fixture",
        },
        "source_ip": "192.168.1.77",
    }


class SkinGPTObservationEdgeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.frame = frame()
        self.sample, self.envelope = v21.build_skingpt_envelope(self.frame)

    def test_v21_is_additive_and_v2_remains_parent(self) -> None:
        self.assertEqual(v21.CONTRACT, "JANUS_NEXUS_HABITAT_V2_1")
        self.assertEqual(v2.CONTRACT, "JANUS_NEXUS_HABITAT_V2")
        self.assertEqual(set(v21.HEADS) - set(v2.HEADS), {"SKINGPT"})
        self.assertEqual(set(v21.ROUTES) - set(v2.ROUTES), {("SKINGPT", "OBSERVER", "TELEMETRY_SAMPLE")})

    def test_valid_v03_frame_normalizes_and_routes(self) -> None:
        self.assertTrue(skin.verify_frame(self.frame))
        self.assertTrue(skin.verify_sample(self.frame, self.sample))
        self.assertTrue(v21.verify_skingpt_envelope(self.envelope, self.frame, self.sample))
        route = v21.route_receipt(self.envelope)
        self.assertEqual(route["status"], "ROUTE_ADMITTED_READ_ONLY")
        self.assertFalse(route["claim_ceiling"]["telemetry_is_observation_signal"])
        self.assertFalse(route["claim_ceiling"]["telemetry_is_truth"])

    def test_raw_identifiers_are_not_forwarded(self) -> None:
        serialized = repr(self.sample)
        self.assertNotIn(self.frame["device_id"], serialized)
        self.assertNotIn(self.frame["boot_id"], serialized)
        self.assertNotIn(self.frame["source_ip"], serialized)
        self.assertTrue(self.sample["privacy"]["source_identity_bound_by_hash"])
        self.assertFalse(self.sample["privacy"]["raw_device_id_forwarded"])
        self.assertFalse(self.sample["privacy"]["raw_boot_id_forwarded"])
        self.assertFalse(self.sample["privacy"]["raw_source_ip_forwarded"])

    def test_wrong_schema_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        bad["schema"] = "skingpt.frame.v9.9"
        self.assertFalse(skin.verify_frame(bad))

    def test_missing_required_field_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        del bad["thermal"]
        self.assertFalse(skin.verify_frame(bad))

    def test_unknown_event_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        bad["event"]["type"] = "damage_detected"
        self.assertFalse(skin.verify_frame(bad))

    def test_classifier_upgrade_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        bad["event"]["classifier"] = "validated_neural_diagnostic"
        self.assertFalse(skin.verify_frame(bad))

    def test_score_semantics_upgrade_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        bad["event"]["score_semantics"] = "damage_probability"
        self.assertFalse(skin.verify_frame(bad))

    def test_baseline_alias_mismatch_rejects(self) -> None:
        bad = copy.deepcopy(self.frame)
        bad["baseline_ready"] = True
        self.assertFalse(skin.verify_frame(bad))

    def test_severity_cannot_be_relabelled_as_damage_probability(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["event"]["severity_semantics"] = "calibrated_damage_probability"
        bad.pop("sample_sha256")
        bad["sample_sha256"] = skin.digest(bad)
        self.assertFalse(skin.verify_sample(self.frame, bad))

    def test_confidence_cannot_be_relabelled_as_posterior_probability(self) -> None:
        bad = copy.deepcopy(self.sample)
        bad["event"]["confidence_semantics"] = "calibrated_posterior_probability"
        bad.pop("sample_sha256")
        bad["sample_sha256"] = skin.digest(bad)
        self.assertFalse(skin.verify_sample(self.frame, bad))

    def test_hash_integrity_never_becomes_sensor_truth(self) -> None:
        self.assertFalse(self.sample["claim_ceiling"]["hash_integrity_is_sensor_truth"])
        self.assertFalse(self.sample["claim_ceiling"]["physical_sensor_validation_established"])
        self.assertFalse(self.sample["claim_ceiling"]["medical_or_safety_authority"])

    def test_unadmitted_route_rejects(self) -> None:
        bad = copy.deepcopy(self.envelope)
        bad["target_head"] = "REGISTRY"
        with self.assertRaises(ValueError):
            v21.validate_envelope(bad)

    def test_authority_and_mass_effect_escalation_reject(self) -> None:
        for field in ("authority_delta", "mass_effect_budget_delta"):
            bad = copy.deepcopy(self.envelope)
            bad["control"][field] = 1
            with self.assertRaises(ValueError):
                v21.validate_envelope(bad)

    def test_route_as_delivery_claim_rejects(self) -> None:
        bad = copy.deepcopy(self.envelope)
        bad["control"]["delivery_claimed"] = True
        with self.assertRaisesRegex(ValueError, "cannot claim delivery"):
            v21.validate_envelope(bad)


if __name__ == "__main__":
    unittest.main()
