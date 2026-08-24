# TOPA / JANUS — Akinator P=NP Closure Contract

**Frozen:** 2026-08-25  
**Status:** `ACTIVE_CLOSURE_PROGRAM`  
**Global ceiling:** `P_VS_NP = OPEN`

## Core correction

The Akinator does **not** need a constant number of questions.

For input encoding length `N`, a proof of `P = NP` may use

```text
Q(N) <= N^c
```

questions for any fixed universal constant `c`.

Examples such as `N`, `N^2`, or `N^100` are allowed.  A bound such as `2^N`, `N^{log N}`, or `N^{c(N)}` with unbounded `c(N)` is not a polynomial-time closure.

## Closure theorem target

Let `F` be any CNF of encoding length `N`.  A JANUS-Akinator machine may adaptively generate questions

```text
Q_1(F,state_0), Q_2(F,state_1), ..., Q_k(F,state_{k-1})
```

with exact answers and proof-carrying receipts.

If there exists a fixed constant `c` such that for **every** CNF `F`:

1. `k <= N^c`;
2. total question-generation time is `<= N^c`;
3. total exact-answer computation time is `<= N^c`;
4. total certificate-verification time is `<= N^c`;
5. total live representation / memory / serialized proof bytes are `<= N^c`;
6. every transition is deterministic and fully specified;
7. the machine halts with the correct `SAT` or `UNSAT` answer;
8. a `SAT` answer carries an independently verified assignment;
9. an `UNSAT` answer carries a sound proof object or a formally proved exhaustive decision argument;

then

```text
SAT in P
=> P = NP.
```

This is the exact positive closure condition.

## Total-cost law

Question count alone has no authority.

```text
TOTAL_COST
 = QUESTION_PROPOSAL
 + ANSWER_COMPUTATION
 + CERTIFICATE_PRODUCTION
 + CERTIFICATE_VERIFICATION
 + STATE_UPDATE
 + REPRESENTATION_MAINTENANCE
 + FINAL_DECISION.
```

All of this must be bounded by one fixed polynomial in the original input length `N`.

## Oracle firewall

A short yes/no question may hide an NP-hard, coNP-hard, or #P-hard computation.

Therefore:

```text
SHORT_QUESTION != CHEAP_ANSWER
BALANCED_SPLIT != CHEAP_SPLIT_DISCOVERY
SMALL_NUMBER_OF_QUESTIONS != POLYNOMIAL_TOTAL_RUNTIME
```

No external oracle is permitted unless its answers are themselves computed and certified within the same polynomial bound.

## Wave firewall

An exact global wave observable is admissible only if its computation cost is paid.

For a SAT indicator `f_F`, the zero Walsh coefficient equals `#SAT(F)`.  Therefore full exact Walsh-spectrum access cannot be treated as a free primitive.

The active search is for a restricted observable family `O` such that, for every CNF, JANUS can deterministically obtain enough exact proof-carrying information from `O` at polynomial total cost to force termination.

## Progress requirement

A question need not split the candidate space 50/50.

The required object is a certified global progress law.  A sufficient shape is a potential `mu` with

```text
mu(root) <= N^c
sum(mu(children)) <= mu(parent) - 1
```

for every expanded state, with all values / inequalities themselves cheaply certified.

Any equivalent polynomial telescoping invariant is admissible.

## Odonto mapping

```text
PULP      = immutable CNF
AKINATOR  = exact adaptive question generator
PROOF     = exact answer + certificate
DENTIN    = certified reduced state
TUBULES   = unresolved exact branches only
ENAMEL    = verified SAT assignment / UNSAT proof
```

Heuristic ordering may exist in an experimental lane, but it has zero authority in the closure proof.

## Exit states

```text
P_VS_NP = CLOSE__P_EQUALS_NP
```

is permitted **only** after every closure condition above has a formal proof and independent mechanical receipts where applicable.

Until then:

```text
P_VS_NP = OPEN
```
