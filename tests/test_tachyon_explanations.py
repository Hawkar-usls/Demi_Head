"""Text split and provenance contracts; does not need torch."""
import hashlib
import unittest
from tachyon.explanations import SOURCE, load_data, make_vocab, samples, tokenize, encode

class TachyonExplanationContracts(unittest.TestCase):
    def test_templates_are_disjoint_by_family(self):
        doc=load_data()
        for name in doc['mechanisms']:
            rows=doc['mechanisms'][name]['questions']
            self.assertEqual(len(set(rows[:6])&set(rows[8:])),0)
            self.assertEqual(len(set(rows[6:8])&set(rows[8:])),0)
        self.assertEqual(len(samples(doc,'train')),36)
        self.assertEqual(len(samples(doc,'tune')),12)
        self.assertEqual(len(samples(doc,'holdout')),12)
    def test_vocab_sees_training_only(self):
        doc=load_data(); vocab=make_vocab(doc)
        self.assertIn('<unk>',vocab)
        self.assertEqual(len(encode('unknown fictional gravityword',vocab)),26)
    def test_every_class_has_falsifier(self):
        doc=load_data()
        self.assertTrue(all(v['counterexample'] for v in doc['mechanisms'].values()))
        self.assertEqual(hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
          'e466ec34a4dbcc99291de0c04335f8b9b473ee13ae7a93eeefedb207e52ba97c')

if __name__=='__main__':unittest.main()
