from probes.patch_proposal_evaluator import evaluate, append_evaluation, verify_ledger

def _sha(ch): return ch*64

def test_positive_external_receipt_becomes_review_only(tmp_path):
    p={"origin":"janus","baseline_sha256":_sha("a"),"candidate_sha256":_sha("b"),"patch_class":"cache_results"}
    audit={"status":"PASS_STATIC","source_sha256":_sha("b")}
    metric={"baseline_sha256":_sha("a"),"candidate_sha256":_sha("b"),"execution_origin":"sandbox_test",
            "metric_name":"latency_ms","direction":"minimize","baseline_metric":10.0,"candidate_metric":8.0}
    r=evaluate(proposal=p,audit_receipt=audit,metric_receipt=metric)
    assert r["decision"]=="ELIGIBLE_FOR_HUMAN_REVIEW"
    assert r["improvement"]==2.0
    assert r["authority"]["applies_patch"] is False
    path=tmp_path/"patches.jsonl"
    assert append_evaluation(path,r)["appended"] is True
    assert append_evaluation(path,r)["appended"] is False
    assert verify_ledger(path)["valid"] is True

def test_unbound_or_runtime_self_metric_holds():
    p={"origin":"janus","baseline_sha256":_sha("a"),"candidate_sha256":_sha("b")}
    audit={"status":"PASS_STATIC","source_sha256":_sha("c")}
    metric={"baseline_sha256":_sha("a"),"candidate_sha256":_sha("b"),"execution_origin":"runtime_self_eval",
            "metric_name":"score","direction":"maximize","baseline_metric":1.0,"candidate_metric":2.0}
    r=evaluate(proposal=p,audit_receipt=audit,metric_receipt=metric)
    assert r["decision"]=="HOLD"
    assert "AUDIT_NOT_BOUND_TO_CANDIDATE" in r["findings"]
    assert "METRIC_ORIGIN_NOT_EXTERNAL_TEST" in r["findings"]
