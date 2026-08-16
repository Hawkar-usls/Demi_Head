from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_habitat import (  # noqa: E402
    CONTRACT,
    ENVELOPE_SCHEMA,
    HEADS,
    ROUTES,
    habitat_snapshot,
    route_receipt,
    self_test,
    sha256,
    validate_envelope,
)


class NexusHabitatTests(unittest.TestCase):
    def envelope(self, source: str, target: str, kind: str):
        return {
            "schema": ENVELOPE_SCHEMA,
            "contract": CONTRACT,
            "envelope_id": f"test-{source.lower()}-{target.lower()}-{kind.lower()}",
            "source_head": source,
            "target_head": target,
            "payload_kind": kind,
            "payload_ref": {
                "sha256": sha256({"source": source, "target": target, "kind": kind}),
                "locator": "memory://test/payload",
            },
            "trace": [],
            "control": {
                "read_only_transfer": True,
                "direct_workspace_mutation": False,
                "external_effect_permitted": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
                "ttl_hops": 4,
            },
        }

    def test_all_admitted_routes_validate(self):
        for source, target, kind in ROUTES:
            with self.subTest(source=source, target=target, kind=kind):
                validate_envelope(self.envelope(source, target, kind))

    def test_route_receipt_is_not_delivery_or_authority(self):
        receipt = route_receipt(
            self.envelope("FUNDAMENTUM", "GUARDIAN", "EVIDENCE_RECEIPT")
        )
        self.assertEqual(receipt["status"], "ROUTE_ADMITTED_READ_ONLY")
        self.assertFalse(receipt["claim_ceiling"]["delivery_performed"])
        self.assertFalse(receipt["claim_ceiling"]["provider_realization_established"])
        self.assertFalse(receipt["claim_ceiling"]["route_is_authority"])
        self.assertEqual(receipt["routing"]["authority_delta"], 0)
        self.assertEqual(receipt["routing"]["mass_effect_budget_delta"], 0)
        self.assertFalse(receipt["routing"]["external_effect_permitted"])
        self.assertFalse(receipt["routing"]["direct_workspace_mutation"])

    def test_kind_compatibility_does_not_create_route(self):
        envelope = self.envelope("PORTAL", "REGISTRY", "ROUTE_RECEIPT")
        validate_envelope(envelope)
        envelope["target_head"] = "GUARDIAN"
        with self.assertRaises(ValueError):
            validate_envelope(envelope)

    def test_unknown_head_fails_closed(self):
        envelope = self.envelope("FUNDAMENTUM", "GUARDIAN", "EVIDENCE_RECEIPT")
        envelope["target_head"] = "UNKNOWN_HEAD"
        with self.assertRaises(ValueError):
            validate_envelope(envelope)

    def test_authority_or_effect_escalation_fails_closed(self):
        base = self.envelope("GUARDIAN", "RELEASE_CONTROL", "GUARDIAN_RESULT")
        for field, value in (
            ("authority_delta", 1),
            ("mass_effect_budget_delta", 1),
            ("external_effect_permitted", True),
            ("direct_workspace_mutation", True),
            ("read_only_transfer", False),
        ):
            with self.subTest(field=field):
                bad = copy.deepcopy(base)
                bad["control"][field] = value
                with self.assertRaises(ValueError):
                    validate_envelope(bad)

    def test_hop_budget_is_bounded(self):
        envelope = self.envelope("FUNDAMENTUM", "GUARDIAN", "EVIDENCE_RECEIPT")
        envelope["control"]["ttl_hops"] = 2
        envelope["trace"] = ["HRAIN", "BICAMERAL_BRIDGE"]
        with self.assertRaises(ValueError):
            validate_envelope(envelope)

    def test_snapshot_preserves_missing_as_unknown(self):
        snapshot = habitat_snapshot({"HRAIN": "READY", "INAIHR": "OFFLINE"})
        states = {item["head_id"]: item["availability"] for item in snapshot["heads"]}
        self.assertEqual(states["HRAIN"], "READY")
        self.assertEqual(states["INAIHR"], "OFFLINE")
        self.assertEqual(states["FUNDAMENTUM"], "UNKNOWN")
        self.assertFalse(snapshot["global_control"]["missing_head_means_success"])
        self.assertFalse(snapshot["global_control"]["degraded_head_may_be_silently_replaced"])

    def test_head_registry_has_no_authority_grant(self):
        self.assertGreaterEqual(len(HEADS), 9)
        snapshot = habitat_snapshot()
        self.assertTrue(all(item["authority_delta"] == 0 for item in snapshot["heads"]))
        self.assertEqual(snapshot["global_control"]["mass_effect_budget_delta"], 0)

    def test_sysear_fixture_is_hash_bound_and_read_only(self):
        payload_path = ROOT / "examples" / "sysear_sanitized_observation.json"
        envelope_path = ROOT / "examples" / "nexus_sysear_observer_to_guardian.json"
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        envelope = json.loads(envelope_path.read_text(encoding="utf-8"))

        self.assertTrue(payload["fixture"])
        self.assertFalse(payload["source"]["raw_identifiers_included"])
        self.assertFalse(payload["source"]["raw_syslog_included"])
        self.assertFalse(payload["quality"]["quantum_randomness_claim"])
        self.assertFalse(payload["control"]["direct_model_temperature_control"])
        self.assertFalse(payload["control"]["cryptographic_entropy_source"])
        self.assertEqual(payload["control"]["authority_delta"], 0)
        self.assertEqual(payload["control"]["mass_effect_budget_delta"], 0)
        self.assertEqual(envelope["payload_ref"]["sha256"], sha256(payload))

        receipt = route_receipt(envelope)
        self.assertEqual(receipt["source_head"], "OBSERVER")
        self.assertEqual(receipt["target_head"], "GUARDIAN")
        self.assertEqual(receipt["payload_kind"], "OBSERVATION_SIGNAL")
        self.assertFalse(receipt["claim_ceiling"]["delivery_performed"])
        self.assertFalse(receipt["routing"]["external_effect_permitted"])

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
