from itertools import product


def clause(*lits):
    s = frozenset(lits)
    assert all(-lit not in s for lit in s)
    return s


def resolve(a, b, pivot):
    assert pivot in a and -pivot in b
    out = (set(a) - {pivot}) | (set(b) - {-pivot})
    assert not any(-lit in out for lit in out), (a, b, pivot, out)
    return frozenset(out)


def restrict_clause(c, rho):
    out = set()
    for lit in c:
        var = abs(lit)
        if var not in rho:
            out.add(lit)
            continue
        value = rho[var]
        satisfied = (lit > 0 and value == 1) or (lit < 0 and value == 0)
        if satisfied:
            return None
        # falsified context literal disappears
    return frozenset(out)


def restrict_formula(formula, rho):
    return [r for c in formula if (r := restrict_clause(c, rho)) is not None]


def blocking_clause(rho):
    return frozenset(var if value == 0 else -var for var, value in rho.items())


def max_width(lines):
    return max((len(c) for c in lines), default=0)


def assert_axiom_lift_shape(formula, rho):
    """Finite check of A subseteq (A|rho) OR B(rho) for surviving axioms."""
    block = blocking_clause(rho)
    for axiom in formula:
        residual = restrict_clause(axiom, rho)
        if residual is None:
            continue
        assert axiom <= (set(residual) | set(block)), (axiom, residual, block)


def test_single_context():
    formula = [
        clause(1, 2),
        clause(1, -2),
        clause(-1, 3),
        clause(-1, -3),
    ]
    w0 = max_width(formula)

    left_residual = restrict_formula(formula, {1: 0})
    right_residual = restrict_formula(formula, {1: 1})
    assert set(left_residual) == {clause(2), clause(-2)}
    assert set(right_residual) == {clause(3), clause(-3)}
    assert_axiom_lift_shape(formula, {1: 0})
    assert_axiom_lift_shape(formula, {1: 1})

    # Each residual width-1 contradiction lifts to the child's blocking unit clause.
    left_block = resolve(formula[0], formula[1], 2)
    right_block = resolve(formula[2], formula[3], 3)
    assert left_block == blocking_clause({1: 0}) == clause(1)
    assert right_block == blocking_clause({1: 1}) == clause(-1)

    root = resolve(left_block, right_block, 1)
    assert root == frozenset()

    local_width = 1
    depth = 1
    bound = max(w0, local_width + depth)
    compiled = [*formula, left_block, right_block, root]
    assert max_width(compiled) <= bound
    return bound, max_width(compiled)


def test_nested_context_depth2():
    # Four clauses forbid the four assignments of x1,x2.
    formula = [
        clause(1, 2),
        clause(1, -2),
        clause(-1, 2),
        clause(-1, -2),
    ]

    # A depth-2 branch tree reaches an empty residual axiom at every leaf.
    for x1, x2 in product([0, 1], repeat=2):
        rho = {1: x1, 2: x2}
        residual = restrict_formula(formula, rho)
        assert frozenset() in residual, (rho, residual)
        assert_axiom_lift_shape(formula, rho)

    # Compile the exhaustive question tree back to ordinary Resolution.
    left = resolve(formula[0], formula[1], 2)
    right = resolve(formula[2], formula[3], 2)
    root = resolve(left, right, 1)
    assert left == clause(1)
    assert right == clause(-1)
    assert root == frozenset()

    w0 = max_width(formula)
    local_width = 0
    depth = 2
    bound = max(w0, local_width + depth)
    compiled = [*formula, left, right, root]
    assert max_width(compiled) <= bound
    return bound, max_width(compiled)


def test_root_global_flatten():
    formula = [
        clause(1, 2),
        clause(1, -2),
        clause(-1, 3),
        clause(-1, -3),
    ]
    d1 = resolve(formula[0], formula[1], 2)
    d2 = resolve(formula[2], formula[3], 3)
    empty = resolve(d1, d2, 1)
    proof = [*formula, d1, d2, empty]
    assert empty == frozenset()
    assert max_width(proof) == 2
    return max_width(proof)


def main():
    bound1, actual1 = test_single_context()
    bound2, actual2 = test_nested_context_depth2()
    root_width = test_root_global_flatten()

    print("AKINATOR_O5_CONTEXT_AXIOM_LIFT_SHAPE = PASS")
    print(
        "AKINATOR_O5_SINGLE_CONTEXT_WIDTH_BOUND = PASS",
        f"bound={bound1}",
        f"actual={actual1}",
    )
    print(
        "AKINATOR_O5_NESTED_TREE_WIDTH_BOUND = PASS",
        f"bound={bound2}",
        f"actual={actual2}",
    )
    print("AKINATOR_O5_ROOT_GLOBAL_FLATTEN = PASS", f"width={root_width}")
    print("AKINATOR_O5_BRANCH_COMPOSITION = PASS")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
