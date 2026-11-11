"""Offline fixture tests for frozen Ocean 009B => Tachyon => TOPA shadow audit."""
from __future__ import annotations
import copy
from datetime import datetime, timezone
import hashlib
import unittest
from tachyon import ocean_link as m

OCEAN_COMMIT='2eb40f516ca53d56141b5408f2e5c241f75fd936'
DATE='2026-11-12'
EARLY_GITHUB='2026-11-11T09:00:00Z'

def sample_early():
    from datetime import date
    rounds=m.fixed_rounds(date.fromisoformat(DATE))
    p={
      'schema':m.SCHEMA,'lane':'OPEN-FUTURE-009B','phase':'EARLY_PRECOMMIT',
      'timestamp_self_reported':'2026-11-11T08:58:00+00:00',
      'target_date':DATE,'n_distinct_rounds':m.N,
      'quicknet_hash':m.CHAIN,'quicknet_genesis_unix':m.GENESIS,
      'quicknet_period_seconds':m.PERIOD,'target_rounds':rounds,
      'first_release_unix':m.release(rounds[0]),'last_release_unix':m.release(rounds[-1]),
      'latest_bls_verified_round_at_preparation':rounds[0]-30,
      'forecast_model':'HISTORIC_FROZEN_JANUS_TINY_TRANSFORMER_004_BORN_TRAINED_NOT_DRAND_TRAINED',
      'frozen_checkpoint_sha256':'a'*64,'frozen_training_report_sha256':'b'*64,
      'forecast_encoding':'MODEL_PUBLIC_ROUND_AND_POSITION_ONLY',
      'probability_1':[0.3,0.7]*64,'bits':['0','1']*64,
      'future_results_seen':False,'postselection_allowed':False,
      'training_after_precommit':False,'no_physical_receiver':True,
      'retrocausality_proven':False}
    return {'payload':p,'sha256':m.digest(p)}

class ShadowBridgeTests(unittest.TestCase):
    def test_early_frozen_valid(self):
        r=m.validate_early(sample_early(),EARLY_GITHUB)
        self.assertEqual(len(r['bits']),128)
        self.assertTrue(r['witness_timestamp_supplied'])
    def test_early_without_external_witness_pending(self):
        r=m.bridge(sample_early(),ocean_commit=OCEAN_COMMIT)
        self.assertEqual(r['late']['status'],'PENDING_FUTURE_OUTCOMES')
        self.assertFalse(r['independent_external_timestamp_verified_by_this_program'])
        self.assertFalse(r['tachyon']['learned_training_signal'])
        self.assertFalse(r['feedback']['eligible_as_gradient_label'])
    def test_early_tamper_refused(self):
        p=sample_early();p['payload']['probability_1'][0]=0.99
        with self.assertRaisesRegex(ValueError,'SHA_MISMATCH'):
            m.validate_early(p)
    def test_future_round_mismatch_refused(self):
        p=sample_early();p['payload']['target_rounds'][0]+=1;p['sha256']=m.digest(p['payload'])
        with self.assertRaisesRegex(ValueError,'ROUNDS_OR_CHAIN_CHANGED'):
            m.validate_early(p)
    def test_late_witness_refused(self):
        with self.assertRaisesRegex(ValueError,'WITNESS_TOO_LATE'):
            m.validate_early(sample_early(),'2026-11-12T08:00:00Z')
    def test_no_retro_relabel(self):
        p=sample_early();p['payload']['retrocausality_proven']=True;p['sha256']=m.digest(p['payload'])
        with self.assertRaisesRegex(ValueError,'EARLY_FUTURE_LEAKAGE'):
            m.validate_early(p)
    def test_no_postselection(self):
        p=sample_early();p['payload']['postselection_allowed']=True;p['sha256']=m.digest(p['payload'])
        with self.assertRaisesRegex(ValueError,'EARLY_FUTURE_LEAKAGE'):
            m.validate_early(p)
    def test_late_scored_report_only(self):
        r=m.validate_early(sample_early(),EARLY_GITHUB)
        a={'schema':m.SCHEMA,'lane':'OPEN-FUTURE-009B',
           'status':'ALL_SIGNED_INDEPENDENT_DRAND_ROUNDS_SCORED',
           'precommitted_sha256':r['precommit_sha256'],'target_date':DATE,
           'n_distinct_rounds':128,'time_separation_externally_timestamped':True,
           'randomness_bls_verified':True,'no_late_outcomes_filtered':True,
           'real_physical_early_receiver':False,'retrocausality_proven':False,
           'github_server_artifact_timestamp':EARLY_GITHUB,
           'matches':64,'accuracy':0.5,'brier':0.29,'fair_baseline_brier':0.25,
           'better_brier_than_fair':False,'exact_two_sided_binomial_p':1.0}
        res=m.bridge(sample_early(),ocean_commit=OCEAN_COMMIT,
                     github_created_at=EARLY_GITHUB,late_assessment=a)
        self.assertEqual(res['late']['status'],'UPSTREAM_REPORT_ONLY_NO_INDEPENDENT_RECALC')
        self.assertFalse(res['late']['labels_recomputed'])
        self.assertTrue(res['topa']['envelope']['status']=='HYPOTHESIS_ONLY')
    def test_reject_late_without_witness(self):
        r=m.validate_early(sample_early())
        a={'schema':m.SCHEMA,'lane':'OPEN-FUTURE-009B',
           'status':'ALL_SIGNED_INDEPENDENT_DRAND_ROUNDS_SCORED',
           'precommitted_sha256':r['precommit_sha256'],'target_date':DATE,
           'n_distinct_rounds':128,'time_separation_externally_timestamped':True,
           'randomness_bls_verified':True,'no_late_outcomes_filtered':True,
           'real_physical_early_receiver':False,'retrocausality_proven':False,
           'github_server_artifact_timestamp':None,'matches':64,'accuracy':0.5,
           'brier':0.25,'fair_baseline_brier':0.25,'better_brier_than_fair':False}
        with self.assertRaisesRegex(ValueError,'NEEDS_EXTERNAL_PRECOMMIT_WITNESS'):
            m.independently_recompute_late(r,a)
    def test_bad_ocean_commit(self):
        with self.assertRaisesRegex(ValueError,'PINNED_OCEAN_COMMIT'):
            m.bridge(sample_early(),ocean_commit='main')
    def test_unknown_future_date_refused(self):
        from datetime import date
        with self.assertRaisesRegex(ValueError,'OUTSIDE_PREREGISTERED'):
            m.fixed_rounds(date(2026,11,20))

if __name__=='__main__': unittest.main()
