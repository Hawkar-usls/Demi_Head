"""Experimental bounded textual mechanism head. Not a science truth engine.

Training task: classify six supplied physics mechanism families from questions.
Holdout consists of disjoint paraphrase templates, never training text. This is
NOT general free-form explanation, unseen physics, or an experimental prediction.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
from collections import Counter
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[1]/'data/tachyon/explanation_cards_v1.json'
TOKEN=re.compile(r'[^\W_]+',re.UNICODE)
PAD=0;UNK=1

def load_data(path=SOURCE):
    doc=json.loads(Path(path).read_text('utf8'))
    if doc.get('schema')!='janus.demihead.tachyon.semantic_mechanisms.v1' or len(doc.get('mechanisms',{}))!=6:
        raise ValueError('EXPLANATION_CORPUS_REJECTED')
    for obj in doc['mechanisms'].values():
        if len(obj.get('questions',[]))!=10 or len(set(obj['questions']))!=10:
            raise ValueError('EXPLANATION_SPLITS_INVALID')
        if not obj.get('counterexample') or not obj.get('explanation'):
            raise ValueError('EXPLANATION_FALSIFIER_MISSING')
    return doc

def tokenize(s):
    return TOKEN.findall(s.lower())

def samples(doc, part):
    bound={'train':(0,6),'tune':(6,8),'holdout':(8,10)}[part]
    result=[]
    for c,(name,obj) in enumerate(sorted(doc['mechanisms'].items())):
        for sentence in obj['questions'][bound[0]:bound[1]]:
            result.append((sentence,c))
    return result

def make_vocab(data):
    counts=Counter(t for text,_ in samples(data,'train') for t in tokenize(text))
    return {'<pad>':PAD,'<unk>':UNK,**{t:i+2 for i,(t,_) in enumerate(counts.most_common(1000))}}

def encode(text, vocab, maxlen=26):
    return [vocab.get(w,UNK) for w in tokenize(text)[:maxlen]] + [PAD]*max(0,maxlen-len(tokenize(text)))

def train(outdir:Path,epochs:int=25,seed:int=20261111)->dict:
    import torch
    from torch import nn
    from torch.utils.data import TensorDataset,DataLoader
    if not (1<=epochs<=50):raise ValueError('EPOCH_BUDGET_EXCEEDED')
    torch.set_num_threads(min(2,os.cpu_count() or 1))
    random.seed(seed);torch.manual_seed(seed)
    doc=load_data(); vocab=make_vocab(doc)
    def ds(part):
        pairs=samples(doc,part)
        return TensorDataset(torch.tensor([encode(x,vocab) for x,_ in pairs],dtype=torch.long),
                             torch.tensor([y for _,y in pairs],dtype=torch.long))
    sets={part:ds(part) for part in ('train','tune','holdout')}
    class Tiny(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb=nn.Embedding(len(vocab),40,padding_idx=0)
            self.position=nn.Embedding(26,40)
            self.transformer=nn.TransformerEncoder(nn.TransformerEncoderLayer(
               d_model=40,nhead=4,dim_feedforward=80,dropout=0.,batch_first=True),num_layers=1,
               enable_nested_tensor=False)
            self.head=nn.Linear(40,6)
        def forward(self,x):
            positions=torch.arange(x.size(1),device=x.device)
            seq=self.emb(x)+self.position(positions)[None,:,:]
            a=self.transformer(seq,src_key_padding_mask=x.eq(0))
            w=(~x.eq(0)).float().unsqueeze(-1)
            return self.head((a*w).sum(dim=1)/w.sum(dim=1).clamp_min(1))
    model=Tiny(); optim=torch.optim.AdamW(model.parameters(),lr=0.002,weight_decay=0.005)
    def stats(part):
        model.eval()
        with torch.no_grad():
            inp,lbl=sets[part].tensors
            logits=model(inp)
            loss=nn.functional.cross_entropy(logits,lbl).item()
            correct=int((logits.argmax(1)==lbl).sum().item())
            return {'n':len(lbl),'accuracy':round(correct/len(lbl),6),'loss':round(loss,6)}
    best=None; best_loss=float('inf');best_ep=0
    for epoch in range(epochs):
        model.train()
        gen=torch.Generator().manual_seed(seed+epoch)
        for x,y in DataLoader(sets['train'],batch_size=12,shuffle=True,generator=gen):
            optim.zero_grad(set_to_none=True)
            loss=nn.functional.cross_entropy(model(x),y)
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.)
            optim.step()
        v=stats('tune')
        if v['loss']<best_loss:
            best_loss=v['loss'];best_ep=epoch+1
            best={k:t.detach().clone() for k,t in model.state_dict().items()}
    model.load_state_dict(best)
    report={'schema':'janus.tachyon.explanation_generalization.v0.3',
       'model':'small torch TransformerEncoder 1 layer 4 heads width 40',
       'model_parameters':sum(p.numel() for p in model.parameters()),
       'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
       'train':stats('train'),'tune':stats('tune'),'frozen_heldout':stats('holdout'),
       'heldout_majority_class_baseline':round(1/6,6),
       'split':'6 training, 2 tuning, 2 heldout questions per each of six mechanism classes',
       'best_epoch_selected_using_tune_only':best_ep,
       'training_samples_are_human_curated_not_physical_measurements':True,
       'heldout_uses_unseen_phrasing_but_known_physical_families':True,
       'external_physical_validation':False,
       'claim':'MECHANISM_FAMILY_CLASSIFICATION_ONLY_NOT_VERIFIED_EXPLANATION_OR_RETROCAUSAL_SIGNAL',
       'authority_delta':0,'auto_deploy':False}
    report['candidate_gate']={'passed':report['frozen_heldout']['accuracy']>=0.65,
                              'required_accuracy':0.65,
                              'status':'EXPLORATORY_TEXT_CANDIDATE' if report['frozen_heldout']['accuracy']>=0.65 else 'HOLD_NO_TEXT_GENERALIZATION_GAIN'}
    outdir.mkdir(parents=True,exist_ok=True)
    torch.save({'state_dict':best,'vocab':vocab,'model':report['model'],
      'source_sha256':report['source_sha256'],'auto_deploy':False},outdir/'explanation_candidate.pt')
    (outdir/'explanation_receipt.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--epochs',type=int,default=25)
    p.add_argument('--outdir',type=Path,default=Path('artifacts/tachyon-explanations'))
    args=p.parse_args()
    print(json.dumps(train(args.outdir,args.epochs),indent=2))
if __name__=='__main__':main()
