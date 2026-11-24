"""TACHYON-R1 anti-leakage and non-promotion regression suite."""
import json
import tempfile
from pathlib import Path
import unittest
from tachyon.temporal_evidence import SCHEMA, TemporalHold, digest, seal, validate, main

SOURCE = dict(repository="Hawkar-usls/Janus-Demiurge", commit_sha="a"*40,
              path="experiments/ocean_transformer/observed.json", content_sha256="b"*64,
              source_family_id="OCEAN-009B-20261112", evidence_class="SYNTHETIC_CONTROL")
TIMES = dict(observed_at="2026-11-10T17:00:00Z", available_at="2026-11-10T18:00:00Z",
             feature_cutoff_at="2026-11-10T19:00:00Z", forecast_frozen_at="2026-11-10T20:00:00Z",
             target_at="2026-11-12T08:00:00Z", resolved_at=None)

def make(kind="FEATURE"):
    times = dict(TIMES)
    if kind == "FORECAST":
        times.update(observed_at=None, available_at="2026-11-10T20:01:00Z")
    elif kind == "RESOLUTION":
        times.update(observed_at="2026-11-12T08:00:05Z",
                     available_at="2026-11-12T08:00:10Z",
                     resolved_at="2026-11-12T08:02:00Z")
    controls = dict(provenance_checked_externally=False, training_permitted=False,
                    automatic_deployment=False, scientific_claim_promoted=False,
                    forecast_link_sha256="c"*64 if kind == "RESOLUTION" else None)
    value = dict(probability_1=0.47 if kind == "FORECAST" else None,
                 observed_label=1 if kind == "RESOLUTION" else None,
                 description="synthetic fixture only")
    r = dict(schema=SCHEMA, record_id="R1-synthetic-0001", kind=kind,
             target_id="D-20261112-R001", source=dict(SOURCE),
             times=times, value=value, controls=controls)
    return seal(r)

class TemporalEvidenceTests(unittest.TestCase):
    def reject(self, item, reason):
        item["content_sha256"] = digest({k:v for k,v in item.items() if k != "content_sha256"})
        with self.assertRaisesRegex(TemporalHold, reason):
            validate(item)

    def test_feature_structural_pass_no_training(self):
        r=validate(make())
        self.assertFalse(r["outcome_admitted_for_training"])
        self.assertFalse(r["source_bytes_authenticated"])

    def test_forecast_pass_without_outcome(self):
        self.assertEqual(validate(make("FORECAST"))["kind"], "FORECAST")

    def test_resolution_requires_separate_admission(self):
        r=validate(make("RESOLUTION"))
        self.assertFalse(r["outcome_admitted_for_training"])

    def test_old_observation_published_after_freeze_is_rejected(self):
        r=make(); r["times"]["available_at"]="2026-11-11T01:00:00Z"
        self.reject(r,"LATE_FEATURE_NOT_ADMISSIBLE")

    def test_future_label_in_forecast_rejected(self):
        r=make("FORECAST");r["value"]["observed_label"]=1
        self.reject(r,"FORECAST_PROBABILITY_OR_OUTCOME_LEAK")

    def test_forecast_artifact_after_target_rejected(self):
        r=make("FORECAST");r["times"]["available_at"]="2026-11-12T09:00:00Z"
        self.reject(r,"FORECAST_PUBLICATION_NOT_PRE_TARGET")

    def test_backdated_resolution_rejected(self):
        r=make("RESOLUTION");r["times"]["resolved_at"]="2026-11-11T08:00:00Z"
        self.reject(r,"LATE_OUTCOME_TIMESTAMP_ORDER_INVALID")

    def test_altered_digest_rejected(self):
        r=make();r["source"]["path"]="another.json"
        with self.assertRaisesRegex(TemporalHold,"ENVELOPE_DIGEST_MISMATCH"):
            validate(r)

    def test_automatic_training_claim_rejected(self):
        r=make("RESOLUTION");r["controls"]["training_permitted"]=True
        self.reject(r,"ASSERTED_AUTHORITY_NOT_ACCEPTED")

    def test_future_outcome_in_feature_rejected(self):
        r=make();r["value"]["observed_label"]=0
        self.reject(r,"FEATURE_HAS_FUTURE_LABEL")

    def test_source_family_required(self):
        r=make();r["source"]["source_family_id"]=""
        self.reject(r,"SOURCE_FAMILY_REQUIRED")

    def test_naive_timestamp_rejected(self):
        r=make();r["times"]["available_at"]="2026-11-10T18:00:00"
        self.reject(r,"UTC_Z_TIMESTAMP_REQUIRED")

    def test_duplicate_json_keys_rejected_by_cli(self):
        with tempfile.TemporaryDirectory() as p:
            path=Path(p)/"x.json";path.write_text('{"schema":"x","schema":"y"}')
            with self.assertRaisesRegex(TemporalHold,"DUPLICATE_JSON_KEY"):
                main(["--record",str(path),"--out",str(Path(p)/"out.json")])

    def test_unexpected_fields_rejected(self):
        r=make();r["superuser"]=True
        self.reject(r,"BAD_RECORD_FIELDS")

if __name__ == "__main__":
    unittest.main()
