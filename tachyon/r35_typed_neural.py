"""R3.5 reproducible dimension-aware neural surrogate for textbook-only families.

No GDELT, open laboratory rows, blind keys, private questions or unreviewed
source data are trainable. This explicitly trained surrogate NEVER overrides
an exact unit-checked mathematical formula in deployment.
"""
from __future__ import annotations
import argparse,copy,hashlib,json,math
from pathlib import Path
from collections import defaultdict

from tachyon.r35_typed_quantities import (
 FAMILIES,TRAIN_FAMILIES,UNTRAINED_FAMILY,ROLES,ROLE_SCALE,
 canonical,digest,need,normalize_case,exact,check_splits,
 dataset,load_manifest,source_manifest_check
)

SCHEMA="janus.tachyon.r35.typed_si_research_training_result.v1"
SEEDS=(20261111,20261112)
HIDDEN=48
STEPS=1200
LR=.009
CAL_EVERY=20
INPUT_WIDTH=2*(1+4+len(ROLES))+len(TRAIN_FAMILIES)+4

def vector(case):
    family,qs,_=normalize_case(case)
    need(family in TRAIN_FAMILIES,"R35_UNSEEN_FAMILY_CANNOT_BE_MODEL_INPUT")
    out=[]
    for idx in range(2):
        if idx<len(qs):
            q=qs[idx]
            need(q.name in ROLE_SCALE,"R35_UNKNOWN_PHYSICAL_ROLE")
            out.append(q.si/ROLE_SCALE[q.name])
            out.extend(float(x)/4 for x in q.dims)
            out.extend(float(r==q.name) for r in ROLES)
        else:
            out.extend([0.]*(1+4+len(ROLES)))
    out.extend(float(family==f) for f in TRAIN_FAMILIES)
    out.extend(float(x)/4 for x in FAMILIES[family]["target"])
    need(len(out)==INPUT_WIDTH and all(math.isfinite(v) for v in out),
         "R35_BAD_MODEL_VECTOR")
    return out

def tensors(rows):
    import torch
    xx=[];yy=[]
    for row in rows:
        need(row["label_type"]=="AUTHOR_TEXTBOOK_EQUATION_NOT_LAB_DATA"
             and row["train_family_eligible"] is True,
             "R35_GRADIENT_SOURCE_NOT_AUTHORIZED")
        family=row["case"]["family"]
        xx.append(vector(row["case"]))
        yy.append([row["target_value"]/FAMILIES[family]["scale"]])
    return torch.tensor(xx,dtype=torch.float32),torch.tensor(
        yy,dtype=torch.float32)

def model():
    from torch import nn
    return nn.Sequential(
        nn.Linear(INPUT_WIDTH,HIDDEN),nn.Tanh(),
        nn.Linear(HIDDEN,HIDDEN),nn.Tanh(),
        nn.Linear(HIDDEN,1))

def one_candidate(seed,training,calibration,output,manifest_hash):
    import torch
    from torch import nn
    torch.manual_seed(seed)
    net=model()
    optimizer=torch.optim.AdamW(net.parameters(),lr=LR,weight_decay=.0001)
    x,y=tensors(training)
    vx,vy=tensors(calibration)
    champion=None;best=math.inf;best_step=0
    for step in range(1,STEPS+1):
        net.train();optimizer.zero_grad(set_to_none=True)
        val=net(x)
        loss=nn.functional.mse_loss(val,y)
        need(bool(torch.isfinite(loss)),"R35_NONFINITE_TRAIN_LOSS")
        loss.backward()
        nn.utils.clip_grad_norm_(net.parameters(),1.)
        optimizer.step()
        if step%CAL_EVERY==0 or step==1:
            net.eval()
            with torch.inference_mode():
                cal=float(nn.functional.mse_loss(net(vx),vy))
            need(math.isfinite(cal),"R35_NONFINITE_CALIBRATION_LOSS")
            if cal<best:
                best=cal;best_step=step
                champion=copy.deepcopy(net.state_dict())
    need(champion is not None,"R35_NO_CALIBRATED_MODEL")
    ck=Path(output)/f"r35_typed_neural_seed_{seed}.pt"
    need(not ck.exists(),"R35_CHECKPOINT_OVERWRITE_DENIED")
    torch.save({
        "schema":"janus.tachyon.r35.typed_si_checkpoint.v1",
        "weights":champion,
        "trained_families":list(TRAIN_FAMILIES),
        "input_width":INPUT_WIDTH,
        "hidden":HIDDEN,
        "seed":seed,"selected_calibration_step":best_step,
        "calibration_mse":best,
        "source_manifest_sha256":manifest_hash,
        "train_label_type":"AUTHOR_DERIVED_TEXTBOOK_FORMULAS_ONLY",
        "new_physics_family_training":False,
        "new_laboratory_measurements_used_for_gradient":False,
        "production_model_promotion":False,
        "scientific_admission":"HOLD",
    },ck)
    return {
        "seed":seed,
        "checkpoint_path":str(ck),
        "checkpoint_sha256":hashlib.sha256(ck.read_bytes()).hexdigest(),
        "best_calibration_step":best_step,
        "best_calibration_mse":best,
    }

