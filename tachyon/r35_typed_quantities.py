"""JANUS TACHYON R3.5: typed SI quantities, source families and fail-closed gates.

All permitted labels are author-generated textbook formula values. Real measured
Super-K/Offenburg records may be represented as typed metadata but are NEVER
automatically admitted as neural training labels based on source hashes alone.
"""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path

SCHEMA="janus.tachyon.r35.author_verified_formula_sandbox.v1"
M,L,T,I=0,1,2,3
D0=(0,0,0,0)
DA=(0,0,0,1)
DOHM=(1,2,-3,-2)
DV=(1,2,-3,-1)
DS=(0,0,1,0)
DL=(0,1,0,0)
DVEL=(0,1,-1,0)
DW=(1,2,-3,0)
DP=(1,1,-1,0)  # linear momentum; MeV/c, NOT energy
# factor to SI base; no implicit conversion on unknown units
UNITS={
 "1":(1.,D0),"%":(.01,D0),
 "A":(1.,DA),"mA":(.001,DA),
 "Ω":(1.,DOHM),"kΩ":(1000.,DOHM),
 "V":(1.,DV),"mV":(.001,DV),
 "s":(1.,DS),"ms":(.001,DS),"µs":(1e-6,DS),
 "m":(1.,DL),"cm":(.01,DL),
 "m/s":(1.,DVEL),"km/h":(1/3.6,DVEL),
 "W":(1.,DW),
 "MeV/c":(1.602176634e-13/299792458.,DP)
}
FAMILIES={
 "SR_PROPER_TIME_RATIO":{"inputs":(("beta",D0),),"target":D0,"target_unit":"1","scale":1.0,"source":"https://openstax.org/books/university-physics-volume-3/pages/5-3-time-dilation"},
 "TWO_LEVEL_BORN_PROBABILITY":{"inputs":(("rho00",D0),),"target":D0,"target_unit":"1","scale":1.0,"source":"https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements"},
 "OHMIC_VOLTAGE":{"inputs":(("current",DA),("resistance",DOHM)),"target":DV,"target_unit":"V","scale":20.0,"source":"https://openstax.org/books/college-physics-2e/pages/20-2-ohms-law-resistance-and-simple-circuits"},
 "CONSTANT_VELOCITY_DISPLACEMENT":{"inputs":(("velocity",DVEL),("duration",DS)),"target":DL,"target_unit":"m","scale":50.0,"source":"https://openstax.org/books/college-physics-2e/pages/2-3-time-velocity-and-speed"},
 "ELECTRIC_POWER_IV":{"inputs":(("current",DA),("voltage",DV)),"target":DW,"target_unit":"W","scale":40.0,"source":"https://openstax.org/books/college-physics-2e/pages/20-section-summary"}
}
TRAIN_FAMILIES=tuple(FAMILIES)[:4]
UNTRAINED_FAMILY="ELECTRIC_POWER_IV"
SOURCE_RESTRICTIONS={
 "https://zenodo.org/records/15081911":"MUON_STOP_DECAY_AND_NEUTRON_CAPTURE",
 "https://zenodo.org/records/13142016":"BATTERY_SOC_VOLTAGE_CURVE"
}
ROLE_SCALE={"beta":1.,"rho00":1.,"current":2.,"resistance":20.,
            "velocity":8.,"duration":10.,"voltage":20.}
ROLES=tuple(ROLE_SCALE)
# Explicit developer-crafted combinations; train, calibration, public developer
# cases have disjoint tuples. No independent / secret blinded answers included.
PAIR_VALUES={
 "SR_PROPER_TIME_RATIO":{
  "train":[(.03,),(.09,),(.17,),(.25,),(.33,),(.41,),(.50,),(.59,),(.67,),(.74,),(.81,),(.86,)],
  "calibration":[(.14,),(.37,),(.63,),(.89,)],
  "public_dev":[(.20,),(.46,),(.72,),(.84,),(.92,),(.96,)]},
 "TWO_LEVEL_BORN_PROBABILITY":{
  "train":[(.02,),(.10,),(.18,),(.26,),(.34,),(.42,),(.50,),(.58,),(.66,),(.74,),(.82,),(.90,)],
  "calibration":[(.07,),(.31,),(.57,),(.85,)],
  "public_dev":[(.15,),(.39,),(.61,),(.79,),(.93,),(.98,)]},
 "OHMIC_VOLTAGE":{
  "train":[(.15,2.),(.30,4.),(.45,7.),(.60,10.),(.75,13.),(.90,16.),
           (1.05,19.),(1.20,22.),(1.35,4.),(1.50,8.),(1.65,11.),(1.80,15.)],
  "calibration":[(.25,6.),(.70,9.),(1.10,12.),(1.55,17.)],
  "public_dev":[(.35,5.),(.55,14.),(.85,18.),(1.25,9.),(1.70,12.),(1.95,20.)]},
 "CONSTANT_VELOCITY_DISPLACEMENT":{
  "train":[(.8,1.),(1.2,2.),(1.6,3.),(2.0,4.),(2.4,5.),(2.8,6.),
           (3.2,7.),(3.6,8.),(4.0,2.),(4.4,3.),(4.8,5.),(5.2,7.)],
  "calibration":[(1.0,6.),(2.3,7.),(3.8,4.),(5.0,9.)],
  "public_dev":[(1.5,2.5),(2.7,4.5),(3.3,6.5),(4.6,6.),(5.5,8.),(6.2,9.)]},
 "ELECTRIC_POWER_IV":{
  "public_dev":[(.5,3.),(.8,5.),(1.2,8.),(1.6,10.),(2.,12.),(2.4,16.)]}
}

