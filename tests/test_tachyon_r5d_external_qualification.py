"""R5D: external data qualification and scientific no-blind-gain invariants."""
from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.tachyon_r5d_external_qualification import (
    HOLD, SOURCES, _textual_dataset_stats,
    check_frozen_r5c_rejects_real_text, git_blob_sha, parse_tdt,
    verify_source,
)


class R5DExternalQualificationTests(unittest.TestCase):
    def test_pins_are_complete(self):
        self.assertEqual(set(SOURCES), {"TDT_EXPERT", "TDT_CROWD", "TORQUE_DEV", "TORQUE_TEST"})
        for src in SOURCES.values():
            self.assertEqual(len(src["ref"]), 40)
            self.assertEqual(len(src["blob"]), 40)
            self.assertIn(src["license"], ("BSD-2-Clause", "Apache-2.0"))

    def test_git_blob_known_hash(self):
        self.assertEqual(git_blob_sha(b"hello\n"),
                         hashlib.sha1(b"blob 6\x00hello\n").hexdigest())

    def test_git_blob_not_sha256(self):
        self.assertEqual(len(git_blob_sha(b"R5D")), 40)

    def test_verify_fails_closed_for_unpinned(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"bad.txt"
            path.write_text("not original")
            with self.assertRaises(ValueError):
                verify_source(path, "TDT_EXPERT")

    def test_empty_tdt_has_zero_rows(self):
        s = parse_tdt("",source_name="fixture")
        self.assertEqual(s["rows"],0)

    def test_tdt_tabular_parsing_and_relations(self):
        fixture=(
            "doc1\t1\t3\t3\tOCCURRENCE\t0\t2\t2\tbefore\n"
            "doc1\t2\t1\t1\tREPORTING\t1\t3\t3\tafter\n"
        )
        s=parse_tdt(fixture,source_name="fixture")
        self.assertEqual(s["rows"],2)
        self.assertEqual(s["documents"],1)
        self.assertEqual(s["relation_distribution"],{"after":1,"before":1})

    def test_tdt_rejects_malformed_columns(self):
        with self.assertRaises(ValueError):
            parse_tdt("not\tthe\tfull\trow",source_name="fixture")

    def test_tdt_rejects_invalid_coordinates(self):
        with self.assertRaises(ValueError):
            parse_tdt("doc\tbad\t3\t3\tEVENT\t1\t2\t2\tbefore",source_name="fixture")

    def test_tdt_accepts_root_parent_minus_one(self):
        s=parse_tdt("doc\t0\t1\t1\tTIMEX\t-1\t-1\t-1\tDepend-on",source_name="fixture")
        self.assertEqual(s["rows"],1)

    def test_tdt_duplicate_row_detection(self):
        line="doc\t1\t2\t2\tEVENT\t0\t2\t2\tbefore\n"
        s=parse_tdt(line*2,source_name="fixture")
        self.assertEqual(s["duplicate_row_keys"],1)

    def test_torque_external_corpus_metadata(self):
        rows={
            "doc1":{"passage":"short quoted story","question_answer_pairs":{
                "What happened before?":{"cluster_id":"0","is_default_question":False},
                "What happened after?":{"cluster_id":"0","is_default_question":False}
            }},
        }
        s=_textual_dataset_stats(rows,split="test")
        self.assertEqual(s["passages"],1)
        self.assertEqual(s["questions"],2)
        self.assertEqual(s["answer_field_occurrences"],0)

    def test_torque_test_gold_leak_detected(self):
        rows={"doc1":{"passage":"story","question_answer_pairs":{
            "When?":{"cluster_id":"0","answers":["fake"]},
        }}}
        s=_textual_dataset_stats(rows,split="test")
        self.assertEqual(s["answer_field_occurrences"],1)

    def test_torque_rejects_wrong_schema(self):
        with self.assertRaises(ValueError):
            _textual_dataset_stats([1,2,3],split="test")

    def test_torque_rejects_missing_passage(self):
        with self.assertRaises(ValueError):
            _textual_dataset_stats({"id":{"question_answer_pairs":{}}},split="test")

    def test_r5c_real_world_guard(self):
        self.assertTrue(check_frozen_r5c_rejects_real_text())

    def test_r5c_is_not_human_text_interpreter(self):
        from tools.tachyon_r5c_observation_native_train import extract_observation_features
        with self.assertRaises(ValueError):
            extract_observation_features({
                "schema":"external.torque.reading_comprehension.v1",
                "synthetic_only":False,
                "passage":"event A happened yesterday",
                "question":"what happened before B?",
            })

    def test_no_automatic_relabeling_to_synthetic(self):
        from tools.tachyon_r5c_observation_native_train import extract_observation_features
        with self.assertRaises(ValueError):
            extract_observation_features({
                "synthetic_only":True,
                "passage":"A happened yesterday",
                "target":"ORDER_A_BEFORE_B",
                "reference_time_utc":"2026-11-22T12:00:00+00:00",
                "witnesses":[],
            })

    def test_research_hold_is_explicit(self):
        self.assertIn("HOLD", HOLD)


if __name__ == "__main__":
    unittest.main()
