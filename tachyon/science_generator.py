"""TACHYON-R2B experimental sequence-to-sequence Transformer.

Exactly 12 nonverbatim, source-audited Meta Registry video explanations plus
two short, independently paraphrased questions for each of 6 theory papers.
The 2010/2022/2023 atomic-clock publications are held out by source family.
No measured clock numbers or raw laboratory traces are read during training.

Pure research candidate, NOT a pretrained GPT, verified physical interpretation,
independent scientific replication, temporal precognition or production model.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import random
import re

SCHEMA="janus.tachyon.r2b.seq2seq_explanation.v1"
TOKEN=re.compile(r"(?u)\w+|[^\w\s]")
PAD,BOS,EOS,UNK=0,1,2,3
SPECIAL=["<pad>","<bos>","<eos>","<unk>"]
VIDEO_ID="PwOk0GKDv9c"
REGISTRY_COMMIT="a7f77b02ba6f66efc3a0df5d275de7e57eb0e28d"
PRIMARY_FAMILIES=frozenset((
 "PAPER_ALCUBIERRE_1994","PAPER_HAWKING_1992",
 "PAPER_MORRIS_THORNE_YURTSEVER_1988",
 "PAPER_FINAZZI_LIBERATI_BARCELO_2009","PAPER_VISSER_1993",
 "PAPER_MISRA_SUDARSHAN_1977"))
HOLDOUT_FAMILIES=frozenset((
 "CLOCK_NIST_CHOU_2010","CLOCK_JILA_BOTHWELL_2022",
 "CLOCK_WISCONSIN_ZHENG_2023"))
HOLDOUT_DOIS=frozenset((
 "10.1126/science.1192720","10.1038/s41586-021-04349-7",
 "10.1038/s41467-023-40629-8"))
MAX_SOURCE=58
MAX_TARGET=78

class ScienceHold(ValueError):
    pass

def require(test,reason):
    if not test:raise ScienceHold(reason)

def canonical(data):
    return json.dumps(data,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def sha(raw):return hashlib.sha256(raw).hexdigest()

def load_json(path):
    raw=Path(path).read_bytes()
    require(len(raw)<300_000,"INPUT_TOO_LARGE")
    def unique(pairs):
        d={}
        for k,v in pairs:
            require(k not in d,"DUPLICATE_JSON_KEY")
            d[k]=v
        return d
    obj=json.loads(raw,object_pairs_hook=unique,
                   parse_constant=lambda _:(_ for _ in ()).throw(ScienceHold("NONFINITE_JSON")))
    require(isinstance(obj,dict),"EXPECTED_OBJECT")
    return obj,sha(raw)

def tokens(s):return TOKEN.findall(str(s).lower())

def training_rows(video,papers):
    require(video.get("schema")=="janus.tachyon.media_science_instruction_corpus.v1","VIDEO_SCHEMA")
    require(video.get("status")=="INSTRUCTION_EXAMPLES_PREPARED_NOT_NEURAL_TRAINING","VIDEO_STATE")
    check=video.get("receipt_sha256")
    require(isinstance(check,str) and
            check==sha(canonical({k:v for k,v in video.items() if k!="receipt_sha256"})),
            "VIDEO_RECEIPT_SHA_MISMATCH")
    src=video.get("source",{})
    require(src.get("video_id")==VIDEO_ID and src.get("commit_sha")==REGISTRY_COMMIT,
            "VIDEO_SOURCE_NOT_PINNED")
    examples=video.get("examples",[])
    require(isinstance(examples,list) and len(examples)==12 and video.get("count")==12,
            "VIDEO_EXAMPLE_COUNT")
    require(video.get("split_policy",{}).get("media_source_families")==1,
            "FAKE_VIDEO_SOURCE_INDEPENDENCE")
    require(video.get("lab_holdout",{}).get("lab_data_in_training_examples") is False and
            video.get("rights",{}).get("may_train_on_independent_lab_measurements") is False,
            "LAB_TRAINING_LEAK")
    require(papers.get("schema")=="janus.tachyon.r2b.reviewed_primary_explanation_seeds.v1",
            "THEORY_PAPERS_SCHEMA")
    require(papers.get("not_actual_lab_measurements") is True,"PAPER_MEASUREMENTS_FORBIDDEN")
    sources=papers.get("sources",[])
    require(isinstance(sources,list) and len(sources)==6 and
            {x.get("family") for x in sources}==PRIMARY_FAMILIES,
            "THEORY_PAPER_FAMILY_INVENTORY")
    rows=[]
    for x in examples:
        require(x.get("split")=="TRAIN" and x.get("source_family_id")=="HOMO-DEUS-PWOK0GKDv9c",
                "VIDEO_SPLIT_CHANGED")
        require(x.get("is_independent_lab_measurement") is False and
                x.get("scientific_retrocausality_proven") is False and
                x.get("record_provenance")=="AUDITED_MEDIA_PARAPHRASE_NOT_VERBATIM_CAPTIONS",
                "MEDIA_SOURCE_AUTHORITY_ESCALATION")
        q,a=x.get("input_ru"),x.get("target_ru")
        require(isinstance(q,str) and len(q)>50 and
                isinstance(a,str) and len(a)>50,"INVALID_MEDIA_EXPLANATION")
        rows.append({"family":"HOMO-DEUS-PWOK0GKDv9c","question":q,"answer":a,
                     "provenance":"SECONDARY_VIDEO_PARAPHRASE"})
    for x in sources:
        doi=x.get("doi");qs=x.get("questions");a=x.get("answer")
        require(x.get("kind")=="THEORETICAL_RESEARCH" and
                isinstance(doi,str) and doi not in HOLDOUT_DOIS and
                x.get("url")=="https://doi.org/"+doi,
                "LAB_SOURCE_OR_THEORY_PROVENANCE_CHANGED")
        require(isinstance(qs,list) and len(qs)==2 and
                len(set(qs))==2 and isinstance(a,str) and len(a)>90,
                "THEORY_PAPER_TEXT_INVALID")
        for q in qs:
            require(isinstance(q,str) and len(q)>25,"THEORY_QUESTION_INVALID")
            rows.append({"family":x["family"],"question":q,"answer":a,
                         "provenance":"PRIMARY_THEORY_PAPER_PARAPHRASE"})
    require(len(rows)==24 and len({r["question"] for r in rows})==24,
            "TRAINING_PAIR_INVENTORY_CHANGED")
    require(not ({r["family"] for r in rows}&HOLDOUT_FAMILIES),
            "CLOCK_HOLDOUT_SOURCE_IN_TRAINING")
    return rows

def make_vocab(rows):
    counts=Counter(t for r in rows for name in ("question","answer")
                   for t in tokens(r[name]))
    return SPECIAL+[k for k,_ in sorted(counts.items(),
                  key=lambda pair:(-pair[1],pair[0]))]

def vectorize(s,lookup,length):
    ids=[lookup.get(t,UNK) for t in tokens(s)[:length-2]]
    return [BOS]+ids+[EOS]+[PAD]*max(0,length-len(ids)-2)

def build_model(n_vocab,width=64):
    import torch
    from torch import nn
    class ScienceDecoder(nn.Module):
        def __init__(self):
            super().__init__()
            self.encoder_embedding=nn.Embedding(n_vocab,width,padding_idx=PAD)
            self.decoder_embedding=nn.Embedding(n_vocab,width,padding_idx=PAD)
            self.source_positions=nn.Embedding(MAX_SOURCE,width)
            self.target_positions=nn.Embedding(MAX_TARGET,width)
            self.transformer=nn.Transformer(
                d_model=width,nhead=4,num_encoder_layers=1,
                num_decoder_layers=1,dim_feedforward=2*width,
                dropout=0.,batch_first=True)
            self.head=nn.Linear(width,n_vocab)
        def forward(self,src,tgt):
            sx=self.encoder_embedding(src)+self.source_positions(
                torch.arange(src.size(1),device=src.device))[None,:,:]
            ty=self.decoder_embedding(tgt)+self.target_positions(
                torch.arange(tgt.size(1),device=tgt.device))[None,:,:]
            mask=nn.Transformer.generate_square_subsequent_mask(
                tgt.size(1),device=tgt.device)
            output=self.transformer(
                sx,ty,tgt_mask=mask,
                src_key_padding_mask=src.eq(PAD),
                tgt_key_padding_mask=tgt.eq(PAD),
                memory_key_padding_mask=src.eq(PAD))
            return self.head(output)
    return ScienceDecoder()

def prepare_tensors(rows,lookup):
    import torch
    x=[vectorize(r["question"],lookup,MAX_SOURCE) for r in rows]
    y=[vectorize(r["answer"],lookup,MAX_TARGET) for r in rows]
    return torch.tensor(x,dtype=torch.long),torch.tensor(y,dtype=torch.long)

def train(video_path,papers_path,outdir,epochs=35,seed=20261111):
    require(1<=epochs<=45 and isinstance(seed,int),"CPU_EPOCH_BUDGET")
    # Deliberately no "holdout" argument; cannot read clock reference labels.
    video,vsha=load_json(video_path)
    papers,psha=load_json(papers_path)
    rows=training_rows(video,papers)
    import torch
    from torch import nn
    from torch.utils.data import DataLoader,TensorDataset
    torch.set_num_threads(min(2,os.cpu_count() or 1))
    random.seed(seed);torch.manual_seed(seed)
    vocab=make_vocab(rows);lookup={token:i for i,token in enumerate(vocab)}
    model=build_model(len(vocab))
    optimizer=torch.optim.AdamW(model.parameters(),lr=0.002,weight_decay=0.003)
    src,target=prepare_tensors(rows,lookup)
    history=[]
    for epoch in range(epochs):
        model.train();total=0.;n=0
        g=torch.Generator().manual_seed(seed+epoch)
        for xb,yb in DataLoader(TensorDataset(src,target),batch_size=8,
                                shuffle=True,generator=g):
            optimizer.zero_grad(set_to_none=True)
            logits=model(xb,yb[:,:-1])
            loss=nn.functional.cross_entropy(
                logits.reshape(-1,logits.size(-1)),yb[:,1:].reshape(-1),
                ignore_index=PAD)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.)
            optimizer.step()
            total+=float(loss.item());n+=1
        if epoch==0 or epoch==epochs-1 or (epoch+1)%5==0:
            history.append({"epoch":epoch+1,"teacher_forced_loss":round(total/n,6)})
    outdir=Path(outdir);outdir.mkdir(parents=True,exist_ok=True)
    model_path=outdir/"r2b_candidate.pt"
    torch.save({"schema":SCHEMA,"model_state":model.state_dict(),"vocab":vocab,
                "width":64,"seed":seed,"epochs":epochs,
                "video_sha256":vsha,"papers_sha256":psha,
                "auto_deploy":False},model_path)
    result={"schema":"janus.tachyon.r2b.training_receipt.v1",
            "model":"tiny_encoder_decoder_transformer_from_scratch",
            "parameter_count":sum(p.numel() for p in model.parameters()),
            "training_pairs":len(rows),
            "training_source_families":len({r["family"] for r in rows}),
            "video_secondary_pairs":12,"primary_theory_pairs":12,
            "checkpoint_sha256":sha(model_path.read_bytes()),
            "video_sha256":vsha,"papers_sha256":psha,
            "teacher_forced_training_loss_history":history,
            "clock_lab_measurements_read_during_training":False,
            "clock_heldout_answers_read_during_training":False,
            "checkpoint_admitted":False,"model_deployed":False,
            "authority_delta":0}
    (outdir/"training_receipt.json").write_text(
        json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    return result

def generate(model,vocab,question,max_tokens=65):
    import torch
    lookup={v:i for i,v in enumerate(vocab)}
    src=torch.tensor([vectorize(question,lookup,MAX_SOURCE)])
    tgt=torch.tensor([[BOS]],dtype=torch.long)
    model.eval()
    with torch.no_grad():
        for _ in range(min(max_tokens,MAX_TARGET-2)):
            next_token=int(model(src,tgt)[:,-1,:].argmax(-1).item())
            if next_token==EOS:break
            tgt=torch.cat((tgt,torch.tensor([[next_token]])),dim=1)
    words=[vocab[t] for t in tgt[0].tolist()[1:] if t not in (PAD,BOS,EOS)]
    return " ".join(words).replace(" ,",",").replace(" .",".").replace(" :",":").replace(" ;",";")

def f1(generated,reference):
    a=Counter(tokens(generated));b=Counter(tokens(reference))
    matched=sum((a&b).values())
    prec=matched/max(1,sum(a.values()));rec=matched/max(1,sum(b.values()))
    return 0. if prec+rec==0 else 2*prec*rec/(prec+rec)

def retrieve(question,rows):
    q=set(tokens(question))
    return max(rows,key=lambda r:len(q&set(tokens(r["question"])))/
               (1+len(q|set(tokens(r["question"])))))["answer"]

def evaluate(checkpoint_path,holdout_path,video_path,papers_path,out_path):
    import torch
    torch.set_num_threads(min(2,os.cpu_count() or 1))
    state=torch.load(checkpoint_path,map_location="cpu",weights_only=True)
    require(state.get("schema")==SCHEMA and state.get("auto_deploy") is False,
            "CHECKPOINT_NOT_SAFE")
    video,vsha=load_json(video_path);papers,psha=load_json(papers_path)
    require(state["video_sha256"]==vsha and state["papers_sha256"]==psha,
            "CHECKPOINT_TRAIN_SOURCE_MISMATCH")
    rows=training_rows(video,papers)
    hold,hsha=load_json(holdout_path)
    require(hold.get("schema")=="janus.tachyon.r2b.source_family_holdout.v1" and
            hold.get("role")=="EVALUATION_ONLY_NEVER_TRAIN" and
            hold.get("benchmark_frozen_before_candidate_training") is True and
            hold.get("lab_measurement_results_training_allowed") is False,
            "HOLDOUT_NOT_FROZEN")
    groups=hold.get("source_groups",[])
    require(len(groups)==3 and {g.get("family") for g in groups}==HOLDOUT_FAMILIES,
            "HOLDOUT_SOURCE_FAMILIES_CHANGED")
    require(not ({r["family"] for r in rows}&HOLDOUT_FAMILIES),
            "TRAIN_EVAL_SOURCE_OVERLAP")
    vocab=state["vocab"];model=build_model(len(vocab),state["width"])
    model.load_state_dict(state["model_state"])
    cases=[]
    for group in groups:
        require(group.get("doi") in HOLDOUT_DOIS and
                group.get("url")=="https://doi.org/"+group["doi"] and
                len(group.get("questions",[]))==2 and
                len(group.get("required_mechanism_stems",[]))==3,
                "HOLDOUT_REFERENCE_INVENTORY_CHANGED")
        for question in group["questions"]:
            generated=generate(model,vocab,question)
            baseline=retrieve(question,rows)
            cover=sum(stem.lower() in generated.lower()
                      for stem in group["required_mechanism_stems"])/3
            cases.append({"source_family_id":group["family"],"question":question,
                          "generated_explanation":generated,
                          "reference_explanation":group["reference_answer"],
                          "neural_token_f1":round(f1(generated,group["reference_answer"]),6),
                          "lexical_retrieval_token_f1":round(f1(baseline,group["reference_answer"]),6),
                          "mechanism_stem_coverage_diagnostic":round(cover,6)})
    neural=sum(r["neural_token_f1"] for r in cases)/len(cases)
    baseline=sum(r["lexical_retrieval_token_f1"] for r in cases)/len(cases)
    coverage=sum(r["mechanism_stem_coverage_diagnostic"] for r in cases)/len(cases)
    result={"schema":"janus.tachyon.r2b.source_family_holdout_evaluation.v1",
            "model_checkpoint_sha256":sha(Path(checkpoint_path).read_bytes()),
            "heldout_source_sha256":hsha,
            "training_source_families":7,"test_source_families":3,"test_n":len(cases),
            "mean_neural_token_f1":round(neural,6),
            "mean_lexical_baseline_token_f1":round(baseline,6),
            "mean_mechanism_coverage_diagnostic":round(coverage,6),
            "lexical_overlap_is_not_scientific_validity":True,
            "independent_scientific_correctness_review":False,
            "independent_physical_time_prediction":False,
            "training_laboratory_data_used":False,
            "result_status":"RESEARCH_ONLY_HOLD_NO_EXTERNAL_BLIND_SCIENCE_REVIEW",
            "candidate_admitted":False,"model_deployed":False,"authority_delta":0,
            "individual_cases":cases}
    result["receipt_sha256"]=sha(canonical(result))
    output=Path(out_path);output.parent.mkdir(parents=True,exist_ok=True)
    with output.open("x",encoding="utf8") as f:
        json.dump(result,f,indent=2,ensure_ascii=False,sort_keys=True);f.write("\n")
    return result

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="mode",required=True)
    a=sub.add_parser("train");a.add_argument("--video",required=True)
    a.add_argument("--papers",required=True);a.add_argument("--outdir",required=True)
    a.add_argument("--epochs",type=int,default=35)
    b=sub.add_parser("evaluate");b.add_argument("--checkpoint",required=True)
    b.add_argument("--video",required=True);b.add_argument("--papers",required=True)
    b.add_argument("--holdout",required=True);b.add_argument("--out",required=True)
    z=ap.parse_args()
    if z.mode=="train":
        result=train(z.video,z.papers,z.outdir,z.epochs)
    else:result=evaluate(z.checkpoint,z.holdout,z.video,z.papers,z.out)
    print(json.dumps({k:v for k,v in result.items()
                      if k not in ("individual_cases","teacher_forced_training_loss_history")},
                     ensure_ascii=False,sort_keys=True))
if __name__=="__main__":main()
