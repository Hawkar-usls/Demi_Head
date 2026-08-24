#!/usr/bin/env python3
"""Finite mechanics replay for F3D-D4-X parity residual transfer.

Checks exact truth-table CNF restriction identity and the arithmetic/locality
mechanics used by the analytical theorem. It does not prove the asymptotic
Resolution lower bound.
"""
from itertools import product


def parity(bits):
    out=0
    for b in bits: out ^= b
    return out


def blocking_clause(vars_, alpha):
    # Literal (var, sign) with sign 1 meaning positive x, 0 meaning ~x.
    # Clause is falsified exactly by alpha.
    return tuple((v, 1-a) for v,a in zip(vars_, alpha))


def dir_parity(vars_, c):
    clauses=[]
    for bits in product((0,1), repeat=len(vars_)):
        if parity(bits) != c:
            clauses.append(blocking_clause(vars_, bits))
    return tuple(sorted(clauses))


def restrict_clause(clause, rho):
    out=[]
    for v,positive in clause:
        if v not in rho:
            out.append((v,positive)); continue
        lit_value = rho[v] if positive else 1-rho[v]
        if lit_value==1:
            return None  # satisfied clause
    return tuple(out)


def restrict_cnf(cnf, rho):
    out=[]
    for C in cnf:
        D=restrict_clause(C,rho)
        if D is not None:
            out.append(D)
    return tuple(sorted(set(out)))


def residual_constant(c, vars_, rho):
    assigned=[rho[v] for v in vars_ if v in rho]
    return c ^ parity(assigned)


def replay_one(vars_, c, rho):
    lhs=restrict_cnf(dir_parity(vars_,c),rho)
    free=tuple(v for v in vars_ if v not in rho)
    if not free:
        # If rho satisfies the equation, all clauses disappear.
        expected=() if parity(tuple(rho[v] for v in vars_))==c else ((),)
    else:
        expected=dir_parity(free,residual_constant(c,vars_,rho))
    assert lhs==expected,(vars_,c,rho,lhs,expected)


def main():
    V=("x","y","z","w")
    for c in (0,1):
        # Exhaust every partial assignment pattern with values 0/1/*.
        for states in product((-1,0,1), repeat=len(V)):
            rho={v:s for v,s in zip(V,states) if s!=-1}
            replay_one(V,c,rho)

    # Residual balancedness arithmetic: epsilon=1/16, Delta=16.
    eps=1/16
    Delta=16
    dmin=(1-2*eps)*Delta
    assert dmin-1 >= 6*eps*Delta
    assert (1-8*eps)*Delta >= 1

    # Semantic-local admission mechanics in a residual locality hypergraph.
    hoods=[{"x","y"},{"y","z"},{"w"}]
    assert any({"x","y"} <= H for H in hoods)
    assert not any({"x","z"} <= H for H in hoods)

    # Input-size ratio factor from degree shrink is 2^(2 eps Delta).
    ratio_exp=2*eps*Delta
    assert ratio_exp==2
    assert 2**int(ratio_exp)==4

    print("TOPA_F3D_D4_X_DIRECT_PARITY_RESTRICTION_IDENTITY = PASS")
    print("TOPA_F3D_D4_X_FULLY_SATISFIED_OUTPUT_DISAPPEARS = PASS")
    print("TOPA_F3D_D4_X_RESIDUAL_BALANCEDNESS_ARITHMETIC = PASS")
    print("TOPA_F3D_D4_X_LOCAL_FUNCTION_ADMISSION_MECHANICS = PASS")
    print("TOPA_F3D_D4_X_FIXED_POLY_INPUT_RATIO_FIXTURE = PASS")
    print("TOPA_F3D_D4_X_CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("TOPA_F3D_D4_X_ASYMPTOTIC_LOWER_BOUND = SOURCE_THEOREM_DERIVED_NOT_CI_PROVED")
    print("P_VS_NP = OPEN")

if __name__=='__main__':
    main()
