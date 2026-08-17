from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Mapping

ANCHOR_SCHEMA = "janus.goldprompt.intent_anchor.v1"
HANDOFF_SCHEMA = "janus.goldprompt.intent_handoff.v1"
CONTEXT_TIERS = {
    0: "CURRENT_EXPLICIT_USER_REQUEST",
    1: "IMMEDIATELY_REQUIRED_RECENT_REFERENTS",
    2: "ACTIVE_PROJECT_CONSTRAINTS_REQUIRED_FOR_CORRECTNESS",
    3: "OLDER_RELEVANT_CONTEXT",
    4: "ASSOCIATIVE_OR_EMERGENT_CONTEXT",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ANCHOR_KEYS = {
    "schema", "current_turn_digest", "requested_operation", "primary_entities",
    "must_answer_points", "required_answer_evidence", "operation_markers",
    "optional_association_markers", "explicit_constraints",
    "allow_anaphoric_continuation", "context_priority", "intent_id",
}
HANDOFF_KEYS = {
    "schema", "intent_id", "current_turn_digest", "requested_operation",
    "primary_entities", "must_answer_points", "face_id", "context_tier_used",
    "context_tier_name", "handoff_sha256",
}


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(isinstance(item, str) and item.strip() for item in value)


def verify_anchor(anchor: Mapping[str, Any]) -> bool:
    if not isinstance(anchor, Mapping) or set(anchor) != ANCHOR_KEYS:
        return False
    if anchor.get("schema") != ANCHOR_SCHEMA:
        return False
    if not isinstance(anchor.get("current_turn_digest"), str) or HEX64.fullmatch(anchor["current_turn_digest"]) is None:
        return False
    if not isinstance(anchor.get("intent_id"), str) or HEX64.fullmatch(anchor["intent_id"]) is None:
        return False
    if not isinstance(anchor.get("requested_operation"), str) or not anchor["requested_operation"].strip():
        return False
    entities = anchor.get("primary_entities")
    if not isinstance(entities, Mapping) or not entities:
        return False
    for entity, aliases in entities.items():
        if not isinstance(entity, str) or not entity.strip() or not _string_list(aliases):
            return False
    if not _string_list(anchor.get("must_answer_points")):
        return False
    evidence = anchor.get("required_answer_evidence")
    if not isinstance(evidence, list) or not all(_string_list(group) for group in evidence):
        return False
    for key in ("operation_markers", "optional_association_markers", "explicit_constraints"):
        value = anchor.get(key)
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            return False
    if not isinstance(anchor.get("allow_anaphoric_continuation"), bool):
        return False
    if anchor.get("context_priority") != [CONTEXT_TIERS[i] for i in sorted(CONTEXT_TIERS)]:
        return False
    payload = dict(anchor)
    payload.pop("intent_id", None)
    return sha256(payload) == anchor["intent_id"]


def build_handoff(anchor: Mapping[str, Any], face_id: str, context_tier_used: int = 2) -> dict[str, Any]:
    if not verify_anchor(anchor):
        raise ValueError("GOLDPROMPT_INTENT_ANCHOR_INVALID")
    if context_tier_used not in CONTEXT_TIERS:
        raise ValueError("GOLDPROMPT_CONTEXT_TIER_INVALID")
    handoff = {
        "schema": HANDOFF_SCHEMA,
        "intent_id": anchor["intent_id"],
        "current_turn_digest": anchor["current_turn_digest"],
        "requested_operation": anchor["requested_operation"],
        "primary_entities": sorted(anchor["primary_entities"]),
        "must_answer_points": list(anchor["must_answer_points"]),
        "face_id": str(face_id),
        "context_tier_used": context_tier_used,
        "context_tier_name": CONTEXT_TIERS[context_tier_used],
    }
    handoff["handoff_sha256"] = sha256(handoff)
    return handoff


def verify_handoff(anchor: Mapping[str, Any], handoff: Mapping[str, Any], expected_face_id: str) -> bool:
    if not verify_anchor(anchor) or not isinstance(handoff, Mapping) or set(handoff) != HANDOFF_KEYS:
        return False
    required = {
        "schema": HANDOFF_SCHEMA,
        "intent_id": anchor["intent_id"],
        "current_turn_digest": anchor["current_turn_digest"],
        "requested_operation": anchor["requested_operation"],
        "primary_entities": sorted(anchor["primary_entities"]),
        "must_answer_points": list(anchor["must_answer_points"]),
        "face_id": str(expected_face_id),
    }
    if any(handoff.get(key) != value for key, value in required.items()):
        return False
    tier = handoff.get("context_tier_used")
    if tier not in CONTEXT_TIERS or handoff.get("context_tier_name") != CONTEXT_TIERS[tier]:
        return False
    claimed = handoff.get("handoff_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        return False
    payload = dict(handoff)
    payload.pop("handoff_sha256", None)
    return sha256(payload) == claimed
