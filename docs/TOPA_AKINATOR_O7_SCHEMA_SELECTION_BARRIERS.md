# TOPA / JANUS — Akinator O7 Universal Schema-Selection Barriers

**Frozen:** 2026-08-25  
**Status:** `PROVED_IN_STATED_SCOPE__CI_PASS`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Context

The O7 graph-PHP positive control proves that a family-specific B2/Extended-Resolution extension schema can be generated in polynomial time and can remove a plain-Resolution bottleneck. The remaining closure burden is therefore not "do extensions ever help?" but:

```text
Given an arbitrary CNF and current proof state,
choose the right extension schema deterministically,
with polynomial total proposal/verification/proof cost,
and with a certified global progress bound.
```

This note kills two naïve routes to such a selector.

---

## 1. Barrier A — exact semantic candidate usefulness is coNP-complete

Let `H` be an arbitrary CNF over root variables `X`. Introduce fresh root variables `s,t` and define the selector-lift CNF

```text
F_H = { (s OR C) : C in H } union { (t) }.
```

Introduce one frozen-B2 candidate extension

```text
e <-> (s AND t).
```

### Theorem

```text
F_H union Def(e) entails e
iff
H is UNSAT.
```

### Proof

If `H` is UNSAT, then `F_H` entails `s`: setting `s=0` would require every clause `C in H` to hold, producing a satisfying assignment of `H`. Also `F_H` entails `t` by the root unit clause. Therefore `e=s AND t` is true in every model of `F_H union Def(e)`.

Conversely, if `H` is SAT, take a satisfying root assignment of `H`, set `s=0`, `t=1`, and hence `e=0`. Every lifted clause `(s OR C)` is satisfied by `C`, so this is a model of `F_H union Def(e)` with `e=0`. Thus `e` is not entailed.

The mapping `H -> (F_H,e)` is polynomial. Literal entailment from a CNF plus a fixed-size definitional gate is in coNP (a falsifying model is an NP witness), hence the decision problem is coNP-complete.

### Akinator interpretation

The equivalent exact branch question is:

```text
"Is the e=0 branch impossible?"
```

because `F_H union Def(e) entails e` iff the branch with `e=0` is UNSAT.

Therefore an O7 selector may not use exact global forcedness / exact branch death as a supposedly cheap semantic score unless it supplies a new polynomial algorithm for this coNP-complete task. Such an algorithm would itself have major P-vs-NP consequences.

This does **not** rule out syntactic/proof-carrying selectors that prove usefulness on a restricted subset of candidates and return UNKNOWN otherwise.

---

## 2. Barrier B — brute-force extension-sequence enumeration is exponential

Suppose a schema-search procedure explores every live extension choice at each stage. Let `M_i >= 1` be the number of live candidates at extension stage `i`, and let `K` be the number of stages.

The number of complete candidate sequences is exactly

```text
PRODUCT_{i=1..K} M_i.
```

If `M_i >= 2` for all `i`, then

```text
sequences >= 2^K.
```

Therefore if `K = Omega(N^alpha)` for any fixed `alpha>0`, exhaustive extension-sequence enumeration costs

```text
2^{Omega(N^alpha)},
```

before accounting for proof checking inside each branch.

Even with polynomially many candidates per stage, `M_i <= N^c`, the naïve bound

```text
(N^c)^K = N^{cK}
```

is not a fixed polynomial when `K` grows with the input.

Thus:

```text
POLY_CANDIDATES_PER_STAGE
!=
POLY_GLOBAL_SCHEMA_DISCOVERY.
```

This is a lower bound on the **explicit exhaustive-enumeration strategy**, not on all possible selectors.

---

## 3. Barrier C — proof verification remains cheap while selection may be hard

The B2/ER verifier can check a supplied extension definition and a supplied proof locally in time polynomial in serialized proof size. This does not imply a polynomial procedure for finding the extension sequence.

The graph-PHP positive control demonstrates the distinction sharply:

```text
known family-specific schema -> cheap deterministic generation
arbitrary CNF              -> selector still unknown
```

Hence:

```text
CHEAP_VERIFIER != CHEAP_SCHEMA_SELECTOR.
```

