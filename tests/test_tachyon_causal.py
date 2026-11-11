"""Tachyon v0.2 independent numeric causal-classification safeguards."""
from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import torch

from tachyon.causal import (
    TachyonCausalTransformer, analytic, dataset, evaluate,
    validate_source, SOURCE, EXPECTED_SHA256
)


class TachyonCausalTests(unittest.TestCase):
    def test_video_source_sha_pinned(self):
        self.assertEqual(validate_source(), EXPECTED_SHA256)

    def test_spacelike_is_necessary_for_coordinate_reversal(self):
        for q in (0.02,0.2,0.5,0.95,1.0,1.25,1.8):
            for beta in (0.,0.1,0.4,0.8,0.98):
                reversed_order, spacelike = analytic(q,beta)
                self.assertLessEqual(reversed_order,spacelike)

    def test_exact_lorentz_source_cases(self):
        r=json.loads(SOURCE.read_text(encoding='utf-8'))
        reference=r['reproducible_calculations']['ftl_event_order_sweep']
        dt=reference['delta_t_seconds']; dx=reference['delta_x_lightseconds']
        for row in reference['cases']:
            beta=row['relative_speed_over_c']
            actual=(dt-beta*dx)/math.sqrt(1.-beta**2)
            self.assertAlmostEqual(actual,row['delta_t_prime_seconds'],places=7)
            self.assertEqual(analytic(dt/dx,beta)[0],int(actual<0))

    def test_separate_holdout_beta_band(self):
        tr=dataset(17,300,'train').tensors[0]
        out=dataset(18,300,'new_beta_band').tensors[0]
        self.assertTrue(torch.all(tr[:,1]<=0.85))
        self.assertTrue(torch.all(out[:,1]>=0.85))

    def test_examples_are_seed_deterministic_but_disjoint(self):
        train=dataset(17,200,'train'); again=dataset(17,200,'train')
        test=dataset(101,200,'iid')
        self.assertTrue(torch.equal(train.tensors[0],again.tensors[0]))
        self.assertFalse(torch.equal(train.tensors[0],test.tensors[0]))
        trvals=set(map(tuple,train.tensors[0].tolist()))
        tevals=set(map(tuple,test.tensors[0].tolist()))
        self.assertEqual(len(trvals & tevals),0)

    def test_untrained_model_matches_shape_and_no_leakage(self):
        model=TachyonCausalTransformer()
        x=dataset(42,8,'iid').tensors[0]
        logits=model(x)
        self.assertEqual(tuple(logits.shape),(8,2))
        self.assertTrue(torch.all(torch.isfinite(logits)))
        self.assertEqual(model.classifier.out_features,2)

    def test_small_cpu_training_smoke(self):
        from tachyon.causal import run
        with tempfile.TemporaryDirectory() as td:
            result=run(outdir=Path(td),train_n=120,epochs=1,seed=101)
            self.assertEqual(result['source']['sha256'],EXPECTED_SHA256)
            self.assertTrue(Path(td,'candidate.pt').exists())
            self.assertFalse(result['authority_delta']) if isinstance(result['authority_delta'],bool) else self.assertEqual(result['authority_delta'],0)
            self.assertFalse(result['external_effects'])
            self.assertFalse(result['gate']['training_admission'])


if __name__=='__main__':
    unittest.main()
