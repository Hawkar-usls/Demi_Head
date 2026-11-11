#!/usr/bin/env python3
"""Train a small text-order transformer on source-bounded JANUS video summaries.

The model learns narrative ordering, NOT future data, faster-than-light signalling,
or retrocausality. All evaluation uses unseen segments, not shuffled pairs of the
same segment. Training is offline, CPU-bounded, and has no external effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

RECORD_ID = "JANUS-TIME-HOMODEUS-PwOk0GKDv9c-20261111"
EXPECTED_SHA256 = "44c1030da28ecea4ca1fc6891dea34a63445f9a981e2387b1e4bf4d189f43409"
SOURCE = Path(__file__).resolve().parents[1] / "data" / "tachyon" / "source_video_relativity_20261111.json"
TOKEN_RE = re.compile(r"[^\W_]+|[^\s]", re.UNICODE)
SPECIAL = ("<pad>", "<unk>", "<cls>", "<sep>")
EXCLUDED = {"advertisement", "advertisement_and_intro"}


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def load_segments(path: Path = SOURCE, expected_sha: str = EXPECTED_SHA256) -> tuple[list[dict], str]:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha:
        raise ValueError(f"source_sha256_mismatch: {digest} != {expected_sha}")
    doc = json.loads(raw)
    if doc.get("record_id") != RECORD_ID:
        raise ValueError("wrong_source_record_id")
    if doc.get("transcription_provenance", {}).get("representation", "").find("NOT full verbatim") < 0:
        raise ValueError("unexpected_caption_provenance")
    segments = []
    for row in doc.get("subtitle_semantic_segments", []):
        if row.get("category") in EXCLUDED:
            continue
        if row.get("origin") != "original_caption_paraphrase":
            raise ValueError("unexpected_segment_origin")
        timestamp = row.get("start", "")
        parts = timestamp.split(":")
        if len(parts) != 3:
            raise ValueError("invalid_timestamp")
        sec = int(parts[0])*3600 + int(parts[1])*60 + int(parts[2])
        summary = row.get("summary_ru", "").strip()
        if not summary:
            raise ValueError("empty_segment")
        segments.append({"time_sec": sec, "summary": summary})
    if any(a["time_sec"] >= b["time_sec"] for a,b in zip(segments, segments[1:])):
        raise ValueError("non_monotonic_segments")
    if len(segments) < 12:
        raise ValueError("insufficient_segments")
    return segments, digest


def chronology_split(segments: list[dict], train_fraction: float = 0.7) -> tuple[list[dict], list[dict]]:
    cut = max(6, min(len(segments)-4, int(len(segments)*train_fraction)))
    return segments[:cut], segments[cut:]


def build_vocab(training: list[dict], max_size: int=2048) -> dict[str,int]:
    from collections import Counter
    freq = Counter(t for s in training for t in tokens(s["summary"]))
    return {word:i for i, word in enumerate([*SPECIAL,*(w for w,_ in freq.most_common(max_size-len(SPECIAL)))])}


def make_examples(rows: list[dict]) -> list[tuple[str,str,int]]:
    result = []
    for i in range(len(rows)):
        for j in range(i+1,len(rows)):
            a,b=rows[i]["summary"],rows[j]["summary"]
            result.extend([(a,b,1),(b,a,0)])
    return result


def encode(a: str,b: str,vocab: dict[str,int],max_len: int=48) -> tuple[list[int],list[int]]:
    # Critical: only descriptive text is encoded; timeline labels and timestamps
    # are never inputs to the transformer.
    budget = (max_len-2)//2
    left=tokens(a)[:budget]
    right=tokens(b)[:max_len-2-len(left)]
    seq=["<cls>",*left,"<sep>",*right]
    ids=[vocab.get(t,1) for t in seq]
    return ids+[0]*(max_len-len(ids)), [1]*len(seq)+[0]*(max_len-len(seq))


def tensorize(examples: list[tuple[str,str,int]],vocab: dict[str,int],max_len: int) -> TensorDataset:
    encoded=[encode(a,b,vocab,max_len) for a,b,_ in examples]
    return TensorDataset(torch.tensor([e[0] for e in encoded],dtype=torch.long),
                         torch.tensor([e[1] for e in encoded],dtype=torch.bool),
                         torch.tensor([lab for _,_,lab in examples],dtype=torch.float32))


class TachyonTransformer(nn.Module):
    """Small bidirectional Transformer Encoder for *text pair chronology*."""
    def __init__(self, vocab_size: int, max_len: int=48, width: int=32, heads: int=2):
        super().__init__()
        self.word=nn.Embedding(vocab_size,width,padding_idx=0)
        self.pos=nn.Embedding(max_len,width)
        block=nn.TransformerEncoderLayer(d_model=width,nhead=heads,
                                          dim_feedforward=width*2,dropout=0.0,
                                          activation="gelu",batch_first=True,norm_first=False)
        self.encoder=nn.TransformerEncoder(block,num_layers=1,enable_nested_tensor=False)
        self.final=nn.Linear(width,1)

    def forward(self,ids: torch.Tensor,valid: torch.Tensor) -> torch.Tensor:
        positions=torch.arange(ids.shape[1],device=ids.device)
        x=self.word(ids)+self.pos(positions)[None,:,:]
        x=self.encoder(x,src_key_padding_mask=~valid)
        return self.final(x[:,0,:]).squeeze(-1)


def assess(model: nn.Module, ds: TensorDataset, batch: int=32) -> dict:
    model.eval(); n=0;loss=0.0;correct=0; brier=0.0
    with torch.no_grad():
        for ids, mask, labels in DataLoader(ds,batch_size=batch,shuffle=False):
            p=torch.sigmoid(model(ids,mask)); d=p-labels
            n+=len(labels)
            loss+=nn.functional.binary_cross_entropy(p,labels,reduction="sum").item()
            brier+=(d*d).sum().item()
            correct+=((p>=0.5)==(labels>0.5)).sum().item()
    return {"count":n,"accuracy":round(correct/n,6),
            "log_loss":round(loss/n,6),"brier":round(brier/n,6)}


def run(source: Path=SOURCE, outdir: Path=Path("artifacts/tachyon"),
        epochs: int=8, seed: int=1729, max_len: int=48, batch_size: int=32,
        lr: float=0.002, expected_sha: str=EXPECTED_SHA256) -> dict:
    if not 1<=epochs<=30 or not 16<=max_len<=128 or not 1<=batch_size<=128:
        raise ValueError("resource_budget_exceeded")
    torch.set_num_threads(min(2,os.cpu_count() or 1))
    random.seed(seed);torch.manual_seed(seed)
    segments,digest=load_segments(source,expected_sha)
    training,holdout=chronology_split(segments)
    vocab=build_vocab(training)
    train_examples=make_examples(training); val_examples=make_examples(holdout)
    ds_train=tensorize(train_examples,vocab,max_len)
    ds_val=tensorize(val_examples,vocab,max_len)
    model=TachyonTransformer(len(vocab),max_len=max_len)
    optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=0.01)
    for _ in range(epochs):
        model.train()
        generator=torch.Generator().manual_seed(seed+_)
        for ids,mask,labels in DataLoader(ds_train,batch_size=batch_size,shuffle=True,generator=generator):
            optimizer.zero_grad(set_to_none=True)
            loss=nn.functional.binary_cross_entropy_with_logits(model(ids,mask),labels)
            loss.backward();nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optimizer.step()
    train_metrics=assess(model,ds_train,batch_size)
    holdout_metrics=assess(model,ds_val,batch_size)
    # Balanced pairs; fixed honest baseline 50% / Brier=.25 / logloss=ln 2.
    baseline={"accuracy":0.5,"brier":0.25,"log_loss":round(math.log(2),6)}
    promoted=(holdout_metrics["accuracy"] >= 0.55 and holdout_metrics["brier"] < 0.25)
    outdir.mkdir(parents=True,exist_ok=True)
    checkpoint=outdir/"candidate.pt"
    torch.save({"version":"tachyon-0.1","state_dict":model.state_dict(),
                "vocab":vocab,"max_len":max_len,"source_sha256":digest,
                "status":"EXPERIMENTAL_CANDIDATE_NOT_AUTHORIZED"},checkpoint)
    receipt={"schema":"janus.demihead.tachyon.training.v1","model_name":"Tachyon",
             "model_kind":"tiny_transformer_text_pair_chronology",
             "source_record_id":RECORD_ID,"source_sha256":digest,
             "source_kind":"timestamped_semantic_paraphrases_NOT_raw_physical_measurements",
             "dataset":{"total_segments":len(segments),"train_segments":len(training),
                        "holdout_segments":len(holdout),"train_pairs":len(train_examples),
                        "holdout_pairs":len(val_examples),"holdout_strategy":"chronological_segment_disjoint",
                        "excluded_categories":sorted(EXCLUDED),"training_only_vocab":True,
                        "timestamps_as_input":False},
             "architecture":{"layers":1,"width":32,"heads":2,"vocab_size":len(vocab),
                             "max_len":max_len,"parameters":sum(p.numel() for p in model.parameters())},
             "training":{"epochs":epochs,"seed":seed,"batch_size":batch_size,"lr":lr,
                         "cpu_only":True,"training_loss":train_metrics},
             "validation":{"holdout":holdout_metrics,"constant_baseline":baseline,
                           "admission_gate":"accuracy>=0.55_and_brier<0.25",
                           "passed":promoted},
             "status":"CANDIDATE_GATE_PASS_NOT_EXTERNAL_VALIDATION" if promoted else "HOLD_NO_HOLDOUT_GAIN",
             "scientific_claims":{"new_physics":False,"future_information_access":False,
                                  "retrocausality_demonstrated":False,"physical_signal_measured":False},
             "authority_delta":0,"external_effects":False}
    (outdir/"receipt.json").write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return receipt


def main() -> int:
    p=argparse.ArgumentParser(description="Train JANUS Tachyon on hash-pinned video JSON")
    p.add_argument("--source",type=Path,default=SOURCE)
    p.add_argument("--outdir",type=Path,default=Path("artifacts/tachyon"))
    p.add_argument("--epochs",type=int,default=8)
    p.add_argument("--seed",type=int,default=1729)
    p.add_argument("--expected-sha",default=EXPECTED_SHA256)
    args=p.parse_args()
    result=run(source=args.source,outdir=args.outdir,epochs=args.epochs,seed=args.seed,expected_sha=args.expected_sha)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0


if __name__=="__main__":
    raise SystemExit(main())
