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

from goldprompt_handshake import (
    _sha256,
    build_receipt as build_goldprompt_receipt,
    build_upstream_fixture_receipt,
    verify_receipt as verify_goldprompt_receipt,
    verify_upstream_receipt,
)

PACKET_SCHEMA = "janus.demihead.hemisphere_packet.v2"
RESULT_SCHEMA = "janus.demihead.bicameral_result.v2"
CHAIN_SCHEMA = "janus.goldprompt.receipt_chain.v1"
BRIDGE_CONTRACT = "JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V2"

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

ORIGINS = ("USER", "REMOTE_AI", "LOCAL_FALLBACK", "LEGACY_UNKNOWN", "SYSTEM")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def packet_sha256(packet: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(packet)).hexdigest()


def semantic_key(label: str) -> str:
    text = " ".join(label.strip().split())
    if not text:
        return ""
    for index, char in enumerate(text):
        if unicodedata.category(char)[0] in {"L", "N"}:
            text = text[index:]
            break
    else:
        return text.casefold()
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
        raise ValueError(f"Expected {expected_hemisphere}, received packet for {hemisphere}")
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
    source_revision = source.get("source_revision")
    if not isinstance(source_revision, str) or re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", source_revision) is None:
        raise ValueError("Packet source revision must be a Git-shaped digest")

    upstream_receipt = packet.get("goldprompt_receipt")
    if not isinstance(upstream_receipt, dict) or not verify_upstream_receipt(upstream_receipt, hemisphere):
        raise ValueError(f"{hemisphere} upstream GoldPrompt receipt invalid")
    if upstream_receipt.get("source_revision") != source_revision:
        raise ValueError(f"{hemisphere} packet/receipt source revision mismatch")
    if upstream_receipt.get("repository") != source.get("repository"):
        raise ValueError(f"{hemisphere} packet/receipt repository mismatch")
    if source.get("goldprompt_receipt_sha256") != upstream_receipt.get("receipt_sha256"):
        raise ValueError(f"{hemisphere} packet/receipt SHA binding mismatch")

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
    nodes, links = graph.get("nodes"), graph.get("links")
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
        source_id, target_id = _endpoint_id(link.get("source")), _endpoint_id(link.get("target"))
        if source_id not in ids or target_id not in ids:
            raise ValueError(f"Dangling graph link: {source_id!r} -> {target_id!r}")
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
        "source_revision": packet["source"]["source_revision"],
        "upstream_goldprompt_receipt_sha256": packet["goldprompt_receipt"]["receipt_sha256"],
        "node_count": len(packet["graph"]["nodes"]),
        "link_count": len(packet["graph"]["links"]),
        "origin_counts": {origin: origin_counts.get(origin, 0) for origin in ORIGINS},
    }


def _keys(packet: dict[str, Any]) -> set[str]:
    return {key for node in packet["graph"]["nodes"] if (key := semantic_key(node["label"]))}


def _build_receipt_chain(
    packets: list[dict[str, Any]],
    packet_receipts: dict[str, dict[str, Any]],
    demihead_receipt: dict[str, Any],
) -> dict[str, Any]:
    upstream: dict[str, Any] = {}
    for packet in packets:
        hemisphere = packet["hemisphere"]
        upstream[hemisphere] = {
            "repository": packet["source"]["repository"],
            "source_revision": packet["source"]["source_revision"],
            "receipt_sha256": packet["goldprompt_receipt"]["receipt_sha256"],
            "packet_sha256": packet_receipts[hemisphere]["sha256"],
        }
    core = {
        "schema": CHAIN_SCHEMA,
        "upstream": upstream,
        "demihead": {
            "repository": demihead_receipt["repository"],
            "source_revision": demihead_receipt["source_revision"],
            "receipt_sha256": demihead_receipt["receipt_sha256"],
        },
        "binding_scope": "UPSTREAM_FACE_RECEIPT_TO_PACKET_TO_DEMIHEAD_RESULT",
        "canonical_bicameral_chain_complete": set(upstream) == {"LEFT_HRAIN", "RIGHT_INAIHR"},
        "end_to_end_receipt_binding_established": set(upstream) == {"LEFT_HRAIN", "RIGHT_INAIHR"},
        "origin_authentication_established": False,
        "live_process_identity_established": False,
        "authority_delta": 0,
    }
    return {**core, "chain_sha256": _sha256(core)}


