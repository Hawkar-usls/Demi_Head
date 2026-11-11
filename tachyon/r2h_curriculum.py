"""TACHYON-R2H: bounded, synthetic, supervised *routing* learner.

This does not create a knowledgeable universal LLM. It learns a classifier
for evidence/formula routing from manually written prompts and provenanced
public source-card titles/questions. It NEVER consumes live web snippets,
atomic-clock holdout values or external evaluator keys. R2D is PUBLIC dev.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import random
import re

from tachyon.science_generator import ScienceHold, require, sha
from tachyon.r2c_grounded import new_source_rows
from tachyon.r2f_general_router import load_general_cards
from tachyon.r2d_audit import public_split

LABELS=("SR_FORMULA","BORN_FORMULA","THEORY_SOURCE",
        "NAS_SOURCE","GARDEN_SOURCE","PIZZA_SOURCE",
        "LIVE_SEARCH","ABSTAIN")
TRAIN_BETAS=("0.11","0.22","0.44","0.66","0.77","0.88")
TRAIN_RHOS=("0.10","0.25","0.35","0.55","0.70","0.95")
SR_TEMPLATES=(
    "Найди dτ/dt для часов с v/c={x} в специальной относительности",
    "Определи отношение собственного времени если v/c={x} для идеальных часов",
    "Чему равно замедление времени dτ/dt при v/c={x}",
    "Рассчитай ход инерциальных часов для v/c={x} по формуле Лоренца",
)
BORN_TEMPLATES=(
    "Вычисли P(0) для двухуровневого состояния если ρ00={x}",
    "Найди вероятность проекции на |0> при ρ00={x} по Борну",
    "Для плотности ρ00={x} какова вероятность P(0) измерения",
    "Оцени вероятность исхода ноль если ρ00={x} у кубита",
)
GENERAL_TEMPLATES={
    "NAS_SOURCE":(
        "Как снизить затраты на электричество моего NAS сервера",
        "Как экономить электроэнергию у сетевого хранилища NAS",
        "Помоги уменьшить потребление энергии накопителей в NAS",
        "Какие настройки экономии энергии выбрать для домашнего NAS",
        "Какой метод учета энергопотребления NAS подойдет лучше",
    ),
    "GARDEN_SOURCE":(
        "Как подобрать сорт зимней яблони в моем саду",
        "Как правильно посадить зимнюю яблоню и выбрать опылитель",
        "Какая яблоня подходит для хранения яблок зимой",
        "Как выбрать морозостойкий сорт яблони для сада",
        "Что учитывать для зимнего сорта яблони и подвоя",
    ),
    "PIZZA_SOURCE":(
        "Почему без дрожжей тесто пиццы почти не поднимается",
        "Как испечь пиццу если в тесте нет дрожжей",
        "Что делает разрыхлитель в бездрожжевом тесте пиццы",
        "Какую роль играет брожение при выпекании пиццы",
        "В чем причина плоской пиццы без дрожжей",
    ),
}
FRESH_TRAIN=(
    "Какие сегодня результаты матча футбольного чемпионата",
    "Кто выиграл сегодняшнюю футбольную игру",
    "Какие сейчас новости о результатах выборов",
    "Что произошло на стадионе вчера вечером",
    "Какая свежая новость появилась сегодня",
    "Что нового сейчас в международной ленте новостей",
)
NEGATIVE_TRAIN=(
    "Как сделать акварельный рисунок морского пейзажа",
    "Какая погода ожидается через несколько месяцев",
    "Расскажи историю создания древнего города",
    "Напиши песню о красивом осеннем вечере",
    "Как устроить ремонт деревянной лестницы",
    "Откуда возникло название редкой птицы",
    "Как приготовить компот из спелых ягод",
    "Чем отличается карась от других пресноводных рыб",
)
MAX_TOKENS=140
BUCKETS=4096
DIM=32
EPOCHS_MAX=35

def _ngrams(s):
    s=" "+re.sub(r"\s+"," ",s.casefold()).strip()+" "
    grams=[s[i:i+3] for i in range(max(0,len(s)-2))]
    grams+=re.findall(r"\w+",s)
    if not grams:return [1]
    ids=[]
    for item in grams[:MAX_TOKENS]:
        digest=hashlib.blake2s(item.encode("utf8"),digest_size=4).digest()
        ids.append(1+int.from_bytes(digest,"big")%BUCKETS)
    return ids

def vectorize(prompts):
    import torch
    arr=[]
    for q in prompts:
        ids=_ngrams(q)[:MAX_TOKENS]
        arr.append(ids+[0]*(MAX_TOKENS-len(ids)))
    return torch.tensor(arr,dtype=torch.long)

def build():
    from torch import nn
    class Router(nn.Module):
        def __init__(self):
            super().__init__()
            self.emb=nn.Embedding(BUCKETS+1,DIM,padding_idx=0)
            self.head=nn.Linear(DIM,len(LABELS))
        def forward(self,arr):
            emb=self.emb(arr)
            mask=arr.ne(0).unsqueeze(-1)
            pool=(emb*mask).sum(dim=1)/mask.sum(dim=1).clamp(min=1)
            return self.head(pool)
    return Router()

def training_examples(cards_path,general_path):
    cards,card_sha,rows=new_source_rows(cards_path)
    general=load_general_cards(general_path)
    gsha=sha(Path(general_path).read_bytes())
    require(len(general["cards"])==3 and len(rows)==12,"SOURCES_NOT_PREAPPROVED")
    examples=[]
    for label,values,templates in (
        ("SR_FORMULA",TRAIN_BETAS,SR_TEMPLATES),
        ("BORN_FORMULA",TRAIN_RHOS,BORN_TEMPLATES)
    ):
        for x in values:
            for tpl in templates:
                examples.append((tpl.format(x=x),label))
    # Only one question per scientific source for fitting, never hidden clocks.
    for source in cards["sources"]:
        examples.append((source["questions"][0],"THEORY_SOURCE"))
    card_ids={x["id"] for x in general["cards"]}
    require(card_ids=={"NAS_ENERGY_BASICS","APPLE_WINTER_CULTIVAR",
                       "PIZZA_WITHOUT_YEAST"},"GENERAL_SOURCE_INVENTORY")
    for label,prompts in GENERAL_TEMPLATES.items():
        examples.extend((q,label) for q in prompts)
    examples.extend((q,"LIVE_SEARCH") for q in FRESH_TRAIN)
    examples.extend((q,"ABSTAIN") for q in NEGATIVE_TRAIN)
    require(len(examples)==83, "TRAIN_CASE_COUNT")
    require(len({text for text,_ in examples})==len(examples),"DUPLICATE_TRAIN_QUESTION")
    return examples,card_sha,gsha

def r2d_public_dev_cases(path):
    qs,key=public_split(path)
    by_id={c["case_id"]:c for c in key["cases"]}
    labels=[]
    for c in qs["cases"]:
        gold=by_id[c["case_id"]]
        if gold["kind"]=="numeric":
            labels.append("SR_FORMULA" if gold["case_id"].startswith("speed") else "BORN_FORMULA")
        elif gold["kind"]=="conceptual":
            labels.append("THEORY_SOURCE")
        else:
            labels.append({"nas":"NAS_SOURCE","garden":"GARDEN_SOURCE",
                           "cooking":"PIZZA_SOURCE","football":"LIVE_SEARCH"}[gold["case_id"]])
    require(len(labels)==18,"R2D_DEV_COUNT")
    return [c["question"] for c in qs["cases"]],labels

def train(cards,general,dev_fixture,outdir,*,seed=111,epochs=25):
    require(seed in (117,223,337,449) and
            isinstance(epochs,int) and 1<=epochs<=EPOCHS_MAX,"RESOURCE_BUDGET")
    import torch
    from torch import nn
    torch.set_num_threads(min(2,os.cpu_count() or 1))
    train_rows,source_sha,general_sha=training_examples(cards,general)
    dev_q,dev_labels=r2d_public_dev_cases(dev_fixture)
    require(not set(dev_q)&{q for q,_ in train_rows},"PUBLIC_DEV_QUESTION_LEAK")
    random.seed(seed);torch.manual_seed(seed)
    model=build();optim=torch.optim.AdamW(model.parameters(),lr=0.018,weight_decay=.002)
    # Balance numeric, source and OOD categories by inverse training frequency.
    labels_i={label:i for i,label in enumerate(LABELS)}
    x=vectorize([r[0] for r in train_rows])
    y=torch.tensor([labels_i[r[1]] for r in train_rows])
    w=Counter(y.tolist())
    weights=torch.tensor([len(train_rows)/(len(w)*w[i]) for i in range(len(LABELS))],
                         dtype=torch.float)
    history=[]
    for ep in range(epochs):
        g=torch.Generator().manual_seed(seed+ep)
        perm=torch.randperm(len(train_rows),generator=g)
        model.train();total=0.0
        for idx in perm.split(16):
            optim.zero_grad(set_to_none=True)
            logits=model(x[idx])
            loss=nn.functional.cross_entropy(logits,y[idx],weight=weights)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.0)
            optim.step()
            total+=float(loss.item())
        if ep in (0,epochs-1):
            history.append({"epoch":ep+1,"sum_training_batch_loss":round(total,6)})
    model.eval()
    with torch.no_grad():
        probabilities=model(vectorize(dev_q)).softmax(-1)
    pred=probabilities.argmax(-1).tolist()
    correct=sum(LABELS[i]==gold for i,gold in zip(pred,dev_labels))
    unknown_risky=sum(
        LABELS[i] not in ("LIVE_SEARCH","ABSTAIN") for i,gold in zip(pred,dev_labels)
        if gold=="LIVE_SEARCH"
    )
    out=Path(outdir);out.mkdir(parents=True,exist_ok=True)
    checkpoint=out/"r2h_router_research.pt"
    torch.save({
        "schema":"janus.tachyon.r2h.routing_candidate.v1",
        "state_dict":model.state_dict(),"labels":LABELS,
        "seed":seed,"source_sha":source_sha,"general_sha":general_sha,
        "no_neural_factual_answer":True,"auto_deploy":False,
        "holdout_measurements_read":False
    },checkpoint)
    result={
        "schema":"janus.tachyon.r2h.router_receipt.v1",
        "checkpoint_sha256":sha(checkpoint.read_bytes()),
        "scientific_source_cards_sha256":source_sha,
        "general_source_cards_sha256":general_sha,
        "public_dev_fixture_sha256":sha(Path(dev_fixture).read_bytes()),
        "seed":seed,"epochs":epochs,"train_examples":len(train_rows),
        "train_label_count":dict(Counter(y for _,y in train_rows)),
        "public_dev_n":len(dev_q),"public_dev_correct_routes":correct,
        "public_dev_route_accuracy":round(correct/len(dev_q),4),
        "public_dev_live_false_positive":unknown_risky,
        "per_case":[{"case_id":idx,"expected_route":gold,"predicted_route":LABELS[pred[idx]],
                     "confidence":round(float(probabilities[idx,pred[idx]]),4)}
                    for idx,gold in enumerate(dev_labels)],
        "training_loss":history,
        "all_answers_source_or_formula_gated":True,
        "scientific_correctness_verified":False,
        "independent_blind_test":False,
        "main_or_ocean_modified":False,
        "scientifically_admitted":False,"auto_deployed":False,
        "status":"PUBLIC_DEVELOPMENT_ROUTING_ONLY_HOLD"
    }
    (out/"receipt.json").write_text(json.dumps(result,indent=2,sort_keys=True,
                                              ensure_ascii=False)+"\n",encoding="utf8")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--cards",required=True)
    ap.add_argument("--general",required=True)
    ap.add_argument("--dev",required=True)
    ap.add_argument("--outdir",required=True)
    ap.add_argument("--seed",type=int,required=True)
    ap.add_argument("--epochs",type=int,default=25)
    args=ap.parse_args()
    r=train(args.cards,args.general,args.dev,args.outdir,
            seed=args.seed,epochs=args.epochs)
    print(json.dumps({k:r[k] for k in (
        "seed","train_examples","public_dev_n","public_dev_correct_routes",
        "public_dev_route_accuracy","public_dev_live_false_positive",
        "scientifically_admitted")},sort_keys=True))

if __name__=="__main__":
    main()
