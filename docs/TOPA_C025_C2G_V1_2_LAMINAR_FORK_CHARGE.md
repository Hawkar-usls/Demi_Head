# TOPA C025-C2G v1.2 — Laminar Fork-Charge Repair

**Frozen:** 2026-08-24T23:17:00+03:00  
**Parent:** `TOPA_C025_C2G_V1_1_FORK_CHARGE_REPAIR.md`  
**Status:** `V1_1_PAIRWISE_DISJOINT_FORK_RULE_REFUTED__V1_2_LAMINAR_COUNT_THEOREM_PROVED`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. v1.1 nested-fork barrier

v1.1 required the charge cubes for all binary forks to be pairwise disjoint.

That is incompatible with nested forks.

Let fork `A` have first-child context `rho_A`. Let fork `D` occur inside the explored first-child subtree of `A`, with first-child context `rho_D` extending `rho_A`.

If clause `C_A` is falsified by `rho_A`, every full assignment extending `rho_A` falsifies `C_A`, so its cube `Q(C_A)` contains the entire context cube of `rho_A`.

Likewise `Q(C_D)` contains every extension of `rho_D`.

Because `rho_D` extends `rho_A`, choose any full assignment extending `rho_D`. It lies in both cubes. Hence

```text
Q(C_A) intersect Q(C_D) != empty.
```

### C2G-F2 — nested-fork disjointness impossibility

No charge system tied to actual first-child contexts can assign pairwise-disjoint cubes to an ancestor fork and a descendant fork inside its first-child subtree.

Thus v1.1 pairwise-disjointness is refuted as a universal fork-charge rule.

---

# 2. Exact machine witness — K4 Tseitin odd charge

Use the degree-3 graph `K4` with one Boolean edge variable per edge and parity constraints at each vertex whose total charge is odd.

The standard degree-3 truth-table CNF contains four width-3 clauses per vertex and is UNSAT because XORing all vertex equations cancels every edge variable but leaves odd total charge.

On the frozen Policy-0B.1 baseline:

- root preprocessing has no conflict/unit;
- branch on edge variable `1`;
- the false child branches again on edge variable `2` before contradiction;

so the explored first-child subtree contains a nested binary fork.

This finite fixture witnesses that the v1.1 geometric obstruction occurs in the actual frozen machine, not only in an abstract tree.

Finite replay validates mechanics only; the general nested-cube theorem above is analytic.

---

# 3. v1.2 repair — laminar charge cubes

Replace pairwise disjointness by **laminarity**.

A family of charge cubes is laminar iff every two distinct cubes satisfy exactly one of:

```text
Q(C) intersect Q(D) = empty,
Q(C) proper_subset Q(D),
Q(D) proper_subset Q(C).
```

For falsifying cubes of canonical non-tautological clauses, all three relations are checkable directly from literals:

### Disjoint

```text
exists literal l with l in C and -l in D.
```

### Containment

```text
Q(C) subseteq Q(D)
iff
D subseteq C
```

because a wider clause fixes more falsifying coordinates and therefore defines a smaller cube.

No semantic or counting oracle is required.

---

# 4. Laminar width-to-count theorem

Let `L={Q(C_1),...,Q(C_k)}` be a finite laminar family of distinct nonempty falsifying cubes, each defined by a clause of width at most `w`.

## 4.1 Nesting depth

If

```text
Q(C_0) proper_superset Q(C_1) proper_superset ... proper_superset Q(C_t),
```

then the corresponding required coordinate sets strictly increase at every step. Width therefore increases by at least one per strict containment.

Since every width is at most `w`, every strict nesting chain contains at most

```text
w+1
```

cubes.

## 4.2 Number of leaves

The inclusion-minimal cubes of a laminar family are pairwise disjoint.

Each has width at most `w`, hence size at least

```text
2^(n-w).
```

They all lie inside the `2^n` assignment cube, so the number of inclusion-minimal cubes is at most

```text
2^w.
```

## 4.3 Total family size

