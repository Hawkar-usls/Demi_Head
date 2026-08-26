#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def load(name: str):
    path = ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def main() -> int:
    gate = load("toch_gate_registry")
    tranception = load("toch_tranception_kernel")
    adversary = load("toch_adversary_gates")
    gate.self_test()
    tranception.self_test()
    adversary.self_test()
    assert gate.P_VS_NP == tranception.P_VS_NP == adversary.P_VS_NP == "OPEN"
    print("TOCH_AGGREGATE_SELF_TEST=PASS")
    print("P_VS_NP=OPEN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
