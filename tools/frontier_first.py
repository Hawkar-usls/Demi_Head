from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LAW = ROOT / "configs" / "frontier_first_law.json"


def load_law() -> dict[str, Any]:
    return json.loads(LAW.read_text(encoding="utf-8"))


def evaluate(*, internal_hits: int, external_hits: int, verified_frontiers: int, open_gaps: int) -> dict[str, Any]:
    if internal_hits < 0 or external_hits < 0 or verified_frontiers < 0 or open_gaps < 0:
        raise ValueError("counts must be non-negative")

    total_hits = internal_hits + external_hits
    if total_hits == 0:
        state = "NO_RELEVANT_PRIOR_WORK_FOUND"
        next_action = "START_FROM_FIRST_PRINCIPLES_WITH_SEARCH_RECEIPT"
    elif verified_frontiers == 0:
        state = "PRIOR_WORK_FOUND_UNVERIFIED"
        next_action = "VERIFY_RELEVANCE_PROVENANCE_AND_LIMITS_BEFORE_REUSE"
    elif open_gaps == 0:
        state = "FRONTIER_REUSED"
        next_action = "DO_NOT_REBUILD_SOLVED_WORK; RECORD_REUSE_AND_STOP_OR_REFRAME"
    else:
        state = "VERIFIED_FRONTIER_FOUND"
        next_action = "REUSE_SOLVED_COMPONENTS_AND_ATTACK_OPEN_GAPS"

    return {
        "schema": "janus.demihead.frontier_first_receipt.v1",
        "state": state,
        "counts": {
            "internal_hits": internal_hits,
            "external_hits": external_hits,
            "verified_frontiers": verified_frontiers,
            "open_gaps": open_gaps,
        },
        "next_action": next_action,
        "laws": load_law()["laws"],
        "claim_ceiling": {
            "novelty_established": False,
            "plagiarism_established": False,
            "reuse_permission_established": False,
            "authority_delta": 0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="JANUS Frontier-First decision gate")
    parser.add_argument("--internal-hits", type=int, default=0)
    parser.add_argument("--external-hits", type=int, default=0)
    parser.add_argument("--verified-frontiers", type=int, default=0)
    parser.add_argument("--open-gaps", type=int, default=0)
    args = parser.parse_args()
    print(json.dumps(evaluate(
        internal_hits=args.internal_hits,
        external_hits=args.external_hits,
        verified_frontiers=args.verified_frontiers,
        open_gaps=args.open_gaps,
    ), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
