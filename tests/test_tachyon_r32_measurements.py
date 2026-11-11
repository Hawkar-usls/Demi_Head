"""Offline adversarial tests for frozen candidate and published raw lab sources."""
import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from tachyon.r32_external_measurements import (
    SOURCES, FROZEN_CHECKPOINT_SHA, manifest_check,
    muon_summary,battery_summary,evaluate_manifest,BATTERY_API_FILE
)

MANIFEST_PATH=Path("data/tachyon/r32/independent_origin_measurement_manifest.json")

class R32Measurement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads(MANIFEST_PATH.read_text(encoding="utf8"))

    def test_only_two_immutable_sources(self):
        self.assertIs(manifest_check(self.manifest),self.manifest)
        self.assertEqual(len(self.manifest["public_measurement_sources"]),2)
        self.assertFalse(self.manifest["independent_custodian_connected"])
        self.assertFalse(self.manifest["independent_blind_evaluation"])

    def test_source_md5_rewrite_denied(self):
        bad=copy.deepcopy(self.manifest)
        bad["public_measurement_sources"][0]["expected_md5"]="0"*32
        with self.assertRaisesRegex(ValueError,"R32_UNPINNED_SOURCE"):
            manifest_check(bad)

    def test_candidate_checkpoint_identity_cannot_move(self):
        bad=copy.deepcopy(self.manifest)
        bad["candidate"]["reference_checkpoint_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"R32_CANDIDATE_SHA_OR_TRAINING_DRIFT"):
            manifest_check(bad)

    def test_unjustified_blind_claim_denied(self):
        bad=copy.deepcopy(self.manifest)
        bad["independent_blind_evaluation"]=True
        with self.assertRaisesRegex(ValueError,"R32_NO_BLIND_EVALUATOR_AVAILABLE"):
            manifest_check(bad)

    def test_muon_timing_descriptive_not_vacuum_lifetime(self):
        raw=b"momentum,time,neutrons\n10,2.4\n2,0\n11,4.0,3.3\n"
        s=muon_summary(raw,3)
        self.assertEqual(s["raw_event_rows"],3)
        self.assertEqual(s["tagged_decay_electron_delays_count"],2)
        self.assertAlmostEqual(s["tagged_delay_mean_microseconds"],3.2)
        self.assertIn("NOT_MUON_VACUUM_LIFETIME",s["interpretation"])

    def test_ocv_measurement_bounds(self):
        raw=b"StateOfCharge;OpenCircuitVoltage\n0,00;3,0\n0,50;3,65\n1,00;4,2\n"
        s=battery_summary(raw,3)
        self.assertEqual(s["raw_measurement_rows"],3)
        self.assertEqual(s["ocv_volts_max"],4.2)
        self.assertEqual(s["soc_observed_max"],1.)

    def test_refuse_muon_row_count_incomplete(self):
        with self.assertRaisesRegex(ValueError,"R32_MUON_EVENT_COUNT_DRIFT"):
            muon_summary(b"1,1\n2,2\n",3)

    def test_refuse_nonnumeric_and_unphysical_ocv(self):
        with self.assertRaisesRegex(ValueError,"R32_OCV_OUT_OF_RANGE"):
            battery_summary(b"0,1.1\n0.5,10.01\n1,4.2\n",3)

    def test_official_battery_api_content_fallback_requires_exact_md5(self):
        muon=b"momentum,delay\n10,2.4\n2,0\n11,4.0\n"
        ocv=b"soc;V\n0;3\n0,5;3,7\n1;4,2\n"
        samples={
            "SKVI_MUON_CAPTURE_TIMING_2025":muon,
            "OFFENBURG_BATTERY_OCV_2024":ocv
        }
        fake=copy.deepcopy(self.manifest)
        updates={}
        for source in fake["public_measurement_sources"]:
            data=samples[source["id"]]
            source["expected_md5"]=hashlib.md5(
                data,usedforsecurity=False).hexdigest()
            source["expected_measurement_count"]=3
            fam,url,md5,limit,n=SOURCES[source["id"]]
            updates[source["id"]]=(fam,url,source["expected_md5"],limit,3)
        with patch.dict(SOURCES,updates):
            requests=[]
            def fetch(url,limit):
                requests.append(url)
                if url==BATTERY_API_FILE:return ocv
                if url==SOURCES["OFFENBURG_BATTERY_OCV_2024"][1]:
                    return b"<html>PROXY-ERROR</html>"
                if url==SOURCES["SKVI_MUON_CAPTURE_TIMING_2025"][1]:
                    return muon
                raise ValueError("R32_NOT_ALLOWLISTED")
            o=evaluate_manifest(fake,fetch)
        self.assertEqual(o["external_measurement_sources_verified"],2)
        self.assertIn(BATTERY_API_FILE,requests)
        self.assertEqual(o["observations"][1]["download_endpoint_used"],
                         "OFFICIAL_RECORD_API_CONTENT")
        self.assertFalse(o["new_family_numeric_generalization_demonstrated"])

    def test_both_real_sources_unavailable_must_be_visible(self):
        def unavailable(url,budget):
            raise ValueError("R32_HTTP_429")
        r=evaluate_manifest(self.manifest,unavailable)
        self.assertEqual(r["external_measurement_sources_verified"],0)
        self.assertEqual(r["status"],"EXTERNAL_MEASUREMENT_SOURCE_INCOMPLETE")
        self.assertFalse(r["new_family_numeric_generalization_demonstrated"])
        self.assertEqual(r["unsupported_family_decisions"],2)
        self.assertTrue(all(x["source_failure_reason"]=="R32_HTTP_429"
                            for x in r["observations"]))

    def test_synthetic_two_source_integrity_only_no_generalization(self):
        muon=b"momentum,delay\n10,2.4\n2,0\n11,4.0\n"
        ocv=b"soc;V\n0;3\n0,5;3,7\n1;4,2\n"
        samples={
            "SKVI_MUON_CAPTURE_TIMING_2025":muon,
            "OFFENBURG_BATTERY_OCV_2024":ocv
        }
        fake=copy.deepcopy(self.manifest)
        changed={}
        for e in fake["public_measurement_sources"]:
            raw=samples[e["id"]]
            e["expected_md5"]=hashlib.md5(raw,usedforsecurity=False).hexdigest()
            e["expected_measurement_count"]=3
            fam,url,md5,budget,n=SOURCES[e["id"]]
            changed[e["id"]]=(fam,url,e["expected_md5"],budget,3)
        with patch.dict(SOURCES,changed):
            def fetch(url,limit):
                for entry in fake["public_measurement_sources"]:
                    if entry["id"] in SOURCES and SOURCES[entry["id"]][1]==url:
                        return samples[entry["id"]]
                raise RuntimeError("WRONG_URL")
            result=evaluate_manifest(fake,fetch)
        self.assertEqual(result["external_measurement_sources_verified"],2)
        self.assertEqual(result["unsupported_family_decisions"],2)
        self.assertEqual(result["status"],
                         "EXTERNAL_MEASUREMENTS_WITNESSED_NO_NEW_FAMILY_LEARNING")
        self.assertFalse(result["independently_blind"])
        self.assertFalse(result["model_weights_updated"])
        self.assertTrue(all(o["candidate_numeric_prediction"] is None
                            for o in result["observations"]))

if __name__=="__main__":
    unittest.main()