def need(valid,msg):
    if not valid: raise ValueError(msg)

def canonical(obj):
    return json.dumps(obj,sort_keys=True,ensure_ascii=False,
                      separators=(",",":"),allow_nan=False).encode("utf8")

def digest(obj):return hashlib.sha256(canonical(obj)).hexdigest()

@dataclass(frozen=True)
class Quantity:
    name:str
    si:float
    dims:tuple
    original_unit:str

def quantity(row, expected_name, expected_dim):
    need(isinstance(row,dict) and set(row)=={"name","value","unit"},
         "R35_QUANTITY_SCHEMA")
    need(row["name"]==expected_name,"R35_QUANTITY_ROLE_MISMATCH")
    unit=row["unit"]
    need(isinstance(unit,str) and unit in UNITS,"R35_UNKNOWN_UNIT")
    factor,dims=UNITS[unit]
    need(dims==expected_dim,"R35_DIMENSION_MISMATCH")
    value=row["value"]
    need(type(value) in (int,float) and math.isfinite(value),
         "R35_NONFINITE_OR_NONNUMERIC_QUANTITY")
    val=value*factor
    need(math.isfinite(val),"R35_NONFINITE_SI")
    return Quantity(expected_name,val,dims,unit)

def normalize_case(case):
    need(isinstance(case,dict) and
         set(case)=={"family","inputs","target_unit","source_url"},
         "R35_CASE_SCHEMA")
    fam=case["family"]
    need(isinstance(fam,str) and fam in FAMILIES,"R35_UNTRAINED_FAMILY")
    spec=FAMILIES[fam]
    need(case["source_url"]==spec["source"],"R35_SOURCE_SPOOF")
    indata=case["inputs"]
    need(isinstance(indata,list) and len(indata)==len(spec["inputs"]),
         "R35_NUMBER_OF_INPUTS")
    q=[quantity(val,name,dim) for val,(name,dim) in
       zip(indata,spec["inputs"])]
    unit=case["target_unit"]
    need(isinstance(unit,str) and unit in UNITS,"R35_UNKNOWN_TARGET_UNIT")
    need(UNITS[unit][1]==spec["target"],"R35_TARGET_DIMENSION_MISMATCH")
    x=[p.si for p in q]
    if fam=="SR_PROPER_TIME_RATIO":
        need(0<=x[0]<1,"R35_SR_BETA_OUT_OF_DOMAIN")
    elif fam=="TWO_LEVEL_BORN_PROBABILITY":
        need(0<=x[0]<=1,"R35_BORN_PROBABILITY_OUT_OF_DOMAIN")
    elif fam=="OHMIC_VOLTAGE":
        need(0<=x[0]<=5 and .001<=x[1]<=1e4,
             "R35_OHMIC_DOMAIN_OR_ZERO_RESISTANCE")
    elif fam=="CONSTANT_VELOCITY_DISPLACEMENT":
        need(0<=x[0]<=150 and 0<=x[1]<=3600,
             "R35_KINEMATIC_DOMAIN")
    else:
        need(0<=x[0]<=5 and 0<=x[1]<=300,
             "R35_ELECTRIC_POWER_DOMAIN")
    return fam,q,unit

