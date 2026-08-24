# TOPA F3D-D2 — Exact Source Self-Reduction Proof Program

**Frozen:** 2026-08-24T22:15:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA F3D-D1 Semantic Residual Classifier Proof Program`  
**Primary source:** Dmitry Sokolov, *Pseudorandom Generators, Resolution and Heavy Width*, CCC 2022, DOI `10.4230/LIPIcs.CCC.2022.15`.  
**Status:** `D2_SOURCE_MODEL_FROZEN__STOCHASTIC_COMPLETION_NOT_YET_UNIQUE`  
**Global ceiling:** `P_VS_NP = OPEN`.

---

# 1. Why D2 exists

D1 established a strict split:

```text
REFERENCE SEMANTICS = exact but potentially exponential
OPERATIONAL SEMANTICS = proof-carrying partial, UNKNOWN allowed
```

D2 must now freeze the exact restriction process used by the heavy-width source before any quantity such as

```text
SURV_P(B0,D0; D)
```

is called a probability.

The source gives a mathematically valid self-reduction construction, but its Algorithm 1 contains nonunique choices. Therefore the phrase "the source distribution" is not yet a single stochastic kernel until those choices are completed explicitly.

---

# 2. Source facts frozen from Sokolov

## D2-S1 — self-reduction object

Definition 20 states that an x-assignment `rho` is a self-reduction when there is a left-vertex set `L_rho` satisfying the source size bound, `rho` assigns exactly the root variables in `N(L_rho)` while satisfying those output constraints, and the residual dependency graph remains an expander with the weakened expansion parameter.

Remark 21 identifies the restricted functional encoding with the residual PRG instance under normal assignments, with base functions replaced by residual functions `f_i|rho`.

## D2-S2 — functional forms survive partial x-assignments

Lemma 12 states that if `F` is a functional form of a clause `D` and `rho` is a partial x-assignment, then `F|rho` is a functional form of `D|rho^y`.

This is the source-backed reason the post-restriction semantic object is a residual Boolean function rather than original syntactic support.

## D2-S3 — Algorithm 1 random choices

Algorithm 1 includes at least these explicitly random steps:

```text
pick active output vertex v_i uniformly at random;
pick sigma_i uniformly at random from a stated preimage set.
```

It then removes the chosen neighborhood, computes a closure-like bad set `B_i`, assigns variables satisfying the constraints in `B_i`, updates the residual graph/functions, and iterates.

## D2-S4 — source theorem use

Lemma 22 proves Algorithm 1 generates a self-reduction under the stated expander/balancedness hypotheses.

Theorem 23 uses the construction to show that a sufficiently short Resolution proof admits, with high probability, a self-reduction yielding small heavy width.

These facts concern the source functional encoding and Resolution proof. They do not directly quantify semantic survival of arbitrary unrestricted B2 crossing macros introduced by JANUS.

---

# 3. D2-A barrier — Algorithm 1 does not define one unique probability distribution

Two steps are nonunique in the published pseudocode:

```text
B_i := argmax { |B| : B satisfies the stated constraints }
```

and

```text
pick an x-assignment nu_i on N(B_i) satisfying all constraints from B_i.
```

No tie-breaking rule is specified when several maximizing `B_i` exist, and no probability law is specified over multiple valid `nu_i` assignments.

Therefore the expression

```text
rho ~ D_source
```

is under-specified if it is intended to denote one unique distribution over complete restrictions.

This does not invalidate Sokolov's theorem. It only blocks JANUS from importing an unstated probability law into a new semantic-survival theorem.

---

# 4. Admissible stochastic completions

Before defining survival probability, JANUS must choose one of the following explicitly.

## D2-C1 — universal/adversarial completion

Quantify over all source-valid completions of nonunique choices:

```text
SURV_min := inf over valid completions C of Pr_{rho~D_C}[survival].
```

A lower bound on `SURV_min` is strongest for theorem transfer because it cannot depend on favorable hidden tie-breaking.

## D2-C2 — existential completion

Prove there exists a valid completion `C` with a desired survival property.

This is mathematically meaningful but weaker and cannot be turned into an algorithmic selector without separately constructing `C` and charging its cost.

## D2-C3 — canonical deterministic completion

Freeze a total ordering of vertices/sets/assignments and choose the lexicographically first valid maximizer/assignment.

This produces a deterministic completion, but JANUS must prove:

1. it preserves every source invariant needed by Lemma 22/Theorem 23;
2. the selected maximizer/assignment can actually be computed within the claimed resource bound.

The second item is not free: computing an argmax over subsets or finding a satisfying assignment may itself hide combinatorial search.

## D2-C4 — explicit randomized completion

For example, uniform choice among all maximizing `B_i` and all satisfying `nu_i` assignments.

This defines a probability measure but introduces two new algorithmic/counting tasks. No efficiency is inherited from the source theorem merely by writing "uniform".

---

# 5. D2-B hidden-cost firewall

The source proof establishes realizability of the self-reduction steps under its hypotheses. JANUS must not convert this into an uncharged algorithmic claim.

Freeze:

```text
EXISTS_VALID_B_i != POLYTIME_FIND_B_i
EXISTS_VALID_nu_i != POLYTIME_FIND_nu_i
SOURCE_RANDOM_RESTRICTION_ARGUMENT != POLYTIME_SOLVER_SUBROUTINE
```

If a future SAT/Policy-0B algorithm actually executes a D2 selector, all of the following must be charged:

- search for a maximizing or otherwise admissible `B_i`;
- tie-breaking;
- search or sampling of `nu_i`;
- representation and update of the residual graph;
- representation and update of residual base functions;
- any semantic certification used to decide crossing/local collapse.

---

# 6. Source-versus-JANUS semantic boundary

Sokolov's functional encoding contains variables for **local functions** supported inside one NW neighborhood. The restriction theorem describes how those local functional objects residualize.

An unrestricted JANUS B2 crossing macro may depend on roots from several neighborhoods and need not correspond to any source functional variable `y_g`.

Therefore:

```text
SOURCE FUNCTIONAL-FORM STABILITY
!=
SEMANTIC SURVIVAL THEOREM FOR ARBITRARY CROSSING B2 MACROS
```

JANUS may evaluate such a macro externally under a source-generated root restriction, but that is a new object requiring its own theorem.

This is the exact target of F3D-D3/D4.

---

# 7. Candidate theorem statements

## D2-T1 — source-completion ambiguity

The published Algorithm 1 does not by itself define a unique complete probability distribution on self-reductions because at least the `argmax B_i` and satisfying `nu_i` choices are nonunique and are not assigned a probability law.

## D2-T2 — completion-independent self-reduction validity

Candidate: every completion that chooses a valid maximizing `B_i` and a valid satisfying `nu_i` preserves the deterministic invariants used by Lemma 22.

This must be checked line-by-line against the proof; it is not assumed merely from pseudocode.

## D2-T3 — adversarial survival theorem

Preferred positive target:

```text
For every source-valid completion C,
Pr_{rho~D_C}[ semantic (b_rho,d_rho) survives above thresholds ] >= p(N).
```

Any non-negligible lower bound here would be robust to hidden source choice semantics.

## D2-T4 — explicit collapse escape

Preferred adversarial target:

```text
Construct a polynomial-size unrestricted B2 escape P_N and a source-valid completion C
such that the source heavy-width hypotheses remain valid but P_N's crossing skeleton
collapses with high probability under D_C.
```

Either T3 or T4 is scientifically valuable.

---

# 8. Falsifier templates

## F-D2-01 — two-maximizer divergence

Construct a small source-like graph state where two distinct valid maximum `B_i` sets exist. Attach a test macro whose kill variables intersect only one branch. Verify the two completions induce different macro-survival outcomes.

## F-D2-02 — multiple satisfying `nu_i` divergence

Freeze the same `B_i` but two valid satisfying assignments `nu_i`; construct a macro killed by one and surviving the other.

## F-D2-03 — favorable-completion laundering

Any proof that selects only the completion preserving the desired macro without proving its selection rule must be rejected.

## F-D2-04 — algorithmic free-search laundering

Any runtime claim that invokes `argmax` or a satisfying assignment oracle without a complexity bound must fail the hidden-cost gate.

## F-D2-05 — local-source/global-macro mismatch

Give a crossing macro with no single source neighborhood containing its semantic support. Source functional-variable stability must not be cited as if it directly tracked this macro.

---

# 9. Exit criteria

D2 is complete only if:

```text
D2-E1 exact source pseudocode and theorem hypotheses are frozen;
D2-E2 every nonunique choice is explicitly enumerated;
D2-E3 one completion semantics is selected or results are quantified over all completions;
D2-E4 selector/search complexity is separately accounted when algorithmic use is claimed;
D2-E5 source-local functional variables are kept distinct from arbitrary crossing B2 macros;
D2-E6 D2 falsifiers pass independent replay;
D2-E7 a mathematically well-defined survival quantity is handed to D3.
```

Until D2-E3 passes, the symbol

```text
D_source
```

must not be treated as one unique probability distribution.

---

# 10. Claim firewall

```text
SOURCE SELF-REDUCTION EXISTS
!=
UNIQUE SOURCE DISTRIBUTION

SOURCE ALGORITHM PSEUDOCODE
!=
POLYTIME IMPLEMENTATION

LOCAL FUNCTIONAL VARIABLE
!=
ARBITRARY CROSSING B2 MACRO

WHIGH-PROBABILITY HEAVY-WIDTH REDUCTION
!=
HIGH-PROBABILITY CROSSING-MACRO SURVIVAL

D2 MODEL
!=
UNRESTRICTED ER3 LOWER BOUND

P_VS_NP = OPEN
```
