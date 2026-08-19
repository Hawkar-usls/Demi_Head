from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import i0_measurement_adapter as i0  # noqa: E402
import nexus_habitat_v2_3 as v23  # noqa: E402
import nexus_habitat_v2_4 as v24  # noqa: E402


def summary(status: str = "OBSERVATION_ONLY") -> dict:
    s = {
        "schema": "janus.demihead.i0_measurement_summary.v1",
        "measurement_id": "I0-MEAS-0001",
        "source_bundle_sha256": "c" * 64,
        "status": status,
        "integrity_valid": True,
        "comparability_valid": False,
        "holdout_replication": False,
        "independent_replications": 0,
        "overlapping_views_counted_as_independent": False,
        "exposure": {"known": True, "checked_hashes": 1000000},
        "facts": {
            "accepted_shares": {"state": "OBSERVED", "value": 2, "unit": "count", "current": True},
            "wall_power_w": {"state": "UNKNOWN", "value": None, "unit": "W", "current": False},
            "temperature_c": {"state": "STALE", "value": 61.5, "unit": "C", "current": False},
        },
        "derived_metrics": {
            "accepted_per_mh": {"state": "OBSERVED", "value": 2.0, "unit": "per_MH", "current": True},
        },
        "claim_flags": {name: False for name in i0.FORBIDDEN_CLAIMS},
    }
    if status == "CONFIRMED":
        s["comparability_valid"] = True
        s["holdout_replication"] = True
        s["independent_replications"] = 1
        s["facts"]["temperature_c"] = {"state": "OBSERVED", "value": 61.5, "unit": "C", "current": True}
    return s


