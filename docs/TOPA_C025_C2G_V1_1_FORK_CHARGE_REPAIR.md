# TOPA C025-C2G v1.1 — Binary-Fork Charge Repair

**Frozen:** 2026-08-24T23:17:00+03:00  
**Parent:** `TOPA_C025_C2G_DISJOINT_CUBE_CHARGE_CANDIDATE.md`  
**Status:** `V1_PER_BRANCH_REQUIREMENT_REFUTED__V1_1_FORK_CHARGE_SUFFICIENT_THEOREM_PROVED`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why v1.0 was too strong

The first C2G candidate required every branch event to emit a fresh pairwise-disjoint globally certified reason of width `O(log N)`.

That condition is sufficient, but it is not universally necessary even for formulas that the frozen Policy-0B.1 solves in polynomial time.

## 2. Infinite counterfamily to universal per-branch short charging

Let

```text
F_n := (x_1 OR x_2 OR ... OR x_n)
```

be a CNF consisting of one width-`n` clause.

### Policy-0B.1 behavior

With minimum-root-id, false-first branching:

```text
x_1=0,
x_2=0,
...,
x_(n-1)=0,
```

leaves the final unit `(x_n)`, and exact UP assigns `x_n=1`.

The first explored child remains satisfiable throughout the path, so the execution contains only a unary SAT spine and does not open the unvisited true siblings.

Total branch events are `O(n)`.

### Lemma — no narrow non-tautological implicate

If a non-tautological clause `D` mentions fewer than `n` root variables, select an unmentioned root `x_j` and set `x_j=1`. Assign every variable mentioned by `D` so that its literal in `D` is false. Then:

```text
F_n is true,
D is false.
```

Hence

```text
F_n does not imply D.
```

Therefore every non-tautological implicate of `F_n` has width at least `n`.

For any fixed constant `c`, eventually

```text
n > c log N.
```

Thus no universal rule can require a fresh globally implied `O(log N)` root clause on **every** branch of this family.

### C2G-F1

```text
EVERY_BRANCH_REQUIRES_SHORT_DISJOINT_CHARGE
```

is refuted as a universal discovery requirement.

The underlying disjoint-cube counting theorem remains correct.

---

# 3. Correct object — explored execution tree

Define the **explored execution tree** of the deterministic depth-first solver:

- a terminal node has outdegree `0`;
- a node has outdegree `1` when its first explored child returns SAT and the second branch is never opened;
- a node has outdegree `2` exactly when the first child returns UNSAT and the solver proceeds to explore the second child.

Call an outdegree-`2` node a **binary fork**.

For an UNSAT run every internal node is a fork. For a SAT run, long satisfiable spines may be unary.

---

# 4. Tree combinatorics

Let execution-tree depth be at most `n`, and let `B` be the number of binary forks.

For any finite rooted tree with outdegrees in `{0,1,2}`:

```text
number_of_leaves = B + 1.
```

This follows from

```text
leaves = 1 + sum_internal(outdegree-1),
```

and unary nodes contribute zero.

Every root-to-leaf path contains at most `n+1` nodes. The entire tree is contained in the union of its root-to-leaf paths, hence

```text
TOTAL_NODES <= (n+1)(B+1).
```

### C2G-T3 — fork-to-total-node bound

A polynomial bound on binary forks is sufficient for a polynomial total execution-tree bound, because `n<=N`.

---

# 5. v1.1 fork charge rule

Only binary forks require a charge.

At a fork, the first child has already returned UNSAT. Before the second child is explored, require a fresh charge reason

```text
(C_j, pi_j)
```

such that:

1. `pi_j` standalone-verifies `F |= C_j` from the immutable root CNF;
2. the first-child decision/propagation context falsifies every literal of `C_j`;
3. `|C_j| <= c log_2 N` for one universal fixed `c`;
4. `Q(C_j)` is disjoint from every earlier fork-charge cube;
5. the charge is immutable and used once.

Condition 2 makes the charge proof-relevant: it generalizes an actually explored UNSAT first child rather than serving as an unrelated decorative token.

---

# 6. v1.1 polynomial execution theorem

By the original disjoint-cube theorem, pairwise-disjoint charge cubes of width at most `w` number at most

```text
B <= 2^w.
```

With

```text
w <= c log_2 N,
```

we have

```text
B <= N^c.
```

Using C2G-T3:

```text
TOTAL_NODES
<= (n+1)(B+1)
<= (N+1)(N^c+1)
= N^O(1).
```

### C2G-T4 — fork-charge sufficient theorem

If every binary fork of the frozen deterministic solver admits a fresh proof-carrying pairwise-disjoint root-clause charge of width at most `c log N`, then its explored state count is polynomial.

Combined with polynomial per-state work and polynomial total proof/ledger representation, total runtime is polynomial.

This is a sufficient theorem only.

---

# 7. Why this repair is strictly better

The wide-single-clause family has no short global implicates, but its successful execution has

```text
B=0.
```

Therefore v1.1 asks for no charges on its unary SAT spine and correctly permits the polynomial run.

The charge mechanism is now targeted precisely at **search duplication**, not at harmless depth.

---

# 8. Remaining killer gate

Prove or refute:

> Whenever the frozen successor solver encounters a binary fork, can it deterministically extract from the first UNSAT child a fresh context-independent root reason of width `O(log N)`, pairwise-disjoint from all prior fork charges, with total discovery/proof/ledger cost polynomial in original `N`?

This is now the exact C2G-v1.1 discovery problem.

Likely failure modes to test next:

- deep conflicts whose minimum root implicate width is `omega(log N)`;
- many conflicts whose natural reasons overlap all earlier charge cubes;
- short reasons exist but their B2 proofs are large;
- short proofs exist but deterministic extraction is expensive;
- orthogonalizing reasons by path guards increases width beyond `O(log N)`.

---

# 9. Status

```text
C2G_V1_EVERY_BRANCH_CHARGE               = REFUTED
C2G_V1_1_TREE_FORK_COMBINATORICS         = PROVED
C2G_V1_1_DISJOINT_SHORT_FORK_BOUND       = PROVED_AS_SUFFICIENT
C2G_V1_1_UNIVERSAL_FORK_REASON_EXISTENCE = OPEN
C2G_V1_1_POLYTIME_FORK_REASON_DISCOVERY  = OPEN
C2G_V1_1_POLY_TOTAL_PROOF_BYTES          = OPEN
P_VS_NP                                  = OPEN
```

---

# 10. Claim firewall

```text
POLYNOMIAL_TREE_IF_FORK_CHARGES_EXIST
!=
FORK_CHARGES_EXIST_FOR_ALL_CNF

SHORT_CONFLICT_REASON_EXISTS
!=
CHEAP_CONFLICT_ANALYSIS

V1_COUNTEREXAMPLE
!=
C2_IMPOSSIBILITY

V1_1_SUFFICIENT_THEOREM
!=
P_EQUALS_NP

P_VS_NP = OPEN
```
