from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from repository_awareness import load_best_available, load_json


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_AWARENESS_CONFIG = ROOT / "configs" / "repository_awareness.json"
TOKEN = re.compile(r"[A-Za-zА-Яа-яЁёІіЇїЄє0-9_+.-]{3,}")
STOP = {
    "janus", "repo", "repository", "project", "main", "public", "private",
    "with", "from", "this", "that", "для", "или", "это", "как", "the", "and",
}


def terms(text: str) -> set[str]:
    return {m.group(0).casefold() for m in TOKEN.finditer(text) if m.group(0).casefold() not in STOP}


def score_repository(repo: dict[str, Any], idea: str) -> tuple[int, list[str]]:
    idea_terms = terms(idea)
    fields = " ".join(
        str(repo.get(key) or "")
        for key in ("name", "full_name", "description", "default_branch")
    )
    repo_terms = terms(fields)
    overlap = sorted(idea_terms & repo_terms)
    score = len(overlap)

    name = str(repo.get("name") or "").casefold()
    for term in idea_terms:
        if term in name:
            score += 2
    return score, overlap


def internal_candidates(idea: str, inventory: dict[str, Any], *, limit: int = 8) -> list[dict[str, Any]]:
    self_repo = inventory.get("self_repository")
    ranked: list[dict[str, Any]] = []
    for repo in inventory.get("repositories", []):
        if repo.get("full_name") == self_repo:
            continue
        score, overlap = score_repository(repo, idea)
        if score <= 0:
            continue
        ranked.append({
            "candidate_repository": repo.get("full_name"),
            "visibility": repo.get("visibility", "unknown"),
            "archived": bool(repo.get("archived", False)),
            "score": score,
            "matched_terms": overlap,
            "why_relevant": "lexical_or_metadata_overlap_for_inspection",
            "provenance_state": "SAME_OWNER_REPOSITORY_NOT_YET_MECHANISM_VERIFIED",
            "confidence": "routing_hint_only",
            "read_only_reference": True,
        })
    ranked.sort(key=lambda row: (-int(row["score"]), str(row["candidate_repository"])))
    return ranked[:limit]


def build_proposal(idea: str, inventory: dict[str, Any], *, limit: int = 8) -> dict[str, Any]:
    candidates = internal_candidates(idea, inventory, limit=limit)
    return {
        "schema": "janus.demihead.convergence_internal_proposal.v1",
        "idea": idea,
        "inventory_source": inventory.get("source", "unknown"),
        "inventory_authenticated": inventory.get("authenticated_inventory", False),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "next_route": [
            "KETO_INSPECT_CANDIDATE_MECHANISMS",
            "TOPA_SPIDER_EXTERNAL_ANALOGUES",
            "CONVERGENCE_STRUCTURAL_ALIGNMENT",
            "FUNDAMENTUM_FALSIFICATION",
            "META_REGISTRY_RECEIPT",
        ],
        "claim_ceiling": {
            "novelty_established": False,
            "plagiarism_established": False,
            "candidate_relevance_established": False,
            "cross_repository_write_permission": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
        },
        "invariants": [
            "OVERLAP != PLAGIARISM",
            "INDEPENDENT_CONVERGENCE != COPYING",
            "SAME_OWNER != SAME_PROVENANCE",
            "REPOSITORY_AWARENESS_IS_CONTEXT_NOT_AUTHORITY",
            "THIRD_THING_REQUIRES_EXPLICIT_INTERACTION_DELTA",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="DemiHead Convergence internal-portfolio proposal surface")
    parser.add_argument("idea", help="Idea, mechanism or problem description")
    parser.add_argument("--limit", type=int, default=8)
    parser.add_argument("--inventory", type=Path)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    if args.inventory:
        inventory = load_json(args.inventory)
    else:
        config = load_json(DEFAULT_AWARENESS_CONFIG)
        inventory = load_best_available(config)

    result = build_proposal(args.idea, inventory, limit=max(1, args.limit))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
