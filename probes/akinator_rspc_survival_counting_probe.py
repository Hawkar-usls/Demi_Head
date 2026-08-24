#!/usr/bin/env python3
"""Finite mechanics probe for the RSPC survival-counting reduction.

The probe constructs actual frozen-style B2 AND-gate DAGs for small 3-CNFs,
then exhaustively verifies that residual crossing survival under full X
assignments equals the SAT witness set. It does NOT prove #P-hardness; that is
an analytical reduction documented separately.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Dict, Iterable, List, Sequence, Tuple


@dataclass(frozen=True)
class Lit:
    var: str
    neg: bool = False

    def flipped(self) -> "Lit":
        return Lit(self.var, not self.neg)


@dataclass(frozen=True)
class Gate:
    out: str
    a: Lit
    b: Lit


class B2Circuit:
    def __init__(self) -> None:
        self.gates: List[Gate] = []
        self._next = 0

    def and_gate(self, a: Lit, b: Lit, prefix: str = "e") -> Lit:
        # Frozen B2 legality gate used by this finite construction.
        assert a.var != b.var, (a, b)
        self._next += 1
        out = f"{prefix}{self._next}"
        self.gates.append(Gate(out, a, b))
        return Lit(out, False)

    def or2(self, a: Lit, b: Lit) -> Lit:
        # a OR b = NOT((NOT a) AND (NOT b)).
        u = self.and_gate(a.flipped(), b.flipped(), "or")
        return u.flipped()

    def or3(self, a: Lit, b: Lit, c: Lit) -> Lit:
        return self.or2(self.or2(a, b), c)

    def and_many(self, lits: Sequence[Lit]) -> Lit:
        assert lits
        cur = lits[0]
        for nxt in lits[1:]:
            cur = self.and_gate(cur, nxt, "conj")
        return cur

    def eval(self, roots: Dict[str, bool], target: Lit) -> bool:
        values: Dict[str, bool] = dict(roots)

        def lit_value(lit: Lit) -> bool:
            v = values[lit.var]
            return (not v) if lit.neg else v

        for gate in self.gates:
            values[gate.out] = lit_value(gate.a) and lit_value(gate.b)
        return lit_value(target)


def root_lit(encoded: int) -> Lit:
    var = f"x{abs(encoded)}"
    return Lit(var, encoded < 0)


def compile_3cnf(clauses: Sequence[Tuple[int, int, int]]) -> Tuple[B2Circuit, Lit]:
    c = B2Circuit()
    clause_outputs: List[Lit] = []
    for clause in clauses:
        assert len({abs(x) for x in clause}) == 3, clause
        a, b, d = (root_lit(x) for x in clause)
        clause_outputs.append(c.or3(a, b, d))
    h = c.and_many(clause_outputs)
    return c, h


def eval_cnf(clauses: Sequence[Tuple[int, int, int]], alpha: Dict[str, bool]) -> bool:
    def lit_ok(v: int) -> bool:
        bit = alpha[f"x{abs(v)}"]
        return (not bit) if v < 0 else bit

    return all(any(lit_ok(v) for v in clause) for clause in clauses)


def support_over_pq(c: B2Circuit, e: Lit, alpha: Dict[str, bool]) -> set[str]:
    table: Dict[Tuple[bool, bool], bool] = {}
    for p, q in product([False, True], repeat=2):
        roots = dict(alpha)
        roots.update({"p": p, "q": q})
        table[(p, q)] = c.eval(roots, e)

    support: set[str] = set()
    if any(table[(False, q)] != table[(True, q)] for q in [False, True]):
        support.add("p")
    if any(table[(p, False)] != table[(p, True)] for p in [False, True]):
        support.add("q")
    return support


def add_crossing_tail(c: B2Circuit, h: Lit) -> Lit:
    g = c.and_gate(Lit("p"), Lit("q"), "cross")
    return c.and_gate(h, g, "target")


def assignments(n: int) -> Iterable[Dict[str, bool]]:
    for bits in product([False, True], repeat=n):
        yield {f"x{i+1}": bit for i, bit in enumerate(bits)}


def forbidding_clause(bits: Tuple[bool, bool, bool]) -> Tuple[int, int, int]:
    # Clause false on exactly `bits`.
    out = []
    for i, bit in enumerate(bits, start=1):
        out.append(-i if bit else i)
    return tuple(out)  # type: ignore[return-value]


def check_fixture(name: str, clauses: Sequence[Tuple[int, int, int]], n: int = 3) -> None:
    c, h = compile_3cnf(clauses)
    e = add_crossing_tail(c, h)

    # Every emitted B2 gate respects the distinct-underlying-variable rule.
    assert all(g.a.var != g.b.var for g in c.gates)

    sat_witnesses = []
    crossing_witnesses = []
    for alpha in assignments(n):
        sat = eval_cnf(clauses, alpha)
        crossing = support_over_pq(c, e, alpha) == {"p", "q"}
        assert crossing == sat, (name, alpha, sat, crossing)
        if sat:
            sat_witnesses.append(tuple(alpha[f"x{i+1}"] for i in range(n)))
        if crossing:
            crossing_witnesses.append(tuple(alpha[f"x{i+1}"] for i in range(n)))

    assert sat_witnesses == crossing_witnesses
    assert len(crossing_witnesses) == len(sat_witnesses)


def main() -> None:
    all_forbid = [forbidding_clause(bits) for bits in product([False, True], repeat=3)]
    all_but_111 = [
        forbidding_clause(bits)
        for bits in product([False, True], repeat=3)
        if bits != (True, True, True)
    ]

    fixtures = {
        "one_clause": [(1, 2, 3)],
        "exclude_000_111": [(1, 2, 3), (-1, -2, -3)],
        "mixed": [(1, 2, 3), (-1, 2, 3), (1, -2, 3), (1, 2, -3)],
        "unique_111": all_but_111,
        "unsat_all_assignments_forbidden": all_forbid,
    }

    for name, clauses in fixtures.items():
        check_fixture(name, clauses)

    print(f"AKINATOR_RSPC_EXACT_SURVIVAL_NUMERATOR_EQ_SAT_COUNT = PASS fixtures={len(fixtures)}")
    print("AKINATOR_RSPC_SINGLE_CANDIDATE_SURVIVAL_WITNESS_EQ_SAT_WITNESS = PASS")
    print("AKINATOR_RSPC_B2_DISTINCT_OPERAND_GATE = PASS")
    print("EXACT_SURVIVAL_#P_HARDNESS = ANALYTICAL_REDUCTION_NOT_CI")
    print("SURVIVAL_WITNESS_SEARCH_HARDNESS = ANALYTICAL_REDUCTION_NOT_CI")
    print("SOKOLOV_SOURCE_MATCHED_SURVIVAL_HARDNESS = NOT_PROVED")
    print("SOUND_INCOMPLETE_SURVIVAL_LOWER_BOUND_CERTIFICATE = OPEN")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
