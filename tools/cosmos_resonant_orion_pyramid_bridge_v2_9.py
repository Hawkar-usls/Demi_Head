from __future__ import annotations

import argparse
import copy
import json
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Mapping

import cosmos_voice_pyramid_bridge_v2_8 as base

COSMOS_SHA = "c543eb6ed753339fabed33d7f0ab880d43433d0f"
EXTENSION_SCHEMA = "janus.cosmos.origin_prime_resonant_representation_extension.v1"
MEDIATION_SCHEMA = "janus.demihead.cosmos_origin_prime_resonant_pyramid_mediation.v2_9"
PROFILE_ID = "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3"
ORION_ANCHOR = "ORION_BELT_SAH_OSIRIS_CONTEXT_v1"
TRANSFER_CLASS = "VARIABLE_RENAMING_BIJECTION"

ASTRAL_REPRESENTATION = {
    "anchor_id": ORION_ANCHOR,
    "star_triplet": ["Mintaka", "Alnilam", "Alnitak"],
    "egyptological_context": "SAH_ORION_OSIRIS_RELIGIOUS_TEXTUAL_CONTEXT",
    "giza_orion_correlation": "HYPOTHESIS_NOT_ASSERTED_AS_ARCHITECTURAL_FACT",
    "janus_rebus_alias": "S𓂸ḥ",
    "janus_rebus_alias_is_historical_transliteration": False,
    "seasonal_visibility": "CONTEXT_ONLY",
    "role": "ASTRAL_CONTEXT_AND_NAVIGATION_REPRESENTATION_ONLY",
    "authority_delta": 0,
    "astral_geometry_is_proof": False,
    "astral_context_changes_solver_correctness": False,
}


@contextmanager
def _pin_cosmos_provider():
    prior = base.COSMOS_SHA
    base.COSMOS_SHA = COSMOS_SHA
    try:
        yield
    finally:
        base.COSMOS_SHA = prior


def _representation_binding_core(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "origin_prime_state_commitment": packet["origin_prime"]["state_commitment"],
        "experience_commitment": packet["origin_prime"].get("experience_commitment"),
        "voice_representation": packet["voice_representation"],
        "astral_representation": packet["astral_representation"],
        "lineage_representation": packet["lineage_representation"],
        "authority_delta": 0,
    }


def validate_resonant_packet(packet: Mapping[str, Any]) -> None:
    with _pin_cosmos_provider():
        base.validate_cosmos_packet(packet)
    if packet.get("representation_extension_schema") != EXTENSION_SCHEMA:
        raise ValueError("RESONANT_EXTENSION_SCHEMA_INVALID")
    if packet.get("astral_representation") != ASTRAL_REPRESENTATION:
        raise ValueError("RESONANT_ASTRAL_REPRESENTATION_INVALID")

    lineage = packet.get("lineage_representation")
    if not isinstance(lineage, Mapping):
        raise ValueError("RESONANT_LINEAGE_REPRESENTATION_INVALID")
    if lineage.get("memory_may_propose_not_verdict") is not True or lineage.get("authority_delta") != 0:
        raise ValueError("RESONANT_LINEAGE_AUTHORITY_INVALID")
    if lineage.get("transfer_present"):
        if lineage.get("transfer_class") != TRANSFER_CLASS:
            raise ValueError("RESONANT_LINEAGE_TRANSFER_CLASS_INVALID")
        for field in ("source_experience_commitment", "transformation_certificate_sha256"):
            value = lineage.get(field)
            if not isinstance(value, str) or base.HEX64.fullmatch(value) is None:
                raise ValueError(f"RESONANT_LINEAGE_{field.upper()}_INVALID")

    claimed_binding = packet.get("representation_binding_sha256")
    if not isinstance(claimed_binding, str) or base.HEX64.fullmatch(claimed_binding) is None:
        raise ValueError("RESONANT_REPRESENTATION_BINDING_INVALID")
    if claimed_binding != base.digest(_representation_binding_core(packet)):
        raise ValueError("RESONANT_REPRESENTATION_BINDING_TAMPERED")

    profile = packet.get("voice_representation")
    if not isinstance(profile, Mapping) or profile.get("profile_id") != PROFILE_ID:
        raise ValueError("RESONANT_VOICE_PROFILE_INVALID")
    if profile.get("frequencies_create_math_authority") is not False or profile.get("audio_output_is_evidence") is not False:
        raise ValueError("RESONANT_VOICE_AUTHORITY_LEAK")


