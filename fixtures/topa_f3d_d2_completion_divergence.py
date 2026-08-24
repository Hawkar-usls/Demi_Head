#!/usr/bin/env python3
"""Finite source-like replay for TOPA F3D-D2 completion ambiguity.

This probe targets two under-specified choices in Sokolov Algorithm 1:
  * line 11: multiple maximum-cardinality valid B_i sets;
  * line 12: multiple satisfying assignments nu_i for one fixed B_i.

The fixture validates only the local mechanics of completion-dependent semantic
survival. It does NOT claim that the full hard NW family or every source-valid
state exhibits the divergence.
"""
from __future__ import annotations

from itertools import combinations, product
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

Left = str
Right = str
Assignment = Dict[Right, int]

LEFT: Tuple[Left, ...] = ("a", "b", "c", "d")
RIGHT: Tuple[Right, ...] = ("y1", "w1", "y2", "w2", "z1", "z2")

# Line-11 graph state G': two twin left pairs.  Each twin pair has zero
# unique-neighbour boundary, while any mixed pair has four unique neighbours.
ADJ: Dict[Left, Set[Right]] = {
    "a": {"y1", "w1"},
    "b": {"y1", "w1"},
    "c": {"y2", "w2"},
    "d": {"y2", "w2"},
}

R_LIMIT = 2
EPSILON = 0.25

# Each left constraint is parity-zero on its two neighbours.  Thus a twin pair
# admits two satisfying nu assignments: 00 and 11.

def constraint_holds(left: Left, assignment: Mapping[Right, int]) -> bool:
    if left in ("a", "b"):
        return (assignment["y1"] ^ assignment["w1"]) == 0
    if left in ("c", "d"):
        return (assignment["y2"] ^ assignment["w2"]) == 0
    raise KeyError(left)


def neighborhood(B: Iterable[Left]) -> Set[Right]:
    out: Set[Right] = set()
    for u in B:
        out |= ADJ[u]
    return out


def unique_boundary(B: Iterable[Left]) -> Set[Right]:
    B = tuple(B)
    counts: Dict[Right, int] = {}
    for u in B:
        for x in ADJ[u]:
            counts[x] = counts.get(x, 0) + 1
    return {x for x, count in counts.items() if count == 1}


def line11_valid(B: Iterable[Left]) -> bool:
    B = tuple(B)
    if len(B) > R_LIMIT:
        return False
    return len(unique_boundary(B)) <= (1.0 - 2.0 * EPSILON) * len(B)


def line11_maximizers() -> List[Tuple[Left, ...]]:
    valid: List[Tuple[Left, ...]] = [()]
    for k in range(1, R_LIMIT + 1):
        for B in combinations(LEFT, k):
            if line11_valid(B):
                valid.append(B)
    max_size = max(map(len, valid))
    return sorted(B for B in valid if len(B) == max_size)


def satisfying_nu(B: Sequence[Left]) -> List[Assignment]:
    vars_ = tuple(sorted(neighborhood(B)))
    out: List[Assignment] = []
    for bits in product((0, 1), repeat=len(vars_)):
        a = dict(zip(vars_, bits))
        if all(constraint_holds(u, a) for u in B):
            out.append(a)
    return out


def lex_first_nu(B: Sequence[Left]) -> Assignment:
    vals = satisfying_nu(B)
    if not vals:
        raise AssertionError("expected at least one satisfying nu")
    vars_ = tuple(sorted(neighborhood(B)))
    return min(vals, key=lambda a: tuple(a[v] for v in vars_))

# Target frozen-B2 macro:
#     h := z1 AND z2
#     M := y1 AND h
# Locality hypergraph intentionally keeps y1, z1, z2 in different blocks.
HOODS: Tuple[Set[Right], ...] = (
    {"y1", "w1"},
    {"y2", "w2"},
    {"z1"},
    {"z2"},
)


