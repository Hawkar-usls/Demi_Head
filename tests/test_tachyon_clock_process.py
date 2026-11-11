import tempfile
import unittest
from pathlib import Path
from tachyon.clock_process_replay import replay,DATA

class PublishedProcessedClockData(unittest.TestCase):
    def test_exact_zenodo_fig3_replay(self):
        x=replay()
        self.assertEqual(x['source']['md5'],'257eab6f29cf3480c536cac73ed3998a')
        self.assertEqual(x['primary_measurement']['count_individual_runs'],14)
        self.assertAlmostEqual(x['primary_measurement']['weighted_mean_gradient_in_1e19_per_cm'],-12.362409,places=5)
        self.assertAlmostEqual(x['primary_measurement']['uncertainty_stat_in_1e19_per_cm'],0.680959,places=5)
        self.assertTrue(x['physics_comparison']['consistent_with_GR_at_2sigma'])
        self.assertFalse(x['scientific_limits']['tachyon_neural_evaluation'])
    def test_reject_modified_rows(self):
        b=DATA.read_bytes().replace(b'-15.721620183759372',b'-15.821620183759372')
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'tampered.csv';p.write_bytes(b)
            with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
                replay(p)
    def test_raw_status_not_fabricated(self):
        x=replay();s=x['scientific_limits']
        self.assertFalse(s['raw_instrument_data_replicated'])
        self.assertTrue(s['processed_published_data_replayed'])
        self.assertFalse(s['independent_fresh_instrument_experiment'])
        self.assertFalse(s['trained_on_this_dataset'])
if __name__=='__main__':unittest.main()
