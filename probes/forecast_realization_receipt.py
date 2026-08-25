from __future__ import annotations
import hashlib, json, math
from typing import Any

SCHEMA="janus.forecast.realization.v1"

def _canon(value:Any)->bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")

def _finite(name:str,value:Any)->float:
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not math.isfinite(float(value)):
        raise ValueError(f"{name} must be finite")
    return float(value)

def realize(*, forecast_receipt:dict[str,Any], realized_score:float, realized_aux_metric:float|None=None, outcome_id:str)->dict[str,Any]:
    forecast_sha=str(forecast_receipt.get("forecast_sha256","") or "")
    if len(forecast_sha)!=64 or any(c not in "0123456789abcdefABCDEF" for c in forecast_sha):
        return {"schema":SCHEMA,"status":"HOLD","findings":["INVALID_FORECAST_RECEIPT_SHA256"]}
    check=dict(forecast_receipt); claimed=check.pop("forecast_sha256",None)
    if hashlib.sha256(_canon(check)).hexdigest()!=claimed:
        return {"schema":SCHEMA,"status":"HOLD","findings":["FORECAST_RECEIPT_HASH_MISMATCH"]}
    predicted=_finite("predicted_score",forecast_receipt.get("predicted_score"))
    actual=_finite("realized_score",realized_score)
    aux_error=None
    if realized_aux_metric is not None and forecast_receipt.get("predicted_aux_metric") is not None:
        aux_error=_finite("realized_aux_metric",realized_aux_metric)-_finite("predicted_aux_metric",forecast_receipt.get("predicted_aux_metric"))
    signed=actual-predicted
    body={
      "schema":SCHEMA,"status":"REALIZED","forecast_sha256":forecast_sha,"outcome_id":str(outcome_id),
      "predicted_score":predicted,"realized_score":actual,"signed_error":signed,"absolute_error":abs(signed),
      "aux_signed_error":aux_error,
      "authority":{"promotes_forecaster":False,"claims_future_information":False,"chooses_action":False},
      "laws":["FORECAST_MUST_PRECEDE_REALIZATION","ONE_HIT_NE_PREDICTIVE_VALIDITY","PREDICTIVE_UTILITY_REQUIRES_AGGREGATED_PROSPECTIVE_SCORE"]
    }
    body["realization_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body

def summarize(realizations:list[dict[str,Any]])->dict[str,Any]:
    valid=[r for r in realizations if r.get("schema")==SCHEMA and r.get("status")=="REALIZED" and isinstance(r.get("absolute_error"),(int,float))]
    if not valid:
        return {"schema":"janus.forecast.summary.v1","status":"NO_VALID_REALIZATIONS","n":0}
    mae=sum(float(r["absolute_error"]) for r in valid)/len(valid)
    bias=sum(float(r["signed_error"]) for r in valid)/len(valid)
    body={"schema":"janus.forecast.summary.v1","status":"DESCRIPTIVE_ONLY","n":len(valid),"mean_absolute_error":mae,"mean_signed_error":bias,
          "boundary":"NO_BASELINE_COMPARISON_OR_STATISTICAL_SIGNIFICANCE_ESTABLISHED"}
    body["summary_sha256"]=hashlib.sha256(_canon(body)).hexdigest()
    return body
