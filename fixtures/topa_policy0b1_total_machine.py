#!/usr/bin/env python3
"""Finite mechanics replay for heuristic-free Policy-0B.1.

The executable checks determinism/correctness on a finite exhaustive CNF suite.
It does not prove a universal polynomial-time theorem.  The frozen machine has
an explicit exponential branch-tree upper bound.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations, product
from typing import Iterable, Mapping

Clause = tuple[int, ...]
CNF = tuple[Clause, ...]


def lit_key(lit: int) -> tuple[int, bool]:
    return (abs(lit), lit < 0)


def canonical_clause(clause: Iterable[int]) -> Clause | None:
    literals = set(clause)
    if any(-lit in literals for lit in literals):
        return None
    return tuple(sorted(literals, key=lit_key))


def canonical_cnf(clauses: Iterable[Iterable[int]]) -> CNF:
    normalized: set[Clause] = set()
    for clause in clauses:
        c = canonical_clause(clause)
        if c is not None:
            normalized.add(c)
    return tuple(sorted(normalized, key=lambda c: (len(c), c)))


def subsumption_reduce(cnf: CNF) -> CNF:
    frozen = canonical_cnf(cnf)
    sets = [set(c) for c in frozen]
    keep: list[Clause] = []
    for i, clause in enumerate(frozen):
        if any(j != i and sets[j] < sets[i] for j in range(len(frozen))):
            continue
        keep.append(clause)
    return canonical_cnf(keep)


def restrict_cnf(cnf: CNF, assignment: Mapping[int, int]) -> CNF:
    out: list[Clause] = []
    for clause in cnf:
        satisfied = False
        residual: list[int] = []
        for lit in clause:
            var = abs(lit)
            if var in assignment:
                value = assignment[var] if lit > 0 else 1 - assignment[var]
                if value:
                    satisfied = True
                    break
            else:
                residual.append(lit)
        if not satisfied:
            out.append(tuple(residual))
    return subsumption_reduce(canonical_cnf(out))


@dataclass
class PrepStats:
    scans: int = 0
    attempts: int = 0
    strengthening_steps: int = 0
    unit_assignments: int = 0


@dataclass(frozen=True)
class StrengthResult:
    conflict: bool
    units: tuple[int, ...]
    cnf: CNF
    attempts: int
    changed: bool


def fair_strengthen(cnf: CNF) -> StrengthResult:
    frozen = subsumption_reduce(canonical_cnf(cnf))
    positive: dict[int, list[Clause]] = {}
    negative: dict[int, list[Clause]] = {}
    for clause in frozen:
        for lit in clause:
            (positive if lit > 0 else negative).setdefault(abs(lit), []).append(clause)

    frozen_sets = {clause: set(clause) for clause in frozen}
    best: dict[Clause, Clause | None] = {clause: None for clause in frozen}
    units: set[int] = set()
    attempts = 0

    for pivot in sorted(set(positive) & set(negative)):
        for left in positive[pivot]:
            for right in negative[pivot]:
                attempts += 1
                candidate = canonical_clause(
                    (set(left) - {pivot}) | (set(right) - {-pivot})
                )
                if candidate is None:
                    continue
                if len(candidate) == 0:
                    return StrengthResult(True, (), frozen, attempts, False)
                if len(candidate) == 1:
                    units.add(candidate[0])
                    continue
                candidate_set = set(candidate)
                for old_clause in frozen:
                    if candidate_set < frozen_sets[old_clause]:
                        previous = best[old_clause]
                        if previous is None or (len(candidate), candidate) < (
                            len(previous),
                            previous,
                        ):
                            best[old_clause] = candidate

    replacements: list[Clause] = []
    changed = False
    for old_clause in frozen:
        candidate = best[old_clause]
        if candidate is None:
            replacements.append(old_clause)
        else:
            replacements.append(candidate)
            changed = True

    new_cnf = subsumption_reduce(canonical_cnf(replacements))
    if changed:
        assert sum(map(len, new_cnf)) < sum(map(len, frozen))

    L = sum(len(c) for c in frozen)
    assert 4 * attempts <= L * L
    return StrengthResult(
        False,
        tuple(sorted(units, key=lit_key)),
        new_cnf,
        attempts,
        changed,
    )


@dataclass(frozen=True)
class PrepResult:
    conflict: bool
    cnf: CNF
    assignment: dict[int, int]
    stats: PrepStats


def preprocess(cnf: CNF, assignment: Mapping[int, int]) -> PrepResult:
    rho = dict(assignment)
    active = restrict_cnf(cnf, rho)
    stats = PrepStats()

    while True:
        if () in active:
            return PrepResult(True, active, rho, stats)

        units = sorted({c[0] for c in active if len(c) == 1}, key=lit_key)
        if units:
            lit = units[0]
            var, value = abs(lit), int(lit > 0)
            if var in rho and rho[var] != value:
                return PrepResult(True, ((),), rho, stats)
            if var not in rho:
                rho[var] = value
                stats.unit_assignments += 1
            active = restrict_cnf(active, rho)
            continue

        layer = fair_strengthen(active)
        stats.scans += 1
        stats.attempts += layer.attempts

        if layer.conflict:
            return PrepResult(True, ((),), rho, stats)

        if layer.units:
            lit = layer.units[0]
            var, value = abs(lit), int(lit > 0)
            if var in rho and rho[var] != value:
                return PrepResult(True, ((),), rho, stats)
            if var not in rho:
                rho[var] = value
                stats.unit_assignments += 1
            active = restrict_cnf(active, rho)
            continue

        if layer.changed:
            stats.strengthening_steps += 1
            active = layer.cnf
            continue

        return PrepResult(False, active, rho, stats)


@dataclass(frozen=True)
class ConflictLeaf:
    pass


@dataclass(frozen=True)
class BranchCertificate:
    var: int
    false_child: object
    true_child: object


@dataclass
class SolveStats:
    nodes: int = 0
    max_depth: int = 0
    scans: int = 0
    attempts: int = 0
    strengthening_steps: int = 0
    unit_assignments: int = 0
    branches: int = 0


def solve(cnf: CNF) -> tuple[str, object, SolveStats]:
    root = canonical_cnf(cnf)
    root_vars = sorted({abs(l) for c in root for l in c})
    stats = SolveStats()

    def rec(active: CNF, assignment: dict[int, int], depth: int) -> tuple[bool, object]:
        stats.nodes += 1
        stats.max_depth = max(stats.max_depth, depth)
        prepared = preprocess(active, assignment)
        stats.scans += prepared.stats.scans
        stats.attempts += prepared.stats.attempts
        stats.strengthening_steps += prepared.stats.strengthening_steps
        stats.unit_assignments += prepared.stats.unit_assignments

        if prepared.conflict:
            return False, ConflictLeaf()

        if not prepared.cnf:
            witness = dict(prepared.assignment)
            for var in root_vars:
                witness.setdefault(var, 0)
            return True, witness

        remaining = sorted(
            {
                abs(l)
                for c in prepared.cnf
                for l in c
                if abs(l) not in prepared.assignment
            }
        )
        assert remaining
        var = remaining[0]
        stats.branches += 1

        rho0 = dict(prepared.assignment)
        rho0[var] = 0
        sat0, result0 = rec(prepared.cnf, rho0, depth + 1)
        if sat0:
            return True, result0

        rho1 = dict(prepared.assignment)
        rho1[var] = 1
        sat1, result1 = rec(prepared.cnf, rho1, depth + 1)
        if sat1:
            return True, result1

        return False, BranchCertificate(var, result0, result1)

    sat, result = rec(root, {}, 0)
    return ("SAT" if sat else "UNSAT"), result, stats


def verify_sat(cnf: CNF, witness: Mapping[int, int]) -> bool:
    for clause in canonical_cnf(cnf):
        if not any(
            (witness[abs(l)] if l > 0 else 1 - witness[abs(l)])
            for l in clause
        ):
            return False
    return True


def verify_unsat(cnf: CNF, cert: object) -> bool:
    def rec(active: CNF, assignment: dict[int, int], node: object) -> bool:
        prepared = preprocess(active, assignment)
        if prepared.conflict:
            return isinstance(node, ConflictLeaf)
        if not prepared.cnf or isinstance(node, ConflictLeaf):
            return False
        if not isinstance(node, BranchCertificate):
            return False
        remaining = sorted(
            {
                abs(l)
                for c in prepared.cnf
                for l in c
                if abs(l) not in prepared.assignment
            }
        )
        if not remaining or node.var != remaining[0]:
            return False
        rho0 = dict(prepared.assignment)
        rho0[node.var] = 0
        rho1 = dict(prepared.assignment)
        rho1[node.var] = 1
        return rec(prepared.cnf, rho0, node.false_child) and rec(
            prepared.cnf, rho1, node.true_child
        )

    return rec(canonical_cnf(cnf), {}, cert)


def brute_sat(cnf: CNF) -> bool:
    root = canonical_cnf(cnf)
    variables = sorted({abs(l) for c in root for l in c})
    for bits in product((0, 1), repeat=len(variables)):
        assignment = dict(zip(variables, bits))
        if all(
            any(
                (assignment[abs(l)] if l > 0 else 1 - assignment[abs(l)])
                for l in clause
            )
            for clause in root
        ):
            return True
    return False


def all_non_tautological_clauses(n: int) -> list[Clause]:
    clauses: list[Clause] = []
    for choices in product((-1, 0, 1), repeat=n):
        if all(c == 0 for c in choices):
            continue
        clause: list[int] = []
        for var, choice in enumerate(choices, start=1):
            if choice > 0:
                clause.append(var)
            elif choice < 0:
                clause.append(-var)
        c = canonical_clause(clause)
        assert c is not None
        clauses.append(c)
    return sorted(set(clauses), key=lambda c: (len(c), c))


def exhaustive_small_suite() -> int:
    clauses = all_non_tautological_clauses(3)
    checked = 0
    for clause_count in range(4):
        for selected in combinations(clauses, clause_count):
            cnf = canonical_cnf(selected)
            status, result, stats = solve(cnf)
            expected = brute_sat(cnf)
            assert (status == "SAT") == expected
            assert stats.max_depth <= 3
            if status == "SAT":
                assert isinstance(result, dict)
                assert verify_sat(cnf, result)
            else:
                assert verify_unsat(cnf, result)

            # Determinism: same exact input must produce the same result object/stats.
            status2, result2, stats2 = solve(cnf)
            assert status2 == status
            assert repr(result2) == repr(result)
            assert stats2 == stats
            checked += 1
    return checked


def strengthening_fixture() -> None:
    cnf = canonical_cnf(((1, 2), (-1, 2, 3)))
    before = sum(map(len, cnf))
    layer = fair_strengthen(cnf)
    assert layer.changed and not layer.conflict and not layer.units
    assert layer.cnf == canonical_cnf(((1, 2), (2, 3)))
    assert sum(map(len, layer.cnf)) < before


def main() -> None:
    strengthening_fixture()
    checked = exhaustive_small_suite()
    print("TOPA_POLICY0B1_TOTAL_MACHINE_FINITE_REPLAY = PASS")
    print("TOPA_POLICY0B1_DETERMINISM = PASS")
    print("TOPA_POLICY0B1_SAT_WITNESS_REPLAY = PASS")
    print("TOPA_POLICY0B1_UNSAT_BRANCH_CERTIFICATE_REPLAY = PASS")
    print("TOPA_POLICY0B1_FAIR_STRENGTHENING_POTENTIAL = PASS")
    print(f"TOPA_POLICY0B1_EXHAUSTIVE_CNFS_CHECKED = {checked}")
    print("TOPA_POLICY0B1_AUTOMATIC_EXTENSIONS = NONE")
    print("TOPA_POLICY0B1_GLOBAL_REASON_CACHE = NONE")
    print("TOPA_POLICY0B1_TOTAL_RUNTIME_BOUND = 2^N * N^O(1)")
    print("TOPA_POLICY0B1_POLYNOMIAL_TOTAL_RUNTIME = NOT_ESTABLISHED")
    print("TOPA_POLICY0B1_CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
