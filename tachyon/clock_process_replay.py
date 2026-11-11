"""Read-only replay of exact published *processed* Fig3.csv from Zheng et al 2023.

This checks arithmetic reproduction of authors' 14 reported run estimates; the
original instrument time-series, covariance model and analysis code are not in
this file, so it is not an independent raw-data replication or ML evaluation.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

DATA=Path(__file__).resolve().parents[1]/'data/tachyon/experiments/WISCONSIN_ZHENG_2023_Fig3.csv'
EXPECTED_MD5='257eab6f29cf3480c536cac73ed3998a'
EXPECTED_SHA256='a4384040d5678893b4df15ea0be2980661023305f5009de876179fab1dea632f'
C=299792458.0

def replay(path=DATA)->dict:
    raw=Path(path).read_bytes()
    if hashlib.md5(raw).hexdigest()!=EXPECTED_MD5 or hashlib.sha256(raw).hexdigest()!=EXPECTED_SHA256:
        raise ValueError('ZENODO_FILE_HASH_MISMATCH')
    rows=list(csv.reader(raw.decode('utf-8').splitlines()))
    if len(rows)!=16 or len(rows[0])!=6:
        raise ValueError('FIG3_SHAPE_MISMATCH')
    runs=[];height=[]
    for row in rows[2:]:
        if row[3]:
            runs.append((int(row[3]),float(row[4]),float(row[5])))
        if row[0]:
            height.append((float(row[0]),float(row[1]),float(row[2])))
    if len(runs)!=14 or sorted(i for i,_,_ in runs)!=list(range(1,15)) or len(height)!=4:
        raise ValueError('RUN_IDENTITIES_OR_HEIGHTS_INVALID')
    if any(s<=0 or not math.isfinite(y) or not math.isfinite(s) for _,y,s in runs):
        raise ValueError('MEASUREMENT_NONFINITE_OR_NONPOSITIVE_UNCERTAINTY')
    sumweights=sum(1/(s*s) for _,_,s in runs)
    weighted=sum(y/(s*s) for _,y,s in runs)/sumweights
    sem=1/math.sqrt(sumweights)
    # A second summary of four height-dependent points, NOT an independent data source.
    denom=sum(h*h/(s*s) for h,y,s in height)
    through_origin=sum(h*y/(s*s) for h,y,s in height)/denom
    through_origin_error=1/math.sqrt(denom)
    expected=-9.80665*.01/(C*C)/1e-19
    systematic=2.5
    z=(weighted-expected)/math.hypot(sem,systematic)
    if abs(weighted-(-12.4))>0.1 or abs(sem-0.7)>0.1:
        raise ValueError('PUBLISHED_GRADIENT_REPLAY_DISAGREES_WITH_PAPER')
    return {
      'schema':'janus.tachyon.clock_process_replay.v1',
      'source':{'zenodo_doi':'10.5281/zenodo.8184043',
                'paper_doi':'10.1038/s41467-023-40629-8',
                'file':'Fig3.csv','file_size_bytes':len(raw),
                'md5':EXPECTED_MD5,'sha256':EXPECTED_SHA256,
                'data_kind':'AUTHORS_PUBLISHED_PROCESSED_FIGURE_DATA_NOT_INSTRUMENT_RAW'},
      'primary_measurement':{'count_individual_runs':14,
           'weighted_mean_gradient_in_1e19_per_cm':round(weighted,6),
           'uncertainty_stat_in_1e19_per_cm':round(sem,6),
           'published_rounded_mean':-12.4,'published_rounded_stat_uncertainty':0.7,
           'published_systematic_uncertainty':systematic},
      'four_height_diagnostic':{'heights_cm':[r[0] for r in height],
           'through_origin_slope':round(through_origin,6),
           'naive_diagonal_uncertainty':round(through_origin_error,6),
           'covariances_not_available':True,'independent_confirmation':False},
      'physics_comparison':{'model':'weak_field_gravitational_redshift',
           'sign_convention':'experimental negative signed gradient',
           'theory_gradient_1e19_per_cm':round(expected,6),
           'combined_stat_and_published_systematic_z':round(z,6),
           'consistent_with_GR_at_2sigma':abs(z)<2},
      'scientific_limits':{'raw_instrument_data_replicated':False,
           'processed_published_data_replayed':True,
           'independent_fresh_instrument_experiment':False,
           'model_predictions_frozen_before_2023_publication':False,
           'tachyon_neural_evaluation':False,'trained_on_this_dataset':False,
           'proof_of_retrocausality':False,'authority_delta':0}
    }

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();r=replay();args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(r,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'n_runs':r['primary_measurement']['count_individual_runs'],
                      'z':r['physics_comparison']['combined_stat_and_published_systematic_z']}))
if __name__=='__main__':main()
