# TOPA / JANUS — Policy-0B.1 Total Machine Freeze

**Frozen:** 2026-08-24T23:17:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Status:** `FROZEN_BASELINE__TOTAL_CORRECT__EXPONENTIAL_BRANCH_BOUND_EXPLICIT`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Purpose

C025 had proved several sound components but did not yet define one complete deterministic machine. This document freezes **Policy-0B.1** as a scientific control solver.

The goal is not to pretend that C2 proof discovery has been solved. The goal is the opposite: remove every heuristic/underspecified transition so that the remaining exponential resource is visible and can be attacked directly.

Policy-0B.1 therefore contains no hidden phrases such as:

```text
pick a useful extension
choose a promising branch
retain an important reason
prefer a high-confidence candidate
```

Every transition is exact and deterministic.

---

# 2. Input and canonical order

Input is a finite CNF `F` over root variables encoded by positive integer ids.

A literal is an integer `l != 0`; variable id is `abs(l)`.

Canonical literal order is

```text
(abs(l), l < 0)
```

so positive and negative forms of one variable have a fixed order.

A clause is canonicalized by:

1. deleting duplicate literals;
2. rejecting the clause as a tautology if it contains both `l` and `-l`;
3. sorting remaining literals canonically.

The CNF is canonicalized by deduplicating and sorting clauses by

```text
(length, literal_tuple).
```

Any clause strictly subsumed by another active clause is deleted. This is exact redundancy elimination, not a score or heuristic.

---

# 3. Frozen machine state

A recursive state is

```text
S = (K, rho)
```

where:

- `K` is the current canonical residual CNF valid under the current ancestor context;
- `rho` is the current partial assignment of root variables.

Policy-0B.1 has **no** automatically generated extension variables.

Freeze:

```text
AUTOMATIC_EXTENSION_PROPOSAL = NONE
GLOBAL_REASON_CACHE          = NONE
EXACT_RESIDUAL_MEMOIZATION   = NONE
MODEL_SCORE_OR_CONFIDENCE    = FORBIDDEN
```

The existing B2 reason language/verifier remains a separately proved library component, but is not silently invoked by this baseline machine.

This separation is deliberate: C2 must later supply a deterministic discovery rule before extensions/reasons are inserted into the total machine.

---

# 4. Deterministic preprocessing loop

For one state `(K,rho)`, repeat the following until conflict or fixpoint.

## 4.1 Restriction

Apply `rho` exactly:

- remove every satisfied clause;
- remove every assigned-false literal from remaining clauses;
- if an empty clause appears, return `UNSAT_LEAF`.

Then canonicalize and subsumption-reduce.

## 4.2 Unit propagation

If unit clauses exist, choose the smallest unit literal in canonical literal order.

Assign it, restrict again, and repeat.

No activity score, frequency score, phase saving or random tie-break is permitted.

## 4.3 Complete fair frozen Resolution layer

If there is no unit clause, freeze the current clause set `K`.

For every pivot with both polarities, in increasing variable-id order, visit **every** complementary parent pair from the frozen set exactly once.

For frozen literal occurrence count `L`, the already-proved C025-A bound is

```text
attempts = sum_x p_x q_x <= L^2/4.
```

New resolvents are not parents in the same layer.

## 4.4 Retention rule — no heuristic clause database

A non-tautological candidate resolvent is treated as follows.

### Empty resolvent

Immediate conflict.

### Unit resolvent

Place the literal into the deterministic forced-unit queue. It is assigned on the next preprocessing iteration and is not retained as a permanent additional clause.

### Non-unit resolvent

It is eligible only if it is a **strict subset** of at least one frozen active clause.

For each frozen clause `D`, among all candidates `C` with

```text
C proper_subset D
```

retain exactly one canonical strengthening:

```text
best(D) = minimum by (|C|, C).
```

Replace `D` by `best(D)`. All other candidates are discarded.

Then canonicalize and subsumption-reduce.

### Potential theorem

The clause count does not increase.

If at least one non-unit replacement occurs, total active literal volume decreases strictly:

```text
L_new < L_old.
```

Thus repeated fair-strengthening cannot create an unbounded clause database.

This rule is intentionally conservative. Completeness is supplied by branching, not by an unproved belief that the retained resolvents are the “best” proof clauses.

---

# 5. Branch rule

After preprocessing reaches a non-conflicting fixpoint:

- if no clauses remain, return `SAT`;
- otherwise choose the **smallest-id unassigned root variable appearing in the residual CNF**;
- recurse on value `0` first;
- if that child is SAT, return its witness;
- otherwise recurse on value `1`;
- if both children are UNSAT, return a branch certificate.

Freeze:

