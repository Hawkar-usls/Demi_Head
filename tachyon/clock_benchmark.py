"""Compare frozen published clock summaries to Newtonian weak-field GR baseline.

The Tokyo reported aggregate is the only precise numerical measurement present.
This is a *physics reproducibility calculation*, not ML performance or raw-data
replication; the analytical baseline is authoritative and no model is trained.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

C = 299792458.0
SOURCE = Path(__file__).resolve().parents[1]/'data/tachyon/experiments/published_clock_studies_v1.json'

def expected_redshift(height_m: float, gravity_m_s2: float) -> float:
    if not (math.isfinite(height_m) and math.isfinite(gravity_m_s2) and
            0 <= height_m <= 10**6 and 0 < gravity_m_s2 < 50):
        raise ValueError('OUTSIDE_DECLARED_WEAK_FIELD_BENCHMARK_DOMAIN')
    return gravity_m_s2*height_m/(C*C)

def check_studies(path:Path=SOURCE) -> dict:
    source=path.read_bytes()
    obj=json.loads(source)
    if obj.get('schema')!='janus.tachyon.published_clock_studies.v1' or obj.get('training_eligible') is not False:
        raise ValueError('INVALID_BENCHMARK_SOURCE')
    if len(obj.get('studies', []))!=3 or not obj.get('all_records_heldout_from_model_training'):
        raise ValueError('SOURCE_OR_HOLDOUT_MISSING')
    results=[]
    for row in obj['studies']:
        if row.get('raw_time_series_available_in_this_package') is not False:
            raise ValueError('RAW_DATA_FLAG_UNEXPECTED')
        u=row.get('primary_url','')
        if not u.startswith('https://doi.org/'):
            raise ValueError('PRIMARY_SOURCE_INVALID')
        name=row['id']
        if name=='TOKYO_SKYTREE_2020':
            theoretical=expected_redshift(row['height_m'],row['gravity_m_s2'])/1e-18
            observed=row['measured_fractional_shift_in_1e18']
            sigma_observed=row['measured_sigma_in_1e18']
            predicted=row['geodetic_baseline_fractional_shift_in_1e18']
            sigma_predicted=row['geodetic_baseline_sigma_in_1e18']
            z=(observed-predicted)/math.hypot(sigma_observed,sigma_predicted)
            results.append({'id':name,'scored':True,'observed_in_1e18':observed,
              'observed_sigma_in_1e18':sigma_observed,
              'reconstructed_weak_field_prediction_in_1e18':round(theoretical,5),
              'published_geodetic_prediction_in_1e18':predicted,
              'reported_combined_uncertainty_z':round(z,5),
              'consistent_with_baseline_at_2sigma':abs(z)<2,
              'data_class':'PUBLISHED_AGGREGATE_NOT_RAW_TIME_SERIES'})
        else:
            results.append({'id':name,'scored':False,
               'reason':'PUBLISHED_SUMMARY_ONLY_WITHOUT_EXACT_MEASUREMENT_AND_UNCERTAINTY'})
    return {'schema':'janus.demihead.tachyon.clock_benchmark.v1',
      'input_sha256':hashlib.sha256(source).hexdigest(),'source_laboratories':3,
      'scoreable_published_aggregates':1,'raw_independent_reproductions':0,
      'rows':results,'baseline':'GR_GRAVITATIONAL_REDSHIFT_g_delta_h_over_c_squared',
      'tachyon_neural_model_evaluated':False,'tachyon_trained_on_clock_studies':False,
      'future_information_claim':False,'external_effects':False,
      'external_validation_status':'PUBLISHED_AGGREGATE_CHECK_ONLY__RAW_MEASUREMENT_VALIDATION_OPEN',
      'authority_delta':0}

def main()->None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',type=Path,default=SOURCE)
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    result=check_studies(args.input)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'laboratories':result['source_laboratories'],
                       'scored':result['scoreable_published_aggregates'],
                       'z':result['rows'][1]['reported_combined_uncertainty_z']},sort_keys=True))
if __name__=='__main__':
    main()
