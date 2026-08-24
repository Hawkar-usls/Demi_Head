# TOPA / JANUS — Policy-0B.1 Resolution Lower-Bound Route Closure

**Frozen:** 2026-08-24  
**Parent:** `TOPA_POLICY0B1_TOTAL_MACHINE_FREEZE.md`  
**Status:** `POLICY0B1_POLYTIME_ROUTE_REFUTED_BY_RESOLUTION_LOWER_BOUND`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Purpose

Policy-0B.1 was frozen as a complete deterministic heuristic-free SAT solver with polynomial preprocessing per recursive state and only the trivial exponential branch-tree upper bound.

This note strengthens that status: the baseline is not merely *unproved* polynomial. Its UNSAT computations remain inside ordinary Resolution, so classical Resolution lower bounds imply an unconditional superpolynomial runtime/state lower bound on explicit formula families.

The result closes **Policy-0B.1 as a polynomial-time candidate**. It does not close P vs NP and does not apply automatically to a future Policy-0B.2 that adds genuinely stronger B2/ER proof-producing operations.

---

# 2. Execution-to-Resolution compilation

Consider one complete UNSAT execution of the frozen Policy-0B.1 machine on root CNF `F`.

## 2.1 Local strengthening

Every retained non-unit strengthening is, by machine definition, a non-tautological Resolution resolvent of two frozen active clauses.

Thus every retained local strengthening already has a one-step Resolution justification relative to the current residual formula.

## 2.2 Unit propagation / local conflict

Unit propagation and conflicts are performed under a root decision context `rho`.

The existing C025-B/F2 restriction-lift machinery gives the standard fact:

```text
if F|rho has a Resolution derivation of contradiction,
then F has a Resolution derivation of a clause falsified by rho,
```

with polynomial/linear overhead in the local derivation and number of propagated/decision literals.

No weakening rule is required in the final calculus; restriction-lift yields an ordinary Resolution derivation of a blocking subclause.

## 2.3 Branch composition

At a branch on root variable `x`, let the false and true children return root-derived blocking clauses `C_0,C_1` falsified by their child contexts.

If the parent already falsifies one child clause, propagate that stronger reason upward. Otherwise the false-child clause contains `x`, the true-child clause contains `~x`, and one Resolution inference on `x` yields a parent blocking clause.

This is exactly the already-proved C025-B branch-composition mechanism.

## 2.4 Root

At the empty root context, a non-tautological clause falsified by the context must be the empty clause.

Therefore recursively compiling the complete UNSAT execution yields an ordinary Resolution refutation of `F`.

### Theorem P0B1-R1 — execution compilation

Every complete UNSAT execution of Policy-0B.1 can be transformed into a Resolution refutation of the root CNF.

If the execution explores `T` recursive states and performs at most `P(N)` explicit local inference/propagation work per state for some fixed polynomial `P`, the compiled Resolution proof has size

```text
<= T * N^O(1).
```

The exact exponent depends on the chosen explicit representation/compiler; fixed polynomial overhead is sufficient for the lower-bound transfer.

---

# 3. Classical hard family

Let `PHP_{n+1}^n` be the standard pigeonhole-principle CNF asserting that `n+1` pigeons inject into `n` holes.

A. Haken, *The intractability of resolution*, Theoretical Computer Science 39 (1985), proved an exponential lower bound for Resolution proofs of the pigeonhole principle. Standard modern presentations state a bound of the form

```text
RES_SIZE(PHP_{n+1}^n) >= 2^(Omega(n))
```

(and one common explicit presentation gives `>=2^(n/20)`).

The PHP CNF has polynomial encoded size in `n` (ordinary clause count `Theta(n^3)` up to encoding conventions and identifier-bit factors).

---

# 4. Runtime/state lower bound for Policy-0B.1

Let `T_n` be the number of recursive states explored by Policy-0B.1 on `PHP_{n+1}^n`.

By P0B1-R1, the run compiles to a Resolution refutation of size

```text
<= T_n * n^O(1).
```

Haken's lower bound forces

```text
T_n * n^O(1) >= 2^(Omega(n)).
```

Hence

```text
T_n >= 2^(Omega(n)) / n^O(1)
     = 2^(Omega(n)).
```

In actual encoded input bit length `N=poly(n)` this is superpolynomial in `N` (for the standard encoding, roughly `exp(Omega((N/log N)^(1/3)))` up to encoding factors).

### Theorem P0B1-R2 — baseline route closure

```text
POLICY0B1_UNIVERSAL_POLYNOMIAL_TOTAL_RUNTIME = REFUTED.
```

The frozen baseline has an explicit infinite family on which its total execution work/state count is superpolynomial.

This is an unconditional theorem transfer from Resolution proof complexity, assuming only the execution-to-Resolution compilation proved above.

---

# 5. Why this result is useful

The baseline freeze removed heuristic ambiguity. The new theorem now removes a second ambiguity:

```text
THE EXPONENTIAL BRANCH FRONTIER IS NOT JUST A LOOSE ANALYSIS ARTIFACT.
```

Some inputs force the Resolution-contained baseline to spend superpolynomial total work.

Therefore a successful Policy-0B successor cannot be obtained solely by polishing:

- deterministic branch order;
- fair Resolution scheduling;
- subsumption retention;
- plain Resolution conflict reasons;
- polynomial-per-state indexing.

It needs a mechanism whose globally compiled proof/decision power escapes the Resolution lower bound — for example a genuinely stronger extension/reason calculus **plus** a deterministic discovery/progress theorem.

---

# 6. Relation to B2 / ER

Haken's own abstract notes that Extended Resolution can have polynomial-length proofs of the pigeonhole formulas even though Resolution is exponentially hard.

Thus PHP is a useful separator here:

```text
POLICY0B1 / PLAIN RESOLUTION      -> exponential on PHP
B2 / EXTENDED RESOLUTION LANGUAGE -> proof-size escape exists on PHP
```

But:

```text
SHORT ER PROOF EXISTS
!=
POLICY FINDS IT IN POLYTIME.
```

So the lower bound moves the active project frontier directly to C2 discovery/representation rather than solving it.

---

# 7. Status movement

```text
POLICY0B1_TOTAL_CORRECTNESS                  = PROVED
POLICY0B1_PER_STATE_WORK                     = POLYNOMIAL
POLICY0B1_EXECUTION_TO_RESOLUTION             = PROVED
POLICY0B1_POLYNOMIAL_TOTAL_RUNTIME            = REFUTED
POLICY0B1_PHP_STATE_WORK_LOWER_BOUND          = SUPERPOLYNOMIAL / EXPONENTIAL-IN-n
POLICY0B2_STRONGER_DISCOVERY                  = REQUIRED
C2_DETERMINISTIC_DISCOVERY                    = OPEN
P_VS_NP                                       = OPEN
```

---

# 8. Claim firewall

```text
POLICY0B1_EXPONENTIAL_LOWER_BOUND
!=
P_NOT_EQUAL_NP

RESOLUTION_LOWER_BOUND
!=
ER_LOWER_BOUND

PHP_EASY_FOR_ER
!=
ER_AUTOMATABLE

BASELINE_ROUTE_CLOSED
!=
PROJECT_CLOSED

P_VS_NP = OPEN
```

## Literature anchors

- A. Haken, *The intractability of resolution*, Theoretical Computer Science 39 (1985), 297–308.
- Standard proof-complexity lecture notes: PHP requires exponential unrestricted Resolution size; Extended Resolution / stronger Frege-style systems admit polynomial proofs.
