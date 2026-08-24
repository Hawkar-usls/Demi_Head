# TOPA F3D-D1 — Semantic Residual Classifier Proof Program

**Frozen:** 2026-08-24T22:15:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific canonical lineage:** `Hawkar-usls/TOPA`  
**Parent front:** `C025-E2R-L1G-F3-D`  
**Status:** `D1_PROOF_PROGRAM_FROZEN__EXACT_TOTAL_CLASSIFIER_NOT_ASSUMED_EFFICIENT`  
**Global ceiling:** `P_VS_NP = OPEN`.

This document is a proof program, not a theorem receipt. Its job is to state exactly what must be defined, proved, falsified and replayed before F3D-D1 can be promoted.

The central correction is:

```text
EXACT SEMANTIC RESIDUAL CLASSIFICATION
!=
FREE OR POLYNOMIAL-TIME ORACLE
```

For unrestricted frozen-B2 DAGs, exact constant/local/equivalence recognition already contains standard circuit-unsatisfiability/equivalence problems. Therefore D1 is split into:

1. an **exact reference oracle** for finite fixtures;
2. an **operational proof-carrying partial classifier** that is allowed to return `UNKNOWN`.

No heuristic fallback is admissible.

---

# 1. Frozen objects and definitions

## D1.1 Root variables and locality hypergraph

Let `R={x_1,...,x_n}` be the root Boolean variables.

Let

```text
H = {V_1,...,V_m}
```

be an explicit family of locality neighborhoods, `V_i subseteq R`.

A Boolean function `f` over roots is **H-local** iff there exists `i` such that `f` depends only on variables in `V_i`.

Otherwise it is **H-crossing**.

This is a semantic definition. Syntactic support is not authoritative.

## D1.2 Frozen B2 DAG

A frozen-B2 extension DAG is topologically ordered and every extension has the form

```text
e_j := a_j AND b_j
```

where each operand is a signed literal over a root variable or an earlier extension variable.

Negation is therefore available on every operand. The basis is functionally complete because

```text
u OR v = NOT( (NOT u) AND (NOT v) ).
```

## D1.3 Root restriction

A root restriction is a partial assignment

```text
rho : dom(rho) subseteq R -> {0,1}.
```

For every root or extension node `u`, let

```text
f_u^rho
```

be its exact residual Boolean function over the free roots

```text
R_rho = R \ dom(rho).
```

## D1.4 Essential support

For a Boolean function `f` over `R_rho`, define

```text
Ess(f) = { x in R_rho : exists alpha,beta differing only on x with f(alpha) != f(beta) }.
```

This is semantic support.

## D1.5 Exact semantic classes

The exact reference classifier returns one of:

```text
CONST_0
CONST_1
ROOT_LITERAL(x)
NEG_ROOT_LITERAL(x)
LOCAL(V_i-list, Ess(f))
CROSSING(Ess(f))
```

Rules:

1. `CONST_0` iff `f` is identically zero.
2. `CONST_1` iff `f` is identically one.
3. `ROOT_LITERAL(x)` iff `f(alpha)=alpha(x)` for every assignment.
4. `NEG_ROOT_LITERAL(x)` iff `f(alpha)=1-alpha(x)` for every assignment.
5. `LOCAL` iff `Ess(f) subseteq V_i` for at least one neighborhood. All matching neighborhood IDs are returned.
6. `CROSSING` iff no neighborhood contains `Ess(f)`.

Constants are classified before locality. Literal aliases are classified before generic locality.

## D1.6 Semantic fingerprint and alias

For a fixed ordered list of free roots, the exact truth table is the finite semantic fingerprint

```text
FP_rho(u) = truth_table(f_u^rho).
```

Two nodes are semantically aliases under `rho` iff their fingerprints are identical.

This fingerprint is only a finite reference representation. Its byte size is exponential in the number of free roots in the worst case.

---

# 2. Lemmas to prove

## Lemma D1-L1 — residual semantics is unique

For a frozen topological B2 DAG and a fixed root restriction `rho`, evaluation of the DAG induces a unique residual Boolean function `f_u^rho` for every node.

**Proof route:** induction over topological gate order.

## Lemma D1-L2 — cofactor characterization of essential support

For free root `x`,

```text
x notin Ess(f)
iff
f|x=0 == f|x=1.
```

This gives an exact finite test and exposes the connection to circuit equivalence.

## Lemma D1-L3 — exact locality criterion

For every residual Boolean function `f`,

```text
f is local to V_i
iff
Ess(f) subseteq V_i.
```

Hence

```text
f is H-crossing
iff
for every V_i in H, Ess(f) is not a subset of V_i.
```

## Lemma D1-L4 — semantic support cannot grow under further root restriction

If `sigma` extends `rho`, then

```text
Ess(f^sigma) subseteq Ess(f^rho) \ (dom(sigma) \ dom(rho)).
```

Restriction may destroy dependencies but cannot create dependence on a variable that was already semantically inessential.

## Lemma D1-L5 — exact truth-table oracle cost

Let `r=|R_rho|` and let the explicit DAG contain `S` gates. Exhaustive evaluation gives all residual truth tables in

