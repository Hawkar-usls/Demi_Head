from __future__ import annotations

from typing import Any, Mapping

import cosmos_voice_pyramid_bridge as cvp
import nexus_habitat as v1
import nexus_habitat_v2_4 as v24

CONTRACT = "JANUS_NEXUS_HABITAT_V2_7"
ENVELOPE_SCHEMA = "janus.demihead.nexus_envelope.v2_7"
ROUTE_RECEIPT_SCHEMA = "janus.demihead.nexus_route_receipt.v2_7"

ORIGIN_PRIME_STATE_PACKET = "ORIGIN_PRIME_STATE_PACKET"
COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE = "COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE"
PYRAMID_PCM_HANDOFF = "PYRAMID_PCM_HANDOFF"
PYRAMID_AUDIO_RECEIPT = "PYRAMID_AUDIO_RECEIPT"

HEADS = dict(v24.HEADS)

_parent_cosmos = HEADS["COSMOS"]
HEADS["COSMOS"] = v1.HeadRule(
    role="SPECIALIZED_PROOF_AND_ORIGIN_PRIME_STATE_PROVIDER_NOT_TRUTH_ARBITER",
    repository=_parent_cosmos.repository,
    accepts=tuple(_parent_cosmos.accepts),
    emits=tuple(dict.fromkeys([*_parent_cosmos.emits, ORIGIN_PRIME_STATE_PACKET])),
    lineage_repository=_parent_cosmos.lineage_repository,
)
HEADS.update(
    {
        "VOICE_BROKER": v1.HeadRule(
            role="DEMIHEAD_INTENT_BOUND_STATE_TO_VOICE_MEDIATOR",
            repository="Hawkar-usls/Demi_Head",
            accepts=(ORIGIN_PRIME_STATE_PACKET, PYRAMID_AUDIO_RECEIPT),
            emits=(COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE,),
        ),
        "VOICE": v1.HeadRule(
            role="PYRAMID_LANGUAGE_AUDIO_RENDERER",
            repository=cvp.VOICE_REPOSITORY,
            accepts=(COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE,),
            emits=(PYRAMID_PCM_HANDOFF, PYRAMID_AUDIO_RECEIPT),
        ),
        "ECHO_PYRAMID": v1.HeadRule(
            role="PHYSICAL_PCM_VOICE_BODY",
            repository=cvp.ECHO_REPOSITORY,
            accepts=(PYRAMID_PCM_HANDOFF,),
            emits=(),
        ),
    }
)

NEW_ROUTES = frozenset(
    {
        ("COSMOS", "VOICE_BROKER", ORIGIN_PRIME_STATE_PACKET),
        ("VOICE_BROKER", "VOICE", COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE),
        ("VOICE", "ECHO_PYRAMID", PYRAMID_PCM_HANDOFF),
        ("VOICE", "VOICE_BROKER", PYRAMID_AUDIO_RECEIPT),
    }
)
ROUTES = frozenset(set(v24.ROUTES) | set(NEW_ROUTES))


def _is_hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in "0123456789abcdef" for ch in value)


def _control(ttl_hops: int = 5) -> dict[str, Any]:
    return {
        "read_only_transfer": True,
        "external_effect_permitted": False,
        "delivery_claimed": False,
        "playback_claimed": False,
        "admission_claimed": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
        "ttl_hops": ttl_hops,
    }


