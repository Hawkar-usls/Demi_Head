"""Nexus ESSENCE v0.7 empirical WAL pilot contracts, no production authority."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from essence_v07_wal_fault_pilot import MODES, pilot, corrupt

class RealSQLiteWalPilot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = pilot(cycles=2)

    def test_all_cases_created_by_real_sqlite_engine(self):
        r = self.result
        self.assertEqual(r["total_trials"], 16)
        self.assertTrue(r["generated_new_faults_not_natural_failures"])
        self.assertEqual(len({c["trial_id"] for c in r["records"]}), 16)
        self.assertTrue(all(c["origin"] == "LOCAL_SQLITE_RUNTIME_PLUS_INDUCED_FAULT"
                            for c in r["records"]))

    def test_control_healthy_is_never_rejected(self):
        r = self.result
        self.assertEqual(r["baseline"]["false_reject_intact_wal"], 0)
        self.assertEqual(r["candidate"]["false_reject_intact_wal"], 0)
        self.assertEqual(r["already_existing_stronger_checksum_gate"]["false_reject_intact_wal"], 0)

    def test_candidate_detects_physical_faults(self):
        hits = {"magic_corrupt","version_corrupt","page_size_corrupt",
                "frame_page_zero","frame_truncation"}
        for c in self.result["records"]:
            if c["case_kind"] in hits:
                self.assertTrue(c["candidate_says_bad"], c["case_kind"])

    def test_candidate_misses_checksum_only_faults_and_owns_negative_evidence(self):
        misses = {"payload_bit_flip","frame_salt_flip"}
        for c in self.result["records"]:
            if c["case_kind"] in misses:
                self.assertFalse(c["candidate_says_bad"], c["case_kind"])
                self.assertTrue(c["stronger_existing_gate_says_bad"], c["case_kind"])
        self.assertGreater(self.result["candidate"]["false_accept_corrupt_wal"], 0)

    def test_not_strawman_existing_stronger_checker_is_reported(self):
        r = self.result
        self.assertLess(r["already_existing_stronger_checksum_gate"]["false_accept_corrupt_wal"],
                        r["candidate"]["false_accept_corrupt_wal"])

    def test_full_baseline_and_candidate_metrics_recorded(self):
        r = self.result
        self.assertGreater(r["baseline"]["false_accept_corrupt_wal"],
                           r["candidate"]["false_accept_corrupt_wal"])
        self.assertEqual(r["total_trials"], len(r["records"]))

    def test_no_external_scientific_claim(self):
        r = self.result
        self.assertEqual(r["scientific_gate"],
                         "DEVELOPMENT_ONLY_NO_PROSPECTIVE_OR_EXTERNAL_REPLICATION")
        self.assertFalse(r["production_authority"])
        self.assertFalse(r["offspring_activation"])
        self.assertFalse(r["externally_independent_verifier"])
        self.assertFalse(r["new_neural_model_trained"])

    def test_error_on_unregistered_fault(self):
        with self.assertRaisesRegex(ValueError,"UNREGISTERED_FAULT_FAMILY"):
            corrupt(b"really", "unregistered")

    def test_bounded_cases(self):
        for n in (0,17,-1):
            with self.assertRaisesRegex(ValueError,"UNBOUNDED_CYCLES"):
                pilot(n)

    def test_real_samples_include_distinct_source_hashes(self):
        self.assertGreater(len({r["wal_sha256"] for r in self.result["records"]}), 5)

if __name__=="__main__":
    unittest.main()
