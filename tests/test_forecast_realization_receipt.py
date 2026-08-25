import hashlib, json
from probes.forecast_realization_receipt import realize, summarize


def _forecast(predicted=3.0,aux=0.5):
    body={
      "schema":"janus.metric_trend_forecast.v1","phase":"FORECAST","score":2.0,"aux_metric":0.4,
      "velocity":1.0,"acceleration":0.0,"predicted_score":predicted,"predicted_aux_metric":aux,
      "lead_factor":1.8,"authority":{"changes_runtime":False,"chooses_action":False,"claims_future_information":False},
      "laws":["TREND_EXTRAPOLATION_NE_PRECOGNITION","FORECAST_NE_CAUSAL_EVIDENCE","FORECAST_MUST_BE_SCORED_AGAINST_REALIZED_OUTCOME"]
    }
    body["forecast_sha256"]=hashlib.sha256(json.dumps(body,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return body


def test_realization_binds_exact_forecast_and_scores_error():
    f=_forecast(3.0,0.5)
    r=realize(forecast_receipt=f,realized_score=2.5,realized_aux_metric=0.7,outcome_id="cycle-10")
    assert r["status"]=="REALIZED"
    assert r["signed_error"]==-0.5
    assert r["absolute_error"]==0.5
    assert abs(r["aux_signed_error"]-0.2)<1e-12
    assert r["authority"]["claims_future_information"] is False


def test_tampered_forecast_holds_and_summary_is_descriptive_only():
    f=_forecast(); f["predicted_score"]=99
    assert realize(forecast_receipt=f,realized_score=1,outcome_id="x")["status"]=="HOLD"
    rows=[realize(forecast_receipt=_forecast(3),realized_score=2,outcome_id="a"),realize(forecast_receipt=_forecast(4),realized_score=5,outcome_id="b")]
    s=summarize(rows)
    assert s["n"]==2 and s["mean_absolute_error"]==1.0
    assert s["mean_signed_error"]==0.0
    assert s["status"]=="DESCRIPTIVE_ONLY"
