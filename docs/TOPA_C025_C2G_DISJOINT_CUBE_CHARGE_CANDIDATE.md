# TOPA C025-C2G — Disjoint Proof-Carrying Cube Charge

**Frozen:** 2026-08-24T23:17:00+03:00  
**Parent:** `TOPA_C025_C2_HIDDEN_SEARCH_EXPONENT_AUDIT.md`  
**Status:** `SUFFICIENT_PROGRESS_THEOREM_PROVED__UNIVERSAL_DISCOVERY_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Motivation

C2-G1 asks for a polynomially bounded global progress object that defeats branch-mass conservation without a heuristic score or hidden union-counting oracle.

A globally proof-carrying clause gives an exact geometric object in the root assignment cube.

---

# 2. Falsifying cube of a clause

Let `C` be a non-tautological clause over distinct root variables.

Define

```text
Q(C) := { alpha in {0,1}^n : alpha falsifies every literal of C }.
```

If `|C|=r`, exactly `r` root bits are fixed, so

```text
|Q(C)| = 2^(n-r).
```

If a standalone verifier proves

```text
F |= C,
```

then every assignment in `Q(C)` is certified not to satisfy `F`.

No semantic classifier is needed: clause implication is supplied by the existing proof-carrying reason certificate.

---

# 3. Exact disjointness test

For two non-tautological clauses `C,D`, their falsifying cubes are disjoint iff their required falsifying assignments conflict on at least one root variable.

Equivalently:

```text
Q(C) intersect Q(D) = empty
iff
exists literal l such that l in C and -l in D.
```

### Proof

Falsifying literal `x` requires `x=0`; falsifying literal `~x` requires `x=1`. Opposite signs on one shared variable make simultaneous falsification impossible. If there is no such opposite-sign pair, all required bit values are compatible and can be extended to a full assignment in both cubes. □

Thus pairwise disjointness is deterministically checkable in polynomial time from the explicit clauses.

---

# 4. Width-to-count theorem

Let

```text
C_1,...,C_k
```

be clauses whose falsifying cubes are pairwise disjoint and whose widths satisfy

```text
|C_i| <= w.
```

Every cube has size at least `2^(n-w)`. Since all cubes lie inside the `2^n` root assignments,

```text
k * 2^(n-w) <= 2^n.
```

Therefore

```text
k <= 2^w.
```

If

```text
w <= c*log_2 N
```

for a universal fixed `c`, then

```text
k <= N^c.
```

### C2G-T1 — disjoint cube charge bound

A pairwise-disjoint ledger of globally certified reasons of width at most `c log N` contains at most `N^c` entries.

This is an exact counting theorem; it does not require computing a union of overlapping cubes.

---

# 5. Branch-charge theorem

Consider a deterministic successor of Policy-0B.1.

Require every nonterminal branch event to emit a **new charge reason** `C_j` satisfying all of:

1. `C_j` has a standalone accepted proof from the immutable root CNF;
2. `|C_j| <= c log_2 N`;
3. `Q(C_j)` is disjoint from every previously charged cube;
4. the reason is added once to an immutable charge ledger;
5. no branch event occurs without a fresh charge.

Then the total number of branch events is at most

```text
N^c.
```

A binary branch tree with `B` internal branch nodes has at most `2B+1` total nodes. Hence total recursive state count is polynomial.

If per-state work and total active representation are also polynomial in original `N`, total runtime is polynomial.

### C2G-T2 — sufficient polynomial branch bound

The charge rule above is a sufficient global amortization theorem that defeats the Policy-0B.1 branch exponent.

It is **not** a claim that a deterministic algorithm can always discover such a reason.

---

# 6. Why this avoids the first coverage trap

Naively summing excluded volumes of arbitrary reasons is unsound because their falsifying cubes can overlap.

The charge ledger avoids exact union counting entirely:

```text
PAIRWISE_DISJOINTNESS -> SUM_OF_VOLUMES_IS_EXACT.
```

No maximum-union, inclusion-exclusion or #P-style coverage oracle is invoked.

---

# 7. Operational interface

A proposed discovery module may charge a branch only with

```text
CHARGE = (
  canonical_root_clause C,
  standalone_proof_certificate pi,
  width_receipt,
  pairwise_disjointness_receipt
)
```

Verification:

1. verify `pi` proves `F |= C`;
2. verify canonical non-tautological root clause;
3. verify `|C| <= floor(c log_2 N)` under frozen constants;
4. compare `C` against all prior charge clauses and require an opposite-sign shared variable for each pair.

All verification cost is polynomial in explicit ledger/certificate volume. The ledger-volume-in-`N` gate remains separately charged.

---

# 8. Immediate falsifiers / cautions

## Overlap falsifier

Clauses such as

```text
(x OR y)
(y OR z)
```

have overlapping falsifying cubes and cannot both be charged.

## Prefix-guard width trap

One can make branch-local reasons disjoint by appending decision-prefix literals, but every appended literal increases width. A depth-`d` guard can create width `Omega(d)`, destroying the required `O(log N)` width when branches become deep.

Therefore

```text
DISJOINT_BY_FULL_PATH_GUARDING
```

is not a free solution.

## Empty-clause case

If the empty clause itself has a verified proof, its falsifying cube is the entire assignment space and one charge suffices. This merely reflects that a complete UNSAT proof has already been found; it does not make discovery cheap.

---

# 9. Exact remaining killer gate

Prove or refute the existence of a deterministic discovery algorithm which, on **every branch event of every CNF**, returns a fresh charge reason meeting C2G-T2 in total polynomial work and polynomial proof/ledger volume.

This is substantially stronger than reason soundness and existing-cache lookup.

A negative result for this charge scheme would close only this C2 candidate, not P vs NP.

---

# 10. Status

```text
C2G_FALSIFYING_CUBE_SIZE                 = PROVED
C2G_PAIRWISE_DISJOINTNESS_CRITERION      = PROVED
C2G_WIDTH_TO_CHARGE_COUNT                = PROVED
C2G_BRANCH_COUNT_FROM_CHARGE_LEDGER      = PROVED_AS_SUFFICIENT_THEOREM
C2G_POLYTIME_UNIVERSAL_CHARGE_DISCOVERY  = OPEN / KILLER GATE
C2G_POLY_TOTAL_PROOF_LEDGER               = OPEN / COUPLED REPRESENTATION GATE
P_VS_NP                                  = OPEN
```

---

# 11. Claim firewall

```text
SUFFICIENT_PROGRESS_CERTIFICATE
!=
UNIVERSAL_EXISTENCE

UNIVERSAL_EXISTENCE
!=
POLYTIME_DISCOVERY

PAIRWISE_DISJOINT_CUBES
!=
ARBITRARY_REASON_UNION

SHORT_WIDTH_REASON
!=
CHEAP_REASON_SEARCH

C2G_T2
!=
P_EQUALS_NP

P_VS_NP = OPEN
```
