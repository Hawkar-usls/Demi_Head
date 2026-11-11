"""R2B fail-closed source/holdout controls. No freeform model correctness claims."""
import copy
import json
import os
from pathlib import Path
import unittest

from tachyon.science_generator import (
    ScienceHold, load_json, training_rows, canonical, sha,
    make_vocab, f1, HOLDOUT_DOIS, HOLDOUT_FAMILIES,
)

VIDEO=Path(os.environ.get("TACHYON_R2B_VIDEO_CORPUS","artifacts/tachyon-r2b/video-corpus.json"))
PAPERS=Path("data/tachyon/r2b/primary_papers_train.json")
HOLDOUT=Path("data/tachyon/r2b/clock_explanation_holdout.json")

class R2B(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not VIDEO.is_file():
            raise unittest.SkipTest("R2B source-built corpus is available only in its dedicated workflow")
        cls.video,_=load_json(VIDEO)
        cls.papers,_=load_json(PAPERS)
        cls.held,_=load_json(HOLDOUT)
    def resign(self,video):
        video["receipt_sha256"]=sha(canonical(
            {k:v for k,v in video.items() if k!="receipt_sha256"}))
        return video
    def test_train_24_pairs_seven_families(self):
        rows=training_rows(self.video,self.papers)
        self.assertEqual(len(rows),24)
        self.assertEqual(len({x["family"] for x in rows}),7)
    def test_lab_holdout_not_in_training(self):
        rows=training_rows(self.video,self.papers)
        self.assertFalse({x["family"] for x in rows}&HOLDOUT_FAMILIES)
        self.assertTrue(set(x["doi"] for x in self.papers["sources"]).isdisjoint(HOLDOUT_DOIS))
    def test_holdout_three_external_papers(self):
        self.assertEqual(len(self.held["source_groups"]),3)
        self.assertEqual({x["family"] for x in self.held["source_groups"]},HOLDOUT_FAMILIES)
        self.assertFalse(self.held["lab_measurement_results_training_allowed"])
    def test_video_corruption_rejected(self):
        v=copy.deepcopy(self.video)
        v["examples"][0]["target_ru"]="untrusted"
        with self.assertRaisesRegex(ScienceHold,"VIDEO_RECEIPT_SHA_MISMATCH"):
            training_rows(v,self.papers)
    def test_resigned_fake_lab_authority_rejected(self):
        v=copy.deepcopy(self.video)
        v["lab_holdout"]["lab_data_in_training_examples"]=True
        self.resign(v)
        with self.assertRaisesRegex(ScienceHold,"LAB_TRAINING_LEAK"):
            training_rows(v,self.papers)
    def test_resigned_fake_early_physical_proof_rejected(self):
        v=copy.deepcopy(self.video)
        v["examples"][0]["scientific_retrocausality_proven"]=True
        self.resign(v)
        with self.assertRaisesRegex(ScienceHold,"MEDIA_SOURCE_AUTHORITY_ESCALATION"):
            training_rows(v,self.papers)
    def test_resigned_video_source_change_rejected(self):
        v=copy.deepcopy(self.video)
        v["source"]["commit_sha"]="f"*40
        self.resign(v)
        with self.assertRaisesRegex(ScienceHold,"VIDEO_SOURCE_NOT_PINNED"):
            training_rows(v,self.papers)
    def test_published_clock_doi_as_train_rejected(self):
        p=copy.deepcopy(self.papers)
        p["sources"][0]["doi"]="10.1126/science.1192720"
        p["sources"][0]["url"]="https://doi.org/10.1126/science.1192720"
        with self.assertRaisesRegex(ScienceHold,"LAB_SOURCE_OR_THEORY_PROVENANCE_CHANGED"):
            training_rows(self.video,p)
    def test_vocabulary_has_no_holdout_dependency(self):
        rows=training_rows(self.video,self.papers)
        v1=make_vocab(rows)
        h=copy.deepcopy(self.held)
        h["source_groups"][0]["reference_answer"]="changed on purpose"
        v2=make_vocab(training_rows(self.video,self.papers))
        self.assertEqual(v1,v2)
    def test_similarity_is_not_scientific_judgement(self):
        self.assertEqual(f1("кривизна время","другие слова"),0)
        self.assertEqual(f1("время пространство","пространство время"),1)
    def test_training_function_has_no_holdout_argument(self):
        from inspect import signature
        from tachyon.science_generator import train
        self.assertNotIn("holdout",signature(train).parameters)
    def test_torch_small_model_is_generative(self):
        import torch
        from tachyon.science_generator import build_model
        torch.set_num_threads(2)
        net=build_model(20)
        source=torch.tensor([[1,4,2]+[0]*55])
        target=torch.tensor([[1,5,2]])
        self.assertEqual(tuple(net(source,target).shape),(1,3,20))

if __name__=="__main__":unittest.main()
