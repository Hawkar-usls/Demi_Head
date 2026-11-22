#!/usr/bin/env python3
"""TACHYON experiment-lane router.

This is an OPT-IN local research CLI. It has no production event hooks,
no agent autonomy, and does not change frozen R5F source/calibration.

The describe command never runs experiments. Runtime evaluation is explicit.
"""
from __future__ import annotations

import argparse
import json


def describe() -> dict:
    return {
        "schema": "janus.demihead.tachyon.experiment_router.v1",
        "status": "INTEGRATED_EXPERIMENTS_NOT_EXECUTED_BY_INSTALLATION",
        "lanes": {
            "retrobound-r1": {
                "module": "tools.tachyon_retrobound_r1",
                "method": "OFFLINE_TWO_BOUNDARY_TRANSFER",
                "controls": ["CAUSAL_FORWARD_NULL", "FORWARD_POSTSELECTION"],
                "gate": "NO_PHYSICAL_RETROCAUSALITY_PROMOTION",
                "requires_explicit_run": True,
            },
            "r5f-causal-replay": {
                "module": "tools.tachyon_r5f_causal_memory_audit",
                "method": "REVERSE_INFERENCE_THEN_FORWARD_REPLAY",
                "gate": "FROZEN_EXISTING_R5F_SCIENCE_HOLD",
                "requires_explicit_run": True,
            },
        },
        "domains_separate": [
            "SUBJECTIVE_TIME_RULE001",
            "RETROBOUND_CLASSICAL_CONDITIONAL_HISTORY",
            "PROSPECTIVE_PHYSICAL_CAUSAL_FALSIFICATION",
        ],
        "deployed_models_changed": False,
        "scientific_claim": "NONE",
    }


def dispatch(lane: str, *, steps=8, rho=0.85, eta=0.9,
             trials=40000, seed=20261123) -> dict:
    if lane == "retrobound-r1":
        from tools.tachyon_retrobound_r1 import run_gated
        return run_gated(steps=steps, rho=rho, eta=eta, trials=trials, seed=seed)
    if lane == "r5f-causal-replay":
        from tools.tachyon_r5f_causal_memory_audit import audit
        return audit()
    raise ValueError("unknown experiment lane")


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicit JANUS TACHYON experiment routing")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("describe", help="List available lanes without running experiments")
    run = sub.add_parser("run", help="Explicitly run the selected research lane")
    run.add_argument("--lane", required=True, choices=("retrobound-r1", "r5f-causal-replay"))
    run.add_argument("--steps", type=int, default=8)
    run.add_argument("--rho", type=float, default=0.85)
    run.add_argument("--eta", type=float, default=0.9)
    run.add_argument("--trials", type=int, default=40000)
    run.add_argument("--seed", type=int, default=20261123)
    args = parser.parse_args()
    if args.cmd == "describe":
        result = describe()
    else:
        result = dispatch(args.lane, steps=args.steps, rho=args.rho,
                          eta=args.eta, trials=args.trials, seed=args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