def score_checkpoint(checkpoint,rows):
    import torch
    entry=torch.load(checkpoint,map_location="cpu",weights_only=True)
    need(entry.get("schema")=="janus.tachyon.r35.typed_si_checkpoint.v1"
         and entry.get("trained_families")==list(TRAIN_FAMILIES)
         and entry.get("production_model_promotion") is False
         and entry.get("scientific_admission")=="HOLD",
         "R35_CHECKPOINT_TRUST_GATE")
    net=model();net.load_state_dict(entry["weights"],strict=True);net.eval()
    outputs=[]
    with torch.inference_mode():
        for row in rows:
            family=row["case"]["family"]
            value=row["target_value"]
            if family not in TRAIN_FAMILIES:
                outputs.append({
                    "case_id":row["case_id"],"family":family,
                    "decision":"ABSTAIN_UNTRAINED_PHYSICS_FAMILY",
                    "neural_prediction":None,"exact_formula_expected":value,
                    "source":row["case"]["source_url"],
                    "new_family_numeric_skill_proven":False})
                continue
            features=torch.tensor([vector(row["case"])],dtype=torch.float32)
            predicted=float(net(features).item())*FAMILIES[family]["scale"]
            need(math.isfinite(predicted),"R35_NONFINITE_INFERENCE")
            outputs.append({
                "case_id":row["case_id"],"family":family,
                "decision":"NEURAL_SURROGATE_ONLY_EXACT_FORMULA_HAS_PRIORITY",
                "neural_prediction":predicted,"exact_formula_expected":value,
                "absolute_error":abs(predicted-value),
                "source":row["case"]["source_url"],
                "new_family_numeric_skill_proven":False})
    return outputs

def experiment(manifest_path,output_dir):
    import torch
    torch.set_num_threads(1)
    doc=load_manifest(manifest_path)
    split_counts=check_splits(doc)
    output=Path(output_dir);output.mkdir(parents=True,exist_ok=True)
    need(not any(output.iterdir()),"R35_OUTPUT_DIR_NOT_EMPTY")
    training=dataset(doc,"train")
    calibration=dataset(doc,"calibration")
    # Crucial: dev labels are not accessed until both models are frozen.
    record_hash=digest(doc)
    candidates=[
        one_candidate(seed,training,calibration,output,record_hash)
        for seed in SEEDS
    ]
    winner=min(candidates,key=lambda z:(z["best_calibration_mse"],z["seed"]))
    # No model weights change after this step, no heldout score used for selection.
    development=dataset(doc,"public_dev")
    scored=score_checkpoint(winner["checkpoint_path"],development)
    mean_values=defaultdict(list)
    for x in training:
        mean_values[x["case"]["family"]].append(x["target_value"])
    means={family:sum(xs)/len(xs) for family,xs in mean_values.items()}
    sums=defaultdict(list);mean_errors=defaultdict(list)
    for case in scored:
        if case["neural_prediction"] is None:continue
        f=case["family"]
        sums[f].append(case["absolute_error"])
        mean_errors[f].append(abs(case["exact_formula_expected"]-means[f]))
    byfamily={}
    for family,values in sums.items():
        byfamily[family]={
            "n":len(values),
            "neural_mae_SI":sum(values)/len(values),
            "mean_train_constant_mae_SI":sum(mean_errors[family])/len(values),
            "exact_textbook_formula_mae_SI":0.0,
            "worst_neural_absolute_error_SI":max(values)}
    total=sum(len(x) for x in sums.values())
    neural_mae=sum(sum(x) for x in sums.values())/total
    const_mae=sum(sum(x) for x in mean_errors.values())/total
    untrained=[x for x in scored if x["neural_prediction"] is None]
    need(total==24 and len(untrained)==6,"R35_FAMILY_COVERAGE_DRIFT")
    research={
        "schema":SCHEMA,
        "source_manifest_sha256":record_hash,
        "split_counts":split_counts,
        "frozen_checkpoint_before_public_dev_evaluation":True,
        "candidate_selection_criterion":"CALIBRATION_MSE_ONLY_NOT_PUBLIC_DEV",
        "bounded_cpu_seeds":list(SEEDS),"max_steps_per_seed":STEPS,
        "candidate_checkpoints":candidates,
        "selected_seed":winner["seed"],
        "selected_candidate_sha256":winner["checkpoint_sha256"],
        "dimension_aware_input_width":INPUT_WIDTH,
        "trained_family_count":len(TRAIN_FAMILIES),
        "public_dev_trained_family_cases":total,
        "public_dev_withheld_new_family_cases":len(untrained),
        "new_family_abstentions":len(untrained),
        "new_family_numeric_predictions":0,
        "new_family_generalization_proven":False,
        "public_dev_neural_mean_absolute_error_SI_mixed_dimensions_is_not_a_comparable_global_metric":neural_mae,
        "public_dev_train_mean_absolute_error_SI_mixed_dimensions_is_not_a_comparable_global_metric":const_mae,
        "exact_formula_baseline_error":0.0,
        "per_family_SI_metrics":byfamily,
        "observations":scored,
        "training_data_kind":"AUTHOR_TEXTBOOK_FORMULA_DERIVED_ONLY",
        "measured_lab_rows_used_as_gradient_labels":False,
        "independent_blind_assessor_present":False,
        "scientific_admission":"HOLD",
        "production_promotion":False
    }
    research["receipt_sha256"]=digest(research)
    path=output/"r35_typed_physics_public_development_result.json"
    need(not path.exists(),"R35_RECEIPT_OVERWRITE")
    path.write_text(json.dumps(research,ensure_ascii=False,sort_keys=True,
                               indent=2)+"\n",encoding="utf8")
    return research

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",required=True)
    ap.add_argument("--output-dir",required=True)
    args=ap.parse_args()
    r=experiment(args.manifest,args.output_dir)
    print(json.dumps({
        "selected_seed":r["selected_seed"],
        "trained_families":r["trained_family_count"],
        "per_family_SI_metrics":r["per_family_SI_metrics"],
        "new_family_numeric_predictions":r["new_family_numeric_predictions"],
        "new_family_abstentions":r["new_family_abstentions"],
        "scientific_admission":r["scientific_admission"],
    },sort_keys=True))

if __name__=="__main__":main()