def exact(case):
    fam,qs,output_unit=normalize_case(case)
    vals=[q.si for q in qs]
    if fam=="SR_PROPER_TIME_RATIO":result=math.sqrt(1-vals[0]**2)
    elif fam=="TWO_LEVEL_BORN_PROBABILITY":result=vals[0]
    elif fam=="OHMIC_VOLTAGE":result=vals[0]*vals[1]
    elif fam=="CONSTANT_VELOCITY_DISPLACEMENT":result=vals[0]*vals[1]
    elif fam=="ELECTRIC_POWER_IV":result=vals[0]*vals[1]
    else:raise ValueError("R35_NO_EXACT_BASELINE")
    return result/UNITS[output_unit][0]

def source_manifest_check(doc):
    need(isinstance(doc,dict) and doc.get("schema")==SCHEMA,
         "R35_MANIFEST_SCHEMA")
    need(doc.get("research_authorization")=="MATH_SANDBOX_ONLY_NO_UNREVIEWED_LAB"
         and doc.get("model_training_permitted_for_educational_sandbox") is True
         and doc.get("curated_external_laboratory_data_training_permitted") is False
         and doc.get("scientific_admission")=="HOLD"
         and doc.get("production_promotion") is False
         and doc.get("independent_blind_evaluation") is False,
         "R35_SCIENTIFIC_TRAINING_PROMOTION_DENIED")
    refs=doc.get("source_references")
    need(isinstance(refs,list) and len(refs)==len(FAMILIES)
         and {e.get("family"):e.get("url") for e in refs}==
             {family:spec["source"] for family,spec in FAMILIES.items()},
         "R35_SOURCE_FAMILY_REFERENCE_MISMATCH")
    for r in refs:
        family=r["family"]
        need(r.get("target_unit")==FAMILIES[family]["target_unit"],
             "R35_REFERENCE_TARGET_UNIT")
        need(r.get("training_lane")==(
             "WITHHELD_NEW_FAMILY_TEST_ONLY" if family==UNTRAINED_FAMILY
             else "AUTHOR_MATH_ONLY"),"R35_UNEXPECTED_SOURCE_ADMISSION")
    p=doc.get("split_blueprint",{})
    need(p.get("seed")==20261111
         and p.get("experimental_train_families")==list(TRAIN_FAMILIES)
         and p.get("heldout_untrained_family")==UNTRAINED_FAMILY
         and p.get("all_examples_generated_from_source_formula_by_code") is True
         and p.get("never_reuse_hidden_external_blind_labels") is True,
         "R35_BAD_SPLIT_BLUEPRINT")
    lab=doc.get("known_public_lab_measurements",{})
    need(lab.get("allowed_as_neural_gradient_labels") is False
         and lab.get("curator_approval_receipt_present") is False,
         "R35_LAB_DATA_NOT_AUTHORIZED")
    return doc

def refuse_lab_training(record):
    """No lab training allowed from hashes/DOI alone. No signed curator has approved."""
    need(isinstance(record,dict),"R35_LAB_RECORD_SCHEMA")
    url=record.get("dataset_url")
    need(url in SOURCE_RESTRICTIONS,"R35_LAB_UNRECOGNIZED_SOURCE")
    need(record.get("source_family")==SOURCE_RESTRICTIONS[url],
         "R35_LAB_FAMILY_SPOOF")
    # Explicitly never promote a mere integrity receipt into training approval.
    raise ValueError("R35_NO_INDEPENDENT_CURATOR_OR_RIGHTS_APPROVAL")

def case_from_si(fam,vals,variant):
    spec=FAMILIES[fam]
    unit_options={
      "beta":("1","%"),"rho00":("1","%"),
      "current":("A","mA"),"resistance":("Ω","kΩ"),
      "velocity":("m/s","km/h"),"duration":("s","ms"),
      "voltage":("V","mV")
    }
    inputs=[]
    for val,(role,dim) in zip(vals,spec["inputs"]):
        unit=unit_options[role][variant%2]
        value=val/UNITS[unit][0]
        inputs.append({"name":role,"value":value,"unit":unit})
    target_unit=spec["target_unit"]
    return {"family":fam,"inputs":inputs,"target_unit":target_unit,
            "source_url":spec["source"]}

def dataset(doc,split):
    source_manifest_check(doc)
    need(split in ("train","calibration","public_dev"),"R35_UNKNOWN_SPLIT")
    rows=[]
    for fam in (list(TRAIN_FAMILIES)+
                ([UNTRAINED_FAMILY] if split=="public_dev" else [])):
        values=PAIR_VALUES[fam].get(split,[])
        for j,coords in enumerate(values):
            row=case_from_si(fam,coords,j)
            target=exact(row)
            rows.append({
                "case_id":f"r35-{split}-{fam}-{j:02d}",
                "split":split,
                "case":row,
                "target_value":target,
                "target_unit":row["target_unit"],
                "label_type":"AUTHOR_TEXTBOOK_EQUATION_NOT_LAB_DATA",
                "train_family_eligible":fam in TRAIN_FAMILIES
            })
    need(len({x["case_id"] for x in rows})==len(rows),"R35_DUPLICATE_CASE")
    return rows

