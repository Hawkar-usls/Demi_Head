"""Offline negative tests for Tachyon IO/AIFC eligibility gate."""
from __future__ import annotations
import copy
import json
from pathlib import Path
import unittest
from tachyon.observation_aifc_gate import assess

WITNESS = Path("data/tachyon/ocean/real_009b_early_witness_20261112.json")
IO = {
    "schema": "JANUS/proof-of-observation-origin-record/v1",
    "repository": "Hawkar-usls/janus-io-public",
    "claim_level": "telemetry_and_methodology_only",
    "required_layers": [
        "facts","derived_metrics","claims","source_provenance",
        "deterministic_integrity","uncertainty","comparability",
        "independent_repetition","holdout_discipline","fail_closed_claims"],
    "canonical_principles": ["Unknown is not zero."]
}
GRADES = ("NOT_ADMITTED STRUCTURAL_MATCH_ONLY FORWARD_NULL_COMPATIBLE "
          "FORWARD_NULL_INCOMPATIBILITY_CANDIDATE")

class Tests(unittest.TestCase):
    def setUp(self):
        self.w = json.loads(WITNESS.read_text(encoding="utf8"))

    def check(self, w=None, io=None, grades=GRADES, run=None, artifacts=None):
        io = IO if io is None else io
        return assess(w if w is not None else self.w, io,
                      json.dumps(io).encode(), grades, grades.encode(),
                      run, artifacts)

    def test_real_witness_is_observation_only_and_not_admitted(self):
        a=self.check()
        self.assertEqual(a["proof_of_observation"]["status"],"OBSERVATION_ONLY_PARTIAL_CHAIN")
        self.assertEqual(a["aifc"]["grade"],"NOT_ADMITTED")
        self.assertFalse(a["topa"]["promoted"])
        self.assertFalse(a["eligible_as_gradient_label"])
        self.assertFalse(a["proof_of_observation"]["live_github_artifact_binding_pass"])

    def test_tampered_review_fails_closed(self):
        w=copy.deepcopy(self.w)
        w["tachyon_shadow_review"]["early"]["precommit_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"REVIEW_HASH_INVALID"):
            self.check(w=w)

    def test_changed_artifact_id_fails_closed(self):
        w=copy.deepcopy(self.w)
        w["github_artifact_id"]=5
        with self.assertRaisesRegex(ValueError,"IDENTITY_CHANGED"):
            self.check(w=w)

    def test_outcome_leak_and_model_claim_fail_closed(self):
        w=copy.deepcopy(self.w)
        w["limits"]["future_target_outcomes_known"]=True
        with self.assertRaisesRegex(ValueError,"UNFROZEN"):
            self.check(w=w)

    def test_io_policy_missing_holdout_refused(self):
        io=copy.deepcopy(IO)
        io["required_layers"].remove("holdout_discipline")
        with self.assertRaisesRegex(ValueError,"IO_REQUIRED_LAYERS_MISSING"):
            self.check(io=io)

    def test_missing_aifc_grade_refused(self):
        with self.assertRaisesRegex(ValueError,"AIFC_GRADES_CHANGED"):
            self.check(grades="NOT_ADMITTED")

    def test_fake_live_rebinding_refused(self):
        with self.assertRaisesRegex(ValueError,"LIVE_RUN_SOURCE_MISMATCH"):
            self.check(run={"id":-1},artifacts={"artifacts":[]})

    def test_realistic_live_rebinding_does_not_grant_admission(self):
        w=self.w
        run={"id":42878578752,
             "name":"JANUS Ocean / 009B Future drand 128bit Early",
             "conclusion":"success",
             "path":".github/workflows/janus-ocean-open-future-009b-precommit.yml",
             "head_sha":w["original_source_commit"]}
        art={"id":13793425503,
             "name":"janus-open-future-009b-2026-11-12",
             "expired":False,
             "created_at":w["github_artifact_created_at_utc"],
             "digest":"sha256:"+w["github_artifact_zip_sha256"],
             "workflow_run":{"id":42878578752}}
        a=self.check(run=run,artifacts={"artifacts":[art]})
        self.assertTrue(a["proof_of_observation"]["live_github_artifact_binding_pass"])
        self.assertEqual(a["aifc"]["grade"],"NOT_ADMITTED")

if __name__=="__main__":
    unittest.main()
