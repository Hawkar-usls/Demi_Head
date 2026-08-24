#!/usr/bin/env python3
"""Finite mechanics replay for the C025-C2 hidden-search-exponent audit.

This validates exact algebraic counterexamples/identities only.  It does not
prove that no polynomial discovery algorithm exists.
"""
from __future__ import annotations

from typing import Dict, Iterable, Mapping, Tuple

Clause = tuple[int, ...]
CNF = tuple[Clause, ...]


def restrict_once(cnf: CNF, var: int, value: int) -> CNF:
    out: list[Clause] = []
    for clause in cnf:
        satisfied = False
        residual: list[int] = []
        for lit in clause:
            if abs(lit) != var:
                residual.append(lit)
                continue
            literal_value = value if lit > 0 else 1 - value
            if literal_value:
                satisfied = True
                break
        if not satisfied:
            out.append(tuple(residual))
    return tuple(out)


def literal_volume(cnf: CNF) -> int:
    return sum(map(len, cnf))


def branch_duplication_fixture(unrelated_pairs: int = 4) -> tuple[CNF, CNF, CNF]:
    clauses: list[Clause] = [(1, 2), (-1, 3)]
    next_var = 4
    for _ in range(unrelated_pairs):
        clauses.append((next_var, next_var + 1))
        next_var += 2
    parent = tuple(clauses)
    return parent, restrict_once(parent, 1, 0), restrict_once(parent, 1, 1)


def test_branch_mass() -> None:
    for free in range(1, 33):
        parent = 2**free
        children = 2 ** (free - 1) + 2 ** (free - 1)
        assert children == parent
    print("TOPA_C025_C2_RAW_ASSIGNMENT_MASS_CONSERVATION = PASS")


def test_naive_potentials() -> None:
    for free in range(3, 33):
        assert 2 * (free - 1) > free

    parent, child0, child1 = branch_duplication_fixture()
    assert len(child0) + len(child1) > len(parent)
    assert literal_volume(child0) + literal_volume(child1) > literal_volume(parent)

    print("TOPA_C025_C2_UNASSIGNED_COUNT_POTENTIAL = REFUTED_BY_BRANCH_SUM")
    print("TOPA_C025_C2_CLAUSE_COUNT_POTENTIAL = REFUTED_BY_DUPLICATION_FIXTURE")
    print("TOPA_C025_C2_LITERAL_VOLUME_POTENTIAL = REFUTED_BY_DUPLICATION_FIXTURE")


def test_naive_enumeration() -> None:
    # A specific exhaustive candidate-bitstring enumerator has 2^B candidates.
    for n in range(8, 21):
        budget = n * n
        candidate_strings = 2**budget
        assert candidate_strings > n**10
    print("TOPA_C025_C2_EXHAUSTIVE_POLY_BIT_BUDGET_ENUMERATOR = SUPERPOLY_FINITE_WITNESS_PASS")


def test_telescoping_fixture() -> None:
    # Synthetic rank tree satisfying child-sum <= parent-1.
    children: Dict[str, tuple[tuple[str, int], ...]] = {
        "r": (("a", 3), ("b", 3)),
        "a": (("a0", 1), ("a1", 1)),
        "b": (("b0", 1), ("b1", 1)),
        "a0": (),
        "a1": (),
        "b0": (),
        "b1": (),
    }
    ranks = {"r": 7, "a": 3, "b": 3, "a0": 1, "a1": 1, "b0": 1, "b1": 1}
    expanded = 0
    frontier = ["r"]
    previous_phi = sum(ranks[x] for x in frontier)
    while frontier:
        node = frontier.pop(0)
        kids = children[node]
        if not kids:
            continue
        assert sum(rank for _, rank in kids) <= ranks[node] - 1
        frontier.extend(name for name, _ in kids)
        expanded += 1
        phi = sum(ranks[x] for x in frontier)
        assert phi <= previous_phi - 1
        previous_phi = phi
    assert expanded <= ranks["r"]
    print("TOPA_C025_C2_FRONTIER_TELESCOPING_MECHANICS = PASS")


def main() -> None:
    test_branch_mass()
    test_naive_potentials()
    test_naive_enumeration()
    test_telescoping_fixture()
    print("TOPA_C025_C2_USEFUL_POLY_BOUNDED_FRONTIER_POTENTIAL = OPEN")
    print("TOPA_C025_C2_DETERMINISTIC_DISCOVERY = OPEN")
    print("TOPA_C025_C2_CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
