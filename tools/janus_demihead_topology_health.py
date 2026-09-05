#!/usr/bin/env python3
"""Fail-closed topology validator for the JANUS core-repository nerve graph.

The validator is deliberately local and deterministic.  GitHub Actions is
responsible for checking out the exact source revisions; this module verifies
those checkouts, reciprocal markers, frozen DemiHead contracts, drift and the
zero-authority boundary.  A pending edge is HOLD in structural mode and a
failure in admission mode.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


class TopologyError(RuntimeError):
    pass


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TopologyError(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def git_blob_sha_bytes(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def git_blob_sha(path: Path) -> str:
    return git_blob_sha_bytes(path.read_bytes())


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and proc.returncode != 0:
        raise TopologyError(
            f"GIT_FAILED:{repo}:{' '.join(args)}:{proc.stderr.strip() or proc.stdout.strip()}"
        )
    return proc


def contains_exact_list(value: Any, target: list[str]) -> bool:
    if isinstance(value, list):
        if value == target:
            return True
        return any(contains_exact_list(item, target) for item in value)
    if isinstance(value, dict):
        return any(contains_exact_list(item, target) for item in value.values())
    return False


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise TopologyError(code)


def verify_source_git(edge: dict[str, Any], source_dir: Path) -> dict[str, Any]:
    expected_head = edge["promotion_head_sha"]
    baseline = edge["source_baseline_sha"]
    actual_head = run_git(source_dir, "rev-parse", "HEAD").stdout.strip()
    _require(actual_head == expected_head, f"SOURCE_HEAD_DRIFT:{edge['edge_id']}:{actual_head}")

    ancestor = run_git(source_dir, "merge-base", "--is-ancestor", baseline, actual_head, check=False)
    _require(ancestor.returncode == 0, f"BASELINE_NOT_ANCESTOR:{edge['edge_id']}")

    diff = run_git(source_dir, "diff", "--name-only", f"{baseline}..{actual_head}").stdout.splitlines()
    observed = sorted(line.strip() for line in diff if line.strip())
    allowed = sorted(edge["allowed_drift_paths"])
    _require(observed == allowed, f"NON_ALLOWLISTED_SOURCE_DRIFT:{edge['edge_id']}:{observed}")
    return {"actual_head": actual_head, "drift_paths": observed}


def verify_common_marker(edge: dict[str, Any], marker: dict[str, Any]) -> None:
    _require(marker.get("schema") == edge["marker_schema"], f"MARKER_SCHEMA:{edge['edge_id']}")
    _require(marker.get("link_id") == edge["edge_id"], f"MARKER_ID:{edge['edge_id']}")
    _require(marker.get("repository") == edge["repository"], f"MARKER_REPOSITORY:{edge['edge_id']}")
    _require(
        marker.get("source_baseline_sha") == edge["source_baseline_sha"],
        f"MARKER_BASELINE:{edge['edge_id']}",
    )
    boundary = marker.get("authority_boundary") or {}
    _require(boundary.get("authority_delta") == 0, f"AUTHORITY_DELTA:{edge['edge_id']}")
    _require(boundary.get("mass_effect_budget_delta") == 0, f"MASS_EFFECT_DELTA:{edge['edge_id']}")
    _require(boundary.get("write_back_default") == "DENY", f"WRITE_BACK_NOT_DENY:{edge['edge_id']}")
    _require(boundary.get("external_effect_authority") is False, f"EXTERNAL_AUTHORITY:{edge['edge_id']}")


def verify_provider_edge(
    edge: dict[str, Any], repo_root: Path, source_dir: Path
) -> dict[str, Any]:
    source_info = verify_source_git(edge, source_dir)
    marker_path = source_dir / edge["marker_path"]
    _require(marker_path.is_file(), f"MARKER_MISSING:{edge['edge_id']}")
    marker = load_json(marker_path)
    verify_common_marker(edge, marker)

    _require((marker.get("edge") or {}).get("route") == edge["route"], f"MARKER_ROUTE:{edge['edge_id']}")
    demi = marker.get("demihead") or {}
    _require(demi.get("repository") == "Hawkar-usls/Demi_Head", f"MARKER_DEMIHEAD:{edge['edge_id']}")
    _require(demi.get("contract_path") == edge["contract_path"], f"MARKER_CONTRACT_PATH:{edge['edge_id']}")
    _require(demi.get("contract_blob_sha") == edge["contract_blob_sha"], f"MARKER_CONTRACT_BLOB:{edge['edge_id']}")

    contract_path = repo_root / edge["contract_path"]
    _require(contract_path.is_file(), f"CONTRACT_MISSING:{edge['edge_id']}")
    _require(git_blob_sha(contract_path) == edge["contract_blob_sha"], f"CONTRACT_DRIFT:{edge['edge_id']}")
    contract = load_json(contract_path)
    source = contract.get("source") or {}
    _require(source.get("repository") == edge["repository"], f"CONTRACT_SOURCE_REPOSITORY:{edge['edge_id']}")
    _require(source.get("sha") == edge["source_baseline_sha"], f"CONTRACT_SOURCE_SHA:{edge['edge_id']}")
    _require(contains_exact_list(contract, edge["route"]), f"CONTRACT_ROUTE:{edge['edge_id']}")

    return {
        **source_info,
        "marker_blob_sha": git_blob_sha(marker_path),
        "contract_blob_sha": git_blob_sha(contract_path),
        "route": edge["route"],
    }


def verify_genesis_edge(
    edge: dict[str, Any], repo_root: Path, source_dir: Path, demi_nexus: dict[str, Any]
) -> dict[str, Any]:
    source_info = verify_source_git(edge, source_dir)
    marker_path = source_dir / edge["marker_path"]
    _require(marker_path.is_file(), f"MARKER_MISSING:{edge['edge_id']}")
    marker = load_json(marker_path)
    verify_common_marker(edge, marker)

    _require((marker.get("edge") or {}).get("command_route_created") is False, "GENESIS_COMMAND_ROUTE_CREATED")
    _require((marker.get("edge") or {}).get("deployment_permission_created") is False, "GENESIS_DEPLOY_PERMISSION")

    sync_path = source_dir / edge["project_sync_path"]
    _require(sync_path.is_file(), "GENESIS_PROJECT_SYNC_MISSING")
    _require(git_blob_sha(sync_path) == edge["project_sync_blob_sha"], "GENESIS_PROJECT_SYNC_DRIFT")
    sync = load_json(sync_path)
    _require(edge["required_face"] in sync.get("faces", []), "GENESIS_FACE_DEMIHEAD_MISSING")

    heads = set(demi_nexus.get("heads", []))
    missing = sorted(set(edge["required_demihead_heads"]) - heads)
    _require(not missing, f"DEMIHEAD_REQUIRED_HEADS_MISSING:{missing}")

    marker_demi = marker.get("demihead") or {}
    _require(marker_demi.get("repository") == "Hawkar-usls/Demi_Head", "GENESIS_DEMIHEAD_REPOSITORY")
    _require(
        marker_demi.get("nexus_link_blob_sha") == "d10208fbf3594d306464dfac1733490daafc4df9",
        "GENESIS_DEMIHEAD_NEXUS_PIN_DRIFT",
    )
    return {
        **source_info,
        "marker_blob_sha": git_blob_sha(marker_path),
        "project_sync_blob_sha": git_blob_sha(sync_path),
        "required_demihead_heads": edge["required_demihead_heads"],
    }


def validate(
    manifest_path: Path,
    repo_root: Path,
    sources_root: Path,
    mode: str = "structural",
) -> tuple[dict[str, Any], int]:
    manifest = load_json(manifest_path)
    contract_ref = manifest["frozen_contract"]
    contract_path = repo_root / contract_ref["path"]
    contract = load_json(contract_path)
    _require(contract.get("frozen_before_implementation") is True, "TOPOLOGY_CONTRACT_NOT_FROZEN")
    _require(git_blob_sha(contract_path) == contract_ref["blob_sha"], "TOPOLOGY_CONTRACT_DRIFT")

    required = manifest["required_edge_ids"]
    _require(required == contract["required_edges"], "REQUIRED_EDGE_SET_DRIFT")
    edges = manifest["edges"]
    _require([edge["edge_id"] for edge in edges] == required, "EDGE_ORDER_OR_SET_DRIFT")

    nexus_path = repo_root / manifest["demihead"]["nexus_link_path"]
    _require(git_blob_sha(nexus_path) == manifest["demihead"]["nexus_link_blob_sha"], "DEMIHEAD_NEXUS_DRIFT")
    demi_nexus = load_json(nexus_path)

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    pending: list[str] = []

    for edge in edges:
        edge_result: dict[str, Any] = {
            "edge_id": edge["edge_id"],
            "repository": edge["repository"],
            "declared_status": edge["status"],
            "ci_state": edge["ci_state"],
        }
        checkout = edge.get("source_checkout")
        source_dir = sources_root / checkout if checkout else None
        try:
            if source_dir is not None and source_dir.is_dir():
                if edge["edge_class"] == "FROZEN_PROVIDER_RECIPROCAL":
                    evidence = verify_provider_edge(edge, repo_root, source_dir)
                elif edge["edge_class"] == "GENESIS_LIFECYCLE_REFERENCE":
                    evidence = verify_genesis_edge(edge, repo_root, source_dir, demi_nexus)
                else:
                    raise TopologyError(f"UNKNOWN_EDGE_CLASS:{edge['edge_class']}")
                edge_result["verification"] = "PASS_STRUCTURAL"
                edge_result["evidence"] = evidence
            elif edge["status"] == "PROMOTED":
                raise TopologyError(f"PROMOTED_SOURCE_CHECKOUT_MISSING:{edge['edge_id']}")
            else:
                edge_result["verification"] = "HOLD_SOURCE_UNAVAILABLE"

            if edge["status"] != "PROMOTED" or edge["ci_state"].startswith("FAIL") or "FAIL_" in edge["ci_state"]:
                pending.append(edge["edge_id"])
                edge_result["admission"] = "HOLD"
                edge_result["hold_reason"] = edge.get("hold_reason", "EDGE_NOT_PROMOTED")
            else:
                edge_result["admission"] = "ELIGIBLE"
        except (TopologyError, KeyError, TypeError, json.JSONDecodeError) as exc:
            code = str(exc)
            errors.append(code)
            edge_result["verification"] = "FAIL"
            edge_result["error"] = code
        results.append(edge_result)

    if errors:
        status = "FAIL_TOPOLOGY_CONTRADICTION_OR_DRIFT"
        exit_code = 1
    elif pending:
        status = "HOLD_PENDING_REQUIRED_EDGES"
        exit_code = 0 if mode == "structural" else 2
    else:
        status = "PASS_ALL_CORE_ORGANS_MACHINE_VERIFIABLE"
        exit_code = 0

    receipt = {
        "schema": manifest["receipt"]["schema"],
        "manifest_id": manifest["manifest_id"],
        "manifest_sha256": sha256_file(manifest_path),
        "frozen_contract_blob_sha": contract_ref["blob_sha"],
        "mode": mode,
        "status": status,
        "required_edge_count": len(required),
        "structurally_verified_count": sum(r.get("verification") == "PASS_STRUCTURAL" for r in results),
        "pending_edge_ids": pending,
        "errors": errors,
        "edges": results,
        "claim": {
            "all_core_organs_have_machine_verifiable_paths_to_head": status == "PASS_ALL_CORE_ORGANS_MACHINE_VERIFIABLE",
            "live_cross_repository_mesh_established": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
    }
    return receipt, exit_code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="configs/janus_demihead_topology_health.v1.json")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--sources-root", default="topology_sources")
    parser.add_argument("--mode", choices=("structural", "admission"), default="structural")
    parser.add_argument("--output", default="artifacts/JANUS_DEMIHEAD_TOPOLOGY_HEALTH_RECEIPT.json")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    manifest_path = (repo_root / args.manifest).resolve()
    sources_root = (repo_root / args.sources_root).resolve()
    output = (repo_root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        receipt, exit_code = validate(manifest_path, repo_root, sources_root, args.mode)
    except (TopologyError, KeyError, TypeError, json.JSONDecodeError) as exc:
        receipt = {
            "schema": "janus.demihead.topology_health_receipt.v1",
            "mode": args.mode,
            "status": "FAIL_TOPOLOGY_VALIDATOR",
            "errors": [str(exc)],
            "claim": {
                "all_core_organs_have_machine_verifiable_paths_to_head": False,
                "authority_delta": 0,
                "mass_effect_budget_delta": 0,
            },
        }
        exit_code = 1

    output.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