```text
O(S * 2^r)
```

time and `O(S * 2^r)` bits up to ordinary indexing factors.

This is an exact finite oracle, not a polynomial-in-original-`N` algorithm when `r` grows linearly.

---

# 3. D1 complexity barrier

This section is mandatory. D1 may not silently assume semantic classification is cheap.

## Theorem candidate D1-B1 — `CONST_0` recognition is coNP-complete

Problem:

```text
INPUT: frozen-B2 DAG P, output node e, root restriction rho.
QUESTION: is f_e^rho identically 0?
```

### Membership

The complement has a polynomial witness: a free-root assignment on which the output is `1`. Evaluating a frozen B2 DAG is polynomial in its explicit size.

Therefore `CONST_0` is in coNP.

### Hardness

Any Boolean circuit can be translated with linear/polynomial overhead into the `AND + signed-literal` frozen-B2 basis. OR gates are replaced using De Morgan.

For empty restriction,

```text
output is CONST_0
iff
original circuit is UNSAT.
```

Circuit-UNSAT is coNP-complete. Hence exact `CONST_0` recognition is coNP-complete.

The analogous `CONST_1` problem is coNP-complete by complementation of the output circuit.

### Complexity firewall

A deterministic polynomial-time exact total D1 classifier for general B2 DAGs would place a coNP-complete problem in P, and therefore would imply `P=NP=coNP`.

D1 must not assume such an algorithm.

## Theorem candidate D1-B2 — locality to a fixed neighborhood is coNP-complete

Problem:

```text
INPUT: frozen-B2 DAG output f and fixed explicit neighborhood V.
QUESTION: does f depend only on variables in V?
```

### Membership

Non-locality has a polynomial witness: two assignments `alpha,beta` that agree on every variable in `V` but satisfy

```text
f(alpha) != f(beta).
```

### Hardness

Given arbitrary circuit `C(X)`, choose a fresh root `y` outside `V=X` and construct

```text
F(X,y) = C(X) AND y.
```

Then

```text
F is local to V
iff
C is identically 0.
```

Thus fixed-neighborhood locality is coNP-hard, hence coNP-complete.

With an explicit polynomial-size neighborhood list `H`, exact `H`-locality remains coNP-hard already for `|H|=1`.

## Theorem candidate D1-B3 — exact semantic alias recognition is coNP-complete

For two B2 nodes `u,v`, deciding

```text
f_u^rho == f_v^rho
```

is circuit equivalence. Non-equivalence has an assignment witness, and hardness follows by comparing an arbitrary circuit to a constant-zero circuit.

---

# 4. Operational classifier — proof-carrying and partial

Because the exact total semantic classifier is not free, the runtime-safe D1 contract returns only statuses backed by checkable evidence:

```text
CERTIFIED_CONST_0
CERTIFIED_CONST_1
CERTIFIED_LOCAL
WITNESSED_CROSSING
UNKNOWN
```

`UNKNOWN` is a valid terminal result for D1.

No score, confidence, model vote or syntactic guess may replace it.

## D1.7 `WITNESSED_CROSSING`

For every locality neighborhood `V_i`, provide assignments

```text
alpha_i, beta_i
```

such that:

```text
alpha_i|V_i = beta_i|V_i
f(alpha_i) != f(beta_i).
```

If the list `H` is explicit and polynomial-size, the witness bundle is polynomial in `m*n` plus circuit-evaluation work.

### Lemma D1-L6 — crossing witness soundness

If such a witness pair exists for every `V_i`, then the function is not local to any `V_i`; therefore it is H-crossing.

This gives an NP-verifiable positive certificate for crossing without solving the complementary locality problem.

## D1.8 `CERTIFIED_LOCAL`

A local result requires one of:

1. complete exact truth-table evidence when a frozen finite-fixture size cap explicitly permits enumeration; or
2. a formal equivalence/dependency certificate accepted by an independently specified verifier.

Merely observing that syntactic support lies in one neighborhood is a sound sufficient condition only when the syntactic dependency calculation itself is exact for the represented function. It is not a complete semantic classifier and must be labeled `STRUCTURALLY_CERTIFIED_LOCAL`, not `EXACT_SEMANTIC_LOCAL`, unless equivalence is established.

## D1.9 constants

For finite fixtures, constants may be certified by complete truth-table enumeration.

For unbounded general circuits, universal short certificates for every constant/UNSAT circuit are not assumed. Proof size and proof discovery remain separately charged.

---

# 5. Candidate theorem statements

The following are the only promotion candidates currently admitted.

## D1-T1 — finite exact classifier correctness

For a finite frozen fixture with explicitly enumerated free-root assignments, the reference oracle returns the exact residual class defined in Section 1.

**Allowed promotion:** `PROVED_BY_EXHAUSTIVE_FINITE_SEMANTICS` for the fixture mechanics only.

## D1-T2 — exact-classifier complexity barrier

General exact `CONST_0`, fixed-neighborhood locality and semantic alias recognition are coNP-complete for frozen-B2 DAGs.

**Allowed promotion:** theorem after the reductions in Section 3 are independently reviewed.

