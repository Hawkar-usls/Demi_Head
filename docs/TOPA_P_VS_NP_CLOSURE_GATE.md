# TOPA / JANUS — P vs NP Closure Gate

**Frozen:** 2026-08-24T23:20:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Target state:** `P_VS_NP = CLOSE` only after a checkable implication chain reaches `P=NP` or `P!=NP`.  
**Current state:** `P_VS_NP = OPEN`.

## 1. Why this gate is necessary

The current C025-E2R line studies proof size, extension count and proof-search resources in a particular strong proof language (B2 / Extended Resolution / ER3).

These are important gates for the constructive Policy-0B route, but not every possible outcome resolves P vs NP.

No intermediate proof-complexity milestone may be relabeled `P_VS_NP=CLOSE` unless its implication to one side of P vs NP is itself proved.

## 2. Constructive closure branch — route to P=NP

A valid `P=NP` closure through Policy-0B requires all of the following, for every CNF/SAT input of encoded bit length `N`.

### P-CLOSE-A — total frozen machine

One deterministic Policy-0B transition system is fully specified, including:

- preprocessing and canonicalization;
- unit propagation;
- local inference schedule;
- extension-definition proposal and selection;
- reason creation and verification;
- retention/deletion/subsumption;
- cache/index maintenance;
- branching variable and polarity;
- proof-DAG storage/materialization;
- SAT witness return;
- UNSAT certificate return;
- all tie-breaking.

### P-CLOSE-B — active representation bound

There exist universal fixed constants `C,c` such that at every point of every run:

```text
active encoded bytes <= C*N^c.
```

This includes clauses, extension definitions, proof nodes, reasons, caches, indexes and auxiliary state.

### P-CLOSE-C — bounded useful proof/certificate objects

Every UNSAT input admits the proof/certificate objects actually required by the frozen machine within the same universal polynomial resource model.

For the current B2 language this contains the E2/ER p-boundedness frontier.

### P-CLOSE-D — deterministic discovery/search bound

The frozen machine finds every required extension definition, reason, branch result and proof object in total deterministic work

```text
<= C'*N^d
```

for universal fixed constants `C',d`.

Existence of short proofs is insufficient.

### P-CLOSE-E — total run bound

The complete number of transitions and bit-operation cost of each transition combine to a universal deterministic polynomial bound in `N`.

### P-CLOSE-F — decision correctness

For every input the machine halts and returns exactly one of:

```text
SAT + checkable satisfying assignment
UNSAT + checkable sound certificate.
```

If A–F are proved, CNF-SAT is in deterministic polynomial time. Since CNF-SAT is NP-complete,

```text
P = NP.
```

At that point and only then the constructive branch may set:

```text
P_VS_NP = CLOSE__P_EQUALS_NP.
```

## 3. Negative E2/ER result does not close P vs NP

Suppose JANUS proves a superpolynomial lower bound on B2/ER/ER3 proofs, or equivalently refutes the universal polynomial extension-count property targeted by #217.

This establishes that the **current proof language / architecture cannot have universal polynomial proof objects of that form**.

It does not establish that no other deterministic polynomial SAT algorithm exists.

In particular:

```text
ER_NOT_P_BOUNDED
!=
P_NOT_EQUAL_NP.
```

Nor is it presently known in general that ER not p-bounded implies `NP!=coNP`.

Therefore a negative #217 result would close the current Policy-0B/B2 route, not P vs NP.

## 4. What a genuine negative closure branch needs

To set

```text
P_VS_NP = CLOSE__P_NOT_EQUAL_NP
```

JANUS needs a proved implication to the nonexistence of **every** deterministic polynomial-time SAT algorithm, not merely a lower bound for one fixed proof system.

Admissible forms include any theorem that is independently known/proved to imply `P!=NP`, for example a suitable unconditional lower bound for an NP-complete problem in the relevant general computation model.

The exact route must be written explicitly; no phrase such as “ER is very strong” or “close to Extended Frege” counts as an implication.

## 5. Status interpretation of current fronts

```text
C024 Policy-0A residual bridge          = constructive P=NP candidate route; premise refuted for Policy-0A
C025 Policy-0B                          = successor constructive route
C025-E2 / #217                          = necessary proof-object viability gate for current B2 route
C025-C2                                 = deterministic discovery gate
active representation                   = total resource gate
ER lower-bound breakthrough             = major proof-complexity result, not P!=NP by itself
P_VS_NP                                 = OPEN
```

## 6. Project discipline

The word `CLOSE` is reserved for an implication-complete terminal state.

Allowed intermediate statuses include:

```text
PROVED_IN_SCOPE
REFUTED_FOR_CURRENT_POLICY
ROUTE_CLOSED
MAJOR_EXTERNAL_FRONTIER
CONDITIONAL_BRIDGE_PROVED
PROVIDER_PASS
OPEN
```

Forbidden:

```text
P_VS_NP_CLOSE
```

unless the final implication to `P=NP` or `P!=NP` is itself part of the verified artifact.

## 7. Current exit map

### Constructive route

```text
E2 proof-object viability
 -> representation bound
 -> C2 deterministic discovery
 -> frozen total Policy-0B machine
 -> universal total poly(N) runtime
 -> P=NP
 -> CLOSE.
```

### Lower-bound route

```text
ER/B2 lower bound
 -> major result / current route obstruction
 -X-> P!=NP   (no established implication)
```

A separate theorem bridge is required before negative closure.

## 8. Global status

```text
P_VS_NP = OPEN
TARGET   = CLOSE_ONLY_BY_CHECKABLE_IMPLICATION
```
