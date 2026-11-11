"""Score a new R2C seed on the *public* R2D development cases.

The R2D fixture is known and is never an independent blind test. Evaluation
does not fit/fine-tune weights or read clock-lab measurement files.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from tachyon.science_generator import sha, require, build_model, generate
from tachyon.r2d_audit import read_json, numeric_in_answer

def evaluate(checkpoint,fixture,out):
    import torch
    torch.set_num_threads(2)
    state=torch.load(checkpoint,map_location="cpu",weights_only=True)
    require(state.get("schema")=="janus.tachyon.r2c.source_grounded_generator.v1"
            and state.get("auto_deploy") is False
            and state.get("holdout_data_in_training") is False,
            "R2H_CANDIDATE_SAFETY_GATE")
    fixture_obj=read_json(fixture)
    require(fixture_obj.get("status")==
            "PUBLIC_POSTHOC_DEVELOPMENT_ONLY_NOT_INDEPENDENT_BLIND",
            "NOT_PUBLIC_DEV_SET")
    cases=fixture_obj["cases"]
    net=build_model(len(state["vocab"]),state["width"])
    net.load_state_dict(state["model_state"])
    net.eval()
    records=[];correct=0;numeric_count=0
    for item in cases:
        generated=generate(net,state["vocab"],item["question"],max_tokens=44)
        rec={"case_id":item["case_id"],"kind":item["kind"],
             "model_text":generated,"unverified_language_model":True}
        if item["kind"]=="numeric":
            passed,_=numeric_in_answer(
                generated,item["expected_numeric"],item["absolute_tolerance"]
            )
            rec["numeric_text_hit"]=passed
            numeric_count+=1;correct+=int(passed)
        records.append(rec)
    result={
        "schema":"janus.tachyon.r2h.generator_public_dev.v1",
        "checkpoint_sha256":sha(Path(checkpoint).read_bytes()),
        "seed":state["seed"],
        "public_dev_fixture_sha256":sha(Path(fixture).read_bytes()),
        "numeric_count":numeric_count,"numeric_text_hits":correct,
        "all_generated_explanations_unverified":True,
        "independent_blind_test":False,"lab_clock_measurements_read":False,
        "scientifically_admitted":False,"auto_deploy":False,
        "records":records
    }
    output=Path(out);output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    return result

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--checkpoint",required=True)
    ap.add_argument("--fixture",required=True)
    ap.add_argument("--out",required=True)
    args=ap.parse_args()
    r=evaluate(args.checkpoint,args.fixture,args.out)
    print(json.dumps({k:r[k] for k in (
        "seed","checkpoint_sha256","numeric_count","numeric_text_hits",
        "independent_blind_test","scientifically_admitted")},sort_keys=True))
if __name__=="__main__":
    main()
