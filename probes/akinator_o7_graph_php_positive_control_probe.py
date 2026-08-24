from itertools import product


def clause(*lits):
    s = frozenset(lits)
    assert all(-lit not in s for lit in s)
    return s


def resolve(a, b, pivot):
    assert pivot in a and -pivot in b
    out = (set(a) - {pivot}) | (set(b) - {-pivot})
    assert not any(-lit in out for lit in out)
    return frozenset(out)


def gate_clauses(e, a, b):
    # e <-> (a AND b), with signed literals a,b.
    assert abs(a) != abs(b)
    return [
        clause(-e, a),
        clause(-e, b),
        clause(e, -a, -b),
    ]


def eval_lit(lit, values):
    v = values[abs(lit)]
    return v if lit > 0 else (1 - v)


def test_false_gadget():
    # roots a=1,b=2; t1=3,t2=4,z0=5; missing placeholder m=6
    a, b, t1, t2, z0, m = 1, 2, 3, 4, 5, 6
    g1 = gate_clauses(t1, a, b)
    g2 = gate_clauses(t2, -a, b)
    g3 = gate_clauses(z0, t1, t2)
    g4 = gate_clauses(m, z0, a)

    for av, bv in product([0, 1], repeat=2):
        vals = {a: av, b: bv}
        vals[t1] = eval_lit(a, vals) & eval_lit(b, vals)
        vals[t2] = eval_lit(-a, vals) & eval_lit(b, vals)
        vals[z0] = vals[t1] & vals[t2]
        vals[m] = vals[z0] & vals[a]
        assert vals[z0] == 0
        assert vals[m] == 0

    # Pure Resolution derivation of NOT z0.
    z_or_a = resolve(clause(-z0, t1), clause(-t1, a), t1)
    z_or_not_a = resolve(clause(-z0, t2), clause(-t2, -a), t2)
    not_z = resolve(z_or_a, z_or_not_a, a)
    assert not_z == clause(-z0)

    # Derive NOT m from NOT z0 and (NOT m OR z0).
    not_m = resolve(clause(-m, z0), not_z, z0)
    assert not_m == clause(-m)
    return True


def test_cook_macro_b2():
    # Semantic test of x' = a OR (b AND c) encoded as
    # t=(b AND c), u=((NOT a) AND (NOT t)), x' represented by NOT u.
    a, b, c, t, u = 1, 2, 3, 4, 5
    gate_clauses(t, b, c)
    gate_clauses(u, -a, -t)

    for av, bv, cv in product([0, 1], repeat=3):
        vals = {a: av, b: bv, c: cv}
        vals[t] = vals[b] & vals[c]
        vals[u] = (1 - vals[a]) & (1 - vals[t])
        encoded = 1 - vals[u]
        expected = vals[a] | (vals[b] & vals[c])
        assert encoded == expected
    return True


def graph_php_stronger_axioms():
    # Small canonical 3-pigeon / 2-hole graph with nonedges.
    # p0->{h0}; p1->{h0,h1}; p2->{h1}.
    # Full variables get ids 1..6 in (p,h) order.
    ids = {(p, h): 1 + 2 * p + h for p in range(3) for h in range(2)}
    allowed = {(0, 0), (1, 0), (1, 1), (2, 1)}
    missing = set(ids) - allowed

    # Distinct placeholder ids for missing full-PHP variables.
    placeholder = {}
    next_id = 20
    for edge in sorted(missing):
        placeholder[edge] = next_id
        next_id += 1

    def full_lit_var(p, h):
        return ids[(p, h)] if (p, h) in allowed else placeholder[(p, h)]

    stronger = []
    full_axioms = []

    # Pigeon clauses: graph clause is a subclause of the full placeholder clause.
    for p in range(3):
        full = clause(*(full_lit_var(p, h) for h in range(2)))
        graph = clause(*(ids[(p, h)] for h in range(2) if (p, h) in allowed))
        assert graph <= full
        full_axioms.append(full)
        stronger.append(graph)

    # Collision clauses for each hole / pigeon pair.
    for h in range(2):
        for p in range(3):
            for q in range(p + 1, 3):
                vp = full_lit_var(p, h)
                vq = full_lit_var(q, h)
                full = clause(-vp, -vq)
                full_axioms.append(full)
                if (p, h) in allowed and (q, h) in allowed:
                    strong = clause(-ids[(p, h)], -ids[(q, h)])
                elif (p, h) not in allowed:
                    strong = clause(-placeholder[(p, h)])
                else:
                    strong = clause(-placeholder[(q, h)])
                assert strong <= full
                stronger.append(strong)

    assert len(full_axioms) == len(stronger)
    assert all(s <= f for s, f in zip(stronger, full_axioms))
    return True


def strengthen_resolution_proof():
    # Synthetic source proof:
    # A1=(x OR y), A2=(NOT x OR z), A3=(NOT y), A4=(NOT z)
    # source derives (y OR z), then z, then empty.
    # Stronger A1'=(x), A2'=(NOT x OR z), A3/A4 unchanged.
    x, y, z = 1, 2, 3
    A1 = clause(x, y)
    A2 = clause(-x, z)
    A3 = clause(-y)
    A4 = clause(-z)
    source_r1 = resolve(A1, A2, x)
    source_r2 = resolve(source_r1, A3, y)
    source_empty = resolve(source_r2, A4, z)
    assert source_empty == frozenset()

    D1 = clause(x)  # D1 subset A1
    D2 = A2
    # Resolve stronger premises on x -> (z), a subclause of (y OR z).
    r1 = resolve(D1, D2, x)
    assert r1 <= source_r1
    # Source next pivot y disappeared from r1, so reuse r1.
    r2 = r1
    assert r2 <= source_r2
    empty = resolve(r2, A4, z)
    assert empty == frozenset()
    return True


def main():
    assert test_false_gadget()
    assert test_cook_macro_b2()
    assert graph_php_stronger_axioms()
    assert strengthen_resolution_proof()

    print("AKINATOR_O7_B2_FALSE_GADGET = PASS")
    print("AKINATOR_O7_COOK_MACRO_B2_ENCODING = PASS")
    print("AKINATOR_O7_GRAPH_PHP_STRONGER_AXIOM_MAP = PASS")
    print("AKINATOR_O7_SUBSUMPTION_SIMULATION_FIXTURE = PASS")
    print("SOURCE_COOK_POLY_ER = EXTERNAL_THEOREM_NOT_CI")
    print("UNIVERSAL_SCHEMA_SELECTION = OPEN")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
