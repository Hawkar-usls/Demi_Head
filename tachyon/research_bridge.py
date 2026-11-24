"""Read-only, fail-closed Beetle -> Tachyon -> TOPA scientific envelope.

Reads an existing Janus-Demiurge Beetle research-context *projection*, never
its raw inbox, transport ACK, private receiver state or executor commands.
TOPA admission must be confirmed by the canonical external router; this module
only prepares compatible claims and can optionally invoke a supplied pinned router.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
from pathlib import Path
from urllib.parse import urlsplit

BEETLE_SCHEMA = 'janus.beetle.runtime_context.v1'
BEETLE_STATUS = 'TRIAGED_TO_RESEARCH_CONTEXT_NOT_VERIFIED'
BEETLE_OWNER = 'Hawkar-usls/Janus-Demiurge'
BEETLE_CAPABILITIES = {
    'may_generate_research_questions': True,
    'is_verified_evidence': False,
    'may_grant_mutation_authority': False,
    'is_direct_gradient_signal': False,
}
TOPA_PROFILE = 'janus.genesis.topa_foundation.v1.3'
MAX_ROUTES = 8
HEX = re.compile(r'^[a-f0-9]+$')

def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def require_hex(value: object, n: int) -> None:
    if not isinstance(value, str) or len(value) != n or not HEX.fullmatch(value):
        raise ValueError('BEETLE_ID_OR_DIGEST_INVALID')

def validate_beetle_context(raw: bytes) -> dict:
    if len(raw) > 100_000:
        raise ValueError('BEETLE_PROJECTION_TOO_LARGE')
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError('BEETLE_OBJECT_REQUIRED')
    digest = obj.get('context_sha256')
    require_hex(digest, 64)
    body = dict(obj)
    body.pop('context_sha256')
    if sha(canonical(body)) != digest:
        raise ValueError('BEETLE_CONTEXT_HASH_MISMATCH')
    if (obj.get('schema') != BEETLE_SCHEMA or obj.get('status') != BEETLE_STATUS or
        obj.get('target_repository') != BEETLE_OWNER or obj.get('capabilities') != BEETLE_CAPABILITIES):
        raise ValueError('BEETLE_PROJECTION_CONTRACT_REJECTED')
    number = obj.get('last_processed_sequence')
    routes = obj.get('research_routes')
    if type(number) is not int or number < 0 or not isinstance(routes, list) or len(routes) > MAX_ROUTES:
        raise ValueError('BEETLE_SEQUENCE_OR_WINDOW_REJECTED')
    if number == 0 and routes:
        raise ValueError('BEETLE_INVALID_EMPTY_CURSOR')
    if obj.get('hypothesis_routes') != [x.get('title') for x in routes if isinstance(x, dict)]:
        raise ValueError('BEETLE_HYPOTHESES_MISMATCH')
    for r in routes:
        if not isinstance(r, dict):
            raise ValueError('BEETLE_ROUTE_OBJECT_REQUIRED')
        require_hex(r.get('batch_id'), 20)
        require_hex(r.get('input_sha256'), 64)
        for key, limit in [('context_id',128),('candidate_id',128),('direction_id',160),('title',140)]:
            v = r.get(key)
            if not isinstance(v,str) or not v.strip() or len(v)>limit:
                raise ValueError('BEETLE_ROUTE_FIELD_REJECTED')
        url = r.get('source_url')
        if not isinstance(url,str) or len(url)>2048:
            raise ValueError('BEETLE_INVALID_URL')
        p=urlsplit(url)
        if p.scheme not in ('http','https') or not p.hostname or p.username or p.password:
            raise ValueError('BEETLE_INVALID_URL')
    return {'schema':'janus.demihead.tachyon.beetle_snapshot.v1',
            'source_repository':BEETLE_OWNER,
            'context_sha256':digest,'last_processed_sequence':number,
            'research_routes':[{'context_id':r['context_id'],'candidate_id':r['candidate_id'],
                'title':r['title'],'source_url':r['source_url'],
                'batch_id':r['batch_id'],'input_sha256':r['input_sha256']} for r in routes],
            'unverified':True,'training_eligible':False,'model_instructions':False,
            'authority_delta':0}

def make_topa_claim(*, claim_id: str, statement: str, source_urls: list[str],
                    category: str = 'HYPOTHESIS_ONLY',
                    alternative: str = 'Standard gravitational redshift and measurement uncertainty',
                    falsifier: str = 'Independent clock data with predeclared tolerance disagree with the model') -> dict:
    if not isinstance(claim_id,str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{4,120}',claim_id):
        raise ValueError('INVALID_CLAIM_ID')
    if not isinstance(statement,str) or not statement.strip() or len(statement)>2000:
        raise ValueError('INVALID_CLAIM_TEXT')
    if category not in ('HYPOTHESIS_ONLY','SOURCE_FACT'):
        raise ValueError('UNSUPPORTED_AUTHORITY_CLASS')
    if category == 'SOURCE_FACT' and not source_urls:
        raise ValueError('SOURCE_FACT_REQUIRES_PRIMARY_SOURCE')
    for url in source_urls:
        if not isinstance(url,str) or urlsplit(url).scheme!='https' or not urlsplit(url).hostname:
            raise ValueError('SOURCE_URL_NOT_HTTPS')
    return {
      'claim_id':claim_id,'origin_agent_id':'JANUS_TACHYON_RESEARCH',
      'claim_text':statement,'raw_claim_text':statement,
      'claim_kind':'HYPOTHESIS' if category=='HYPOTHESIS_ONLY' else 'REPORTED',
      'source_pointers':source_urls,
      'provenance_channel':'MODEL_INFERENCE' if category=='HYPOTHESIS_ONLY' else 'FORMAL_SOURCE',
      'firsthand_status':'NOT_APPLICABLE',
      'evidence_objects':[], 'evidence_class':category,
      'alternative_hypotheses':[alternative] if category=='HYPOTHESIS_ONLY' else [],
      'falsification_tests':[falsifier] if category=='HYPOTHESIS_ONLY' else [],
      'status':'HYPOTHESIS_ONLY' if category=='HYPOTHESIS_ONLY' else 'SOURCE_BOUND_FACT',
      'raw_ledger_rewritten':False, 'independent_replication':False,
    }

def canonical_topa_assessment(envelope: dict, router_path: Path) -> dict:
    """Run the actual TOPA v1.3 Python validator from an operator-pinned checkout."""
    if not router_path.is_file() or router_path.stat().st_size > 100_000:
        raise ValueError('TOPA_PROVIDER_UNAVAILABLE')
    spec = importlib.util.spec_from_file_location('tachyon_pinned_topa_router',str(router_path))
    if spec is None or spec.loader is None:
        raise ValueError('TOPA_MODULE_LOAD_FAILED')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.TOPAEpistemicRouter().validate(envelope)
    if result.get('schema')!='janus.swarm.topa_assessment.v1.3' or result.get('world_truth_implied') or not result.get('admissible'):
        raise ValueError('TOPA_PROVIDER_REJECTED')
    return {'provider':'Hawkar-usls/TOPA', 'source_sha256':sha(router_path.read_bytes()),
            'claim_id':envelope['claim_id'],'admissible':True,
            'evidence_class':result['evidence_class'], 'status':result['status'],
            'world_truth_implied':False,'authority_delta':0}

def main() -> None:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--beetle-context',type=Path,required=True)
    p.add_argument('--topa-router',type=Path)
    p.add_argument('--clock-receipt',type=Path,help='Previously validated published-clock replay receipt')
    p.add_argument('--out',type=Path,required=True)
    args=p.parse_args()
    snapshot=validate_beetle_context(args.beetle_context.read_bytes())
    hypotheses=[]
    for i,r in enumerate(snapshot['research_routes']):
        envelope=make_topa_claim(claim_id=f'TACHYON-BEETLE-{snapshot["last_processed_sequence"]}-{i}',
          statement='Unverified research lead: '+r['title'],source_urls=[r['source_url']],
          alternative='The source may not describe a reproducible physical effect',
          falsifier='Obtain a primary measurement, independent instrument checks, and a dated negative control')
        row={'envelope':envelope,'topa_provider_status':'NOT_CHECKED'}
        if args.topa_router:
            row['topa_receipt']=canonical_topa_assessment(envelope,args.topa_router)
            row['topa_provider_status']='CANONICAL_ROUTER_ACCEPTED_HYPOTHESIS_ONLY'
        hypotheses.append(row)
    clock_claims=[]
    if args.clock_receipt:
        if args.clock_receipt.stat().st_size>100_000:
            raise ValueError('CLOCK_RECEIPT_TOO_LARGE')
        receipt=json.loads(args.clock_receipt.read_text(encoding='utf-8'))
        if (receipt.get('schema')!='janus.tachyon.clock_process_replay.v1' or
            receipt.get('source',{}).get('sha256')!='a4384040d5678893b4df15ea0be2980661023305f5009de876179fab1dea632f' or
            receipt.get('scientific_limits',{}).get('tachyon_neural_evaluation') is not False or
            receipt.get('scientific_limits',{}).get('raw_instrument_data_replicated') is not False):
            raise ValueError('CLOCK_RECEIPT_AUTHORITY_OR_SOURCE_REJECTED')
        paper='https://doi.org/10.1038/s41467-023-40629-8'
        fact=make_topa_claim(claim_id='TACHYON-WISCONSIN-PUBLISHED-DATA-2023',
           statement='Published Fig3 processed data contain 14 signed redshift-gradient measurements and uncertainty estimates; not raw instrument records.',
           source_urls=[paper],category='SOURCE_FACT')
        hypothesis=make_topa_claim(claim_id='TACHYON-WISCONSIN-GR-CONSISTENCY-2023',
           statement='The 2023 reported clock frequency gradient is statistically compatible with ordinary weak-field GR within its reported systematic uncertainty.',
           source_urls=[paper],alternative='Unmodelled instrumental systematic or shared calibration error',
           falsifier='Independent raw clock reanalysis with predeclared nuisance-parameter model and blind replication')
        for envelope in (fact,hypothesis):
            row={'envelope':envelope,'topa_provider_status':'NOT_CHECKED'}
            if args.topa_router:
                row['topa_receipt']=canonical_topa_assessment(envelope,args.topa_router)
                row['topa_provider_status']='CANONICAL_ROUTER_ACCEPTED_'+envelope['evidence_class']
            clock_claims.append(row)
    result={'schema':'janus.demihead.tachyon.topa_beetle_bridge.v1',
            'beetle':snapshot,'topa':hypotheses,'clock_topa':clock_claims,'model_training_occured':False,
            'external_fetches':False,'authority_delta':0,'publication_enabled':False}
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(json.dumps({'route_count':len(hypotheses),'topa_validated':bool(args.topa_router),
                      'output_sha256':sha(args.out.read_bytes())},sort_keys=True))

if __name__=='__main__':
    main()