def build_mediation(intent_id: str, packet: Mapping[str, Any], *, demihead_revision: str, output_label: str = "osiris_origin_prime_resonant") -> dict[str, Any]:
    validate_resonant_packet(packet)
    with _pin_cosmos_provider():
        parent = base.build_mediation(intent_id, packet, demihead_revision=demihead_revision, output_label=output_label)
    parent_sha = parent["mediation_sha256"]
    core = dict(parent)
    core.pop("mediation_sha256", None)
    core["schema"] = MEDIATION_SCHEMA
    core["parent_v2_8_mediation_sha256"] = parent_sha
    core["resonant_representation"] = {
        "representation_binding_sha256": packet["representation_binding_sha256"],
        "lineage_transfer_present": bool(packet["lineage_representation"].get("transfer_present")),
        "lineage_transfer_class": packet["lineage_representation"].get("transfer_class"),
        "voice_profile": packet["voice_representation"]["profile_id"],
        "orion_anchor": packet["astral_representation"]["anchor_id"],
        "janus_rebus_alias": packet["astral_representation"]["janus_rebus_alias"],
        "janus_rebus_alias_is_historical_transliteration": False,
        "memory_may_propose_not_verdict": True,
        "authority_delta": 0,
    }
    core["claim_ceiling"] = dict(core["claim_ceiling"])
    core["claim_ceiling"].update({
        "astral_geometry_is_proof": False,
        "orion_giza_architectural_intent": "NOT_ESTABLISHED",
    })
    return {**core, "mediation_sha256": base.digest(core)}


def _parent_projection(value: Mapping[str, Any]) -> dict[str, Any]:
    parent = copy.deepcopy(dict(value))
    parent_sha = parent.pop("parent_v2_8_mediation_sha256", None)
    parent.pop("resonant_representation", None)
    parent["schema"] = base.MEDIATION_SCHEMA
    ceiling = parent.get("claim_ceiling")
    if isinstance(ceiling, dict):
        ceiling.pop("astral_geometry_is_proof", None)
        ceiling.pop("orion_giza_architectural_intent", None)
    parent["mediation_sha256"] = parent_sha
    return parent


def validate_mediation(value: Mapping[str, Any]) -> None:
    if not isinstance(value, Mapping) or value.get("schema") != MEDIATION_SCHEMA:
        raise ValueError("RESONANT_MEDIATION_SCHEMA_INVALID")
    parent_sha = value.get("parent_v2_8_mediation_sha256")
    if not isinstance(parent_sha, str) or base.HEX64.fullmatch(parent_sha) is None:
        raise ValueError("RESONANT_PARENT_MEDIATION_HASH_INVALID")

    projected = _parent_projection(value)
    with _pin_cosmos_provider():
        base.validate_mediation(projected)
    if projected["mediation_sha256"] != parent_sha:
        raise ValueError("RESONANT_PARENT_MEDIATION_BINDING_INVALID")

    request = value.get("voice_request")
    envelope = request.get("inline_json") if isinstance(request, Mapping) else None
    packet = envelope.get("cosmos_packet") if isinstance(envelope, Mapping) else None
    if not isinstance(packet, Mapping):
        raise ValueError("RESONANT_PACKET_MISSING")
    validate_resonant_packet(packet)

    expected = {
        "representation_binding_sha256": packet["representation_binding_sha256"],
        "lineage_transfer_present": bool(packet["lineage_representation"].get("transfer_present")),
        "lineage_transfer_class": packet["lineage_representation"].get("transfer_class"),
        "voice_profile": packet["voice_representation"]["profile_id"],
        "orion_anchor": packet["astral_representation"]["anchor_id"],
        "janus_rebus_alias": packet["astral_representation"]["janus_rebus_alias"],
        "janus_rebus_alias_is_historical_transliteration": False,
        "memory_may_propose_not_verdict": True,
        "authority_delta": 0,
    }
    if value.get("resonant_representation") != expected:
        raise ValueError("RESONANT_MEDIATION_REPRESENTATION_BINDING_INVALID")

    ceiling = value.get("claim_ceiling")
    if not isinstance(ceiling, Mapping):
        raise ValueError("RESONANT_MEDIATION_CLAIM_CEILING_INVALID")
    if ceiling.get("P_VS_NP") != "OPEN" or ceiling.get("audio_is_proof") is not False:
        raise ValueError("RESONANT_MEDIATION_CLAIM_CEILING_INVALID")
    if ceiling.get("astral_geometry_is_proof") is not False or ceiling.get("orion_giza_architectural_intent") != "NOT_ESTABLISHED":
        raise ValueError("RESONANT_ASTRAL_CLAIM_ESCALATION")

    claimed = value.get("mediation_sha256")
    if not isinstance(claimed, str) or base.HEX64.fullmatch(claimed) is None:
        raise ValueError("RESONANT_MEDIATION_HASH_INVALID")
    core = dict(value)
    core.pop("mediation_sha256", None)
    if claimed != base.digest(core):
        raise ValueError("RESONANT_MEDIATION_HASH_TAMPERED")


def verify_mediation(value: Mapping[str, Any]) -> bool:
    try:
        validate_mediation(value)
    except (TypeError, ValueError):
        return False
    return True