def validate_envelope(envelope: Mapping[str, Any]) -> None:
    if not isinstance(envelope, Mapping):
        raise ValueError("Nexus v2.7 envelope must be an object")
    if envelope.get("schema") != ENVELOPE_SCHEMA or envelope.get("contract") != CONTRACT:
        raise ValueError("Nexus v2.7 schema or contract mismatch")
    source = envelope.get("source_head")
    target = envelope.get("target_head")
    kind = envelope.get("payload_kind")
    if source not in HEADS or target not in HEADS:
        raise ValueError("Unknown source or target head")
    if kind not in HEADS[source].emits or kind not in HEADS[target].accepts:
        raise ValueError("Payload kind is not compatible with declared heads")
    if (source, target, kind) not in ROUTES:
        raise ValueError("Route is not explicitly admitted")

    payload_ref = envelope.get("payload_ref")
    if not isinstance(payload_ref, Mapping) or not _is_hex64(payload_ref.get("sha256")):
        raise ValueError("payload_ref.sha256 must be lowercase hex64")

    control = envelope.get("control")
    if not isinstance(control, Mapping):
        raise ValueError("control must be an object")
    required = {
        "read_only_transfer": True,
        "external_effect_permitted": False,
        "delivery_claimed": False,
        "playback_claimed": False,
        "admission_claimed": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    for key, expected in required.items():
        if control.get(key) != expected:
            raise ValueError(f"Nexus v2.7 control violation: {key}")
    ttl = control.get("ttl_hops")
    if not isinstance(ttl, int) or isinstance(ttl, bool) or not 1 <= ttl <= 8:
        raise ValueError("ttl_hops must be integer in [1,8]")
    trace = envelope.get("trace")
    if not isinstance(trace, list) or len(trace) >= ttl or any(hop not in HEADS for hop in trace):
        raise ValueError("invalid trace")


def _envelope(*, source: str, target: str, kind: str, sha256: str, locator: str, trace: list[str], envelope_id: str) -> dict[str, Any]:
    value = {
        "schema": ENVELOPE_SCHEMA,
        "contract": CONTRACT,
        "envelope_id": envelope_id,
        "source_head": source,
        "target_head": target,
        "payload_kind": kind,
        "payload_ref": {"sha256": sha256, "locator": locator},
        "trace": trace,
        "control": _control(),
    }
    validate_envelope(value)
    return value


def build_cosmos_state_route(packet: Mapping[str, Any], *, envelope_id: str | None = None) -> dict[str, Any]:
    cvp.validate_cosmos_packet(packet)
    return _envelope(
        source="COSMOS",
        target="VOICE_BROKER",
        kind=ORIGIN_PRIME_STATE_PACKET,
        sha256=str(packet["packet_sha256"]),
        locator=f"memory://cosmos-origin-prime/{packet['origin_prime']['state_commitment']}",
        trace=[],
        envelope_id=envelope_id or f"nexus-v2-7-cosmos-{packet['origin_prime']['state_commitment'][:16]}",
    )


def build_voice_envelope_route(mediation: Mapping[str, Any], *, envelope_id: str | None = None) -> dict[str, Any]:
    cvp.validate_mediation(mediation)
    envelope = mediation["voice_request"]["inline_json"]
    payload_sha = v1.sha256(dict(envelope))
    return _envelope(
        source="VOICE_BROKER",
        target="VOICE",
        kind=COSMOS_ORIGIN_PRIME_VOICE_ENVELOPE,
        sha256=payload_sha,
        locator=f"memory://demihead-cosmos-voice/{mediation['intent_id']}",
        trace=["COSMOS"],
        envelope_id=envelope_id or f"nexus-v2-7-voice-{mediation['intent_id'][:16]}",
    )


def validate_voice_receipt(receipt: Mapping[str, Any]) -> None:
    if not isinstance(receipt, Mapping) or receipt.get("schema") != "janus.voice.cosmos_origin_prime_pyramid_receipt.v1":
        raise ValueError("PYRAMID_AUDIO_RECEIPT_SCHEMA_INVALID")
    if receipt.get("status") != "COSMOS_ORIGIN_PRIME_SONIFIED_WITH_PYRAMID_LANGUAGE_NOT_PLAYED":
        raise ValueError("PYRAMID_AUDIO_RECEIPT_STATUS_INVALID")
    request = receipt.get("request")
    cosmos = receipt.get("cosmos")
    pyramid = receipt.get("pyramid_language")
    body = receipt.get("physical_body")
    control = receipt.get("control")
    ceiling = receipt.get("claim_boundary")
    if not isinstance(request, Mapping) or not _is_hex64(request.get("intent_id")):
        raise ValueError("PYRAMID_AUDIO_RECEIPT_INTENT_INVALID")
    if not isinstance(cosmos, Mapping) or cosmos.get("repository") != cvp.COSMOS_REPOSITORY or cosmos.get("revision") != cvp.COSMOS_SHA:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_COSMOS_INVALID")
    if not _is_hex64(cosmos.get("packet_sha256")) or not _is_hex64(cosmos.get("state_commitment")):
        raise ValueError("PYRAMID_AUDIO_RECEIPT_COSMOS_HASH_INVALID")
    if not isinstance(pyramid, Mapping) or pyramid.get("profile_id") != cvp.PROFILE_ID:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_PROFILE_INVALID")
    if pyramid.get("anchor_band_hz") != [117.0, 121.0] or pyramid.get("center_hz") != 119.0:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_FREQUENCY_INVALID")
    if not isinstance(body, Mapping) or body.get("repository") != cvp.ECHO_REPOSITORY or body.get("revision") != cvp.ECHO_TESTED_SHA:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_BODY_INVALID")
    if body.get("physical_playback_performed") is not False:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_CANNOT_CLAIM_PLAYBACK")
    if not isinstance(control, Mapping) or control.get("authority_delta") != 0 or control.get("mass_effect_budget_delta") != 0:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_AUTHORITY_INVALID")
    if control.get("automatic_playback_performed") is not False:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_AUTOPLAY_INVALID")
    if not isinstance(ceiling, Mapping) or ceiling.get("P_VS_NP") != "OPEN" or ceiling.get("audio_is_proof") is not False:
        raise ValueError("PYRAMID_AUDIO_RECEIPT_CLAIM_CEILING_INVALID")
    claimed = receipt.get("receipt_sha256")
    if not _is_hex64(claimed):
        raise ValueError("PYRAMID_AUDIO_RECEIPT_HASH_INVALID")
    core = dict(receipt)
    core.pop("receipt_sha256", None)
    if claimed != v1.sha256(core):
        raise ValueError("PYRAMID_AUDIO_RECEIPT_HASH_TAMPERED")


def build_pcm_handoff_route(receipt: Mapping[str, Any], *, envelope_id: str | None = None) -> dict[str, Any]:
    validate_voice_receipt(receipt)
    return _envelope(
        source="VOICE",
        target="ECHO_PYRAMID",
        kind=PYRAMID_PCM_HANDOFF,
        sha256=str(receipt["output"]["wav_sha256"]),
        locator=f"file://{receipt['output']['wav_path']}",
        trace=["COSMOS", "VOICE_BROKER"],
        envelope_id=envelope_id or f"nexus-v2-7-pcm-{receipt['request']['intent_id'][:16]}",
    )


def build_audio_receipt_route(receipt: Mapping[str, Any], *, envelope_id: str | None = None) -> dict[str, Any]:
    validate_voice_receipt(receipt)
    return _envelope(
        source="VOICE",
        target="VOICE_BROKER",
        kind=PYRAMID_AUDIO_RECEIPT,
        sha256=str(receipt["receipt_sha256"]),
        locator=f"memory://pyramid-audio-receipt/{receipt['request']['intent_id']}",
        trace=["COSMOS", "VOICE_BROKER"],
        envelope_id=envelope_id or f"nexus-v2-7-receipt-{receipt['request']['intent_id'][:16]}",
    )


def route_receipt(envelope: Mapping[str, Any]) -> dict[str, Any]:
    validate_envelope(envelope)
    return {
        "schema": ROUTE_RECEIPT_SCHEMA,
        "contract": CONTRACT,
        "status": "ROUTE_ADMITTED_READ_ONLY",
        "envelope_id": envelope["envelope_id"],
        "envelope_sha256": v1.sha256(dict(envelope)),
        "source_head": envelope["source_head"],
        "target_head": envelope["target_head"],
        "payload_kind": envelope["payload_kind"],
        "payload_sha256": envelope["payload_ref"]["sha256"],
        "routing": {
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "external_effect_permitted": False,
            "delivery_performed": False,
            "playback_performed": False,
            "provider_execution_performed_by_router": False,
        },
        "claim_ceiling": {
            "route_is_delivery": False,
            "route_is_playback": False,
            "route_is_truth": False,
            "audio_is_proof": False,
            "117_121_hz_is_sat_evidence": False,
            "P_VS_NP": "OPEN",
        },
    }


def habitat_snapshot() -> dict[str, Any]:
    return {
        "schema": "janus.demihead.habitat_snapshot.v2_7",
        "contract": CONTRACT,
        "parent_contract": v24.CONTRACT,
        "new_heads": ["VOICE_BROKER", "VOICE", "ECHO_PYRAMID"],
        "new_routes": [list(route) for route in sorted(NEW_ROUTES)],
        "head_count": len(HEADS),
        "route_count": len(ROUTES),
        "providers": {
            "cosmos_current": cvp.COSMOS_SHA,
            "voice_profile_authority_snapshot": cvp.VOICE_PROFILE_AUTHORITY_SHA,
            "voice_execution": cvp.VOICE_EXECUTION_SHA,
            "echo_tested_physical_snapshot": cvp.ECHO_TESTED_SHA,
        },
        "global_control": {
            "nexus_v2_4_rewritten": False,
            "legacy_cosmos_proof_gate_rewritten": False,
            "direct_cosmos_to_voice_admitted": False,
            "direct_cosmos_to_echo_admitted": False,
            "route_is_delivery": False,
            "route_is_playback": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "P_VS_NP": "OPEN",
        },
    }
