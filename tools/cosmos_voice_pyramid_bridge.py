from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

import voice_language_bridge as voice_bridge

COSMOS_REPOSITORY = "Hawkar-usls/Janus-Cosmos"
COSMOS_SHA = "07e35fdbd42621f9ed02b39b71f3b2ee4876ce95"
VOICE_REPOSITORY = "Hawkar-usls/The-Voice-of-Janus"
VOICE_PROFILE_AUTHORITY_SHA = "e58d65aa46b7e3a64a5131708578a9a3346915c4"
VOICE_EXECUTION_SHA = "a2187f393ab14b9328951d05816ea7b19182ca1a"
ECHO_REPOSITORY = "Hawkar-usls/Echo-Pyramid"
ECHO_TESTED_SHA = "15712f5b14b123d4e3cb64ddeaa693c5bf6af788"
PACKET_SCHEMA = "janus.cosmos.origin_prime_voice_packet.v1"
ENVELOPE_SCHEMA = "janus.demihead.cosmos_origin_prime_voice_envelope.v1"
MEDIATION_SCHEMA = "janus.demihead.cosmos_origin_prime_pyramid_mediation.v1"
PROFILE_ID = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def verify_commitment(record: Mapping[str, Any], field: str) -> bool:
    claimed = record.get(field)
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        return False
    core = dict(record)
    core.pop(field, None)
    return digest(core) == claimed