```text
BRANCH_VARIABLE = MIN_UNASSIGNED_ROOT_ID
BRANCH_ORDER    = FALSE_THEN_TRUE
```

There is no frequency/activity heuristic.

Any root variable absent from the final residual formula is filled with `0` in the canonical SAT witness.

---

# 6. Termination and correctness

## Theorem P0B1-T1 — preprocessing terminates

Along one recursive node define

```text
Phi = active_literal_volume + unassigned_root_count.
```

- every retained non-unit strengthening strictly decreases active literal volume;
- every unit assignment decreases the unassigned-root count;
- restriction/subsumption never increases either quantity.

Therefore preprocessing reaches conflict or fixpoint after at most `L_0 + n` progress iterations.

## Theorem P0B1-T2 — each preprocessing transformation is satisfiability preserving under the node context

- tautology and duplicate deletion are exact;
- subsumed-clause deletion is exact;
- restriction is exact under `rho`;
- unit propagation follows a clause forced under the context;
- every retained strengthening is a Resolution consequence of the frozen node formula;
- because the strengthening `C` strictly subsumes the replaced clause `D`, `C => D`.

Hence simultaneous one-for-one replacements preserve the model set of the node formula under its context.

## Theorem P0B1-T3 — recursive completeness

At a nonterminal fixpoint, splitting on one unassigned root variable partitions the remaining assignments into the two exhaustive cases `x=0` and `x=1`.

No extension variable is branched on.

Branch depth is at most the number `n` of root variables.

Therefore Policy-0B.1 always terminates and decides every finite CNF correctly.

---

# 7. Checkable result objects

## SAT

Return the complete root assignment. Verification is direct evaluation of the original CNF.

## UNSAT

Return a deterministic binary branch tree:

```text
CONFLICT_LEAF
or
BRANCH(var, false_child, true_child).
```

A verifier replays the exact frozen preprocessing at each certificate node, checks that the branch variable is the canonical machine choice, and recursively verifies both children.

Verification work is polynomial per certificate node and polynomial in explicit certificate size. No claim that certificate size is polynomial in original `N` is made.

---

# 8. Resource accounting

Let `N` be original encoded input length.

At every recursive node:

- active clause count never exceeds the input clause count after canonicalization;
- active literal volume never exceeds the root literal volume;
- no global cache, extension database or learned-clause database grows across nodes;
- fair-layer attempts are at most `L^2/4`;
- candidate selection can be streamed while keeping only one `best(D)` per active clause.

A deliberately coarse bit-cost bound for preprocessing one node is

```text
N^O(1)
```

(e.g. `O(N^5 log N)` under straightforward sorted-set/subsumption implementations).

But the branch tree satisfies only

```text
depth <= n <= N,
number_of_recursive_nodes <= 2^(n+1)-1 <= 2^(N+1)-1.
```

Therefore the honest current total bound is

```text
TOTAL_WORK <= 2^N * N^O(1).
```

This is an upper bound, not a lower bound. Policy-0B.1 is **not** proved polynomial-time.

---

# 9. Why freeze an exponential baseline?

Because it removes every other hiding place.

Before this freeze, an exponential cost could be hidden in:

- branch choice;
- clause retention;
- extension proposal;
- reason ranking;
- cache policy;
- proof search;
- tie-breaking.

Policy-0B.1 removes those ambiguities.

The surviving uncontrolled resource is now explicit:

```text
BRANCH FRONTIER / SEARCH MASS.
```

A future Policy-0B.2 may add B2 extensions or proof-carrying reasons only through a separately frozen C2 discovery contract with a proved global resource theorem.

---

# 10. C2 handoff

A C2 replacement is not accepted merely because each invocation runs in polynomial time.

It must establish a **global** theorem that prevents exponentially many states.

At minimum it must specify:

```text
DISCOVER(state) -> certified object(s) or NONE
```

with:

1. deterministic canonical output;
2. independently checkable soundness;
3. explicit bit-cost in original `N`;
4. polynomial bound on total retained representation;
5. a global progress/amortization theorem bounding the total number of expanded states.

`POLY_WORK_PER_STATE != POLY_NUMBER_OF_STATES`.

---

# 11. Claim firewall

```text
TOTAL_DETERMINISTIC_MACHINE
!=
POLYNOMIAL_TIME_MACHINE

NO_HEURISTICS
!=
P_EQUALS_NP

POLYNOMIAL_PREPROCESSING_PER_NODE
!=
POLYNOMIAL_TOTAL_RUNTIME

CHECKABLE_EXPONENTIAL_CERTIFICATE
!=
POLYNOMIAL_CERTIFICATE

POLICY0B1_FROZEN
!=
C2_SOLVED

P_VS_NP = OPEN
```
