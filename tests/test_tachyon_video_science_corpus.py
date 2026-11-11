"""Tachyon R2A integrity, copyright, source-independence, and holdout guards."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from tachyon.video_science_corpus import (
    CAPTION_TRACK_SHA, CLAIM_IDS, INDEX_PATH, INDEX_SCHEMA, LAB_SHA,
    SCIENCE_SCHEMA, SCIENCE_PATH, CorpusHold, REGISTRY_COMMIT,
    SCHEMA, build, canonical, main, protect_lab_holdout, sha,
)

def input_pair():
    index = {
        "schema": INDEX_SCHEMA,
        "video": {"id": "PwOk0GKDv9c", "reported_duration_s": 4252},
        "caption_source": {
            "requested_language": "default", "returned_language": "ru",
            "original_caption_cue_count": 254,
            "original_full_timestamped_caption_track_sha256_utf8": CAPTION_TRACK_SHA,
            "discrepancy_last_start_minus_video_duration_s": 180,
            "caption_and_video_timing_alignment_verified": False,
        },
        "no_full_subtitle_text_redistributed": True,
        "caption_cues_provenance_only": [
            {"index": i + 1,
             "raw_start_second": 4432 if i == 253 else i * 17,
             "original_text_sha256_utf8": "f"*64}
            for i in range(254)
        ],
    }
    science = {
        "schema": SCIENCE_SCHEMA,
        "record_id": "JANUS-VIDEO-PWOK0GKDv9c-SCIENCE-CHAPTERS-CLAIMS-2026-11-11",
        "video_metadata": {"id": "PwOk0GKDv9c", "language": "ru"},
        "original_caption_provenance": {
            "total_original_cues": 254,
            "original_entire_timestamped_transcript_sha256_utf8": CAPTION_TRACK_SHA,
            "raw_cue_start_exceeds_metadata_duration_s": 180,
            "subtitle_to_video_alignment_status": "UNVERIFIED_SOURCE_DISCREPANCY",
            "raw_caption_index_path": INDEX_PATH,
            "raw_detailed_caption_verbatim_reproduced": False,
        },
        "author_description_chapters": [{} for _ in range(25)],
        "audited_science_claims": [{
            "id": claim_id,
            "paraphrase_ru": "Описание физического положения " + claim_id,
            "required_qualification_ru": "Математическое описание не доказывает сигнал из будущего.",
            "scientific_assessment": "CAREFULLY_QUALIFIED",
            "independent_primary_doi": None,
        } for claim_id in sorted(CLAIM_IDS)],
        "on_screen_titles_visual_scene_index_UNVERIFIED": [
            {"actual_frame_verified": False} for _ in range(5)],
        "science_gates": {
            "video_does_not_observe_or_construct_an_actual_time_machine": True,
            "video_not_a_peer_reviewed_lab_experiment": True,
            "physical_retrocausality_observed_in_video": False,
            "full_closed_timelike_curve_physically_realized": False,
        },
    }
    return science, index

def result(s=None, i=None, lab=None):
    science, index = input_pair()
    science = science if s is None else s
    index = index if i is None else i
    return build(science, sha(canonical(science)), index, sha(canonical(index)),
                 lab_holdout_file=lab)

class ScienceCorpusTests(unittest.TestCase):
    def test_builds_twelve_training_ready_not_trained_pairs(self):
        r = result()
        self.assertEqual(r["schema"], SCHEMA)
        self.assertEqual(r["count"], 12)
        self.assertEqual(len(r["examples"]), 12)
        self.assertTrue(all(x["split"] == "TRAIN" for x in r["examples"]))
        self.assertTrue(all("target_ru" in x and "input_ru" in x for x in r["examples"]))
        self.assertEqual(r["status"], "INSTRUCTION_EXAMPLES_PREPARED_NOT_NEURAL_TRAINING")

    def test_no_independent_measurements_enter_training(self):
        r = result()
        self.assertTrue(all(not x["is_independent_lab_measurement"] for x in r["examples"]))
        self.assertFalse(r["lab_holdout"]["lab_data_in_training_examples"])
        self.assertFalse(r["rights"]["may_train_on_independent_lab_measurements"])
        self.assertIsNone(r["benchmark"]["new_independent_lab_accuracy"])

    def test_one_media_source_is_not_independent_holdout(self):
        r = result()
        self.assertEqual({x["source_family_id"] for x in r["examples"]},
                         {"HOMO-DEUS-PWOK0GKDv9c"})
        self.assertEqual(r["split_policy"]["media_source_families"], 1)
        self.assertFalse(r["split_policy"]["out_of_domain_generalization_measured"])

    def test_old_six_class_model_not_silently_retrained(self):
        r = result()
        self.assertFalse(r["rights"]["may_train_existing_six_class_classifier_without_relabeling"])
        self.assertFalse(r["rights"]["may_modify_existing_model_weights"])

    def test_caption_time_misalignment_not_hidden(self):
        r = result()
        self.assertFalse(r["source"]["caption_video_timeline_aligned"])

    def test_caption_track_hash_tamper_rejected(self):
        s, i = input_pair()
        i["caption_source"]["original_full_timestamped_caption_track_sha256_utf8"] = "1"*64
        with self.assertRaisesRegex(CorpusHold, "CAPTION_TRACK_HASH"):
            result(s, i)

    def test_caption_timing_fabricated_alignment_rejected(self):
        s, i = input_pair()
        i["caption_source"]["caption_and_video_timing_alignment_verified"] = True
        with self.assertRaisesRegex(CorpusHold, "SUBTITLE_VIDEO_TIMELINE"):
            result(s, i)

    def test_caption_cue_count_rejected(self):
        s, i = input_pair()
        i["caption_cues_provenance_only"].pop()
        with self.assertRaisesRegex(CorpusHold, "CAPTION_INDEX_COMPLETENESS"):
            result(s, i)

    def test_raw_subtitle_text_unexpected_rejected(self):
        s, i = input_pair()
        i["caption_cues_provenance_only"][0]["original_text"] = "not allowed"
        with self.assertRaisesRegex(CorpusHold, "INVALID_CAPTION_CUE"):
            result(s, i)

    def test_missing_physics_caveat_rejected(self):
        s, i = input_pair()
        s["audited_science_claims"][0]["required_qualification_ru"] = ""
        with self.assertRaisesRegex(CorpusHold, "SCIENCE_CLAIM_TEXT"):
            result(s, i)

    def test_missing_science_gate_rejected(self):
        s, i = input_pair()
        s["science_gates"]["physical_retrocausality_observed_in_video"] = True
        with self.assertRaisesRegex(CorpusHold, "SCIENTIFIC_CLAIM_FIREWALL"):
            result(s, i)

    def test_claim_replacement_rejected(self):
        s, i = input_pair()
        s["audited_science_claims"][0]["id"] = "claim_invented"
        with self.assertRaisesRegex(CorpusHold, "SCIENCE_CLAIM_INVENTORY"):
            result(s, i)

    def test_unverified_frame_assessed_as_verified_rejected(self):
        s, i = input_pair()
        s["on_screen_titles_visual_scene_index_UNVERIFIED"][0]["actual_frame_verified"] = True
        with self.assertRaisesRegex(CorpusHold, "VISUAL_CLAIMS"):
            result(s, i)

    def test_wrong_git_commit_rejected(self):
        s, i = input_pair()
        with self.assertRaisesRegex(CorpusHold, "UNPINNED_REGISTRY"):
            build(s, sha(canonical(s)), i, sha(canonical(i)), registry_commit="a"*40)

    def test_deterministic_report_sha(self):
        a = result()
        b = result()
        self.assertEqual(a["receipt_sha256"], b["receipt_sha256"])
        self.assertEqual(sha(canonical({k:v for k,v in a.items() if k != "receipt_sha256"})),
                         a["receipt_sha256"])

    def test_lab_sha_guard_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t)/"lab.csv"
            path.write_bytes(b"altered laboratory numbers\n")
            with self.assertRaisesRegex(CorpusHold, "INDEPENDENT_LAB_HOLDOUT_SHA_CHANGED"):
                protect_lab_holdout(path)

    def test_different_caption_video_rejected(self):
        s, i = input_pair()
        i["video"]["id"] = "UNRELATED"
        with self.assertRaisesRegex(CorpusHold, "CAPTION_VIDEO_ID_MISMATCH"):
            result(s, i)

    def test_primary_doi_as_plain_metadata_only(self):
        s, i = input_pair()
        s["audited_science_claims"][0]["independent_primary_doi"] = "10.1234/xyz"
        r=result(s,i)
        self.assertEqual(r["examples"][0]["record_provenance"],
                         "AUDITED_MEDIA_PARAPHRASE_NOT_VERBATIM_CAPTIONS")

if __name__ == "__main__":
    unittest.main()
