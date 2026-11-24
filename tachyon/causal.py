#!/usr/bin/env python3
"""Tachyon v0.2: bounded numerical Transformer for Lorentz causal-order cases.

Unlike the narrative-order benchmark (v0.1), this learns an algebraically
well-defined task from independent, newly sampled physical parameters. It does
not learn a mechanism for physical FTL or access to future information. The
analytic relativity equations are the authoritative baseline (100% labels).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from .train import EXPECTED_SHA256, SOURCE, RECORD_ID

VERSION = 'TACHYON-0.2-NUMERIC-CAUSAL'


def validate_source(path: Path = SOURCE, digest: str = EXPECTED_SHA256) -> str:
    raw = path.read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != digest:
        raise ValueError(f'source_digest_mismatch: {actual}')
    obj = json.loads(raw)
    if obj.get('record_id') != RECORD_ID or obj.get('source_video', {}).get('id') != 'PwOk0GKDv9c':
        raise ValueError('unexpected_source_identity')
    formula = obj.get('reproducible_calculations', {}).get('lorentz_transform', '')
    if 'Δt′' not in formula or 'γ' not in formula or 'vΔx/c²' not in formula:
        raise ValueError('lorentz_transform_not_present')
    return actual


def analytic(q: float, beta: float) -> tuple[int, int]:
    """Inputs q=cΔt/Δx and β=v/c, with positive Δt, Δx, 0<=β<1.

    Relative chronological reversal in boosted coordinates: β>q.
    Invariant interval spacelike: q<1. No physical FTL transmitter implied.
    """
    if not (0 < q < 4 and 0 <= beta < 1):
        raise ValueError('out_of_physical_domain')
    return (int(beta > q), int(q < 1.0))


def dataset(seed: int, n: int, regime: str) -> TensorDataset:
    """Fresh independent continuous draws. Heldout seeds are never used in training.

    Boundary cases are intentionally hard and report separately. Parameter
    distributions for OOD cases are specified before the training run.
    """
    if regime not in {'train', 'tuning', 'iid', 'new_beta_band', 'order_boundary', 'lightcone_boundary'}:
        raise ValueError('unknown_regime')
    rng = random.Random(seed)
    xy, yy = [], []
    for i in range(n):
        if regime in {'train', 'tuning', 'iid'}:
            beta = rng.uniform(0.03, 0.85)
            if i % 3 == 0:  # balanced examples near the transition beta=q
                q = max(0.03, beta + rng.uniform(-0.24, 0.24))
            else:
                q = rng.uniform(0.03, 1.6)
        elif regime == 'new_beta_band':
            beta = rng.uniform(0.85, 0.98) # entire beta band excluded from training
            q = max(0.03, beta + rng.uniform(-0.3, 0.3)) if i % 2 else rng.uniform(0.03, 1.6)
        elif regime == 'order_boundary':
            beta = rng.uniform(0.12, 0.83)
            q = beta + rng.choice((-1,1))*rng.uniform(0.004,0.045)
        else:
            beta = rng.uniform(0.03, 0.85)
            q = 1.0 + rng.choice((-1,1))*rng.uniform(0.004,0.045)
        q = min(1.95, q)
        xy.append([q, beta])
        yy.append(analytic(q, beta))
    return TensorDataset(torch.tensor(xy, dtype=torch.float32), torch.tensor(yy, dtype=torch.float32))


class TachyonCausalTransformer(nn.Module):
    """Three-token Transformer: CLS + numeric q token + numeric beta token."""
    def __init__(self, width: int = 32, heads: int = 4):
        super().__init__()
        self.scalar = nn.Linear(1, width)
        self.types = nn.Embedding(3,width)
        self.cls = nn.Parameter(torch.zeros(1,1,width))
        self.blocks = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(d_model=width,nhead=heads,
                                       dim_feedforward=width*2,dropout=0.,
                                       activation='gelu',batch_first=True),
            num_layers=1,enable_nested_tensor=False)
        self.classifier = nn.Linear(width,2)

    def forward(self, xs: torch.Tensor) -> torch.Tensor:
        batch = xs.shape[0]
        values = self.scalar(xs.unsqueeze(-1))
        emb = self.types(torch.arange(3, device=xs.device))
        cls = self.cls.expand(batch,1,-1)
        seq = torch.cat([cls,values],dim=1) + emb[None,:,:]
        return self.classifier(self.blocks(seq)[:,0,:])


def evaluate(model: nn.Module, ds: TensorDataset, batch: int = 256) -> dict:
    model.eval()
    preds, labels = [], []
    with torch.no_grad():
        for x,y in DataLoader(ds,batch_size=batch,shuffle=False):
            preds.append(torch.sigmoid(model(x)).cpu())
            labels.append(y.cpu())
    p=torch.cat(preds); y=torch.cat(labels)
    out={}
    for col,name in enumerate(('reverse_coordinates','spacelike')):
        z=p[:,col]; target=y[:,col]; prevalence=target.mean().item()
        out[name]={
          'count':len(target),
          'positive_fraction':round(prevalence,6),
          'accuracy':round(((z>=0.5)==(target>=0.5)).float().mean().item(),6),
          'brier':round(((z-target)**2).mean().item(),6),
          'logloss':round(nn.functional.binary_cross_entropy(z,target).item(),6),
          'majority_class_accuracy':round(max(prevalence,1-prevalence),6),
          'majority_class_brier':round(prevalence*(1-prevalence),6)
        }
    return out


def source_sanity(model: nn.Module) -> dict:
    # Values copied from the pinned source JSON, never used as training examples.
    beta = [0.,0.3,0.5,0.6,0.8,0.9]
    q = 0.5
    with torch.no_grad():
        preds=torch.sigmoid(model(torch.tensor([[q,v] for v in beta],dtype=torch.float32)))
    expected=[0,0,0,1,1,1]  # at equality β=q, interval exactly simultaneous.
    got=[int(v>=0.5) for v in preds[:,0].tolist()]
    return {'points':len(beta),'expected':expected,'predicted':got,
            'correct':sum(a==b for a,b in zip(expected,got)),
            'probabilities': [round(float(z),6) for z in preds[:,0]]}


def run(source:Path=SOURCE, outdir:Path=Path('artifacts/tachyon-causal'),
        epochs:int=20, seed:int=20261111, train_n:int=7000,
        batch_size:int=128, lr:float=0.002) -> dict:
    if not 1 <= epochs <= 40 or not 100 <= train_n <= 12000 or not 16 <= batch_size <= 256:
        raise ValueError('resource_budget_exceeded')
    digest=validate_source(source)
    torch.set_num_threads(min(2, os.cpu_count() or 1))
    random.seed(seed);torch.manual_seed(seed)
    train=dataset(seed+1,train_n,'train')
    tuning=dataset(seed+2,1500,'tuning')
    # Holdout test seeds/regimes fixed BEFORE training, not used for selection.
    checks={'iid':dataset(seed+101,2500,'iid'),
            'new_beta_band':dataset(seed+102,2000,'new_beta_band'),
            'order_boundary':dataset(seed+103,1500,'order_boundary'),
            'lightcone_boundary':dataset(seed+104,1500,'lightcone_boundary')}
    model=TachyonCausalTransformer()
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0.002)
    best_loss=math.inf; best_state=None; best_epoch=None
    history=[]
    for epoch in range(epochs):
        model.train()
        shuffled=torch.Generator().manual_seed(seed+epoch)
        for x,y in DataLoader(train,batch_size=batch_size,shuffle=True,generator=shuffled):
            optimizer.zero_grad(set_to_none=True)
            z=model(x)
            loss=nn.functional.binary_cross_entropy_with_logits(z,y)
            loss.backward(); nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
        current=evaluate(model,tuning)
        score=sum(current[t]['logloss'] for t in ('reverse_coordinates','spacelike'))
        history.append({'epoch':epoch+1,'tuning_loss_sum':round(score,6)})
        if score<best_loss:
            best_loss=score;best_epoch=epoch+1
            best_state={k:v.detach().clone() for k,v in model.state_dict().items()}
    model.load_state_dict(best_state)
    results={name:evaluate(model,ds) for name,ds in checks.items()}
    source_checks=source_sanity(model)
    # Gate is declared before evaluating the heldout distributions. It does not
    # replace the analytic SR equation, which is exact on these synthetic cases.
    passed=(results['iid']['reverse_coordinates']['accuracy']>=0.95 and
            results['iid']['spacelike']['accuracy']>=0.95 and
            results['new_beta_band']['reverse_coordinates']['accuracy']>=0.90 and
            results['order_boundary']['reverse_coordinates']['accuracy']>=0.8 and
            results['lightcone_boundary']['spacelike']['accuracy']>=0.8 and
            source_checks['correct']>=5)
    outdir.mkdir(parents=True,exist_ok=True)
    torch.save({'version':VERSION,'state_dict':best_state,'source_sha256':digest,
                'training_seed':seed,'not_a_physical_signal_detector':True},outdir/'candidate.pt')
    receipt={
      'schema':'janus.demihead.tachyon.generalization.v2',
      'model_name':'Tachyon', 'version':VERSION,
      'source':{'record_id':RECORD_ID,'sha256':digest,
                'use':'physics_equation_provenance; source_narrative_not_presented_as_numerical_measurements'},
      'task':{'inputs':['q=c*delta_t/delta_x','beta=v/c'],
              'constraints':'delta_t>0, delta_x>0, 0<=beta<1',
              'outputs':['reverse_coordinate_order','spacelike_interval'],
              'label_rules':['beta>q','q<1'],
              'physical_signal_claim':'NONE; coordinate ordering is not controllable FTL'},
      'train':{'n':train_n,'epochs_budget':epochs,'best_epoch_on_tuning_only':best_epoch,
               'seed':seed,'tuning_examples':len(tuning),
               'samples_are_synthetic_from_exact_formula':True,
               'time_labels_as_input':False,'trained_on_holdout':False,
               'train_beta_range':[0.03,0.85], 'history':history},
      'architecture':{'type':'torch TransformerEncoder numerical tokens',
                      'parameters':sum(p.numel() for p in model.parameters()),'layers':1,'heads':4,'width':32},
      'holdout':results,
      'source_sweep_sanity':source_checks,
      'baselines':{'analytic_formula_accuracy':1.0,
                   'majority_class_per_holdout':True,
                   'narrative_order_v0_1_holdout_accuracy':0.5},
      'gate':{'definition':'iid both>=0.95, new beta reverse>=0.90, order boundary reverse>=0.80, lightcone boundary spacelike>=0.80, video sweep >=5/6',
              'passed':passed, 'training_admission':False,
              'status':'RESEARCH_NUMERIC_GATE_PASS_NO_EXTERNAL_VALIDATION' if passed else 'HOLD_NUMERIC_GENERALIZATION'},
      'limitations':['synthetic equations only, not independent laboratory measurements',
                     'not proof of novelty, time travel, FTL, or retrocausality',
                     'not evidence that narrative ordering on heldout video segments improved',
                     'numeric extrapolation outside declared ranges not established'],
      'authority_delta':0,'external_effects':False
    }
    (outdir/'receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return receipt


def main():
    cli=argparse.ArgumentParser(description='Tachyon numerical relativity generalization with heldout gates')
    cli.add_argument('--source',type=Path,default=SOURCE)
    cli.add_argument('--outdir',type=Path,default=Path('artifacts/tachyon-causal'))
    cli.add_argument('--epochs',type=int,default=20)
    cli.add_argument('--train-n',type=int,default=7000)
    cli.add_argument('--seed',type=int,default=20261111)
    args=cli.parse_args()
    print(json.dumps(run(args.source,args.outdir,args.epochs,args.seed,args.train_n),ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