def target_value(assignment: Mapping[Right, int]) -> int:
    h = assignment["z1"] & assignment["z2"]
    return assignment["y1"] & h


def exact_residual_table(rho: Mapping[Right, int]) -> Tuple[Tuple[Right, ...], Dict[Tuple[int, ...], int]]:
    roots = ("y1", "w1", "y2", "w2", "z1", "z2")
    free = tuple(x for x in roots if x not in rho)
    table: Dict[Tuple[int, ...], int] = {}
    for bits in product((0, 1), repeat=len(free)):
        a = dict(rho)
        a.update(dict(zip(free, bits)))
        table[bits] = target_value(a)
    return free, table


def essential_support(free: Sequence[Right], table: Mapping[Tuple[int, ...], int]) -> Set[Right]:
    free = tuple(free)
    ess: Set[Right] = set()
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
                ess.add(var)
                break
    return ess


def residual_class(rho: Mapping[Right, int]) -> Tuple[str, Set[Right]]:
    free, table = exact_residual_table(rho)
    vals = set(table.values())
    if vals == {0}:
        return "CONST_0", set()
    if vals == {1}:
        return "CONST_1", set()
    ess = essential_support(free, table)
    if any(ess <= hood for hood in HOODS):
        return "LOCAL", ess
    return "CROSSING", ess


def replay_d2_01() -> None:
    maximizers = line11_maximizers()
    assert maximizers == [("a", "b"), ("c", "d")], maximizers

    B1, B2 = maximizers
    nu1 = lex_first_nu(B1)
    nu2 = lex_first_nu(B2)

    assert nu1 == {"w1": 0, "y1": 0}
    assert nu2 == {"w2": 0, "y2": 0}

    cls1, ess1 = residual_class(nu1)
    cls2, ess2 = residual_class(nu2)

    assert cls1 == "CONST_0", (cls1, ess1)
    assert cls2 == "CROSSING", (cls2, ess2)
    assert ess2 == {"y1", "z1", "z2"}

    print("TOPA_F3D_D2_F01_TWO_LINE11_MAXIMIZERS = PASS")
    print("TOPA_F3D_D2_F01_SAME_LEX_NU_RULE_DIFFERENT_B = PASS")
    print("TOPA_F3D_D2_F01_B1_TARGET_CLASS = CONST_0")
    print("TOPA_F3D_D2_F01_B2_TARGET_CLASS = CROSSING")


def replay_d2_02() -> None:
    B = ("a", "b")
    nus = satisfying_nu(B)
    expected = [
        {"w1": 0, "y1": 0},
        {"w1": 1, "y1": 1},
    ]
    assert nus == expected, nus

    cls0, ess0 = residual_class(nus[0])
    cls1, ess1 = residual_class(nus[1])

    assert cls0 == "CONST_0", (cls0, ess0)
    assert cls1 == "CROSSING", (cls1, ess1)
    assert ess1 == {"z1", "z2"}

    print("TOPA_F3D_D2_F02_FIXED_B_TWO_VALID_NU = PASS")
    print("TOPA_F3D_D2_F02_NU00_TARGET_CLASS = CONST_0")
    print("TOPA_F3D_D2_F02_NU11_TARGET_CLASS = CROSSING")


def main() -> None:
    replay_d2_01()
    replay_d2_02()
    print("TOPA_F3D_D2_COMPLETION_CHOICE_CAN_CHANGE_SEMANTIC_SURVIVAL = PASS")
    print("TOPA_F3D_D2_CLAIM_CEILING = SOURCE_LIKE_LINE11_12_FIXTURE_ONLY")
    print("TOPA_F3D_D2_FULL_HARD_NW_FAMILY_DIVERGENCE = NOT_ESTABLISHED")
    print("TOPA_F3D_D2_NEXT = SOURCE_VALID_COMPLETION_QUANTIFIER_OR_EXACT_COUNTERFAMILY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
