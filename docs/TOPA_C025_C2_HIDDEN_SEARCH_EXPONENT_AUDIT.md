# TOPA C025-C2 — Hidden Search Exponent / Branch-Mass Audit

**Frozen:** 2026-08-24T23:17:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Parent machine:** `TOPA_POLICY0B1_TOTAL_MACHINE_FROZEN_CONTRACT`  
**Status:** `C2_OPEN__HIDDEN_EXPONENT_IS_GLOBAL_SEARCH_MASS`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why this audit exists

Policy-0B.1 is now a complete deterministic heuristic-free machine. Its preprocessing is polynomial per recursive state, but it can branch to an exponential number of states.

Therefore C2 must not be phrased merely as

```text
find one useful extension/reason in polynomial time.
```

The real obligation is global:

```text
bound the total discovery work + total number of expanded states by N^O(1).
```

---

# 2. Exact branch-mass identity

Suppose a state has `u` unassigned root variables and no inference has yet ruled out any of their completions.

Define the raw assignment mass

```text
A(u) := 2^u.
```

A branch on one root variable produces two children with `u-1` free variables each, hence

```text
A(child_0)+A(child_1)
= 2^(u-1)+2^(u-1)
= 2^u
= A(parent).
```

### C2-M1 — branch mass conservation

```text
PLAIN_BRANCHING DOES NOT REDUCE RAW ASSIGNMENT MASS.
```

It only partitions that mass into two subproblems.

This explains the exact hidden exponential in the frozen baseline:

```text
poly(N) work per state
x
up to 2^n states.
```

---

# 3. Naive polynomial potentials fail

## 3.1 Unassigned-variable count

Let

```text
mu_u(s) = number of unassigned root variables.
```

For a branch with `u>=3`,

```text
mu_u(child_0)+mu_u(child_1)
= 2(u-1)
> u
= mu_u(parent).
```

So this measure grows under frontier splitting.

## 3.2 Clause count

A branch can leave a large collection of clauses not mentioning the branch variable unchanged in **both** children. The common clause set is duplicated in the search frontier.

Thus no universal inequality of the form

```text
clauses(child_0)+clauses(child_1) < clauses(parent)
```

holds.

## 3.3 Literal volume

The same duplication defeats literal volume. If the branch variable occurs in only a small part of the formula, most literal occurrences appear in both residual children.

Hence

```text
L(child_0)+L(child_1)
```

can be close to `2L(parent)`.

## 3.4 Raw assignment mass

`2^u` has the correct additive behavior:

```text
A(child_0)+A(child_1)=A(parent),
```

but the initial value `2^n` is itself exponential.

Therefore it exposes the problem but does not solve it.

---

# 4. C2 global mass-collapse lemma — sufficient route to polynomial state count

Let a deterministic solver maintain a finite frontier of open states.

Suppose there exists a nonnegative integer potential `mu(s)` and universal fixed constants `C,c` such that:

```text
mu(root) <= C*N^c.
```

For every expansion of one nonterminal state `s` into open children

```text
t_1,...,t_k,
```

suppose

```text
sum_i mu(t_i) <= mu(s)-1.
```

Terminal states add no new frontier potential.

### Theorem C2-G1 — frontier telescoping

The number of expanded nonterminal states is at most `mu(root)`.

**Proof.** Let `Phi` be the sum of `mu` over the current open frontier. Initially `Phi<=C*N^c`. Every expansion reduces `Phi` by at least one. Since `Phi>=0`, at most `C*N^c` such expansions are possible. □

If additionally each state expansion and all maintained representation cost `N^O(1)`, total work is polynomial.

This is a **sufficient progress theorem**, not an assumption that such a `mu` exists.

---

# 5. What a useful C2 reason/discovery step must accomplish

A reason or extension is useful for the constructive P=NP route only if it participates in a theorem that beats branch-mass conservation.

It is not enough that:

- the reason is sound;
- verification is polynomial in certificate length;
- the extension circuit is short;
- one call to `DISCOVER` is polynomial;
- a benchmark explores fewer nodes.

C2 needs a global statement such as:

```text
certified inference decreases a polynomially bounded frontier potential,
```

or an equivalent amortized theorem bounding the total search tree/DAG.

---

# 6. Exact-search enumeration barriers

## 6.1 Exhaustive proof-string enumeration

Suppose a proposed C2 algorithm says:

