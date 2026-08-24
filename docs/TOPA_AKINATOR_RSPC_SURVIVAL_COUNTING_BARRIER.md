# TOPA / JANUS — RSPC Survival Counting and Certificate-Discovery Barrier

**Frozen:** 2026-08-25  
**Status:** `ANALYTICAL_BARRIER_FROZEN__FINITE_REPLAY_PENDING`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Why this is the next gate

The surviving Akinator route after the structural-selector barrier is a proof-carrying macro whose useful structure survives an exact restriction relation/distribution. A natural next primitive would be a survival functional such as

```text
SURV(e; D) = Pr_{rho ~ D}[ residual semantic macro e|rho is CROSSING ].
```

This note asks whether exact survival can be used as a cheap structural score, and whether a polynomially enumerable candidate language plus short survival witnesses automatically gives polynomial certificate discovery.

The answer is no in a very small abstract locality model. Exact survival already contains #SAT counting, and survival-witness discovery already contains SAT search even when the candidate language has size one.

This does **not** prove that the exact Sokolov self-reduction survival problem is #P-hard, and it does not prove any unconditional superpolynomial lower bound.

---

## 1. Frozen abstract locality model

Take root variables

```text
X = {x_1,...,x_n}
```

and two additional roots `p,q` with no permitted locality neighborhood containing both. Therefore a residual Boolean function depending essentially on both `p` and `q` is classified `CROSSING`.

A B2 macro DAG uses the already frozen rule

```text
e <-> (a AND b)
```

for signed root/earlier-extension literals with distinct underlying variable identifiers. Negation of a previously defined signal is represented by using its signed literal; OR is compiled by De Morgan with constant gate overhead.

Let `D_X` be the uniform distribution over all **full assignments to X only**, leaving `p,q` unassigned. Semantic residual classification evaluates the Boolean function induced by the B2 DAG after the chosen root restriction.

---

## 2. Polynomial B2 compilation of a CNF truth function

Given a CNF `H(X)`, preprocess in polynomial time to remove duplicate literals/clauses and tautological clauses; trivial constant cases may be handled directly. Compile every nontrivial clause by De Morgan:

```text
OR(a,b) = NOT( (NOT a) AND (NOT b) )
```

and combine clause outputs by B2 AND gates. Fresh extension outputs keep successive operands on distinct variable identifiers. Thus a signed B2 literal `h` computing exactly the Boolean function `H(X)` is obtained with polynomially many gates.

Now introduce

```text
g <-> (p AND q)
e <-> (h AND g).
```

`g` is crossing by construction.

---

## 3. Theorem R1 — exact crossing-survival numerator contains #SAT

For every full assignment `alpha` to `X`:

```text
H(alpha)=0  => h|alpha=0 => e|alpha=0        => CONSTANT
H(alpha)=1  => h|alpha=1 => e|alpha=p AND q  => CROSSING
```

Therefore

```text
# { alpha : e|alpha is CROSSING } = #SAT(H)
```

and under the uniform distribution `D_X`,

```text
SURV(e; D_X) = #SAT(H) / 2^n.
```

The construction `H -> (e,D_X)` has polynomial size.

### Consequence

The computational problem

```text
EXACT_CROSSING_SURVIVAL_NUMERATOR:
input  = B2 macro DAG + named uniform root-restriction distribution
output = exact number of restrictions leaving the target macro CROSSING
```

is #P-hard, because its value on this restricted image is exactly `#SAT(H)`.

Equivalently, exact rational survival probability is #P-hard to compute on this image: multiplying by the known denominator `2^n` recovers `#SAT(H)`.

This is a hardness reduction, not an unconditional time lower bound. We do not infer `P != NP` or `FP != #P` from it.

---

## 4. Corollary R1a — even zero/nonzero survival contains SAT/UNSAT

On the same construction,

```text
SURV(e;D_X) > 0  iff H is SAT,
SURV(e;D_X) = 0  iff H is UNSAT.
```

Thus a total deterministic polynomial algorithm deciding positive exact survival for all such instances would decide SAT in polynomial time. This is a conditional implication into the open P-vs-NP problem, not a separation theorem.

The route

```text
"score every macro by its exact survival probability and choose the best"
```

therefore may not treat that probability as a free primitive.

---

## 5. Theorem R2 — polynomial candidate count + cheap witness checking does not imply cheap discovery

The reduction is sharper than a candidate-enumeration barrier because the candidate vocabulary may contain **exactly one** macro `e`.

For a satisfiable `H`, a survival witness is simply an assignment `alpha` to `X` such that the residual `e|alpha` is crossing. Checking a supplied `alpha` is polynomial:

