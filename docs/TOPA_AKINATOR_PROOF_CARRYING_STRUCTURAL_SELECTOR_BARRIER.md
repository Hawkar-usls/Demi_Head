# TOPA / JANUS — Proof-Carrying Structural Selector Barrier

**Frozen:** 2026-08-25  
**Status:** `ANALYTICAL_BARRIER_FROZEN__FINITE_REPLAY_PENDING`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Question attacked

The surviving O7 route is no longer allowed to use exact semantic usefulness as a free score and cannot brute-force extension sequences. The next proposal is therefore:

```text
PROOF-CARRYING STRUCTURAL SELECTOR
```

A selector receives a CNF/proof state and emits a B2 extension macro together with a polynomially checkable structural progress certificate, or a terminal proof/decomposition certificate.

The key question is whether a polynomially enumerable structural vocabulary can be universal.

This note imports the already proved TOPA NW-local and inversion-structure barriers into the Akinator closure contract.

---

## 1. Frozen selector interface

A structural selector has interface

```text
SELECT_STRUCT(state) ->
    EXTENSION(definition, structural_certificate)
  | TERMINAL(proof)
  | DECOMPOSE(certificate)
  | UNKNOWN
```

For a positive polynomial closure route we require one fixed constant `c` such that on every input of encoded length `N`:

```text
candidate generation cost <= N^c,
certificate verification cost <= N^c,
total emitted extension/proof bytes <= N^c,
total number of selector steps <= N^c,
```

and `UNKNOWN` may not trigger a superpolynomial fallback on an infinite family.

No heuristic ranking, semantic forcedness oracle, model count, or uncharged backtracking has proof authority.

---

## 2. Barrier S1 — NW-neighborhood-local selector vocabulary is not universal

Use the already frozen TOPA family `DIRPARITY(G,b)` from C025-E2R-L1E. For the existential hard NW graph family supplied by Sokolov's heavy-width theorem plus the TOPA transfer, every B2/ER3 refutation in which each extension's transitive root support is contained in one fixed NW neighborhood has superpolynomial size and, in the ER3 regime, superpolynomial extension count in the actual encoded input length.

Define a selector to be **NW-local-only** when every emitted B2 extension satisfies

```text
support(e) subseteq Vars_i
```

for some single NW neighborhood `Vars_i`.

### Theorem S1

No NW-local-only proof-carrying structural selector can simultaneously satisfy all of the following on the frozen hard family:

```text
1. terminate with an ER3 refutation on every UNSAT family member;
2. emit only NW-local B2 extensions;
3. use at most N^c extension variables for one fixed c;
4. use at most N^c total serialized proof/selector work for one fixed c.
```

### Proof

If such a selector existed, concatenate the emitted extension definitions and proof-carrying ER3 transcript. This would be an NW-neighborhood-local ER3 refutation with polynomial extension count and polynomial total size. C025-E2R-L1E proves that every such refutation on sufficiently large members of the stated hard family requires superpolynomial extension count/size. Contradiction.

Therefore on that family every NW-local-only selector must eventually do at least one of:

```text
RETURN_UNKNOWN,
EXCEED_POLY_TOTAL_WORK,
EXCEED_POLY_EXTENSION_COUNT,
LEAVE_NW_LOCAL_VOCABULARY.
```

This conclusion is independent of candidate ranking or enumeration order.

### Claim firewall

The hard graph family here is existential/high-probability from the imported source theorem; deterministic explicit graph selection remains open. This is not a lower bound for unrestricted ER3/ER/EF.

---

## 3. Barrier S2 — a surviving vocabulary must cross neighborhoods with enough inversion complexity

NW locality is therefore too weak. Allow crossing macros and use the already frozen F3 metrics:

```text
b = negative-frontier width,
d = inversion depth.
```

TOPA F3 proved the proof-level simulation bound

```text
S_local <= S^(7 * (b+2)^(d+1))
```

and, on the same NW hard-family transfer, the necessary tradeoff for any polynomial-size B2/ER3 escape

```text
(d+1) * log(b+2) = Omega(log N).
```

### Theorem S2

Fix functions `B(N), D(N)`. Consider any structural selector whose successful polynomial-size ER3 runs always satisfy

```text
b <= B(N),
d <= D(N)
```

throughout the generated B2 macro DAG. If

```text
(D(N)+1) * log(B(N)+2) = o(log N),
```

then this selector class cannot give a polynomial refutation route for all sufficiently large members of the stated NW hard family.

### Immediate corollaries

```text
B=O(1)       => D=Omega(log N) is necessary;
D=O(1)       => B=N^Omega(1) is necessary;
B=polylog N  => D=Omega(log N / log log N) is necessary.
```

Thus a universal structural vocabulary cannot remain simultaneously narrow and shallow.

