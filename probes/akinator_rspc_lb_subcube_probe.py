#!/usr/bin/env python3
"""Finite mechanics probe for RSPC-LB subcube certificates.

Checks two finite identities only:
1) on named 3-CNF fixtures, full-cube universal crossing of
   e=(NOT H) AND (p AND q) iff the fixture is UNSAT;
2) the exact codimension-k subcube count is C(n,k)2^k.

coNP-completeness and asymptotic exp(Theta(log^2 N)) growth are analytical
results, not CI claims.
"""

from __future__ import annotations

import math
from itertools import combinations, product

from akinator_rspc_survival_counting_probe import (
    Lit,
    add_crossing_tail,
    assignments,
    compile_3cnf,
    eval_cnf,
    forbidding_clause,
    support_over_pq,
)


def make_negated_crossing_target(clauses):
    c, h = compile_3cnf(clauses)
    g = c.and_gate(Lit("p"), Lit("q"), "cross")
    e = c.and_gate(h.flipped(), g, "target_not_h")
    return c, e


def full_cube_survives(c, e, n: int) -> bool:
    for alpha in assignments(n):
        if support_over_pq(c, e, alpha) != {"p", "q"}:
            return False
    return True


def check_full_cube_identity() -> None:
    all_forbid = [forbidding_clause(bits) for bits in product([False, True], repeat=3)]
    all_but_111 = [
        forbidding_clause(bits)
        for bits in product([False, True], repeat=3)
        if bits != (True, True, True)
    ]
    fixtures = {
        "one_clause": [(1, 2, 3)],
        "exclude_000_111": [(1, 2, 3), (-1, -2, -3)],
        "unique_111": all_but_111,
        "unsat_all_assignments_forbidden": all_forbid,
    }

    for name, clauses in fixtures.items():
        c, e = make_negated_crossing_target(clauses)
        is_unsat = not any(eval_cnf(clauses, alpha) for alpha in assignments(3))
        survives = full_cube_survives(c, e, 3)
        assert survives == is_unsat, (name, survives, is_unsat)


def enumerate_subcubes(n: int, k: int):
    out = set()
    for vars_fixed in combinations(range(n), k):
        for bits in product([0, 1], repeat=k):
            out.add(tuple(zip(vars_fixed, bits)))
    return out


def check_subcube_count() -> None:
    for n in range(2, 9):
        for k in range(0, min(3, n) + 1):
            actual = len(enumerate_subcubes(n, k))
            expected = math.comb(n, k) * (2**k)
            assert actual == expected, (n, k, actual, expected)

    # Finite scale witnesses only; asymptotic classification is analytical.
    for N in (1024, 4096, 16384):
        k = int(math.log2(N))
        count = math.comb(N, k) * (2**k)
        assert count > N**2


def main() -> None:
    check_full_cube_identity()
    check_subcube_count()
    print("AKINATOR_RSPC_LB_FULL_CUBE_SURVIVAL_EQ_UNSAT = PASS")
    print("AKINATOR_RSPC_LB_SUBCUBE_COUNT_FORMULA = PASS")
    print("AKINATOR_RSPC_LB_FINITE_LARGE_REGION_COUNT = PASS")
    print("SEMANTIC_FULL_CUBE_SURVIVAL_CoNP_COMPLETENESS = ANALYTICAL_REDUCTION_NOT_CI")
    print("CODIM_LOG_N_ENUMERATION_ASYMPTOTIC = ANALYTICAL_COUNTING_NOT_CI")
    print("PROOF_CARRYING_ROBUST_REGION_CONSTRUCTOR = OPEN")
    print("SOKOLOV_SOURCE_MATCHED_REGION_HARDNESS = NOT_PROVED")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