def _rehash_packet(packet: dict[str, Any]) -> None:
    packet.pop("packet_sha256", None)
    packet["packet_sha256"] = base.digest(packet)


def _rehash_binding_and_packet(packet: dict[str, Any]) -> None:
    packet["representation_binding_sha256"] = base.digest(_representation_binding_core(packet))
    _rehash_packet(packet)


def _rehash_mediation(value: dict[str, Any]) -> None:
    value.pop("mediation_sha256", None)
    value["mediation_sha256"] = base.digest(value)


def self_test(packet: Mapping[str, Any], *, demihead_revision: str) -> dict[str, Any]:
    validate_resonant_packet(packet)
    intent_id = "a" * 64
    mediation = build_mediation(intent_id, packet, demihead_revision=demihead_revision)
    validate_mediation(mediation)

    negatives: dict[str, bool] = {}

    candidate = copy.deepcopy(dict(packet))
    candidate["source"] = dict(candidate["source"])
    candidate["source"]["revision"] = "0" * 40
    _rehash_packet(candidate)
    try:
        validate_resonant_packet(candidate)
        negatives["cosmos_provider_sha_tamper"] = False
    except ValueError:
        negatives["cosmos_provider_sha_tamper"] = True

    candidate = copy.deepcopy(dict(packet))
    candidate["representation_binding_sha256"] = "0" * 64
    _rehash_packet(candidate)
    try:
        validate_resonant_packet(candidate)
        negatives["representation_binding_tamper"] = False
    except ValueError:
        negatives["representation_binding_tamper"] = True

    candidate = copy.deepcopy(dict(packet))
    candidate["astral_representation"] = dict(candidate["astral_representation"])
    candidate["astral_representation"]["authority_delta"] = 1
    _rehash_binding_and_packet(candidate)
    try:
        validate_resonant_packet(candidate)
        negatives["astral_authority_escalation"] = False
    except ValueError:
        negatives["astral_authority_escalation"] = True

    candidate = copy.deepcopy(dict(packet))
    candidate["astral_representation"] = dict(candidate["astral_representation"])
    candidate["astral_representation"]["janus_rebus_alias_is_historical_transliteration"] = True
    _rehash_binding_and_packet(candidate)
    try:
        validate_resonant_packet(candidate)
        negatives["rebus_historical_transliteration_escalation"] = False
    except ValueError:
        negatives["rebus_historical_transliteration_escalation"] = True

    candidate = copy.deepcopy(dict(packet))
    candidate["lineage_representation"] = dict(candidate["lineage_representation"])
    candidate["lineage_representation"]["memory_may_propose_not_verdict"] = False
    _rehash_binding_and_packet(candidate)
    try:
        validate_resonant_packet(candidate)
        negatives["lineage_verdict_escalation"] = False
    except ValueError:
        negatives["lineage_verdict_escalation"] = True

    candidate = copy.deepcopy(mediation)
    candidate["control"] = dict(candidate["control"])
    candidate["control"]["direct_cosmos_to_echo_route_used"] = True
    _rehash_mediation(candidate)
    negatives["direct_cosmos_to_echo"] = not verify_mediation(candidate)

    candidate = copy.deepcopy(mediation)
    candidate["resonant_representation"] = dict(candidate["resonant_representation"])
    candidate["resonant_representation"]["authority_delta"] = 1
    _rehash_mediation(candidate)
    negatives["mediation_authority_escalation"] = not verify_mediation(candidate)

    if not all(negatives.values()):
        raise AssertionError(f"NEXUS_V2_9_NEGATIVE_FAILED:{negatives}")
    return {
        "status": "PASS_KEEP_NEXUS_V2_9_RESONANT_ORION_PYRAMID_CHAIN",
        "cosmos_revision": COSMOS_SHA,
        "packet_sha256": packet["packet_sha256"],
        "origin_prime_state_commitment": packet["origin_prime"]["state_commitment"],
        "representation_binding_sha256": packet["representation_binding_sha256"],
        "lineage_transfer_present": bool(packet["lineage_representation"].get("transfer_present")),
        "voice_profile": packet["voice_representation"]["profile_id"],
        "orion_anchor": packet["astral_representation"]["anchor_id"],
        "negative_controls": negatives,
        "authority_delta": 0,
        "P_VS_NP": "OPEN",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead Nexus v2.9 mediator for Cosmos resonant ORIGIN_PRIME -> Voice -> Pyramid")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--intent-id", default="a" * 64)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--output-label", default="osiris_origin_prime_resonant")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    if args.self_test:
        result: Any = self_test(packet, demihead_revision=args.source_revision)
    else:
        result = build_mediation(args.intent_id, packet, demihead_revision=args.source_revision, output_label=args.output_label)
        validate_mediation(result)
    text = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
