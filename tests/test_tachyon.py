"""Tachyon source and leakage boundaries; no extra action permission."""
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from tachyon.train import (EXPECTED_SHA256, build_vocab, chronology_split, encode,
                           load_segments, make_examples, run)

class TachyonTests(unittest.TestCase):
    def test_sha_pinned_and_provenance(self):
        segments,digest=load_segments()
        self.assertEqual(digest,EXPECTED_SHA256)
        self.assertEqual(len(segments),34) # 37 total, 3 ads

    def test_disjoint_future_holdout(self):
        tr,te=chronology_split(load_segments()[0]);self.assertLess(tr[-1]["time_sec"],te[0]["time_sec"])
        self.assertFalse({r["time_sec"] for r in tr}&{r["time_sec"] for r in te})
        self.assertEqual(len(make_examples(tr)),len(tr)*(len(tr)-1))

    def test_no_timestamp_as_features(self):
        tr,_=chronology_split(load_segments()[0]);v=build_vocab(tr)
        left,right=tr[0]["summary"],tr[1]["summary"]
        e1=encode(left,right,v);e2=encode(left,right,v)
        self.assertEqual(e1,e2)
        self.assertEqual(e1[0][0],v["<cls>"])

    def test_wrong_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,"source_sha256_mismatch"):
            load_segments(expected_sha="0"*64)

    def test_training_bounded_and_no_physical_claim(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=run(outdir=Path(tmp),epochs=1)
            self.assertTrue((Path(tmp)/"candidate.pt").is_file())
            self.assertEqual(result["authority_delta"],0)
            self.assertFalse(result["scientific_claims"]["retrocausality_demonstrated"])
            self.assertEqual(result["dataset"]["timestamps_as_input"],False)

if __name__=="__main__":unittest.main()