Every charge cube lies on a containment path ending at at least one inclusion-minimal cube. Summing path lengths gives the safe bound

```text
k <= (w+1) * 2^w.
```

### C2G-T5 — laminar charge count

A laminar family of distinct falsifying cubes represented by root clauses of width at most `w` contains at most

```text
(w+1)2^w
```

members.

For

```text
w <= c log_2 N
```

with universal fixed `c`,

```text
k <= (c log_2 N + 1) N^c = N^O(1).
```

---

# 5. v1.2 fork-charge theorem

At every actual binary fork of the explored deterministic execution tree, after the first child returns UNSAT and before opening the second child, require a fresh charge reason `(C_j,pi_j)` such that:

1. `pi_j` standalone-verifies `F |= C_j`;
2. the first-child root decision/propagation context falsifies `C_j`;
3. `|C_j| <= c log_2 N`;
4. the complete immutable charge-cube family remains laminar;
5. no fork reuses a previous charge object.

Then the number of forks satisfies

```text
B <= (w+1)2^w = N^O(1).
```

Using the already-proved explored-tree bound

```text
TOTAL_NODES <= (n+1)(B+1),
```

total explored states are polynomial.

Together with polynomial per-state work and polynomial proof/ledger representation, total runtime is polynomial.

### C2G-T6 — laminar fork-charge sufficient theorem

The v1.2 rule is a sufficient global progress theorem that allows both sibling-disjoint and ancestor-descendant nested conflict summaries.

It is not a proof that the required reasons universally exist or can be discovered cheaply.

---

# 6. Why natural context clauses fit the geometry but not the width gate

If an UNSAT child is summarized by the clause negating its full decision context, the corresponding falsifying cube is exactly that child context cube.

Execution-tree context cubes are naturally laminar/disjoint according to ancestry.

Therefore full context clauses satisfy the **geometry** of v1.2 automatically.

However their width equals context depth and can be `Theta(n)`.

Thus the remaining nontrivial resource is exactly:

```text
SHORT LAMINAR GENERALIZATION OF A DEEP CONFLICT.
```

This is a proof-complexity/discovery obligation, not a geometric bookkeeping problem.

---

# 7. Next falsifiers

Any universal v1.2 claim must now survive:

1. deep conflicts whose minimum applicable root implicate width is `omega(log N)`;
2. short conflict clauses whose natural cubes cross rather than nest/disjoin with the existing ledger;
3. short clauses with superpolynomial B2 proof bytes;
4. polynomial proof existence but superpolynomial deterministic extraction;
5. attempts to force laminarity by adding path guards that raise width to `Omega(depth)`.

---

# 8. Status

```text
C2G_V1_PER_BRANCH_CHARGE                  = REFUTED
C2G_V1_1_PAIRWISE_DISJOINT_FORK_CHARGE    = REFUTED_BY_NESTED_FORKS
C2G_V1_2_LAMINAR_RELATION_CHECK           = PROVED
C2G_V1_2_LAMINAR_WIDTH_TO_COUNT           = PROVED
C2G_V1_2_FORK_TO_TOTAL_STATE_BOUND        = PROVED_AS_SUFFICIENT
C2G_V1_2_UNIVERSAL_SHORT_LAMINAR_REASON   = OPEN / KILLER GATE
C2G_V1_2_DETERMINISTIC_DISCOVERY          = OPEN
C2G_V1_2_POLY_TOTAL_PROOF_BYTES           = OPEN
P_VS_NP                                   = OPEN
```

---

# 9. Claim firewall

```text
LAMINAR_COUNT_THEOREM
!=
UNIVERSAL_LAMINAR_REASON_EXISTENCE

NATURAL_CONTEXT_CUBES_ARE_LAMINAR
!=
NATURAL_CONTEXT_CLAUSES_ARE_SHORT

K4_FINITE_REPLAY
!=
ASYMPTOTIC_C2_RESULT

C2G_T6
!=
P_EQUALS_NP

P_VS_NP = OPEN
```