```text
enumerate all candidate certificates/proofs of encoded length <= B(N)
and verify them.
```

There are up to

```text
2^B(N)
```

bit strings of length `B(N)`.

Even if verification of each candidate is polynomial, exhaustive enumeration is exponential in the proof-bit budget whenever `B(N)` grows polynomially and nonlogarithmically.

Thus:

```text
POLYNOMIAL_CERTIFICATE_BOUND
!=
POLYNOMIAL_EXHAUSTIVE_CERTIFICATE_SEARCH.
```

## 6.2 Lexicographic extension-program enumeration

Likewise, enumerating all short extension circuits in canonical order is not automatically efficient. A polynomial gate budget still admits exponentially many syntactically distinct gate sequences.

This refutes only the **naive exhaustive enumerator**. It is not an unconditional lower bound against every possible discovery algorithm.

---

# 7. Already known hidden-search traps that C2 may not reuse

From the preceding JANUS/TOPA line:

```text
FAST_REASON_INDEX_IN_M != M_IS_POLY_IN_N
EXACT_SEMANTIC_CLASSIFICATION = coNP-hard in general B2 circuits
GOOD_SOURCE_RESTRICTION_EXISTS != CHEAP_SELECTOR
SHORT_ER_PROOF_EXISTS != CHEAP_ER_PROOF_DISCOVERY
FINITE_BENCHMARK_NODE_REDUCTION != ASYMPTOTIC_PROGRESS_THEOREM
```

The conditional EF/ER non-automatability literature remains an external scale marker, not an unconditional impossibility theorem.

---

# 8. Frozen C2 discovery interface

Any future Policy-0B successor that adds automatic B2/reason discovery must expose a pure deterministic interface

```text
DISCOVER(state, immutable_root_receipt)
    -> CERTIFIED_OBJECT_BUNDLE | NONE
```

with all of:

1. canonical deterministic output;
2. standalone verification of every returned object;
3. full bit-cost for proposal/search/construction;
4. no uncharged exact semantic oracle;
5. total retained-representation bound in original `N`;
6. a global frontier/progress theorem such as C2-G1 or a proved equivalent.

Without item 6, C2 remains open even if items 1–5 pass.

---

# 9. Current exact frontier

```text
POLICY0B1 TOTAL MACHINE                      = FROZEN
POLICY0B1 CORRECTNESS                        = PROVED FROM TRANSITION SEMANTICS
POLICY0B1 PER-NODE WORK                      = POLYNOMIAL
POLICY0B1 TOTAL STATE COUNT                  = ONLY EXPONENTIAL UPPER BOUND

C2 BRANCH-MASS CONSERVATION                  = PROVED
C2 UNASSIGNED-COUNT FRONTIER POTENTIAL        = REFUTED
C2 CLAUSE/LITERAL-VOLUME FRONTIER POTENTIAL   = REFUTED AS UNIVERSAL NAIVE MEASURES
C2 ASSIGNMENT-MASS POTENTIAL                  = EXACT BUT EXPONENTIAL AT ROOT
C2 GLOBAL MASS-COLLAPSE LEMMA                 = PROVED AS SUFFICIENT CONDITION
C2 USEFUL POLY-BOUNDED mu                     = OPEN / KILLER GATE
C2 DETERMINISTIC DISCOVERY                    = OPEN
P_VS_NP                                       = OPEN
```

---

# 10. Next scientific attack

Search for a proof-carrying **frontier potential / disjoint progress certificate** that can be charged to accepted reasons/extensions without solving a hidden #P/coNP-hard subproblem.

Every candidate must first survive:

- branch duplication;
- overlapping reason coverage;
- extension reuse;
- proof rewriting;
- polynomial re-encoding;
- representation-byte accounting.

If a candidate cannot pass these falsifiers, preserve the failure and reject the measure.

---

# 11. Claim firewall

```text
POLY_PER_STATE != POLY_TOTAL_STATES
SHORT_PROOF != CHEAP_SEARCH
EXHAUSTIVE_SEARCH_OF_POLY_SIZE_OBJECTS != POLYTIME
PROGRESS_SCORE != PROVED_PROGRESS_POTENTIAL
C2_G1_SUFFICIENT_LEMMA != EXISTENCE_OF_REQUIRED_mu
POLICY0B1_FREEZE != P_EQUALS_NP
P_VS_NP = OPEN
```
