from __future__ import annotations

import argparse
import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from hemisphere_bridge import validate_packet


PROPOSAL_SCHEMA = "janus.demihead.local_proposal.v1"
ENVELOPE_TYPE = "JANUS_DEMIHEAD_LOCAL_PROPOSAL_V1"
SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{8,128}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TARGETS = {
    "LEFT_HRAIN": "Hawkar-usls/Hrain",
    "RIGHT_INAIHR": "Hawkar-usls/iNaiHR",
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_json(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def validate_safe_id(value: Any, field: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value):
        raise ValueError(f"{field} must be 8-128 safe ASCII characters")
    return value


def validate_proposal(proposal: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(proposal, dict):
        raise ValueError("proposal must be an object")
    required = {"schema", "proposal_id", "created_at", "target", "base_graph_sha256", "operation", "control"}
    if set(proposal) != required:
        raise ValueError("proposal fields must match the frozen contract exactly")
    if proposal["schema"] != PROPOSAL_SCHEMA:
        raise ValueError("unexpected proposal schema")
    validate_safe_id(proposal["proposal_id"], "proposal_id")
    if not isinstance(proposal["created_at"], str) or not proposal["created_at"]:
        raise ValueError("created_at is required")
    if not isinstance(proposal["base_graph_sha256"], str) or not SHA256_RE.fullmatch(proposal["base_graph_sha256"]):
        raise ValueError("base_graph_sha256 must be lowercase SHA-256")

    target = proposal["target"]
    if not isinstance(target, dict) or set(target) != {"hemisphere", "repository"}:
        raise ValueError("target must contain only hemisphere and repository")
    hemisphere = target["hemisphere"]
    if hemisphere not in TARGETS or target["repository"] != TARGETS[hemisphere]:
        raise ValueError("target hemisphere/repository mismatch")

    operation = proposal["operation"]
    if not isinstance(operation, dict) or set(operation) != {"type", "node"}:
        raise ValueError("operation must contain only type and node")
    if operation["type"] != "ADD_NODE":
        raise ValueError("only ADD_NODE is admitted in v1")
    node = operation["node"]
    if not isinstance(node, dict) or set(node) != {"id", "label", "origin"}:
        raise ValueError("node fields must match the v1 contract exactly")
    validate_safe_id(node["id"], "node.id")
    if not isinstance(node["label"], str) or not node["label"].strip() or len(node["label"].strip()) > 240:
        raise ValueError("node.label must contain 1-240 non-whitespace characters")
    if node["label"] != node["label"].strip():
        raise ValueError("node.label must be pre-trimmed")
    if node["origin"] != "SYSTEM":
        raise ValueError("DemiHead-proposed nodes must preserve SYSTEM provenance")

    control = proposal["control"]
    exact_control = {
        "auto_apply": False,
        "requires_explicit_local_accept": True,
        "direct_cross_hemisphere_write": False,
        "external_effect_permitted": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }
    if control != exact_control:
        raise ValueError("proposal control boundary drifted")
    return proposal


def build_proposal(
    packet: dict[str, Any],
    *,
    proposal_id: str,
    node_id: str,
    label: str,
    created_at: str,
) -> dict[str, Any]:
    validate_packet(packet, packet.get("hemisphere"))
    hemisphere = packet["hemisphere"]
    if hemisphere not in TARGETS:
        raise ValueError("unsupported hemisphere")
    if packet["source"]["repository"] != TARGETS[hemisphere]:
        raise ValueError("packet repository/hemisphere mismatch")
    proposal = {
        "schema": PROPOSAL_SCHEMA,
        "proposal_id": validate_safe_id(proposal_id, "proposal_id"),
        "created_at": created_at,
        "target": {
            "hemisphere": hemisphere,
            "repository": TARGETS[hemisphere],
        },
        "base_graph_sha256": sha256_json(packet["graph"]),
        "operation": {
            "type": "ADD_NODE",
            "node": {
                "id": validate_safe_id(node_id, "node_id"),
                "label": label.strip(),
                "origin": "SYSTEM",
            },
        },
        "control": {
            "auto_apply": False,
            "requires_explicit_local_accept": True,
            "direct_cross_hemisphere_write": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    return validate_proposal(proposal)


def envelope(proposal: dict[str, Any]) -> dict[str, Any]:
    checked = validate_proposal(deepcopy(proposal))
    return {
        "type": ENVELOPE_TYPE,
        "proposal_sha256": sha256_json(checked),
        "proposal": checked,
    }


def validate_envelope(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"type", "proposal_sha256", "proposal"}:
        raise ValueError("proposal envelope fields drifted")
    if value["type"] != ENVELOPE_TYPE:
        raise ValueError("unexpected proposal envelope type")
    if not isinstance(value["proposal_sha256"], str) or not SHA256_RE.fullmatch(value["proposal_sha256"]):
        raise ValueError("proposal_sha256 must be lowercase SHA-256")
    validate_proposal(value["proposal"])
    actual = sha256_json(value["proposal"])
    if actual != value["proposal_sha256"]:
        raise ValueError("proposal hash mismatch")
    return value


def self_test() -> dict[str, Any]:
    left = json.loads((Path(__file__).resolve().parents[1] / "examples" / "hemisphere_left_hrain.json").read_text(encoding="utf-8"))
    proposal = build_proposal(
        left,
        proposal_id="proposal-self-test-0001",
        node_id="dh-node-self-test-0001",
        label="Candidate context",
        created_at="2026-08-16T09:55:00Z",
    )
    wrapped = envelope(proposal)
    validate_envelope(wrapped)

    tampered = deepcopy(wrapped)
    tampered["proposal"]["operation"]["node"]["label"] = "Tampered"
    tamper_refused = False
    try:
        validate_envelope(tampered)
    except ValueError:
        tamper_refused = True

    auto_apply = deepcopy(proposal)
    auto_apply["control"]["auto_apply"] = True
    auto_apply_refused = False
    try:
        validate_proposal(auto_apply)
    except ValueError:
        auto_apply_refused = True

    return {
        "status": "PASS" if tamper_refused and auto_apply_refused else "FAIL",
        "proposal_sha256": wrapped["proposal_sha256"],
        "base_graph_sha256": proposal["base_graph_sha256"],
        "checks": {
            "tamper_refused": tamper_refused,
            "auto_apply_refused": auto_apply_refused,
            "operation_allowlist_is_add_node_only": True,
            "proposal_is_mutation": False,
            "requires_explicit_local_accept": True,
            "direct_cross_hemisphere_write": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "claim_ceiling": {
            "sha256_binding_is_signature": False,
            "ui_accept_event_is_verified_human_identity": False,
            "proposal_is_world_effect": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Build or validate a non-mutating DemiHead hemisphere proposal")
    parser.add_argument("--packet")
    parser.add_argument("--proposal-id")
    parser.add_argument("--node-id")
    parser.add_argument("--label")
    parser.add_argument("--created-at")
    parser.add_argument("--validate")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output")
    args = parser.parse_args()

    if args.self_test:
        result: Any = self_test()
    elif args.validate:
        result = validate_envelope(json.loads(Path(args.validate).read_text(encoding="utf-8")))
    else:
        if not all([args.packet, args.proposal_id, args.node_id, args.label, args.created_at]):
            parser.error("build mode requires --packet --proposal-id --node-id --label --created-at")
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        result = envelope(build_proposal(
            packet,
            proposal_id=args.proposal_id,
            node_id=args.node_id,
            label=args.label,
            created_at=args.created_at,
        ))

    text = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
