from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any

import hemisphere_bridge as bridge_v2
from goldprompt_intent_handoff import build_handoff, sha256, verify_anchor, verify_handoff

PACKET_SCHEMA = "janus.demihead.hemisphere_packet.v3"
BRIDGE_CONTRACT = "JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V3"
RESULT_SCHEMA = "janus.demihead.intent_bound_bicameral_result.v1"
INTENT_CHAIN_SCHEMA = "janus.goldprompt.intent_chain.v1"
DEMIHEAD_FACE_ID = "DEMIHEAD_ARBITER"


def packet_sha256(packet: dict[str, Any]) -> str:
    return sha256(packet)


def _legacy_projection(packet: dict[str, Any]) -> dict[str, Any]:
    projected = copy.deepcopy(packet)
    projected["schema"] = bridge_v2.PACKET_SCHEMA
    projected["source"]["bridge_contract"] = bridge_v2.BRIDGE_CONTRACT
    projected["source"].pop("intent_id", None)
    projected["source"].pop("intent_handoff_sha256", None)
    projected.pop("intent_anchor", None)
    projected.pop("intent_handoff", None)
    return projected


def validate_intent_bound_packet(packet: dict[str, Any], expected_hemisphere: str) -> None:
    if not isinstance(packet, dict) or packet.get("schema") != PACKET_SCHEMA:
        raise ValueError(f"{expected_hemisphere}:INTENT_BOUND_PACKET_V3_REQUIRED")
    if packet.get("hemisphere") != expected_hemisphere:
        raise ValueError(f"{expected_hemisphere}:HEMISPHERE_MISMATCH")
    source = packet.get("source")
    if not isinstance(source, dict) or source.get("bridge_contract") != BRIDGE_CONTRACT:
        raise ValueError(f"{expected_hemisphere}:BRIDGE_CONTRACT_V3_REQUIRED")
    anchor = packet.get("intent_anchor")
    handoff = packet.get("intent_handoff")
    if not isinstance(anchor, dict) or not verify_anchor(anchor):
        raise ValueError(f"{expected_hemisphere}:INTENT_ANCHOR_INVALID")
    if not isinstance(handoff, dict) or not verify_handoff(anchor, handoff, expected_hemisphere):
        raise ValueError(f"{expected_hemisphere}:INTENT_HANDOFF_INVALID")
    if source.get("intent_id") != anchor.get("intent_id"):
        raise ValueError(f"{expected_hemisphere}:PACKET_INTENT_ID_BINDING_MISMATCH")
    if source.get("intent_handoff_sha256") != handoff.get("handoff_sha256"):
        raise ValueError(f"{expected_hemisphere}:PACKET_INTENT_HANDOFF_BINDING_MISMATCH")
    bridge_v2.validate_packet(_legacy_projection(packet), expected_hemisphere)


def _build_intent_chain(
    anchor: dict[str, Any],
    left: dict[str, Any],
    right: dict[str, Any],
    demihead_handoff: dict[str, Any],
) -> dict[str, Any]:
    core = {
        "schema": INTENT_CHAIN_SCHEMA,
        "intent_id": anchor["intent_id"],
        "current_turn_digest": anchor["current_turn_digest"],
        "requested_operation": anchor["requested_operation"],
        "primary_entities": sorted(anchor["primary_entities"]),
        "upstream": {
            "LEFT_HRAIN": {
                "handoff_sha256": left["intent_handoff"]["handoff_sha256"],
                "packet_sha256": packet_sha256(left),
            },
            "RIGHT_INAIHR": {
                "handoff_sha256": right["intent_handoff"]["handoff_sha256"],
                "packet_sha256": packet_sha256(right),
            },
        },
        "demihead": {
            "face_id": DEMIHEAD_FACE_ID,
            "handoff_sha256": demihead_handoff["handoff_sha256"],
        },
        "binding_scope": "CURRENT_TURN_TO_LEFT_RIGHT_TO_DEMIHEAD_WITHOUT_INTENT_REINTERPRETATION",
        "all_handoffs_same_intent": True,
        "emergent_association_may_replace_intent": False,
        "authority_delta": 0,
    }
    return {**core, "intent_chain_sha256": sha256(core)}


