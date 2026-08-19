from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import nexus_habitat_v2_1 as v21  # noqa: E402
import nexus_habitat_v2_2 as v22  # noqa: E402
import swarm_edge_observation_adapter as swarm  # noqa: E402


def summary() -> dict:
    return {
        "schema": "janus.demihead.swarm_edge_summary.v1",
        "node_id": "anchor_pn_lab",
        "node_kind": "ESP32_S3_ANCHOR",
        "firmware_version": "v1.20",
        "declared_identity": "anchor_pn_lab:ESP32_S3_ANCHOR",
        "packet_family": "P/N",
        "observed_at_ms": 1_800_000_123_000,
        "freshness": "FRESH",
        "presence_basis": "CURRENT_PACKET",
        "observer_only": True,
        "submit_pressure": 0,
        "radio": {"channel": 10, "peer_channel": 10, "rx_age_ms": 120, "tx_ok": 88, "tx_fail": 2, "rescue_count": 1},
        "work": {"hash_rate": 12.5, "best_bits": 24, "target_bits": 32, "accepted": 1, "rejected": 0, "stale": 0},
        "sensors": {
            "temperature_c": {"state": "ABSENT", "value": None, "unit": "C"},
            "radio_rssi_dbm": {"state": "FRESH", "value": -62.0, "unit": "dBm"},
        },
    }


class SwarmEdgeObservationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = summary()
        self.sample, self.envelope = v22.build_swarm_envelope(self.summary)

    def test_v22_is_additive_and_v21_remains_parent(self) -> None:
        self.assertEqual(v22.CONTRACT, "JANUS_NEXUS_HABITAT_V2_2")
        self.assertEqual(v21.CONTRACT, "JANUS_NEXUS_HABITAT_V2_1")
        self.assertEqual(set(v22.HEADS) - set(v21.HEADS), {"SWARM_EDGE"})
        self.assertEqual(set(v22.ROUTES) - set(v21.ROUTES), {("SWARM_EDGE", "OBSERVER", "TELEMETRY_SAMPLE")})

    def test_valid_summary_routes_read_only(self) -> None:
        self.assertTrue(swarm.verify_summary(self.summary))
        self.assertTrue(swarm.verify_sample(self.summary, self.sample))
        self.assertTrue(v22.verify_swarm_envelope(self.envelope, self.summary, self.sample))
        route = v22.route_receipt(self.envelope)
        self.assertFalse(route["routing"]["delivery_performed"])
        self.assertFalse(route["routing"]["command_performed"])
        self.assertFalse(route["claim_ceiling"]["edge_telemetry_is_command"])

    def test_unknown_packet_family_rejects(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["packet_family"] = "T/P"
        self.assertFalse(swarm.verify_summary(bad))

    def test_unknown_freshness_rejects(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["freshness"] = "MAGICALLY_CURRENT"
        self.assertFalse(swarm.verify_summary(bad))

    def test_stale_sensor_with_numeric_value_rejects(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["sensors"]["temperature_c"] = {"state": "STALE", "value": 22.0, "unit": "C"}
        self.assertFalse(swarm.verify_summary(bad))

    def test_absent_sensor_with_numeric_value_rejects(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["sensors"]["temperature_c"] = {"state": "ABSENT", "value": 17.0, "unit": "C"}
        self.assertFalse(swarm.verify_summary(bad))

    def test_fresh_sensor_requires_real_numeric_value(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["sensors"]["radio_rssi_dbm"]["value"] = None
        self.assertFalse(swarm.verify_summary(bad))

    def test_observer_only_submit_pressure_must_be_zero(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["submit_pressure"] = 0.1
        self.assertFalse(swarm.verify_summary(bad))

    def test_prediction_cannot_be_fresh_current_presence(self) -> None:
        for basis in ("PREDICTION", "MEMORY"):
            bad = copy.deepcopy(self.summary)
            bad["presence_basis"] = basis
            self.assertFalse(swarm.verify_summary(bad))

    def test_stale_memory_remains_stale_not_current(self) -> None:
        stale = copy.deepcopy(self.summary)
        stale["freshness"] = "STALE"
        stale["presence_basis"] = "MEMORY"
        stale["sensors"]["radio_rssi_dbm"] = {"state": "STALE", "value": None, "unit": "dBm"}
        self.assertTrue(swarm.verify_summary(stale))
        sample = swarm.build_sample(stale)
        self.assertFalse(sample["presence"]["current_presence_established"])
        self.assertTrue(sample["presence"]["stale_or_degraded_state_preserved"])

    def test_semantic_identity_collision_or_alias_rejects(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["declared_identity"] = "beacon:UNRELATED_NODE"
        self.assertFalse(swarm.verify_summary(bad))

    def test_pool_sha_truth_cannot_be_promoted(self) -> None:
        bad_sample = copy.deepcopy(self.sample)
        bad_sample["work"]["sha_target_submit_semantics_reinterpreted"] = True
        bad_sample.pop("sample_sha256")
        bad_sample["sample_sha256"] = swarm.digest(bad_sample)
        self.assertFalse(swarm.verify_sample(self.summary, bad_sample))

    def test_unadmitted_route_rejects(self) -> None:
        bad = copy.deepcopy(self.envelope)
        bad["target_head"] = "REGISTRY"
        with self.assertRaises(ValueError):
            v22.validate_envelope(bad)

    def test_authority_mass_effect_and_delivery_escalation_reject(self) -> None:
        for field, value in (("authority_delta", 1), ("mass_effect_budget_delta", 1), ("delivery_claimed", True)):
            bad = copy.deepcopy(self.envelope)
            bad["control"][field] = value
            with self.assertRaises(ValueError):
                v22.validate_envelope(bad)


if __name__ == "__main__":
    unittest.main()
