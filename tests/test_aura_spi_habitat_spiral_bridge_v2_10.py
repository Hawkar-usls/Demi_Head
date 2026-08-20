from tools.aura_spi_habitat_spiral_bridge_v2_10 import arbitrate


def request():
    return {
        "schema": "janus.aura_spi.spiral_event.v1",
        "session_id": "s1",
        "generation": 1,
        "intent_id": "c" * 64,
        "trigger_text": "fresh evidence",
    }


def aura():
    return {
        "schema": "janus.aura_spi.aura_reflection.v1",
        "session_id": "s1",
        "generation": 1,
        "intent_id": "c" * 64,
        "predictive_label_authority": False,
        "scientific_evidence_authority": False,
        "may_train_predictive_head": False,
        "may_replace_primary_intent": False,
    }


def spi():
    return {
        "schema": "janus.aura_spi.semantic_synthesis.v1",
        "session_id": "s1",
        "generation": 1,
        "intent_id": "c" * 64,
        "retrieval_refs": [],
        "semantic_similarity_is_evidence": False,
        "prediction_is_truth": False,
        "aura_is_predictive_label": False,
    }


def test_preview_pass_is_not_verified_return():
    out = arbitrate(
        request=request(), aura=aura(), spi=spi(), decision="PASS", intent_authority="LOCAL_PREVIEW"
    )
    assert out["verified_return_eligible"] is False
    assert "verified_return" not in out
    assert out["authority_delta"] == 0
    assert out["external_effect_authorized"] is False


def test_verified_intent_pass_can_emit_scoped_verified_return():
    out = arbitrate(
        request=request(), aura=aura(), spi=spi(), decision="PASS", intent_authority="DEMIHEAD_GOLDPROMPT_VERIFIED"
    )
    assert out["verified_return_eligible"] is True
    assert out["verified_return"]["world_truth"] is False
    assert out["verified_return"]["predictive_training_label"] is False


def test_aura_as_label_rejected():
    bad = aura()
    bad["predictive_label_authority"] = True
    try:
        arbitrate(request=request(), aura=bad, spi=spi(), decision="PASS", intent_authority="DEMIHEAD_GOLDPROMPT_VERIFIED")
    except ValueError as exc:
        assert "AURA_AS_PREDICTIVE_LABEL_REJECT" in str(exc)
    else:
        raise AssertionError("Aura predictive-label authority must fail closed")


def test_intent_split_rejected():
    bad = spi()
    bad["intent_id"] = "d" * 64
    try:
        arbitrate(request=request(), aura=aura(), spi=bad, decision="HOLD", intent_authority="LOCAL_PREVIEW")
    except ValueError as exc:
        assert "INTENT_SPLIT_REJECT" in str(exc)
    else:
        raise AssertionError("intent split must fail closed")