def combine_intent_bound_packets(*, left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    validate_intent_bound_packet(left, "LEFT_HRAIN")
    validate_intent_bound_packet(right, "RIGHT_INAIHR")

    left_anchor = left["intent_anchor"]
    right_anchor = right["intent_anchor"]
    if left_anchor != right_anchor:
        raise ValueError("DEMIHEAD_INTENT_SPLIT_ANCHOR_MISMATCH")
    anchor = copy.deepcopy(left_anchor)
    if left["intent_handoff"]["intent_id"] != right["intent_handoff"]["intent_id"]:
        raise ValueError("DEMIHEAD_INTENT_SPLIT_ID_MISMATCH")
    if left["intent_handoff"]["requested_operation"] != right["intent_handoff"]["requested_operation"]:
        raise ValueError("DEMIHEAD_INTENT_SPLIT_OPERATION_MISMATCH")

    bicameral = bridge_v2.combine_packets(
        left=_legacy_projection(left),
        right=_legacy_projection(right),
    )
    demihead_handoff = build_handoff(anchor, DEMIHEAD_FACE_ID, 2)
    if not verify_handoff(anchor, demihead_handoff, DEMIHEAD_FACE_ID):
        raise ValueError("DEMIHEAD_INTENT_HANDOFF_SELF_VERIFY_FAILED")
    intent_chain = _build_intent_chain(anchor, left, right, demihead_handoff)

    return {
        "schema": RESULT_SCHEMA,
        "intent_anchor": anchor,
        "upstream_intent_handoffs": {
            "LEFT_HRAIN": copy.deepcopy(left["intent_handoff"]),
            "RIGHT_INAIHR": copy.deepcopy(right["intent_handoff"]),
        },
        "demihead_intent_handoff": demihead_handoff,
        "intent_chain": intent_chain,
        "bicameral_result": bicameral,
        "routing": {
            "intent_alignment_required": True,
            "intent_split_permitted": False,
            "older_context_may_redefine_task": False,
            "optional_association_may_replace_primary_path": False,
        },
        "claim_ceiling": {
            "intent_chain_is_factual_correctness": False,
            "intent_alignment_is_truth": False,
            "intent_alignment_is_human_consent": False,
            "authority_delta": 0,
        },
    }


def verify_intent_bound_result(
    result: dict[str, Any],
    *,
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    try:
        if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA:
            return False
        validate_intent_bound_packet(left, "LEFT_HRAIN")
        validate_intent_bound_packet(right, "RIGHT_INAIHR")
        anchor = result.get("intent_anchor")
        if anchor != left.get("intent_anchor") or anchor != right.get("intent_anchor") or not verify_anchor(anchor):
            return False
        upstream = result.get("upstream_intent_handoffs")
        if not isinstance(upstream, dict) or upstream.get("LEFT_HRAIN") != left.get("intent_handoff") or upstream.get("RIGHT_INAIHR") != right.get("intent_handoff"):
            return False
        own = result.get("demihead_intent_handoff")
        if not isinstance(own, dict) or not verify_handoff(anchor, own, DEMIHEAD_FACE_ID):
            return False
        chain = result.get("intent_chain")
        if not isinstance(chain, dict):
            return False
        expected = _build_intent_chain(anchor, left, right, own)
        if chain != expected:
            return False
        bicameral = result.get("bicameral_result")
        if not isinstance(bicameral, dict) or not bridge_v2.verify_receipt_chain_result(bicameral):
            return False
        routing = result.get("routing")
        if routing != {
            "intent_alignment_required": True,
            "intent_split_permitted": False,
            "older_context_may_redefine_task": False,
            "optional_association_may_replace_primary_path": False,
        }:
            return False
        return result.get("claim_ceiling") == {
            "intent_chain_is_factual_correctness": False,
            "intent_alignment_is_truth": False,
            "intent_alignment_is_human_consent": False,
            "authority_delta": 0,
        }
    except (KeyError, TypeError, ValueError):
        return False


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}:JSON_OBJECT_REQUIRED")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description="Strict intent-bound DemiHead bicameral bridge v3.")
    parser.add_argument("--left", type=Path, required=True)
    parser.add_argument("--right", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    try:
        left, right = load_json(args.left), load_json(args.right)
        result = combine_intent_bound_packets(left=left, right=right)
        if not verify_intent_bound_result(result, left=left, right=right):
            raise ValueError("DEMIHEAD_INTENT_BOUND_RESULT_SELF_VERIFY_FAILED")
        text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
        if args.output:
            args.output.write_text(text, encoding="utf-8")
        else:
            sys.stdout.write(text)
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"hemisphere_bridge_intent_v3: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