def verify_receipt_chain_result(result: dict[str, Any]) -> bool:
    if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA:
        return False
    own = result.get("goldprompt_receipt")
    if not isinstance(own, dict) or not verify_goldprompt_receipt(own):
        return False
    hemispheres = result.get("hemispheres_present")
    upstream = result.get("upstream_goldprompt_receipts")
    packet_receipts = result.get("packet_receipts")
    chain = result.get("receipt_chain")
    if not isinstance(hemispheres, list) or not isinstance(upstream, dict) or not isinstance(packet_receipts, dict) or not isinstance(chain, dict):
        return False
    if set(upstream) != set(hemispheres) or set(packet_receipts) != set(hemispheres):
        return False
    for hemisphere in hemispheres:
        receipt = upstream.get(hemisphere)
        packet_receipt = packet_receipts.get(hemisphere)
        if not isinstance(receipt, dict) or not verify_upstream_receipt(receipt, hemisphere):
            return False
        if not isinstance(packet_receipt, dict):
            return False
        if packet_receipt.get("upstream_goldprompt_receipt_sha256") != receipt.get("receipt_sha256"):
            return False
        chain_entry = chain.get("upstream", {}).get(hemisphere) if isinstance(chain.get("upstream"), dict) else None
        expected_entry = {
            "repository": receipt["repository"],
            "source_revision": receipt["source_revision"],
            "receipt_sha256": receipt["receipt_sha256"],
            "packet_sha256": packet_receipt.get("sha256"),
        }
        if chain_entry != expected_entry:
            return False
    expected_core = {
        "schema": CHAIN_SCHEMA,
        "upstream": chain.get("upstream"),
        "demihead": {
            "repository": own["repository"],
            "source_revision": own["source_revision"],
            "receipt_sha256": own["receipt_sha256"],
        },
        "binding_scope": "UPSTREAM_FACE_RECEIPT_TO_PACKET_TO_DEMIHEAD_RESULT",
        "canonical_bicameral_chain_complete": set(hemispheres) == {"LEFT_HRAIN", "RIGHT_INAIHR"},
        "end_to_end_receipt_binding_established": set(hemispheres) == {"LEFT_HRAIN", "RIGHT_INAIHR"},
        "origin_authentication_established": False,
        "live_process_identity_established": False,
        "authority_delta": 0,
    }
    if any(chain.get(key) != value for key, value in expected_core.items()):
        return False
    return chain.get("chain_sha256") == _sha256(expected_core)


