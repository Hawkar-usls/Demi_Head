#!/usr/bin/env python3
"""Operational proof-carrying partial classifier for TOPA F3D-D1.

The operational layer never invokes an unbounded hidden semantic oracle.
It emits only certified/witnessed states or UNKNOWN. Finite exact mode is
explicit and is used solely by bounded fixtures.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Mapping, Sequence, Set, Tuple

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from topa_f3d_d1_semantic_residual_classifier import (  # noqa: E402
    TruthTable,
    classify_exact,
    find_crossing_witnesses,
    verify_crossing_witnesses,
    exact_tables,
    ext,
    root,
)

WitnessBundle = Mapping[int, Tuple[Tuple[int, ...], Tuple[int, ...]]]


def operational_classify(
    table: TruthTable,
    free: Sequence[str],
    neighborhoods: Sequence[Set[str]],
    *,
    finite_exact_mode: bool = False,
    crossing_witnesses: WitnessBundle | None = None,
) -> str:
    """Return only an evidentiary class or UNKNOWN.

    In general mode, a crossing result requires an explicit witness bundle.
    Constant/local results require an explicit certificate class not modeled by
    this minimal replay, so without finite_exact_mode they remain UNKNOWN.
    """
    if crossing_witnesses is not None:
        if verify_crossing_witnesses(table, free, neighborhoods, crossing_witnesses):
            return "WITNESSED_CROSSING"
        return "UNKNOWN"

    if not finite_exact_mode:
        return "UNKNOWN"

    exact = classify_exact(table, free, neighborhoods)
    if exact.kind == "CONST_0":
        return "CERTIFIED_CONST_0"
    if exact.kind == "CONST_1":
        return "CERTIFIED_CONST_1"
    if exact.kind in {"ROOT_LITERAL", "NEG_ROOT_LITERAL", "LOCAL"}:
        return "CERTIFIED_LOCAL"
    if exact.kind == "CROSSING":
        witnesses = find_crossing_witnesses(table, free, neighborhoods)
        if verify_crossing_witnesses(table, free, neighborhoods, witnesses):
            return "WITNESSED_CROSSING"
    return "UNKNOWN"


def replay() -> None:
    roots = ("x", "y", "z")
    neighborhoods = [{"x", "z"}, {"y", "z"}]
    gates = [
        ("zero", root("y"), root("y", True)),
        ("one", ext("zero", True), ext("zero", True)),
        ("alias_x", root("x"), ext("zero", True)),
        ("cross_xy", root("x"), root("y")),
    ]
    free, tables = exact_tables(roots, gates, {})

    # No proof package => no semantic guess.
    assert operational_classify(tables["alias_x"], free, neighborhoods) == "UNKNOWN"
    assert operational_classify(tables["cross_xy"], free, neighborhoods) == "UNKNOWN"

    # Explicit finite reference mode is allowed only for bounded fixtures.
    assert operational_classify(
        tables["zero"], free, neighborhoods, finite_exact_mode=True
    ) == "CERTIFIED_CONST_0"
    assert operational_classify(
        tables["one"], free, neighborhoods, finite_exact_mode=True
    ) == "CERTIFIED_CONST_1"
    assert operational_classify(
        tables["alias_x"], free, neighborhoods, finite_exact_mode=True
    ) == "CERTIFIED_LOCAL"

    witnesses = find_crossing_witnesses(tables["cross_xy"], free, neighborhoods)
    assert operational_classify(
        tables["cross_xy"], free, neighborhoods, crossing_witnesses=witnesses
    ) == "WITNESSED_CROSSING"

    # Missing one neighborhood witness cannot be promoted.
    incomplete = dict(witnesses)
    incomplete.pop(max(incomplete))
    assert operational_classify(
        tables["cross_xy"], free, neighborhoods, crossing_witnesses=incomplete
    ) == "UNKNOWN"

    # Tampered witness cannot be promoted.
    tampered = dict(witnesses)
    first = min(tampered)
    a, _ = tampered[first]
    tampered[first] = (a, a)
    assert operational_classify(
        tables["cross_xy"], free, neighborhoods, crossing_witnesses=tampered
    ) == "UNKNOWN"

    print("TOPA_F3D_D1_OPERATIONAL_UNKNOWN_WITHOUT_CERTIFICATE = PASS")
    print("TOPA_F3D_D1_FINITE_CERTIFIED_CONST = PASS")
    print("TOPA_F3D_D1_FINITE_CERTIFIED_LOCAL = PASS")
    print("TOPA_F3D_D1_WITNESSED_CROSSING = PASS")
    print("TOPA_F3D_D1_INCOMPLETE_WITNESS_REJECTION = PASS")
    print("TOPA_F3D_D1_TAMPERED_WITNESS_REJECTION = PASS")
    print("TOPA_F3D_D1_HEURISTIC_FALLBACK = FORBIDDEN")
    print("TOPA_F3D_D1_GENERAL_EXACT_CLASSIFIER = NOT_CALLED_BY_OPERATIONAL_PATH")
    print("TOPA_F3D_D1_CLAIM_CEILING = PARTIAL_CLASSIFIER_MECHANICS_ONLY")


if __name__ == "__main__":
    replay()