## D1-T3 — crossing witness soundness

The explicit pair-per-neighborhood witness proves `CROSSING` and is polynomially checkable in explicit witness and DAG size.

## D1-T4 — safe partial classifier

A classifier that returns only checkable certified classes or `UNKNOWN` is scientifically sound even if incomplete.

This is an admissibility theorem, not a completeness or efficiency theorem.

---

# 6. Falsifier templates

Every D1 implementation must include at least the following adversarial cases.

## F-D1-01 — one-bit kill switch

Reuse F3D.D0. Large pre-restriction structure becomes constant after one root bit.

Expected result: exact oracle reports constants after the restriction.

## F-D1-02 — syntactic-support false positive

Construct

```text
z0 := y AND NOT y
u  := x AND NOT z0
```

Syntactically `u` depends on `{x,y}` but semantically

```text
u == x.
```

Any classifier that declares crossing from transitive syntactic support alone must fail.

## F-D1-03 — residual alias collision

Construct distinct macros such as

```text
g1 := x AND y
g2 := x AND z
```

and restrict `y=1,z=1`.

Expected:

```text
FP_rho(g1) == FP_rho(g2) == x.
```

## F-D1-04 — neighborhood ambiguity

Use overlapping neighborhoods and a function whose essential support lies in more than one. The exact result must preserve all matching neighborhood IDs rather than choosing one heuristically.

## F-D1-05 — crossing witness positive

For a true crossing function, provide and verify one distinguishing pair per neighborhood.

## F-D1-06 — fake crossing witness rejection

Modify one pair so that the assignments disagree on the claimed neighborhood or produce equal outputs. Verifier must reject.

## F-D1-07 — restriction-created locality

Start from a crossing function such as `x AND y`; restrict one variable to `1`. Expected residual is a root literal/local function.

## F-D1-08 — finite oracle scaling receipt

For fixtures with `r` free roots, record `2^r` enumerated assignments. The implementation must not relabel this as `poly(N)` when `r` is unbounded.

## F-D1-09 — unknown instead of guess

Give an input with no supplied constant/local certificate and no complete crossing witness bundle. Operational classifier must return `UNKNOWN`.

---

# 7. Exit criteria

F3D-D1 may be marked complete only when all of the following are satisfied.

## D1-E1 — definitions frozen

`PASS` only if residual function, essential support, locality, crossing, semantic fingerprint and alias semantics are machine-readable and versioned.

## D1-E2 — exact finite reference oracle

`PASS` only if a deterministic executable replay verifies all frozen finite fixtures by exhaustive semantics.

## D1-E3 — adversarial falsifier suite

`PASS` only if all F-D1-01 through F-D1-09 are represented or their exact equivalent is documented.

## D1-E4 — complexity barrier

`PASS` only if project status explicitly records:

```text
GENERAL_EXACT_SEMANTIC_CLASSIFIER = coNP-hard / not assumed polynomial
TRUTH_TABLE_ORACLE = exponential in free-root count
```

No later layer may erase this boundary.

## D1-E5 — proof-carrying partial classifier

`PASS` only if active outputs are restricted to certified/witnessed states plus `UNKNOWN`, with no heuristic fallback.

## D1-E6 — provider/arbiter replay

The finite mechanics probe must pass independent CI. CI validates implementation mechanics only; it does not prove the asymptotic complexity barrier.

## D1-E7 — handoff to D2

D2 may begin only with this explicit split:

```text
REFERENCE SEMANTICS = exact but potentially exponential
OPERATIONAL SEMANTICS = proof-carrying partial, UNKNOWN allowed
```

D2 must model the exact source self-reduction separately from any algorithm that searches for a useful restriction.

---

# 8. D2 handoff questions created by D1

D1 sharpens D2 into four non-equivalent questions:

1. Under Sokolov's exact self-reduction, what residual Boolean functions arise from the proof's unrestricted crossing macros?
2. Can semantic crossing survival be certified without solving a coNP-complete total classification problem at every node?
3. Does the source proof need only an existential semantic statement, or does JANUS require an efficiently computable classifier/selector?
4. If a restricted subclass admits cheap exact classification, what structural hypothesis makes it cheap, and is that hypothesis preserved by the self-reduction?

The fourth question is the preferred scientific route: find a source-matched restricted object on which exact semantics becomes tractable, rather than assuming a general semantic oracle.

---

# 9. Claim firewall

```text
EXACT_FINITE_TRUTH_TABLE
!=
POLYNOMIAL_GENERAL_CLASSIFIER

SYNTACTIC_SUPPORT
!=
SEMANTIC_SUPPORT

NO_LOCAL_CERTIFICATE
!=
CROSSING

NO_CROSSING_WITNESS
!=
LOCAL

UNKNOWN
!=
FAILURE

PROOF-CARRYING_PARTIAL_CLASSIFIER
!=
COMPLETE_CLASSIFIER

D1_MECHANICS_PASS
!=
UNRESTRICTED_ER3_LOWER_BOUND

F3D_D1
!=
P_VS_NP_RESOLUTION
```

`P_VS_NP = OPEN`.
