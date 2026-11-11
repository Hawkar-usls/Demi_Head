"""R35B: read only, frozen SI neural candidate question-only inference.

This tool accepts NO gold answer or salt; it cannot retrain or perform external
search. Question type and units are strict. Numeric answers are restricted to
the four educational formula families already seen during model training.
"""
from __future__ import annotations
import argparse,hashlib,json,math,re
from pathlib import Path

from tachyon.r35_typed_quantities import (
 FAMILIES,TRAIN_FAMILIES,UNTRAINED_FAMILY,
 MEASURED_SOURCE_CONTRACT,UNITS,normalize_case,quantity,
 canonical,digest,need
)
from tachyon.r35_typed_neural import (
 model,vector,HIDDEN,INPUT_WIDTH
)

FROZEN_CHECKPOINT_SHA="b631748974acd786f8ede06c5e016cbb5e41015f362e03fa3288b2c95d01234a"
SOURCE_MANIFEST_SHA="b959ac81019872a15c4487caba57749a1b8da90b19b2a096e8c0e7abc6e4d34a"
SCHEMA="janus.tachyon.r35b.typed_question_only.v1"
PREDICTIONS_SCHEMA="janus.tachyon.r35b.frozen_typed_predictions.v1"
ROOT_KEYS={"schema","candidate_checkpoint_sha256","case_count",
           "items","contains_gold_answers","questions_sha256"}
ITEM_KEYS={"case_id","task_kind","family","inputs","target_unit",
           "source_url","dataset_sha256"}

def validate(payload):
    need(isinstance(payload,dict) and set(payload)==ROOT_KEYS,
         "R35B_UNKNOWN_ROOT_OR_GOLD_FIELD")
    need(payload["schema"]==SCHEMA
         and payload["candidate_checkpoint_sha256"]==FROZEN_CHECKPOINT_SHA
         and payload["contains_gold_answers"] is False,
         "R35B_WRONG_VERSION_OR_CANDIDATE")
    body={k:v for k,v in payload.items() if k!="questions_sha256"}
    need(payload["questions_sha256"]==digest(body),
         "R35B_QUESTIONS_SHA_MISMATCH")
    items=payload["items"]
    need(isinstance(items,list) and 1<=len(items)<=300
         and type(payload["case_count"]) is int
         and payload["case_count"]==len(items),
         "R35B_QUESTION_COUNT")
    seen=set()
    for item in items:
        need(isinstance(item,dict) and
             set(item).issubset(ITEM_KEYS) and
             {"case_id","task_kind","family","inputs","target_unit",
              "source_url"}.issubset(item),
             "R35B_EXTRA_ITEM_FIELD_MAY_LEAK_GOLD")
        ident=item["case_id"]
        need(isinstance(ident,str) and
             re.fullmatch(r"[A-Za-z0-9_-]{6,80}",ident) is not None
             and ident not in seen,
             "R35B_INVALID_OR_DUPLICATE_CASE_ID")
        seen.add(ident)
        need(item["task_kind"] in ("NUMERIC","CONCEPTUAL","OOD"),
             "R35B_UNSUPPORTED_TASK_KIND")
        family=item["family"]
        need(family in FAMILIES or family in MEASURED_SOURCE_CONTRACT,
             "R35B_UNKNOWN_SCIENTIFIC_FAMILY")
        need(isinstance(item["inputs"],list),
             "R35B_BAD_INPUTS")
        if family in FAMILIES:
            need("dataset_sha256" not in item,
                 "R35B_TEXTBOOK_DATASET_SHA_SPOOF")
            normalize_case({k:item[k] for k in (
                "family","inputs","target_unit","source_url")})
        else:
            contract=MEASURED_SOURCE_CONTRACT[family]
            need(item.get("source_url")==contract["url"]
                 and item.get("dataset_sha256")==contract["sha256"],
                 "R35B_MEASURED_DATASET_IDENTITY_MISMATCH")
            need(len(item["inputs"])==1,
                 "R35B_MEASUREMENT_INPUT_COUNT")
            inp=quantity(item["inputs"][0],*contract["input"])
            target=item["target_unit"]
            need(target in UNITS and UNITS[target][1]==contract["output"][1],
                 "R35B_LAB_TARGET_UNIT_INCOMPATIBLE")
            if family=="BATTERY_SOC_VOLTAGE_CURVE":
                need(0<=inp.si<=1,"R35B_BATTERY_SOC_DOMAIN")
            else:
                need(0<=inp.si<1e-18,"R35B_MUON_MOMENTUM_DOMAIN")
    return payload["questions_sha256"]