1. evaluate `H(alpha)` or the B2 DAG;
2. verify `e|alpha = p AND q`;
3. verify the fixed locality rule says `{p,q}` is crossing.

But by the identity above,

```text
alpha is a survival witness
iff
alpha satisfies H.
```

Therefore the search problem

```text
given an instance promised to have positive survival,
find one surviving restriction alpha
```

is at least as hard as SAT witness search under this polynomial reduction.

So even with

```text
|V(F)| = 1,
certificate size = O(n),
certificate verification = poly(N),
promised certificate existence,
```

polynomial deterministic certificate **discovery** does not follow from those facts alone.

Again, this is a search reduction. It does not prove that SAT witness search requires superpolynomial time unless one separately resolves P vs NP.

---

## 6. What this closes

The following RSPC shortcuts are now invalid as free primitives:

```text
EXACT_SURVIVAL_PROBABILITY_AS_CHEAP_SCORE
    -> #P-hard on a simple abstract locality image

EXACT_POSITIVE_SURVIVAL_DECISION_AS_CHEAP_SCORE
    -> would decide SAT on that image

POLY_ENUMERABLE_CANDIDATES + SHORT_CHECKABLE_SURVIVAL_WITNESS
    -> does NOT imply deterministic polynomial witness discovery

ONE_CANDIDATE
    -> does NOT remove certificate-discovery hardness
```

This moves the hidden cost beyond candidate enumeration: it can sit inside the discovery of a proof-carrying robustness certificate itself.

---

## 7. What remains open

A structural selector can still avoid exact counting by supplying an **incomplete but sound lower-bound certificate** for survival, for example a proof that a syntactically described set of restrictions of known measure preserves a crossing/inversion resource.

The next positive route must therefore look like

```text
CERTIFY_SURVIVAL_LOWER_BOUND(e, certificate) -> PASS/FAIL
```

where:

- verification is polynomial in original input length and certificate bytes;
- the certificate is deterministically discoverable in polynomial time;
- no exact survival count is required;
- for every nonterminal state at least one polynomially discoverable candidate/certificate pair exists;
- repeated certified moves imply one global polynomial potential bound.

The key unresolved question is whether such a sound, incomplete certificate system can be **complete enough for the Akinator closure contract** without becoming equivalent to solving the hard search problem it is meant to guide.

---

## 8. Source-matching firewall

The distribution `D_X` above is deliberately simple and constructed for the reduction. It is **not** claimed to be Sokolov's Algorithm 1/self-reduction distribution.

Therefore the theorem proved here is:

```text
EXACT_SURVIVAL_IS_NOT_A_FREE_UNIVERSAL_RSPC_PRIMITIVE
```

not:

```text
SOKOLOV_SOURCE_MATCHED_SURVIVAL_IS_PROVED_#P_HARD.
```

The source-matched restriction constructor, its nonunique choices, their bit complexity, and quantitative semantic survival remain separate open gates.

---

## 9. Next exact attack

Freeze the next gate as

```text
AKINATOR-RSPC-LB
= SOUND INCOMPLETE SURVIVAL LOWER-BOUND CERTIFICATE
```

Two-sided attack:

**Positive:** construct a polynomially checkable certificate that lower-bounds survival without exact counting and prove a deterministic polynomial constructor plus global potential decrease.

**Adversarial:** for each proposed cheap certificate vocabulary, build a macro family that passes the certificate locally but has low/zero true survival under the exact source-matched restriction relation.

This is the first remaining lane that does not immediately invoke exact semantic forcedness, exact counting, or exponential schema enumeration.

---

## 10. Claim ceiling

```text
EXACT_CROSSING_SURVIVAL_NUMERATOR
= #P_HARD_IN_STATED_ABSTRACT_LOCALITY_MODEL

POSITIVE_SURVIVAL_DECISION
= SAT_HARD_ON_STATED_REDUCTION_IMAGE

SURVIVAL_WITNESS_DISCOVERY
= SAT_SEARCH_HARD_ON_STATED_REDUCTION_IMAGE

POLY_CANDIDATE_COUNT_PLUS_POLY_WITNESS_CHECK
= INSUFFICIENT_FOR_POLY_DISCOVERY

SOKOLOV_SOURCE_MATCHED_SURVIVAL_COUNTING_HARDNESS
= NOT_PROVED

SOUND_INCOMPLETE_SURVIVAL_LOWER_BOUND_CERTIFICATE
= OPEN / NEXT

UNIVERSAL_PROOF_CARRYING_B2_SELECTOR
= OPEN

P_VS_NP
= OPEN
```
