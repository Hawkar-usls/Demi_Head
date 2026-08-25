from probes.indus_repair_candidate import build


def _sha(ch): return ch*64


def test_indus_builds_repair_candidate_without_reaper_authority():
    r=build(module_key="mod_rex",source_sha256=_sha("a"),failure_receipt_sha256=_sha("b"),reason="NameError: python",target_path="services/modules_live/mod_rex.py")
    assert r["status"]=="REPAIR_CANDIDATE"
    assert r["requested_action"]=="DIAGNOSE_AND_PROPOSE_REPAIR"
    assert r["authority"]["deletes_module"] is False
    assert r["authority"]["kills_service"] is False
    assert r["authority"]["edits_source"] is False
    assert "SOVEREIGN_LOCK" in r["next_gates"]
    assert len(r["repair_candidate_sha256"])==64


def test_indus_holds_unbound_failure_or_invalid_identity():
    r=build(module_key="../bad",source_sha256="x",failure_receipt_sha256="y",reason="")
    assert r["status"]=="HOLD"
    assert "INVALID_MODULE_KEY" in r["findings"]
    assert "INVALID_SOURCE_SHA256" in r["findings"]
    assert "INVALID_FAILURE_RECEIPT_SHA256" in r["findings"]
    assert "MISSING_REASON" in r["findings"]