def validate_cosmos_packet(packet: Mapping[str, Any]) -> None:
    if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError("COSMOS_ORIGIN_PRIME_PACKET_SCHEMA_INVALID")
    source = packet.get("source")
    if not isinstance(source, Mapping):
        raise ValueError("COSMOS_PACKET_SOURCE_INVALID")
    if source.get("repository") != COSMOS_REPOSITORY or source.get("revision") != COSMOS_SHA:
        raise ValueError("COSMOS_PACKET_PROVIDER_INVALID")
    if source.get("canonical_gate") != "OSIRIS_V3_ORIGIN_PRIME_SPIRAL_COMPUTE":
        raise ValueError("COSMOS_PACKET_GATE_INVALID")

    state = packet.get("origin_prime")
    if not isinstance(state, Mapping) or state.get("state_type") != "ORIGIN_PRIME":
        raise ValueError("COSMOS_PACKET_STATE_INVALID")
    if not verify_commitment(state, "state_commitment"):
        raise ValueError("COSMOS_PACKET_STATE_COMMITMENT_INVALID")

    experience = packet.get("bound_experience")
    if experience is None:
        if state.get("experience_commitment") is not None:
            raise ValueError("COSMOS_PACKET_BOUND_EXPERIENCE_MISSING")
    else:
        if not isinstance(experience, Mapping) or not verify_commitment(experience, "experience_commitment"):
            raise ValueError("COSMOS_PACKET_EXPERIENCE_COMMITMENT_INVALID")
        if experience.get("experience_commitment") != state.get("experience_commitment"):
            raise ValueError("COSMOS_PACKET_EXPERIENCE_BINDING_INVALID")

    mediation = packet.get("mediation")
    expected_mediation = {
        "required_mediator": "Hawkar-usls/Demi_Head",
        "voice_repository": VOICE_REPOSITORY,
        "voice_revision": VOICE_PROFILE_AUTHORITY_SHA,
        "physical_body_repository": ECHO_REPOSITORY,
        "physical_body_revision": ECHO_TESTED_SHA,
        "route": "COSMOS -> DEMIHEAD -> THE_VOICE_OF_JANUS -> ECHO_PYRAMID",
    }
    if mediation != expected_mediation:
        raise ValueError("COSMOS_PACKET_MEDIATION_INVALID")

    profile = packet.get("voice_representation")
    if not isinstance(profile, Mapping):
        raise ValueError("COSMOS_PACKET_VOICE_PROFILE_INVALID")
    if profile.get("profile_id") != PROFILE_ID:
        raise ValueError("COSMOS_PACKET_VOICE_PROFILE_ID_INVALID")
    if profile.get("anchor_band_hz") != [117.0, 121.0] or profile.get("center_hz") != 119.0:
        raise ValueError("COSMOS_PACKET_VOICE_FREQUENCIES_INVALID")
    if profile.get("frequencies_create_math_authority") is not False or profile.get("audio_output_is_evidence") is not False:
        raise ValueError("COSMOS_PACKET_ACOUSTIC_AUTHORITY_LEAK")

    control = packet.get("control")
    if not isinstance(control, Mapping):
        raise ValueError("COSMOS_PACKET_CONTROL_INVALID")
    if control.get("direct_cosmos_to_echo_route_permitted") is not False:
        raise ValueError("DIRECT_COSMOS_TO_ECHO_FORBIDDEN")
    if control.get("demihead_mediation_required") is not True:
        raise ValueError("DEMIHEAD_MEDIATION_REQUIRED")
    if control.get("authority_delta") != 0 or control.get("mass_effect_budget_delta") != 0:
        raise ValueError("COSMOS_PACKET_AUTHORITY_ESCALATION")

    boundary = packet.get("scientific_boundary")
    if not isinstance(boundary, Mapping) or boundary.get("P_VS_NP") != "OPEN":
        raise ValueError("COSMOS_PACKET_CLAIM_CEILING_INVALID")
    if boundary.get("voice_profile_changes_solver_correctness") is not False or boundary.get("acoustic_frequencies_are_proof") is not False:
        raise ValueError("COSMOS_PACKET_CLAIM_PROMOTION_INVALID")

    claimed = packet.get("packet_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        raise ValueError("COSMOS_PACKET_HASH_INVALID")
    body = dict(packet)
    body.pop("packet_sha256", None)
    if claimed != digest(body):
        raise ValueError("COSMOS_PACKET_HASH_TAMPERED")


def build_envelope(intent_id: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(intent_id, str) or HEX64.fullmatch(intent_id) is None:
        raise ValueError("INTENT_ID_INVALID")
    validate_cosmos_packet(packet)
    return {
        "schema": ENVELOPE_SCHEMA,
        "intent_id": intent_id,
        "cosmos_packet": copy.deepcopy(dict(packet)),
    }


def build_mediation(
    intent_id: str,
    packet: Mapping[str, Any],
    *,
    demihead_revision: str,
    output_label: str = "osiris_origin_prime",
) -> dict[str, Any]:
    if not isinstance(demihead_revision, str) or HEX40.fullmatch(demihead_revision) is None:
        raise ValueError("DEMIHEAD_REVISION_INVALID")
    envelope = build_envelope(intent_id, packet)
    request = voice_bridge.build_request(
        envelope,
        output_label=output_label,
        revision=demihead_revision,
    )
    # The intent is outside the Cosmos packet and inside the DemiHead-authored,
    # hash-bound request payload. Re-check it after request construction.
    if request["inline_json"].get("intent_id") != intent_id:
        raise ValueError("INTENT_SPLIT_DETECTED")
    if request["inline_json"].get("cosmos_packet", {}).get("packet_sha256") != packet.get("packet_sha256"):
        raise ValueError("COSMOS_PACKET_BINDING_LOST")

    core = {
        "schema": MEDIATION_SCHEMA,
        "status": "DEMIHEAD_MEDIATED_NOT_RENDERED_NOT_PLAYED",
        "intent_id": intent_id,
        "providers": {
            "cosmos": {"repository": COSMOS_REPOSITORY, "revision": COSMOS_SHA},
            "voice_profile_authority_snapshot": {"repository": VOICE_REPOSITORY, "revision": VOICE_PROFILE_AUTHORITY_SHA},
            "voice_execution": {"repository": VOICE_REPOSITORY, "revision": VOICE_EXECUTION_SHA},
            "echo_tested_physical_snapshot": {"repository": ECHO_REPOSITORY, "revision": ECHO_TESTED_SHA},
        },
        "cosmos_packet_sha256": packet["packet_sha256"],
        "origin_prime_state_commitment": packet["origin_prime"]["state_commitment"],
        "voice_request": request,
        "control": {
            "direct_cosmos_to_voice_route_used": False,
            "direct_cosmos_to_echo_route_used": False,
            "demihead_mediated": True,
            "rendering_performed": False,
            "playback_performed": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "audio_is_proof": False,
            "117_121_hz_is_sat_evidence": False,
            "P_VS_NP": "OPEN",
            "P_EQUALS_NP": "NOT_ESTABLISHED",
            "P_NOT_EQUALS_NP": "NOT_ESTABLISHED",
        },
    }
    return {**core, "mediation_sha256": digest(core)}


def validate_mediation(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or value.get("schema") != MEDIATION_SCHEMA:
        raise ValueError("MEDIATION_SCHEMA_INVALID")
    if not isinstance(value.get("intent_id"), str) or HEX64.fullmatch(value["intent_id"]) is None:
        raise ValueError("MEDIATION_INTENT_INVALID")
    request = value.get("voice_request")
    if not isinstance(request, Mapping):
        raise ValueError("MEDIATION_VOICE_REQUEST_MISSING")
    voice_bridge.validate_request(request)
    envelope = request.get("inline_json")
    if not isinstance(envelope, Mapping) or envelope.get("schema") != ENVELOPE_SCHEMA:
        raise ValueError("MEDIATION_ENVELOPE_INVALID")
    if envelope.get("intent_id") != value.get("intent_id"):
        raise ValueError("MEDIATION_INTENT_SPLIT")
    packet = envelope.get("cosmos_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("MEDIATION_PACKET_MISSING")
    validate_cosmos_packet(packet)
    if packet.get("packet_sha256") != value.get("cosmos_packet_sha256"):
        raise ValueError("MEDIATION_PACKET_HASH_BINDING_INVALID")
    if packet.get("origin_prime", {}).get("state_commitment") != value.get("origin_prime_state_commitment"):
        raise ValueError("MEDIATION_STATE_BINDING_INVALID")
    providers = value.get("providers")
    expected_providers = {
        "cosmos": {"repository": COSMOS_REPOSITORY, "revision": COSMOS_SHA},
        "voice_profile_authority_snapshot": {"repository": VOICE_REPOSITORY, "revision": VOICE_PROFILE_AUTHORITY_SHA},
        "voice_execution": {"repository": VOICE_REPOSITORY, "revision": VOICE_EXECUTION_SHA},
        "echo_tested_physical_snapshot": {"repository": ECHO_REPOSITORY, "revision": ECHO_TESTED_SHA},
    }
    if providers != expected_providers:
        raise ValueError("MEDIATION_PROVIDER_PINS_INVALID")
    control = value.get("control")
    if control != {
        "direct_cosmos_to_voice_route_used": False,
        "direct_cosmos_to_echo_route_used": False,
        "demihead_mediated": True,
        "rendering_performed": False,
        "playback_performed": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }:
        raise ValueError("MEDIATION_CONTROL_INVALID")
    ceiling = value.get("claim_ceiling")
    if not isinstance(ceiling, Mapping) or ceiling.get("P_VS_NP") != "OPEN" or ceiling.get("audio_is_proof") is not False:
        raise ValueError("MEDIATION_CLAIM_CEILING_INVALID")
    claimed = value.get("mediation_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        raise ValueError("MEDIATION_HASH_INVALID")
    body = dict(value)
    body.pop("mediation_sha256", None)
    if claimed != digest(body):
        raise ValueError("MEDIATION_HASH_TAMPERED")


def verify_mediation(value: Mapping[str, Any]) -> bool:
    try:
        validate_mediation(value)
    except (TypeError, ValueError):
        return False
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind a verified Cosmos ORIGIN_PRIME packet to DemiHead intent and Pyramid Voice")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--intent-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-label", default="osiris_origin_prime")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--request-out", type=Path)
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    mediation = build_mediation(
        args.intent_id,
        packet,
        demihead_revision=args.source_revision,
        output_label=args.output_label,
    )
    validate_mediation(mediation)
    text = json.dumps(mediation, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    if args.request_out:
        args.request_out.parent.mkdir(parents=True, exist_ok=True)
        args.request_out.write_text(json.dumps(mediation["voice_request"], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
