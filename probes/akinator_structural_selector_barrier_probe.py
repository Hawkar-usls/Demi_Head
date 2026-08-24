#!/usr/bin/env python3
"""Finite mechanics probe for the Akinator structural-selector barrier.

This does NOT prove the asymptotic NW lower bound. It checks only exact budget
algebra on named finite regimes and the F3D-style one-bit collapse mechanics.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class BudgetCase:
    N: int
    B: int
    D: int

    @property
    def lhs(self) -> float:
        return (self.D + 1) * math.log2(self.B + 2)

    @property
    def normalized(self) -> float:
        return self.lhs / math.log2(self.N)


def and_gate(a: bool, b: bool) -> bool:
    return a and b


def build_f3d_values(B: int, D: int, z: bool, ys: Tuple[bool, ...]) -> Dict[str, bool]:
    assert B >= 2 and D >= 1 and len(ys) == B
    values: Dict[str, bool] = {}
    tops = []
    for j in range(B):
        prev = and_gate(z, ys[j])
        values[f"g{j+1}_1"] = prev
        for t in range(2, D + 1):
            prev = and_gate(z, not prev)
            values[f"g{j+1}_{t}"] = prev
        tops.append(prev)

    agg = and_gate(not tops[0], not tops[1])
    values["A2"] = agg
    for k in range(3, B + 1):
        agg = and_gate(agg, not tops[k - 1])
        values[f"A{k}"] = agg
    return values


def check_one_bit_collapse() -> None:
    for B in range(2, 7):
        for D in range(1, 6):
            # Exhaust all y assignments for small B. Under z=0 every branch gate
            # is false and every aggregate is true.
            for mask in range(1 << B):
                ys = tuple(bool((mask >> j) & 1) for j in range(B))
                vals = build_f3d_values(B, D, False, ys)
                branch_vals = [v for k, v in vals.items() if k.startswith("g")]
                agg_vals = [v for k, v in vals.items() if k.startswith("A")]
                assert branch_vals and all(v is False for v in branch_vals)
                assert agg_vals and all(v is True for v in agg_vals)


def check_budget_examples() -> None:
    # Small finite sanity checks that do not assert asymptotic dominance.
    for k in range(8, 21):
        N = 2**k

        # With constant frontier width, logarithmic depth carries a larger frozen
        # F3 budget than a deliberately sublogarithmic sqrt(log N) depth.
        constB_shallow = BudgetCase(N=N, B=2, D=max(1, int(math.sqrt(k))))
        constB_log = BudgetCase(N=N, B=2, D=k)
        assert constB_log.normalized > constB_shallow.normalized

        # A polylog frontier paired with logN/loglogN depth is a valid finite
        # instance of the analytical tradeoff expression. This is mechanics only.
        D_bal = max(1, int(k / max(1.0, math.log2(k))))
        balanced = BudgetCase(N=N, B=max(2, k * k), D=D_bal)
        assert balanced.lhs > 0

    # Separate sufficiently-large finite witness for the asymptotic fact
    # N^(1/4) eventually dominates (log_2 N)^2. The previous failed replay
    # incorrectly demanded this already for k=8..20.
    for k in range(48, 81):
        N = 2**k
        poly_B = max(2, int(N ** 0.25))
        polylog_B = max(2, k * k)
        assert poly_B > polylog_B

        constD_polyB = BudgetCase(N=N, B=poly_B, D=2)
        constD_polylogB = BudgetCase(N=N, B=polylog_B, D=2)
        assert constD_polyB.normalized > constD_polylogB.normalized


def main() -> None:
    check_one_bit_collapse()
    check_budget_examples()
    print("AKINATOR_STRUCT_SELECTOR_F3_BUDGET_ALGEBRA = PASS")
    print("AKINATOR_STRUCT_SELECTOR_F3D_ONE_BIT_COLLAPSE = PASS")
    print("AKINATOR_STRUCT_SELECTOR_SMALL_N_ASYMPTOTIC_FIXTURE = REPAIRED")
    print("NW_LOCAL_SELECTOR_LOWER_BOUND = EXTERNAL_PLUS_INTERNAL_THEOREM_NOT_CI")
    print("LOW_BD_SELECTOR_BARRIER = ANALYTICAL_DERIVATION_NOT_CI")
    print("ROBUST_STRUCTURAL_PROGRESS_CERTIFICATE = OPEN")
    print("CLAIM_CEILING = FINITE_MECHANICS_ONLY")
    print("P_VS_NP = OPEN")


if __name__ == "__main__":
    main()
