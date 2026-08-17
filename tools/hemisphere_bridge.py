from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from goldprompt_handshake import build_receipt as build_goldprompt_receipt, verify_receipt as verify_goldprompt_receipt


PACKET_SCHEMA = "janus.demihead.hemisphere_packet.v1"
RESULT_SCHEMA = "janus.demihead.bicameral_result.v1"
BRIDGE_CONTRACT = "JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V1"

HEMISPHERE_RULES = {
    "LEFT_HRAIN": {
        "role": "STRUCTURAL_CONTEXT",
        "repository": "Hawkar-usls/Hrain",
        "workspace_mode": "LOCAL_EDITABLE_GRAPH",
    },
    "RIGHT_INAIHR": {
        "role": "ASSOCIATIVE_CONTEXT",
        "repository": "Hawkar-usls/iNaiHR",
        "workspace_mode": "SEMANTIC_GRAPH",
    },
}

ORIGINS = (
    "USER",
    "REMOTE_AI",
    "LOCAL_FALLBACK",
    "LEGACY_UNKNOWN",
    "SYSTEM",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def packet_sha256(packet: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(packet)).hexdigest()


def semantic_key(label: str) -> str:
    """Return a conservative comparison key without claiming semantic equivalence.

    Browser workspaces often decorate labels with one leading emoji token.  The
    bridge strips only leading non-alphanumeric decoration, folds whitespace and
    case, and then compares exact resulting strings.  This is deliberately much
    weaker than semantic similarity.
    """

    text = " ".join(label.strip().split())
    if not text:
        return ""

    # Drop leading symbols/punctuation/spacing until the first letter or number.
    index = 0
    for index, char in enumerate(text):
        category = unicodedata.category(char)
        if category[0] in {"L", "N"}:
            break
    else:
        return text.casefold()

    text = text[index:]
    return re.sub(r"\s+", " ", text).casefold().strip()


def _endpoint_id(value: Any) -> str:
    if isinstance(value, bool):
        raise ValueError("Boolean node/link identifiers are not allowed")
    if isinstance(value, (str, int)):
        return str(value)
    raise ValueError("Node/link identifiers must be string or integer")


def validate_packet(packet: dict[str, Any], expected_hemisphere: str | None = None) -> None:
    if not isinstance(packet, dict):
        raise ValueError("Hemisphere packet must be a JSON object")
    if packet.get("schema") != PACKET_SCHEMA:
        raise ValueError(f"Unexpected packet schema: {packet.get('schema')!r}")

    hemisphere = packet.get("hemisphere")
    if hemisphere not in HEMISPHERE_RULES:
        raise ValueError(f"Unknown hemisphere: {hemisphere!r}")
    if expected_hemisphere is not None and hemisphere != expected_hemisphere:
        raise ValueError(
            f"Expected {expected_hemisphere}, received packet for {hemisphere}"
        )

    rules = HEMISPHERE_RULES[hemisphere]
    if packet.get("role") != rules["role"]:
        raise ValueError(f"{hemisphere} role mismatch")

    source = packet.get("source")
    if not isinstance(source, dict):
        raise ValueError("Packet source must be an object")
    if source.get("repository") != rules["repository"]:
        raise ValueError(f"{hemisphere} repository mismatch")
    if source.get("workspace_mode") != rules["workspace_mode"]:
        raise ValueError(f"{hemisphere} workspace mode mismatch")
    if source.get("bridge_contract") != BRIDGE_CONTRACT:
        raise ValueError("Bridge contract mismatch")

    control = packet.get("control")
    if not isinstance(control, dict):
        raise ValueError("Packet control must be an object")
    if control.get("read_only_transfer") is not True:
        raise ValueError("Hemisphere transfer must be explicitly read-only")
    if control.get("direct_cross_hemisphere_mutation") is not False:
        raise ValueError("Direct cross-hemisphere mutation is forbidden")
    if control.get("authority_delta") != 0:
        raise ValueError("Hemisphere packet cannot change authority")
    if control.get("mass_effect_budget_delta") != 0:
        raise ValueError("Hemisphere packet cannot change mass-effect budget")

    graph = packet.get("graph")
    if not isinstance(graph, dict):
        raise ValueError("Packet graph must be an object")
    nodes = graph.get("nodes")
    links = graph.get("links")
    if not isinstance(nodes, list) or not isinstance(links, list):
        raise ValueError("Packet graph nodes/links must be arrays")

    ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            raise ValueError("Every graph node must be an object")
        node_id = _endpoint_id(node.get("id"))
        if node_id in ids:
            raise ValueError(f"Duplicate node id: {node_id}")
        ids.add(node_id)
        label = node.get("label")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Node {node_id} must have a non-empty label")
        if node.get("origin") not in ORIGINS:
            raise ValueError(f"Node {node_id} has unknown origin")

    seen_links: set[tuple[str, str]] = set()
    for link in links:
        if not isinstance(link, dict):
            raise ValueError("Every graph link must be an object")
        source_id = _endpoint_id(link.get("source"))
        target_id = _endpoint_id(link.get("target"))
        if source_id not in ids or target_id not in ids:
            raise ValueError(
                f"Dangling graph link: {source_id!r} -> {target_id!r}"
            )
        edge = (source_id, target_id)
        if edge in seen_links:
            raise ValueError(f"Duplicate directed link: {source_id!r} -> {target_id!r}")
        seen_links.add(edge)


def _packet_receipt(packet: dict[str, Any]) -> dict[str, Any]:
    origin_counts = Counter(node["origin"] for node in packet["graph"]["nodes"])
    return {
        "packet_id": packet["packet_id"],
        "sha256": packet_sha256(packet),
        "repository": packet["source"]["repository"],
        "node_count": len(packet["graph"]["nodes"]),
        "link_count": len(packet["graph"]["links"]),
        "origin_counts": {origin: origin_counts.get(origin, 0) for origin in ORIGINS},
    }


def _keys(packet: dict[str, Any]) -> set[str]:
    return {
        key
        for node in packet["graph"]["nodes"]
        if (key := semantic_key(node["label"]))
    }


def combine_packets(
    *,
    left: dict[str, Any] | None = None,
    right: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if left is None and right is None:
        raise ValueError("At least one hemisphere packet is required")

    if left is not None:
        validate_packet(left, "LEFT_HRAIN")
    if right is not None:
        validate_packet(right, "RIGHT_INAIHR")

    packets = [packet for packet in (left, right) if packet is not None]
    hemispheres_present = [packet["hemisphere"] for packet in packets]
    receipts = {packet["hemisphere"]: _packet_receipt(packet) for packet in packets}

    left_keys = _keys(left) if left is not None else set()
    right_keys = _keys(right) if right is not None else set()
    shared = left_keys & right_keys

    if left is not None and right is not None:
        status = (
            "BICAMERAL_OVERLAP_PRESENT"
            if shared
            else "BICAMERAL_DIVERGENCE_PRESERVED"
        )
        mode = "BICAMERAL_REVIEW"
    else:
        status = "DEGRADED_SINGLE_HEMISPHERE"
        mode = "DEGRADED_SINGLE_HEMISPHERE_HOLD"

    goldprompt_receipt = build_goldprompt_receipt()
    if not verify_goldprompt_receipt(goldprompt_receipt):
        raise ValueError("DEMIHEAD_GOLDPROMPT_RECEIPT_SELF_VERIFY_FAILED")

    return {
        "schema": RESULT_SCHEMA,
        "goldprompt_receipt": goldprompt_receipt,
        "status": status,
        "hemispheres_present": hemispheres_present,
        "packet_receipts": receipts,
        "comparison": {
            "shared_semantic_keys": sorted(shared),
            "left_only_semantic_keys": sorted(left_keys - right_keys),
            "right_only_semantic_keys": sorted(right_keys - left_keys),
            "automatic_graph_merge_performed": False,
        },
        "routing": {
            "mode": mode,
            "external_effect_permitted": False,
            "direct_cross_hemisphere_write_permitted": False,
            "disagreement_preserved": True,
        },
        "claim_ceiling": {
            "truth_claim_made": False,
            "agreement_is_truth": False,
            "hemisphere_count_is_authority": False,
            "association_is_evidence": False,
            "structure_is_command": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def load_packet(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        packet = json.load(handle)
    if not isinstance(packet, dict):
        raise ValueError(f"{path}: expected top-level object")
    return packet


def _example_packet(hemisphere: str) -> dict[str, Any]:
    rules = HEMISPHERE_RULES[hemisphere]
    if hemisphere == "LEFT_HRAIN":
        nodes = [
            {"id": 1, "label": "Context", "origin": "USER", "type": "default"},
            {"id": 2, "label": "Evidence", "origin": "USER", "type": "info"},
        ]
    else:
        nodes = [
            {"id": 1, "label": "🧩 Context", "origin": "SYSTEM", "is_ai": False},
            {"id": 2, "label": "🔎 Relation", "origin": "LOCAL_FALLBACK", "is_ai": False},
        ]
    return {
        "schema": PACKET_SCHEMA,
        "packet_id": f"selftest-{hemisphere.lower()}",
        "hemisphere": hemisphere,
        "role": rules["role"],
        "captured_at": "2026-08-16T08:53:00Z",
        "source": {
            "repository": rules["repository"],
            "bridge_contract": BRIDGE_CONTRACT,
            "source_revision": None,
            "workspace_mode": rules["workspace_mode"],
        },
        "graph": {"nodes": nodes, "links": [{"source": 1, "target": 2}]},
        "control": {
            "read_only_transfer": True,
            "direct_cross_hemisphere_mutation": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def self_test() -> dict[str, Any]:
    left = _example_packet("LEFT_HRAIN")
    right = _example_packet("RIGHT_INAIHR")
    result = combine_packets(left=left, right=right)

    checks: dict[str, bool] = {
        "shared_context_detected_without_semantic_model": result["comparison"]["shared_semantic_keys"] == ["context"],
        "goldprompt_startup_receipt_self_verifies": verify_goldprompt_receipt(result["goldprompt_receipt"]),
        "agreement_does_not_become_truth": result["claim_ceiling"]["agreement_is_truth"] is False,
        "two_hemispheres_do_not_gain_authority": result["claim_ceiling"]["authority_delta"] == 0,
        "automatic_graph_merge_is_disabled": result["comparison"]["automatic_graph_merge_performed"] is False,
        "direct_cross_write_is_disabled": result["routing"]["direct_cross_hemisphere_write_permitted"] is False,
        "single_hemisphere_degrades_to_hold": combine_packets(left=left)["routing"]["mode"] == "DEGRADED_SINGLE_HEMISPHERE_HOLD",
    }

    bad = json.loads(json.dumps(left))
    bad["control"]["direct_cross_hemisphere_mutation"] = True
    try:
        combine_packets(left=bad)
    except ValueError:
        checks["direct_mutation_request_fails_closed"] = True
    else:
        checks["direct_mutation_request_fails_closed"] = False

    dangling = json.loads(json.dumps(right))
    dangling["graph"]["links"].append({"source": 2, "target": 999})
    try:
        combine_packets(right=dangling)
    except ValueError:
        checks["dangling_link_fails_closed"] = True
    else:
        checks["dangling_link_fails_closed"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "result": result,
    }


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Bind read-only HRain/iNaiHR hemisphere packets without merging authority."
    )
    parser.add_argument("--left", type=Path, help="LEFT_HRAIN packet JSON")
    parser.add_argument("--right", type=Path, help="RIGHT_INAIHR packet JSON")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    try:
        if args.self_test:
            result = self_test()
            write_json(result, args.output)
            return 0 if result["status"] == "PASS" else 1

        if args.left is None and args.right is None:
            parser.error("provide --left and/or --right, or use --self-test")

        left = load_packet(args.left) if args.left is not None else None
        right = load_packet(args.right) if args.right is not None else None
        result = combine_packets(left=left, right=right)
        write_json(result, args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"hemisphere_bridge: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
