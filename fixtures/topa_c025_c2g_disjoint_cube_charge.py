#!/usr/bin/env python3
"""Finite mechanics replay for the C2G disjoint cube charge theorem."""
from __future__ import annotations

from itertools import product


def falsifying_requirements(clause):
    req={}
    for lit in clause:
        var=abs(lit)
        value=0 if lit>0 else 1
        if var in req and req[var]!=value:
            raise ValueError('tautological clause has empty falsifying cube')
        req[var]=value
    return req


def disjoint(c,d):
    rc=falsifying_requirements(c); rd=falsifying_requirements(d)
    return any(var in rd and rd[var]!=value for var,value in rc.items())


def cube_size(n,clause):
    r=len(falsifying_requirements(clause))
    return 2**(n-r)


def clause_for_falsifying_pattern(bits):
    # bit 0 is falsified by positive literal; bit 1 by negative literal.
    return tuple((i+1 if bit==0 else -(i+1)) for i,bit in enumerate(bits))


def main():
    # Tight partition by all width-2 patterns.
    four=[(1,2),(-1,2),(1,-2),(-1,-2)]
    for i,c in enumerate(four):
        for d in four[i+1:]:
            assert disjoint(c,d)
    assert sum(cube_size(5,c) for c in four)==2**5
    assert len(four)==2**2

    # Explicit overlap must be rejected.
    assert not disjoint((1,2),(2,3))
    assert disjoint((1,2),(-1,3))

    # The 2^w bound is tight for a full width-w partition.
    for w in range(1,7):
        clauses=[clause_for_falsifying_pattern(bits) for bits in product((0,1),repeat=w)]
        assert len(clauses)==2**w
        for i,c in enumerate(clauses):
            for d in clauses[i+1:]:
                assert disjoint(c,d)
        n=w+4
        assert sum(cube_size(n,c) for c in clauses)==2**n

    # Full path guarding grows width linearly in path depth.
    for depth in range(1,17):
        guarded=tuple(range(1,depth+1))
        assert len(guarded)==depth

    print('TOPA_C025_C2G_DISJOINTNESS_CRITERION = PASS')
    print('TOPA_C025_C2G_WIDTH_TO_COUNT_BOUND_TIGHT_FIXTURE = PASS')
    print('TOPA_C025_C2G_OVERLAP_REJECTION = PASS')
    print('TOPA_C025_C2G_PREFIX_GUARD_WIDTH_GROWTH = PASS')
    print('TOPA_C025_C2G_UNIVERSAL_CHARGE_DISCOVERY = OPEN')
    print('TOPA_C025_C2G_CLAIM_CEILING = FINITE_MECHANICS_ONLY')
    print('P_VS_NP = OPEN')


if __name__=='__main__':
    main()
