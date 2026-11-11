"""No torch needed: fail-closed Beetle context and published-clock checks."""
import json
import math
import tempfile
import unittest
from pathlib import Path

from tachyon.research_bridge import (BEETLE_CAPABILITIES, BEETLE_OWNER,
    BEETLE_SCHEMA, BEETLE_STATUS, canonical, sha, validate_beetle_context,
    make_topa_claim, canonical_topa_assessment)
from tachyon.clock_benchmark import check_studies, expected_redshift


def sample_context():
    obj={'schema':BEETLE_SCHEMA,'status':BEETLE_STATUS,
        'target_repository':BEETLE_OWNER,'last_processed_sequence':2,
        'research_routes':[{'candidate_id':'cand-1','context_id':'ctx-1',
         'direction_id':'clock-testing','title':'Independent optical clock test',
         'source_url':'https://example.org/paper','batch_id':'a'*20,'input_sha256':'b'*64}],
        'hypothesis_routes':['Independent optical clock test'],
        'capabilities':dict(BEETLE_CAPABILITIES)}
    obj['context_sha256']=sha(canonical(obj))
    return obj

class BeetleTOPAContracts(unittest.TestCase):
    def test_beetle_checked_projection_only(self):
        obj=sample_context()
        result=validate_beetle_context(canonical(obj))
        self.assertEqual(result['context_sha256'],obj['context_sha256'])
        self.assertFalse(result['training_eligible'])
        self.assertEqual(result['authority_delta'],0)
        self.assertTrue(result['unverified'])

    def test_tampered_projection_is_rejected(self):
        obj=sample_context();obj['research_routes'][0]['title']='Altered'
        with self.assertRaisesRegex(ValueError,'HASH_MISMATCH'):
            validate_beetle_context(canonical(obj))

    def test_cross_target_routing_rejected(self):
        obj=sample_context();obj['target_repository']='Hawkar-usls/Demi_Head'
        obj.pop('context_sha256');obj['context_sha256']=sha(canonical(obj))
        with self.assertRaisesRegex(ValueError,'CONTRACT_REJECTED'):
            validate_beetle_context(canonical(obj))

    def test_beetle_permission_escalation_rejected(self):
        obj=sample_context();obj['capabilities']['is_direct_gradient_signal']=True
        obj.pop('context_sha256');obj['context_sha256']=sha(canonical(obj))
        with self.assertRaisesRegex(ValueError,'CONTRACT_REJECTED'):
            validate_beetle_context(canonical(obj))

    def test_topa_hypotheses_not_mistaken_for_facts(self):
        x=make_topa_claim(claim_id='TEST-0001',statement='Maybe unexplained clock offset',
                          source_urls=['https://example.org/clock'])
        self.assertEqual(x['evidence_class'],'HYPOTHESIS_ONLY')
        self.assertEqual(x['status'],'HYPOTHESIS_ONLY')
        self.assertEqual(x['provenance_channel'],'MODEL_INFERENCE')
        self.assertTrue(x['falsification_tests'])
        self.assertFalse(x['independent_replication'])

    def test_topa_measured_source_needs_primary_source(self):
        with self.assertRaisesRegex(ValueError,'PRIMARY_SOURCE'):
            make_topa_claim(claim_id='TEST-0002',statement='Experiment',source_urls=[],category='SOURCE_FACT')

    def test_topa_fails_closed_without_provider(self):
        with self.assertRaisesRegex(ValueError,'TOPA_PROVIDER_UNAVAILABLE'):
            canonical_topa_assessment(make_topa_claim(claim_id='TEST-0003',
                statement='A hypothesis',source_urls=[]),Path('/nonexistent/topa_epistemic_router.py'))

class PublishedClocks(unittest.TestCase):
    def test_weak_field_expected_magnitude(self):
        self.assertAlmostEqual(expected_redshift(0.33,9.80665),3.600751991825412e-17,places=26)

    def test_tokyo_published_aggregate_consistency(self):
        r=check_studies()
        self.assertEqual(r['scoreable_published_aggregates'],1)
        self.assertEqual(r['raw_independent_reproductions'],0)
        self.assertFalse(r['tachyon_neural_model_evaluated'])
        row=next(x for x in r['rows'] if x['id']=='TOKYO_SKYTREE_2020')
        self.assertTrue(row['consistent_with_baseline_at_2sigma'])
        self.assertAlmostEqual(row['reported_combined_uncertainty_z'],0.15479,places=4)

    def test_missing_measurements_remain_unscored(self):
        r=check_studies()
        self.assertEqual(sum(bool(x['scored']) for x in r['rows']),1)
        self.assertFalse(r['tachyon_trained_on_clock_studies'])

if __name__=='__main__': unittest.main()
