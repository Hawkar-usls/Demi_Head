from itertools import product


def clause(*lits):
    s = frozenset(lits)
    assert all(-lit not in s for lit in s)
    return s


def sat_clause(c, assignment):
    return any((assignment[abs(l)] if l > 0 else 1 - assignment[abs(l)]) for l in c)


def sat_formula(formula, assignment):
    return all(sat_clause(c, assignment) for c in formula)


def vars_of(formula):
    return sorted({abs(l) for c in formula for l in c})


def brute_sat(formula):
    vs = vars_of(formula)
    for bits in product([0, 1], repeat=len(vs)):
        a = dict(zip(vs, bits))
        if sat_formula(formula, a):
            return True
    return False


def gate_clauses(e, a, b):
    # e <-> (a AND b)
    assert abs(a) != abs(b)
    return [
        clause(-e, a),
        clause(-e, b),
        clause(e, -a, -b),
    ]


def selector_lift(H, next_var):
    s, t, e = next_var, next_var + 1, next_var + 2
    FH = [clause(s, *tuple(C)) for C in H]
    FH.append(clause(t))
    full = FH + gate_clauses(e, s, t)
    return full, s, t, e


def entails_literal(formula, lit):
    # finite reference only: F entails lit iff F AND not(lit) is UNSAT
    return not brute_sat(formula + [clause(-lit)])


def test_selector_lift():
    fixtures = [
        # SAT
        [clause(1)],
        [clause(1, 2), clause(-1, 2)],
        [clause(1, 2), clause(-1, -2)],
        # UNSAT
        [clause(1), clause(-1)],
        [clause(1, 2), clause(-1, 2), clause(1, -2), clause(-1, -2)],
    ]

    for H in fixtures:
        maxv = max(vars_of(H), default=0)
        full, s, t, e = selector_lift(H, maxv + 1)
        h_unsat = not brute_sat(H)
        forced_e = entails_literal(full, e)
        assert forced_e == h_unsat, (H, h_unsat, forced_e)

        # Equivalent branch-death statement: e=0 branch is UNSAT iff H UNSAT.
        e0_dead = not brute_sat(full + [clause(-e)])
        assert e0_dead == h_unsat

    return len(fixtures)


def test_sequence_mass():
    # Exhaustive schema search with two live choices per stage.
    for K in range(0, 12):
        seq = 2 ** K
        assert seq == len(list(product([0, 1], repeat=K)))
    # Variable exponent is not a fixed polynomial: N^K with K=N outgrows N^c for fixed c.
    for N in [2, 3, 4, 5]:
        assert N ** N >= 2 ** N
    return True


def main():
    nfix = test_selector_lift()
    assert test_sequence_mass()
    print("AKINATOR_O7_SELECTOR_LIFT_FORCEDNESS_EQ_UNSAT = PASS", f"fixtures={nfix}")
    print("AKINATOR_O7_E0_BRANCH_DEATH_EQ_UNSAT = PASS")
    print("AKINATOR_O7_BINARY_SCHEMA_SEQUENCE_COUNT = PASS")
    print("CO_NP_COMPLETENESS = ANALYTICAL_REDUCTION_NOT_CI")
    print("BRUTE_FORCE_SCHEMA_ENUMERATION_ONLY = BARRIER_SCOPE")
    print("UNIVERSAL_PROOF_CARRYING_B2_SELECTOR = OPEN")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