def checkpoint_load(path):
    import torch
    torch.set_num_threads(1)
    digest_bytes=hashlib.sha256(Path(path).read_bytes()).hexdigest()
    need(digest_bytes==FROZEN_CHECKPOINT_SHA,"R35B_CHECKPOINT_SHA_MISMATCH")
    obj=torch.load(path,map_location="cpu",weights_only=True)
    need(obj.get("schema")=="janus.tachyon.r35.typed_si_checkpoint.v1"
         and obj.get("source_manifest_sha256")==SOURCE_MANIFEST_SHA
         and obj.get("trained_families")==list(TRAIN_FAMILIES)
         and obj.get("input_width")==INPUT_WIDTH
         and obj.get("hidden")==HIDDEN
         and obj.get("seed")==20261111
         and obj.get("new_laboratory_measurements_used_for_gradient") is False
         and obj.get("production_model_promotion") is False
         and obj.get("scientific_admission")=="HOLD",
         "R35B_CHECKPOINT_RESEARCH_PROVENANCE")
    net=model()
    net.load_state_dict(obj["weights"],strict=True)
    net.eval()
    return net,digest_bytes

def predict(payload,weights_path):
    qhash=validate(payload)
    net,ckhash=checkpoint_load(weights_path)
    import torch
    rows=[];forward=0;abstentions=0
    with torch.inference_mode():
        for item in payload["items"]:
            f=item["family"]
            if f not in TRAIN_FAMILIES or item["task_kind"]!="NUMERIC":
                rows.append({"case_id":item["case_id"],"kind":"abstain"})
                abstentions+=1
                continue
            case={k:item[k] for k in ("family","inputs","target_unit","source_url")}
            inp=torch.tensor([vector(case)],dtype=torch.float32)
            val=float(net(inp).item())*FAMILIES[f]["scale"]
            forward+=1
            need(math.isfinite(val),"R35B_MODEL_NAN")
            target_factor=UNITS[item["target_unit"]][0]
            physical_value=val/target_factor
            if physical_value<0 and f in (
              "SR_PROPER_TIME_RATIO","TWO_LEVEL_BORN_PROBABILITY","OHMIC_VOLTAGE"):
                rows.append({"case_id":item["case_id"],"kind":"abstain"})
                abstentions+=1
            else:
                rows.append({"case_id":item["case_id"],"kind":"numeric",
                             "value":physical_value,
                             "unit":item["target_unit"]})
    record={
      "schema":PREDICTIONS_SCHEMA,
      "candidate_checkpoint_sha256":ckhash,
      "questions_sha256":qhash,
      "items":rows,
      "research_execution":{
        "real_torch_forward_calls":forward,
        "abstentions":abstentions,
        "unexpected_new_family_neural_forward_calls":0,
        "trained_on_real_laboratory_measurements":False,
        "consulted_hidden_gold_answers":False,
        "model_weights_modified":False,
        "external_custodian_connected":False,
        "independent_blind_test_completed":False,
        "scientific_admission":"HOLD",
        "production_promotion":False
      }
    }
    record["receipt_sha256"]=digest(record)
    return record

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--questions-only",required=True)
    ap.add_argument("--frozen-checkpoint",required=True)
    ap.add_argument("--output",required=True)
    a=ap.parse_args()
    payload=json.loads(Path(a.questions_only).read_text(encoding="utf8"))
    result=predict(payload,a.frozen_checkpoint)
    dest=Path(a.output)
    need(not dest.exists(),"R35B_REFUSE_OVERWRITE")
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,
                               sort_keys=True,indent=2)+"\n",encoding="utf8")
    print(json.dumps({
      "model_forward_calls":result["research_execution"]["real_torch_forward_calls"],
      "abstentions":result["research_execution"]["abstentions"],
      "external_custodian_connected":False,
      "scientific_admission":"HOLD"
    },sort_keys=True))

if __name__=="__main__":main()
