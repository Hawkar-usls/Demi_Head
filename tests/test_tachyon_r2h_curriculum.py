"""R2H public curriculum tests; do not use independent lab-clock labels."""
from __future__ import annotations
import inspect
from pathlib import Path
import unittest

from tachyon.science_generator import ScienceHold, HOLDOUT_FAMILIES
from tachyon.r2h_curriculum import (
    LABELS, TRAIN_BETAS, TRAIN_RHOS, training_examples,
    r2d_public_dev_cases, _ngrams, train
)

CARDS="data/tachyon/r2c/science_cards.json"
GENERAL="data/tachyon/r2f/general_source_cards.json"
DEV="data/tachyon/r2d/public_dev_challenge.json"

class R2H(unittest.TestCase):
    def test_approved_source_inventory_only(self):
        examples,csha,gsha=training_examples(CARDS,GENERAL)
        self.assertEqual(len(examples),83)
        self.assertEqual(len(csha),64)
        self.assertEqual(len(gsha),64)
        self.assertEqual({label for _,label in examples},set(LABELS))
        self.assertFalse(any("CLOCK_NIST_CHOU_2010" in q for q,_ in examples))

    def test_source_and_dev_questions_never_overlap(self):
        train_data,_,_=training_examples(CARDS,GENERAL)
        questions,expected=r2d_public_dev_cases(DEV)
        self.assertEqual(len(questions),18)
        self.assertEqual(len(expected),18)
        self.assertFalse({q for q,_ in train_data}&set(questions))
        self.assertEqual(expected[:4],["SR_FORMULA"]*4)
        self.assertEqual(expected[4:8],["BORN_FORMULA"]*4)

    def test_numeric_training_values_exclude_public_r2d_set(self):
        for excluded in ("0.3","0.5","0.8","0.9"):
            self.assertNotIn(excluded,TRAIN_BETAS)
        for excluded in ("0.2","0.4","0.65","0.85"):
            self.assertNotIn(excluded,TRAIN_RHOS)

    def test_train_signature_never_gets_lab_holdout(self):
        parameters=set(inspect.signature(train).parameters)
        for prohibited in ("lab_clock_measurements","holdout","hidden_answers",
                           "private_key","future_outcomes","brave_key"):
            self.assertNotIn(prohibited,parameters)

    def test_hashing_is_stable_and_nonempty(self):
        a=_ngrams("Сатурн: скорость света 2026")
        b=_ngrams("Сатурн: скорость света 2026")
        self.assertEqual(a,b)
        self.assertTrue(a)
        self.assertTrue(all(1<=x<=4096 for x in a))

    def test_new_model_can_build_without_using_external_data(self):
        import torch
        from tachyon.r2h_curriculum import build,vectorize
        net=build()
        out=net(vectorize(["Почему тесто пиццы не поднимается?"]))
        self.assertEqual(list(out.shape),[1,len(LABELS)])

    def test_invalid_training_budget_fails_before_any_gradients(self):
        for seed,epochs in ((12,20),(117,100),(117,0)):
            with self.subTest(seed=seed,epochs=epochs):
                with self.assertRaisesRegex(ScienceHold,"RESOURCE_BUDGET"):
                    train(CARDS,GENERAL,DEV,"/tmp/unreachable",seed=seed,epochs=epochs)

if __name__=="__main__":
    unittest.main()