def combine_packets(*, left: dict[str, Any] | None = None, right: dict[str, Any] | None = None) -> dict[str, Any]:
    if left is None and right is None:
        raise ValueError("At least one hemisphere packet is required")
    if left is not None:
        validate_packet(left, "LEFT_HRAIN")
    if right is not None:
        validate_packet(right, "RIGHT_INAIHR")

    packets = [packet for packet in (left, right) if packet is not None]
    hemispheres_present = [packet["hemisphere"] for packet in packets]
    packet_receipts = {packet["hemisphere"]: _packet_receipt(packet) for packet in packets}
    upstream_receipts = {packet["hemisphere"]: json.loads(json.dumps(packet["goldprompt_receipt"])) for packet in packets}

    left_keys = _keys(left) if left is not None else set()
    right_keys = _keys(right) if right is not None else set()
    shared = left_keys & right_keys
    if left is not None and right is not None:
        status = "BICAMERAL_OVERLAP_PRESENT" if shared else "BICAMERAL_DIVERGENCE_PRESERVED"
        mode = "BICAMERAL_REVIEW"
    else:
        status = "DEGRADED_SINGLE_HEMISPHERE"
        mode = "DEGRADED_SINGLE_HEMISPHERE_HOLD"

    goldprompt_receipt = build_goldprompt_receipt()
    if not verify_goldprompt_receipt(goldprompt_receipt):
        raise ValueError("DEMIHEAD_GOLDPROMPT_RECEIPT_SELF_VERIFY_FAILED")
    chain = _build_receipt_chain(packets, packet_receipts, goldprompt_receipt)

    result = {
        "schema": RESULT_SCHEMA,
        "goldprompt_receipt": goldprompt_receipt,
        "upstream_goldprompt_receipts": upstream_receipts,
        "receipt_chain": chain,
        "status": status,
        "hemispheres_present": hemispheres_present,
        "packet_receipts": packet_receipts,
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
    if not verify_receipt_chain_result(result):
        raise ValueError("DEMIHEAD_RECEIPT_CHAIN_SELF_VERIFY_FAILED")
    return result


def load_packet(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        packet = json.load(handle)
    if not isinstance(packet, dict):
        raise ValueError(f"{path}: expected top-level object")
    return packet


def _example_packet(hemisphere: str) -> dict[str, Any]:
    rules = HEMISPHERE_RULES[hemisphere]
    source_revision = ("a" if hemisphere == "LEFT_HRAIN" else "b") * 40
    upstream_receipt = build_upstream_fixture_receipt(hemisphere, source_revision)
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
            "source_revision": source_revision,
            "goldprompt_receipt_sha256": upstream_receipt["receipt_sha256"],
            "workspace_mode": rules["workspace_mode"],
        },
        "goldprompt_receipt": upstream_receipt,
        "graph": {"nodes": nodes, "links": [{"source": 1, "target": 2}]},
        "control": {
            "read_only_transfer": True,
            "direct_cross_hemisphere_mutation": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }


def self_test() -> dict[str, Any]:
    left, right = _example_packet("LEFT_HRAIN"), _example_packet("RIGHT_INAIHR")
    result = combine_packets(left=left, right=right)
    checks: dict[str, bool] = {
        "shared_context_detected_without_semantic_model": result["comparison"]["shared_semantic_keys"] == ["context"],
        "goldprompt_startup_receipt_self_verifies": verify_goldprompt_receipt(result["goldprompt_receipt"]),
        "upstream_receipts_verified_before_analysis": all(verify_upstream_receipt(result["upstream_goldprompt_receipts"][h], h) for h in ("LEFT_HRAIN", "RIGHT_INAIHR")),
        "canonical_receipt_chain_complete": result["receipt_chain"]["canonical_bicameral_chain_complete"] is True,
        "end_to_end_receipt_binding_established": result["receipt_chain"]["end_to_end_receipt_binding_established"] is True,
        "origin_authentication_not_overclaimed": result["receipt_chain"]["origin_authentication_established"] is False,
        "receipt_chain_self_verifies": verify_receipt_chain_result(result),
        "agreement_does_not_become_truth": result["claim_ceiling"]["agreement_is_truth"] is False,
        "two_hemispheres_do_not_gain_authority": result["claim_ceiling"]["authority_delta"] == 0,
        "automatic_graph_merge_is_disabled": result["comparison"]["automatic_graph_merge_performed"] is False,
        "single_hemisphere_chain_not_canonical": combine_packets(left=left)["receipt_chain"]["end_to_end_receipt_binding_established"] is False,
    }

    adversarial: list[tuple[str, dict[str, Any], str]] = []
    bad = json.loads(json.dumps(left)); bad["control"]["direct_cross_hemisphere_mutation"] = True
    adversarial.append(("direct_mutation_request_fails_closed", bad, "LEFT_HRAIN"))
    bad = json.loads(json.dumps(left)); bad["source"]["goldprompt_receipt_sha256"] = "0" * 64
    adversarial.append(("packet_receipt_hash_drift_fails_closed", bad, "LEFT_HRAIN"))
    bad = json.loads(json.dumps(left)); bad["goldprompt_receipt"] = json.loads(json.dumps(right["goldprompt_receipt"])); bad["source"]["goldprompt_receipt_sha256"] = bad["goldprompt_receipt"]["receipt_sha256"]
    adversarial.append(("upstream_receipt_swap_fails_closed", bad, "LEFT_HRAIN"))
    bad = json.loads(json.dumps(left)); bad.pop("goldprompt_receipt")
    adversarial.append(("missing_upstream_receipt_fails_closed", bad, "LEFT_HRAIN"))
    for name, packet, hemisphere in adversarial:
        try:
            validate_packet(packet, hemisphere)
        except ValueError:
            checks[name] = True
        else:
            checks[name] = False

    tampered_result = json.loads(json.dumps(result))
    tampered_result["receipt_chain"]["chain_sha256"] = "0" * 64
    checks["chain_hash_tamper_fails_closed"] = verify_receipt_chain_result(tampered_result) is False

    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "result": result}


def write_json(value: Any, output: Path | None) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if output is None:
        sys.stdout.write(text)
    else:
        output.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Bind receipt-carrying HRain/iNaiHR packets without merging authority.")
    parser.add_argument("--left", type=Path)
    parser.add_argument("--right", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test(); write_json(result, args.output); return 0 if result["status"] == "PASS" else 1
        if args.left is None and args.right is None:
            parser.error("provide --left and/or --right, or use --self-test")
        left = load_packet(args.left) if args.left is not None else None
        right = load_packet(args.right) if args.right is not None else None
        write_json(combine_packets(left=left, right=right), args.output)
        return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"hemisphere_bridge: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
