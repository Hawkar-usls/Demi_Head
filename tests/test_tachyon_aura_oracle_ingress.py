"""DemiHead read-only AURA Oracle advisory receiver: cross-repository fixture tests."""
from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools import tachyon_aura_oracle_ingress as bridge

FIXTURE = Path(__file__).parent / "fixtures" / "aura_tachyon_r1_advisory_ci_20261123.json"


class TachyonAuraIngressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = bridge.load_packet(FIXTURE)

    def test_authentic_ci_packet_reproduces_expected_canonical_digest(self):
        self.assertEqual(self.valid["packet_digest_sha256"], bridge.RECEIVED_PACKET_DIGEST)
        bridge.validate_packet(self.valid)

    def test_ingress_report_is_nonexecuting(self):
        result = bridge.ingest_advisory(self.valid)
        self.assertEqual(result["physical_retrocausality"], "NOT_ESTABLISHED")
        self.assertFalse(result["new_simulations_run"])
        self.assertFalse(result["production_activated"])
        self.assertFalse(result["model_weights_changed"])
        self.assertFalse(result["automated_future_random_choice"])

    def test_r2_controls_preserved_without_promoting_conclusion(self):
        result = bridge.ingest_advisory(self.valid)
        question = result["received_discrimination_question"]
        self.assertEqual(len(question["controls"]), 6)
        self.assertTrue(question["eligible_for_R2_design_review"])
        self.assertFalse(question["eligible_for_autonomous_experiment"])

    def test_reject_tampered_packet_without_recomputed_hash(self):
        changed = copy.deepcopy(self.valid)
        changed["mode"] = "PRODUCTION"
        with self.assertRaises(ValueError):
            bridge.validate_packet(changed)

    def test_reject_tampered_packet_with_recomputed_sha(self):
        changed = copy.deepcopy(self.valid)
        changed["hypothesis_discrimination"]["question"] = "Altered question"
        tmp = dict(changed)
        tmp.pop("packet_digest_sha256")
        changed["packet_digest_sha256"] = bridge.digest(tmp)
        with self.assertRaisesRegex(ValueError, "UNRECOGNIZED_AURA_PACKET_DIGEST"):
            bridge.validate_packet(changed)

    def test_reject_untested_retrocausal_physics_promotion(self):
        changed = copy.deepcopy(self.valid)
        changed["governance"]["may_change_tachyon_weights"] = True
        with self.assertRaises(ValueError):
            bridge.validate_packet(changed)

    def test_reject_forged_external_witness(self):
        changed = copy.deepcopy(self.valid)
        changed["source"]["external_physical_witness"] = True
        with self.assertRaises(ValueError):
            bridge.validate_packet(changed)

    def test_no_calibrated_future_claim(self):
        changed = copy.deepcopy(self.valid)
        changed["hypotheses"][2]["physical_truth_probability"] = 0.99
        with self.assertRaises(ValueError):
            bridge.validate_packet(changed)

    def test_reject_omitted_postselection_or_late_choice_gates(self):
        changed = copy.deepcopy(self.valid)
        changed["hypothesis_discrimination"]["prospective_controls"].remove(
            "PRECOMMITTED_FORWARD_AND_LEAKAGE_NULLS_WITH_MULTIPLICITY"
        )
        with self.assertRaises(ValueError):
            bridge.validate_packet(changed)

    def test_cli_receives_only_read_only_report(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "ack.json"
            with patch("sys.argv", ["tachyon_aura_oracle_ingress",
                                    "--input", str(FIXTURE), "--output", str(output)]):
                self.assertEqual(bridge.main(), 0)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertFalse(report["evidence_state_upgrade"])
            self.assertEqual(report["source_tachyon_commit"], bridge.EXPECTED_SOURCE_COMMIT)


if __name__ == "__main__":
    unittest.main()