def check_splits(doc):
    seen=set()
    result={}
    for name in ("train","calibration","public_dev"):
        rows=dataset(doc,name)
        for x in rows:
            fam=x["case"]["family"]
            q=normalize_case(x["case"])[1]
            fingerprint=(fam,tuple(round(v.si,10) for v in q))
            need(fingerprint not in seen,"R35_SPLIT_PARAMETER_LEAK")
            seen.add(fingerprint)
            need(x["label_type"]=="AUTHOR_TEXTBOOK_EQUATION_NOT_LAB_DATA",
                 "R35_FAKE_MEASURED_LABEL")
        result[name]=len(rows)
    need(result=={"train":48,"calibration":16,"public_dev":30},
         "R35_SPLIT_COUNTS_DRIFT")
    need(all(x["case"]["family"]!=UNTRAINED_FAMILY
             for name in ("train","calibration")
             for x in dataset(doc,name)),"R35_WITHHELD_FAMILY_LEAK")
    return result

MEASURED_SOURCE_CONTRACT={
 "MUON_STOP_DECAY_AND_NEUTRON_CAPTURE":{
   "url":"https://zenodo.org/records/15081911",
   "sha256":"b6bb10270e6c604935b47687293470caeafd01172288170d83349043566cd05a",
   "input":("electron_momentum",DP),
   "output":("tagged_delay",DS)
 },
 "BATTERY_SOC_VOLTAGE_CURVE":{
   "url":"https://zenodo.org/records/13142016",
   "sha256":"d7dd665e6d356721ceb08bbbbd3e9f7401bc3cfac0a1b3fbea8df74637a506ea",
   "input":("soc",D0),
   "output":("ocv",DV)
 }
}

def typed_lab_observation(record):
    """Represent measured physics with units/provenance, NEVER grant gradient rights.

    Does not fetch public observations or copy underlying licensed files.
    Pure unit converter with exact source-id and dataset SHA identity.
    """
    need(isinstance(record,dict) and
         set(record)=={"family","dataset_url","dataset_sha256",
                       "observation_id","input","measured_target",
                       "original_license_review_complete",
                       "independent_curator_approved_for_training"},
         "R35_LAB_OBSERVATION_SCHEMA")
    fam=record["family"]
    need(fam in MEASURED_SOURCE_CONTRACT,"R35_LAB_FAMILY_UNKNOWN")
    expected=MEASURED_SOURCE_CONTRACT[fam]
    need(record["dataset_url"]==expected["url"]
         and record["dataset_sha256"]==expected["sha256"],
         "R35_LAB_DATASET_SHA_OR_ORIGIN_MISMATCH")
    need(isinstance(record["observation_id"],str) and
         3<=len(record["observation_id"])<=100,
         "R35_LAB_OBSERVATION_ID_INVALID")
    need(record["original_license_review_complete"] is False
         and record["independent_curator_approved_for_training"] is False,
         "R35_UNSUPPORTED_TRAINING_APPROVAL_CLAIM")
    inp=quantity(record["input"],*expected["input"])
    output=quantity(record["measured_target"],*expected["output"])
    if fam=="BATTERY_SOC_VOLTAGE_CURVE":
        need(0<=inp.si<=1.0 and 0<output.si<10,
             "R35_BATTERY_SOC_VOLTAGE_DOMAIN")
    else:
        need(inp.si>=0 and 0<=output.si<=0.001,
             "R35_MUON_MOMENTUM_DELAY_DOMAIN")
    return {
       "family":fam,
       "original_dataset_url":record["dataset_url"],
       "original_dataset_sha256":record["dataset_sha256"],
       "observation_id":record["observation_id"],
       "input_SI":inp.si,"input_dimensions":inp.dims,
       "observed_target_SI":output.si,
       "target_dimensions":output.dims,
       "measurement_provenance_verified_by_source_sha":True,
       "physical_instrument_uncertainty_known":False,
       "raw_laboratory_data_copied":False,
       "eligible_for_neural_gradient":False,
       "scientific_admission":"HOLD",
    }

def load_manifest(path):
    doc=json.loads(Path(path).read_text(encoding="utf8"))
    return source_manifest_check(doc)
