#!/usr/bin/env python3
"""Finite exact-semantics replay for TOPA F3D-D1.

This is a deliberately exponential reference oracle over free root variables.
It validates finite mechanics only. It is NOT a polynomial-time general
semantic classifier for frozen-B2 DAGs.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

Literal = Tuple[str, str, bool]  # (kind: root|ext, name, negated)
Gate = Tuple[str, Literal, Literal]
Assignment = Dict[str, int]
TruthTable = Dict[Tuple[int, ...], int]


def root(name: str, neg: bool = False) -> Literal:
    return ("root", name, neg)


def ext(name: str, neg: bool = False) -> Literal:
    return ("ext", name, neg)


def evaluate(
    roots: Sequence[str], gates: Sequence[Gate], assignment: Mapping[str, int]
) -> Dict[str, int]:
    values: Dict[str, int] = {}

    def lit_value(lit: Literal) -> int:
        kind, name, neg = lit
        raw = assignment[name] if kind == "root" else values[name]
        return 1 - raw if neg else raw

    for name, a, b in gates:
        values[name] = lit_value(a) & lit_value(b)
    return values


def exact_tables(
    roots: Sequence[str], gates: Sequence[Gate], rho: Mapping[str, int]
) -> Tuple[Tuple[str, ...], Dict[str, TruthTable]]:
    free = tuple(sorted(set(roots) - set(rho)))
    tables: Dict[str, TruthTable] = {name: {} for name, _, _ in gates}
    for bits in product((0, 1), repeat=len(free)):
        assignment = dict(rho)
        assignment.update(dict(zip(free, bits)))
        values = evaluate(roots, gates, assignment)
        for name in tables:
            tables[name][bits] = values[name]
    return free, tables


def essential_support(table: TruthTable, free: Sequence[str]) -> Set[str]:
    free = tuple(free)
    out: Set[str] = set()
    for j, var in enumerate(free):
        others = [i for i in range(len(free)) if i != j]
        for other_bits in product((0, 1), repeat=len(others)):
            a0 = [0] * len(free)
            a1 = [0] * len(free)
            for idx, bit in zip(others, other_bits):
                a0[idx] = bit
                a1[idx] = bit
            a0[j] = 0
            a1[j] = 1
            if table[tuple(a0)] != table[tuple(a1)]:
                out.add(var)
                break
    return out


def literal_alias(table: TruthTable, free: Sequence[str], var: str) -> str | None:
    j = tuple(free).index(var)
    if all(value == bits[j] for bits, value in table.items()):
        return "ROOT_LITERAL"
    if all(value == 1 - bits[j] for bits, value in table.items()):
        return "NEG_ROOT_LITERAL"
    return None


@dataclass(frozen=True)
class ExactClass:
    kind: str
    essential_support: Tuple[str, ...]
    local_neighborhoods: Tuple[int, ...] = ()
    literal_var: str | None = None


def classify_exact(
    table: TruthTable,
    free: Sequence[str],
    neighborhoods: Sequence[Set[str]],
) -> ExactClass:
    values = set(table.values())
    if values == {0}:
        return ExactClass("CONST_0", ())
    if values == {1}:
        return ExactClass("CONST_1", ())

    ess = tuple(sorted(essential_support(table, free)))
    if len(ess) == 1:
        alias = literal_alias(table, free, ess[0])
        if alias:
            return ExactClass(alias, ess, literal_var=ess[0])

    ess_set = set(ess)
    local_ids = tuple(
        i for i, hood in enumerate(neighborhoods) if ess_set <= set(hood)
    )
    if local_ids:
        return ExactClass("LOCAL", ess, local_neighborhoods=local_ids)
    return ExactClass("CROSSING", ess)


def fingerprint(table: TruthTable) -> Tuple[int, ...]:
    return tuple(table[key] for key in sorted(table))


def find_crossing_witnesses(
    table: TruthTable,
    free: Sequence[str],
    neighborhoods: Sequence[Set[str]],
) -> Dict[int, Tuple[Tuple[int, ...], Tuple[int, ...]]]:
    free = tuple(free)
    result: Dict[int, Tuple[Tuple[int, ...], Tuple[int, ...]]] = {}

    for i, hood in enumerate(neighborhoods):
        hood_positions = tuple(j for j, var in enumerate(free) if var in hood)
        groups: Dict[Tuple[int, ...], Dict[int, Tuple[int, ...]]] = {}
        for bits, value in table.items():
            projection = tuple(bits[j] for j in hood_positions)
            groups.setdefault(projection, {}).setdefault(value, bits)
        for values in groups.values():
            if 0 in values and 1 in values:
                result[i] = (values[0], values[1])
                break
    return result


def verify_crossing_witnesses(
    table: TruthTable,
    free: Sequence[str],
    neighborhoods: Sequence[Set[str]],
    witnesses: Mapping[int, Tuple[Tuple[int, ...], Tuple[int, ...]]],
) -> bool:
    free = tuple(free)
    if set(witnesses) != set(range(len(neighborhoods))):
        return False
    for i, hood in enumerate(neighborhoods):
        a, b = witnesses[i]
        if a not in table or b not in table:
            return False
        for j, var in enumerate(free):
            if var in hood and a[j] != b[j]:
                return False
        if table[a] == table[b]:
            return False
    return True


def structural_supports(roots: Sequence[str], gates: Sequence[Gate]) -> Dict[str, Set[str]]:
    support: Dict[str, Set[str]] = {r: {r} for r in roots}
    for name, a, b in gates:
        support[name] = set(support[a[1]]) | set(support[b[1]])
    return support


def finite_fixture() -> None:
    roots = ("x", "y", "z")
    neighborhoods = [
        {"x", "z"},  # H0
        {"y", "z"},  # H1
    ]

    gates: List[Gate] = [
        ("zero", root("y"), root("y", True)),
        ("one", ext("zero", True), ext("zero", True)),
        # Syntactic support is {x,y}; exact semantics is x.
        ("alias_x", root("x"), ext("zero", True)),
        # Exact semantics is NOT x.
        ("not_x", root("x", True), root("x", True)),
        # True crossing relative to H0/H1 because it depends on {x,y}.
        ("cross_xy", root("x"), root("y")),
        # Two macros that become aliases after y=z=1.
        ("g1", root("x"), root("y")),
        ("g2", root("x"), root("z")),
        # z is local to both overlapping neighborhoods.
        ("alias_z", root("z"), ext("one")),
    ]

    free, tables = exact_tables(roots, gates, {})
    classes = {name: classify_exact(table, free, neighborhoods) for name, table in tables.items()}

    assert classes["zero"].kind == "CONST_0"
    assert classes["one"].kind == "CONST_1"
    assert classes["alias_x"].kind == "ROOT_LITERAL"
    assert classes["alias_x"].literal_var == "x"
    assert classes["not_x"].kind == "NEG_ROOT_LITERAL"
    assert classes["cross_xy"].kind == "CROSSING"
    assert classes["alias_z"].kind == "ROOT_LITERAL"
    assert classes["alias_z"].literal_var == "z"

    support = structural_supports(roots, gates)
    assert support["alias_x"] == {"x", "y"}
    assert not any(support["alias_x"] <= hood for hood in neighborhoods)
    assert classes["alias_x"].kind == "ROOT_LITERAL"

    # Crossing has one explicit distinguishing pair per neighborhood.
    witnesses = find_crossing_witnesses(tables["cross_xy"], free, neighborhoods)
    assert verify_crossing_witnesses(tables["cross_xy"], free, neighborhoods, witnesses)

    # Tamper one witness: equal assignments cannot demonstrate output change.
    bad = dict(witnesses)
    first = min(bad)
    bad[first] = (bad[first][0], bad[first][0])
    assert not verify_crossing_witnesses(tables["cross_xy"], free, neighborhoods, bad)

    # Restriction-created locality: x AND y under y=1 becomes x.
    free_y1, tables_y1 = exact_tables(roots, gates, {"y": 1})
    cross_y1 = classify_exact(tables_y1["cross_xy"], free_y1, neighborhoods)
    assert cross_y1.kind == "ROOT_LITERAL" and cross_y1.literal_var == "x"

    # Residual alias collision.
    free_alias, tables_alias = exact_tables(roots, gates, {"y": 1, "z": 1})
    assert fingerprint(tables_alias["g1"]) == fingerprint(tables_alias["g2"])
    assert classify_exact(tables_alias["g1"], free_alias, neighborhoods).kind == "ROOT_LITERAL"
    assert classify_exact(tables_alias["g2"], free_alias, neighborhoods).kind == "ROOT_LITERAL"

    # Neighborhood ambiguity is preserved by the exact locality rule.
    # Use a non-literal local function z AND z = z would be caught as literal,
    # so classify the support relation itself: {z} is contained in both H0,H1.
    z_support = {"z"}
    matching = tuple(i for i, hood in enumerate(neighborhoods) if z_support <= hood)
    assert matching == (0, 1)

    # Reference-oracle assignment count is explicit: 2^r.
    assert len(next(iter(tables.values()))) == 2 ** len(free)

    print("TOPA_F3D_D1_EXACT_FINITE_REFERENCE_ORACLE = PASS")
    print("TOPA_F3D_D1_CONST0_CONST1 = PASS")
    print("TOPA_F3D_D1_LITERAL_ALIAS = PASS")
    print("TOPA_F3D_D1_SYNTACTIC_SUPPORT_FALSE_POSITIVE = PASS")
    print("TOPA_F3D_D1_CROSSING_WITNESS = PASS")
    print("TOPA_F3D_D1_FAKE_CROSSING_WITNESS_REJECTION = PASS")
    print("TOPA_F3D_D1_RESTRICTION_CREATED_LOCALITY = PASS")
    print("TOPA_F3D_D1_RESIDUAL_ALIAS_COLLISION = PASS")
    print("TOPA_F3D_D1_NEIGHBORHOOD_AMBIGUITY = PASS")
    print(f"TOPA_F3D_D1_REFERENCE_ASSIGNMENTS = {2 ** len(free)}")
    print("TOPA_F3D_D1_REFERENCE_ORACLE_COST = O(S*2^r)")
    print("TOPA_F3D_D1_GENERAL_EXACT_CLASSIFIER_POLYTIME = NOT_ASSUMED")
    print("TOPA_F3D_D1_OPERATIONAL_UNKNOWN = REQUIRED_WHEN_UNCERTIFIED")
    print("TOPA_F3D_D1_CLAIM_CEILING = FINITE_MECHANICS_ONLY")


if __name__ == "__main__":
    finite_fixture()
