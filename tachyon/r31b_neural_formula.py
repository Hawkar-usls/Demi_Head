"""TACHYON R3.1B: genuine bounded tiny neural regressor on curated formulas.

Training uses only TRAIN examples. CALIBRATION selects checkpoint.
PUBLIC_UNSEEN_DEV is read only *after* weights frozen; this is public author-
defined interpolation/extrapolation, NOT independent science or new physics.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,math,random
from pathlib import Path
from tachyon.r31_reference_gate import (
    validate_pack,make_rows,expected,sha,require,FAMILY_ORDER
)

SEED=20261111
STEPS=1200
LEARNING_RATE=.012
HIDDEN=24
EVAL_TOLERANCE=.015
CHECK_EVERY=20
SCHEMA="janus.tachyon.r31b.neural_formula_fit.v1"

def xy(rows):
    import torch
    features=[];targets=[]
    for row in rows:
        family=row["formula_id"]
        require(family in FAMILY_ORDER,"FORMULA_NOT_APPROVED")
        x=float(row["parameter"])
        features.append([x,1.0 if family==FAMILY_ORDER[0] else -1.0])
        targets.append(row["expected_numeric"])
    return torch.tensor(features,dtype=torch.float32),torch.tensor(
        targets,dtype=torch.float32).view(-1,1)

def build():
    import torch
    from torch import nn
    return nn.Sequential(
        nn.Linear(2,HIDDEN),nn.Tanh(),nn.Linear(HIDDEN,HIDDEN),nn.Tanh(),
        nn.Linear(HIDDEN,1),nn.Sigmoid()
    )

def train(pack_path,train_path,outdir):
    import torch
    from torch import nn
    torch.set_num_threads(1)
    pack=validate_pack(json.loads(Path(pack_path).read_text(encoding="utf8")))
    training=json.loads(Path(train_path).read_text(encoding="utf8"))
    require(training.get("schema")==
            "janus.tachyon.r31.formula_router_training_examples.v1",
            "UNAPPROVED_TRAINING_PACK_SCHEMA")
    require(training.get("source_reference_pack_sha256")==sha(pack),
            "TRAIN_PACK_HASH_DRIFT")
    require(training.get("receipt_sha256")==sha({
        k:v for k,v in training.items() if k!="receipt_sha256"
    }),"TRAIN_PACK_RECEIPT_TAMPER")
    require(training.get("split")=="train"
            and training.get("production_authorization") is False,
            "UNAUTHORIZED_TRAINING_SOURCE")
    train_rows=training["examples"]
    require(train_rows==make_rows(pack,"train"),
            "TRAIN_ROWS_NOT_EXACT_APPROVED_SPLIT")
    val_rows=make_rows(pack,"calibration")
    # public_unseen_dev rows intentionally NOT generated before weights freeze.
    require(len(train_rows)==16 and len(val_rows)==8,"SPLIT_SIZE")
    torch.manual_seed(SEED);random.seed(SEED)
    net=build()
    optimizer=torch.optim.AdamW(net.parameters(),lr=LEARNING_RATE,
                                weight_decay=.00001)
    x,y=xy(train_rows);vx,vy=xy(val_rows)
    best=None;best_validation=math.inf;best_step=0
    for step in range(1,STEPS+1):
        net.train()
        optimizer.zero_grad(set_to_none=True)
        prediction=net(x)
        loss=nn.functional.mse_loss(prediction,y)
        require(bool(torch.isfinite(loss)),"NONFINITE_LOSS")
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(),1)
        optimizer.step()
        if step%CHECK_EVERY==0 or step==1:
            net.eval()
            with torch.no_grad():
                validation=float(nn.functional.mse_loss(net(vx),vy))
            require(math.isfinite(validation),"NONFINITE_VALIDATION")
            if validation<best_validation:
                best_validation=validation;best_step=step
                best=copy.deepcopy(net.state_dict())
    require(best is not None,"NO_CALIBRATION_WINNER")
    net.load_state_dict(best)
    net.eval()
    output=Path(outdir);output.mkdir(parents=True,exist_ok=True)
    checkpoint=output/"r31b_math_neural_research_only.pt"
    require(not checkpoint.exists(),"REFUSE_WEIGHTS_OVERWRITE")
    torch.save({
        "schema":"janus.tachyon.r31b.neural_formula_candidate.v1",
        "model_state":net.state_dict(),
        "family_ids":list(FAMILY_ORDER),
        "source_pack_sha256":sha(pack),
        "train_only_receipt_sha256":training["receipt_sha256"],
        "seed":SEED,
        "best_calibration_step":best_step,
        "best_calibration_mse":best_validation,
        "hidden_width":HIDDEN,
        "future_holdout_ever_used_for_gradient":False,
        "production_promotion":False,
        "physical_retrocausality_proven":False,
    },checkpoint)
    checkpoint_sha=hashlib.sha256(checkpoint.read_bytes()).hexdigest()

    # Only AFTER weights are frozen and committed to disk: evaluate new values.
    test_rows=make_rows(pack,"public_unseen_dev")
    tx,ty=xy(test_rows)
    with torch.no_grad():
        estimated=net(tx).flatten().tolist()
    mean_family={}
    for family in FAMILY_ORDER:
        family_values=[r["expected_numeric"] for r in train_rows
                       if r["formula_id"]==family]
        mean_family[family]=sum(family_values)/len(family_values)
    cases=[]
    for row,pred in zip(test_rows,estimated):
        gold=row["expected_numeric"]
        prior=mean_family[row["formula_id"]]
        cases.append({
            "case_id":row["case_id"],
            "formula_id":row["formula_id"],
            "actual_formula_value":gold,
            "neural_prediction":pred,
            "neural_absolute_error":abs(pred-gold),
            "training_mean_baseline_prediction":prior,
            "training_mean_absolute_error":abs(prior-gold),
            "explicit_formula_error":0.0,
            "neural_within_0p015":abs(pred-gold)<=EVAL_TOLERANCE,
            "source_url":row["source_url"],
        })
    neural_mae=sum(x["neural_absolute_error"] for x in cases)/len(cases)
    baseline_mae=sum(x["training_mean_absolute_error"] for x in cases)/len(cases)
    numeric_score=sum(x["neural_within_0p015"] for x in cases)
    result={
        "schema":SCHEMA,
        "source_pack_sha256":sha(pack),
        "train_pack_receipt_sha256":training["receipt_sha256"],
        "checkpoint_sha256":checkpoint_sha,
        "seed":SEED,"steps_max":STEPS,"selected_calibration_step":best_step,
        "calibration_mse":best_validation,
        "train_cases":len(train_rows),"calibration_cases":len(val_rows),
        "public_author_test_cases":len(cases),
        "neural_mae":round(neural_mae,9),
        "train_mean_baseline_mae":round(baseline_mae,9),
        "explicit_formula_baseline_mae":0.0,
        "neural_within_0p015_count":numeric_score,
        "neural_beats_train_mean_on_public_dev":neural_mae<baseline_mae,
        "neural_outperforms_exact_formula":False,
        "test_first_read_after_checkpoint_written":True,
        "neural_weights_actually_trained":True,
        "train_gradient_used_public_unseen_labels":False,
        "independent_external_blind_assessor":False,
        "real_lab_measurements_used":False,
        "scientific_admission":"HOLD",
        "production_model_promotion":False,
        "no_real_time_retrocausal_signal":True,
        "cases":cases,
    }
    result["receipt_sha256"]=sha(result)
    report=output/"r31b_neural_math_public_dev_receipt.json"
    require(not report.exists(),"REFUSE_REPORT_OVERWRITE")
    report.write_text(json.dumps(result,ensure_ascii=False,indent=2,
                                 sort_keys=True)+"\n",encoding="utf8")
    return result

def main():
    p=argparse.ArgumentParser()
    for name in ("pack","train","outdir"):
        p.add_argument("--"+name,required=True)
    args=p.parse_args()
    res=train(args.pack,args.train,args.outdir)
    print(json.dumps({k:res[k] for k in (
        "train_cases","calibration_cases","public_author_test_cases",
        "neural_mae","train_mean_baseline_mae",
        "neural_within_0p015_count","neural_beats_train_mean_on_public_dev",
        "scientific_admission")},sort_keys=True))

if __name__=="__main__":main()