---

## 4. External conditional proof-search barrier

This project does not use cryptographic assumptions as theorems about P vs NP. However they are a useful external sanity barrier for the strength of the requested proof-search result.

Modern proof-complexity literature records that, under standard cryptographic security assumptions, Extended Frege is not weakly automatable by classical polynomial-time algorithms. A 2024/2025 account by Arteche, Carenini and Gray summarizes the earlier Krajicek-Pudlak and Bonet-Pitassi-Raz line: Extended Frege weak automatability would contradict standard RSA/Diffie-Hellman-style security assumptions.

Because our frozen B2 is p-equivalent to Extended Resolution and standard Extended Resolution/Extended Frege are polynomially related proof systems, this is a **conditional warning** that universal strong proof search is a genuinely major gate. We do not import the cryptographic assumption as fact and we do not infer `P != NP` from it.

Reference:
- Arteche, Carenini, Gray, *Quantum Automating TC^0-Frege Is LWE-Hard*, CCC 2024 / Computational Complexity 2025.

---

## 5. Surviving selector contract

A candidate universal O7 selector must therefore be proof-carrying rather than omniscient. Freeze the interface:

```text
SELECT_B2(state) ->
    EXTENSION(definition, progress_certificate)
  | TERMINAL(proof)
  | DECOMPOSE(certificate)
  | UNKNOWN
```

For a positive P=NP closure route, `UNKNOWN` cannot trigger exponential fallback on an infinite family. We need a theorem showing that for every CNF the selector plus its certified fallback makes global progress under one fixed polynomial total-cost bound.

Admissible progress certificates may use only explicitly verified syntactic/proof objects; exact semantic forcedness/model-count balance is not free.

---

## 6. Independent finite mechanics receipt

Dedicated GitHub Actions replay:

```text
workflow = Validate Akinator O7 Schema Selection
head     = d36087362c42b68fa369d4ed0e13bfc7d6eba59d
run      = 32785058422
job      = 97615160428
result   = SUCCESS

AKINATOR_O7_SELECTOR_LIFT_FORCEDNESS_EQ_UNSAT = PASS fixtures=5
AKINATOR_O7_E0_BRANCH_DEATH_EQ_UNSAT = PASS
AKINATOR_O7_BINARY_SCHEMA_SEQUENCE_COUNT = PASS
CO_NP_COMPLETENESS = ANALYTICAL_REDUCTION_NOT_CI
BRUTE_FORCE_SCHEMA_ENUMERATION_ONLY = BARRIER_SCOPE
UNIVERSAL_PROOF_CARRYING_B2_SELECTOR = OPEN
CLAIM_CEILING = FINITE_MECHANICS_ONLY
P_VS_NP = OPEN
```

CI validates the finite selector-lift identity and explicit sequence-count mechanics. The coNP-completeness statement follows from the analytical reduction above; the cryptographic proof-search discussion is conditional external literature, not CI evidence.

---

## 7. Next exact attack

The next question is no longer "which extension looks useful?" It is:

```text
Is there a polynomially enumerable structural vocabulary V(F)
of candidate macro families such that
for every CNF F,
at least one candidate has a polynomially checkable progress certificate,
and a deterministic rule can find such a certificate without enumerating exponentially many extension sequences?
```

A positive theorem would be a genuine move toward the #42 closure contract. A counterfamily closes the proposed vocabulary and is preserved in the JSON journal.

---

## 8. Claim ceiling

```text
EXACT_EXTENSION_FORCEDNESS = coNP_COMPLETE
BRUTE_FORCE_EXTENSION_SEQUENCE_ENUMERATION = EXPONENTIAL_WHEN_K_GROWS
POLY_CANDIDATES_PER_STAGE_IMPLIES_POLY_DISCOVERY = REFUTED
O7_SCHEMA_SELECTION_FINITE_MECHANICS = PROVIDER_CI_PASS
UNIVERSAL_PROOF_CARRYING_B2_SELECTOR = OPEN
UNIVERSAL_B2_SCHEMA_SELECTION = OPEN
P_VS_NP = OPEN
```