This is a necessary structural-richness condition, not a lower bound on the time required to discover such a macro.

---

## 4. Barrier S3 — structural richness is not yet a progress certificate

A tempting selector rule is now:

```text
"choose any macro whose (b,d) crosses the S2 threshold"
```

This is insufficient.

C025-E2R-F3D gives an explicit abstract counterfamily: for arbitrary target width `B` and depth `D`, an `O(BD)` B2 DAG can have pre-restriction

```text
b >= B,
d >= D,
```

while one root restriction `rho(z)=0` makes every crossing macro constant, so the surviving semantic skeleton has

```text
b_rho = d_rho = 0.
```

Therefore

```text
LARGE_PRE_RESTRICTION_BD
!=
RESTRICTION_ROBUST_PROGRESS.
```

A cheap certificate that only proves large original `(b,d)` proves structural richness, but not that the macro contributes durable proof progress under the restrictions used by the NW lower-bound/self-reduction machinery.

---

## 5. The selector target has now sharpened

The first genuinely surviving certificate type must combine:

```text
CROSS_NEIGHBORHOOD_MIXING
+
SUFFICIENT_INVERSION_WIDTH_DEPTH
+
RESTRICTION-ROBUST SEMANTIC SURVIVAL
+
POLYNOMIAL CHECKABILITY
```

Call such an object a

```text
ROBUST_STRUCTURAL_PROGRESS_CERTIFICATE.
```

A positive closure route needs a deterministic polynomial-time rule that, for every nonterminal state, finds either such a certificate or a terminal/decomposition proof and proves a polynomial global progress bound.

The certificate cannot simply ask for exact semantic usefulness: the previous selector-lift reduction shows that exact forcedness/branch death is coNP-complete in general.

---

## 6. Exact place where the hidden exponent can still live

The current map is:

```text
NW-local vocabulary
    -> superpoly extension count on the stated hard family

crossing but low (b,d)
    -> cannot be a polynomial escape on the stated hard family

large pre-restriction (b,d) only
    -> can collapse under one root restriction

therefore surviving route
    -> restriction-robust crossing/inversion structure
```

We have **not** proved that discovering restriction-robust structure requires exponential time. The new exact question is whether robustness can be certified and found in polynomial time without evaluating a coNP-hard semantic predicate or enumerating exponentially many schemas.

---

## 7. Next attack

Freeze the next gate as

```text
AKINATOR-RSPC
= ROBUST STRUCTURAL PROGRESS CERTIFICATE
```

Required components:

1. exact residual semantic classifier for finite B2 fixtures (`CONSTANT / LOCAL / CROSSING`);
2. exact source-matched restriction relation/distribution, not an invented random restriction;
3. polynomial-size certificate that a candidate macro retains a quantified crossing/inversion resource under that relation;
4. deterministic polynomial-time certificate discovery;
5. a potential theorem converting repeated certified survival into polynomial total progress.

The adversarial branch is equally important: construct a polynomial-size family of crossing B2 macros that passes every proposed cheap structural certificate but systematically collapses under the source-matched restrictions.

---

## 8. Claim ceiling

```text
NW_LOCAL_ONLY_STRUCTURAL_SELECTOR_UNIVERSAL_POLY_ROUTE
= REFUTED_ON_STATED_EXISTENTIAL_NW_HARD_FAMILY

LOW_BD_STRUCTURAL_SELECTOR_POLY_ROUTE
= REFUTED_WHEN (D+1)log(B+2)=o(log N) ON STATED HARD FAMILY

LARGE_ORIGINAL_BD_AS_PROGRESS_CERTIFICATE
= REFUTED_BY_F3D_D0 ABSTRACT COUNTERFAMILY

ROBUST_STRUCTURAL_PROGRESS_CERTIFICATE
= OPEN / NEXT

UNRESTRICTED_ER3_ER_EF_LOWER_BOUND
= NOT_PROVED

UNIVERSAL_B2_SCHEMA_SELECTOR
= OPEN

P_VS_NP
= OPEN
```

## 9. Provenance

Internal TOPA dependencies:
- `C025_E2R_L1E_NW_LOCAL_ER3_LOWER_BOUND.md`
- `C025_E2R_L1G_F3_FRONTIER_WIDTH_DEPTH.md`
- `C025_E2R_L1G_F3D_SEMANTIC_SURVIVAL_BARRIER.md`

External theorem boundary:
- Dmitry Sokolov, *Pseudorandom Generators, Resolution and Heavy Width*, CCC 2022.

The source theorem supplies the heavy-width/NW functional-encoding lower-bound regime. The Akinator selector theorems above are our deductions from that source plus the already frozen TOPA transfer/simulation lemmas; they are not claims made by Sokolov.