class I0MeasurementReceiptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.summary = summary()
        self.receipt, self.measurement_envelope = v24.build_measurement_route(self.summary)
        self.candidate, self.evidence_envelope = v24.build_evidence_route(self.receipt)

    def test_v24_is_additive_and_v23_remains_parent(self) -> None:
        self.assertEqual(v24.CONTRACT, "JANUS_NEXUS_HABITAT_V2_4")
        self.assertEqual(v23.CONTRACT, "JANUS_NEXUS_HABITAT_V2_3")
        self.assertEqual(set(v24.HEADS) - set(v23.HEADS), {"I0_MEASUREMENT", "MEASUREMENT_BROKER"})
        self.assertEqual(
            set(v24.ROUTES) - set(v23.ROUTES),
            {
                ("I0_MEASUREMENT", "MEASUREMENT_BROKER", "MEASUREMENT_RECEIPT"),
                ("MEASUREMENT_BROKER", "FUNDAMENTUM", "EVIDENCE_CANDIDATE"),
            },
        )

    def test_measurement_and_projection_routes_pass_without_promotion(self) -> None:
        self.assertTrue(i0.verify_summary(self.summary))
        self.assertTrue(i0.verify_receipt(self.summary, self.receipt))
        self.assertTrue(v24.verify_measurement_route(self.measurement_envelope, self.summary, self.receipt))
        self.assertTrue(i0.verify_evidence_candidate(self.receipt, self.candidate))
        self.assertTrue(v24.verify_evidence_route(self.evidence_envelope, self.receipt, self.candidate))
        self.assertFalse(self.candidate["projection"]["projection_is_claim_promotion"])
        self.assertFalse(self.candidate["projection"]["projection_is_evidence_admission"])

    def test_unknown_cannot_be_zero_filled(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["facts"]["wall_power_w"]["value"] = 0
        self.assertFalse(i0.verify_summary(bad))

    def test_unknown_exposure_cannot_carry_zero_or_count(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["exposure"] = {"known": False, "checked_hashes": 0}
        self.assertFalse(i0.verify_summary(bad))
        bad["exposure"] = {"known": False, "checked_hashes": None}
        self.assertTrue(i0.verify_summary(bad))

    def test_stale_cannot_be_current(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["facts"]["temperature_c"]["current"] = True
        self.assertFalse(i0.verify_summary(bad))

    def test_contaminated_cannot_support_confirmed(self) -> None:
        bad = summary("CONFIRMED")
        bad["facts"]["temperature_c"] = {"state": "CONTAMINATED", "value": 61.5, "unit": "C", "current": False}
        self.assertFalse(i0.verify_summary(bad))

    def test_confirmed_requires_integrity_comparability_holdout_and_replication(self) -> None:
        good = summary("CONFIRMED")
        self.assertTrue(i0.verify_summary(good))
        for key in ("integrity_valid", "comparability_valid", "holdout_replication"):
            bad = copy.deepcopy(good)
            bad[key] = False
            self.assertFalse(i0.verify_summary(bad), key)
        bad = copy.deepcopy(good)
        bad["independent_replications"] = 0
        self.assertFalse(i0.verify_summary(bad))

    def test_overlapping_views_cannot_be_counted_as_independent(self) -> None:
        bad = copy.deepcopy(self.summary)
        bad["overlapping_views_counted_as_independent"] = True
        bad["independent_replications"] = 4
        self.assertFalse(i0.verify_summary(bad))

    def test_forbidden_claims_reject_at_summary(self) -> None:
        for name in i0.FORBIDDEN_CLAIMS:
            bad = copy.deepcopy(self.summary)
            bad["claim_flags"][name] = True
            self.assertFalse(i0.verify_summary(bad), name)

    def test_rehashed_receipt_cannot_promote_broad_claim(self) -> None:
        for claim in (
            "sha256_predictability_or_weakness_established",
            "mining_advantage_or_profitability_established",
            "wall_energy_savings_established",
            "extended_hardware_lifetime_established",
        ):
            bad = copy.deepcopy(self.receipt)
            bad["claim_ceiling"][claim] = True
            bad.pop("receipt_sha256")
            bad["receipt_sha256"] = i0.digest(bad)
            with self.assertRaises(ValueError):
                i0.build_evidence_candidate(bad)

    def test_evidence_projection_preserves_unknown_stale_and_contaminated_lists(self) -> None:
        self.assertIn("facts.wall_power_w", self.candidate["projection"]["unknown_fields_preserved"])
        self.assertIn("facts.temperature_c", self.candidate["projection"]["stale_fields_preserved"])
        self.assertEqual(self.candidate["projection"]["contaminated_fields_preserved"], [])

    def test_unadmitted_routes_reject(self) -> None:
        bad = copy.deepcopy(self.measurement_envelope)
        bad["target_head"] = "FUNDAMENTUM"
        with self.assertRaises(ValueError):
            v24.validate_envelope(bad)
        bad = copy.deepcopy(self.evidence_envelope)
        bad["source_head"] = "I0_MEASUREMENT"
        with self.assertRaises(ValueError):
            v24.validate_envelope(bad)

    def test_authority_mass_effect_delivery_and_admission_escalation_reject(self) -> None:
        for original in (self.measurement_envelope, self.evidence_envelope):
            for field, value in (("authority_delta", 1), ("mass_effect_budget_delta", 1), ("delivery_claimed", True), ("admission_claimed", True)):
                bad = copy.deepcopy(original)
                bad["control"][field] = value
                with self.assertRaises(ValueError):
                    v24.validate_envelope(bad)

    def test_route_receipt_never_claims_admission_or_truth(self) -> None:
        for envelope in (self.measurement_envelope, self.evidence_envelope):
            route = v24.route_receipt(envelope)
            self.assertFalse(route["routing"]["delivery_performed"])
            self.assertFalse(route["routing"]["claim_promotion_performed"])
            self.assertFalse(route["routing"]["evidence_admission_performed"])
            self.assertFalse(route["claim_ceiling"]["measurement_receipt_is_truth"])


if __name__ == "__main__":
    unittest.main()
