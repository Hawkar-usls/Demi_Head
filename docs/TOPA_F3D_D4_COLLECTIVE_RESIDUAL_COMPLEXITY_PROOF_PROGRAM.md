# TOPA F3D-D4 — Collective Residual Crossing Complexity

**Frozen:** 2026-08-24T22:55:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D3_FAR_POINT_GUARD_SURVIVAL_BARRIER.md`  
**Status:** `D4_CONDITIONAL_COLLECTIVE_THEOREM_PROVED__EXACT_RESIDUAL_HARDNESS_TRANSFER_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why D4 replaces per-macro survival

D3 proved that a polynomial-size semantically crossing B2 macro can be killed with probability `exp(-Omega(r))` by the source self-reduction. Therefore no universal inverse-polynomial survival theorem is available for each named extension variable.

D4 discards that requirement entirely.

The object is now the **whole residual proof**:

```text
P  --restrict by rho-->  P|rho.
```

Individual definitions may collapse, alias, become local, become unused, or disappear. The only question is whether the residual proof as a whole can become collectively too local while it still refutes a hard residual instance.

## 2. Residual proof object

Let `P` be a frozen B2/ER3 refutation with explicit encoded size `S`.

For a root restriction `rho`:

1. restrict every root literal by `rho`;
2. simplify root clauses and extension-definition clauses by Boolean constants;
3. restrict every Resolution line;
4. delete satisfied/tautological lines and unreachable proof garbage;
5. prune unused extension definitions;
6. retain only the reachable residual refutation.

Call the resulting proof `P_rho` and its explicit size `S_rho`.

Restriction and deletion do not increase the number of stored source proof nodes/definitions, so under an ordinary monotone encoding

```text
S_rho <= O(S)
```

up to fixed representation overhead. This statement is about proof representation, not semantic classification cost.

## 3. Residual semantic locality

Classify every proof-reachable residual extension by its exact residual Boolean function relative to the residual locality hypergraph.

For theorem statements this classification may be semantic/nonconstructive. D1 forbids treating it as a free polynomial-time runtime oracle.

A residual macro is:

```text
LOCAL     iff its exact essential support is contained in one residual neighborhood;
CROSSING  otherwise.
```

Compute the already frozen F3 collective parameters on the reachable residual crossing skeleton:

```text
b_rho = negative-frontier width;
d_rho = inversion depth.
```

These are proof-level parameters of `P_rho`, not inherited labels from `P`.

## 4. D4-T0 — conditional collective residual theorem

Assume all of the following for a restricted instance `F_rho` and proof `P_rho`:

### A1 — residual refutation

`P_rho` is a valid B2/ER3 refutation of `F_rho`.

### A2 — F3 semantic-local cut elimination applies

Every residual macro classified LOCAL can be represented in the target local functional language required by the established F3 transformation, and the F3 proof-level cut-elimination theorem applies to the residual crossing skeleton.

### A3 — local lower bound

Every resulting local-functional Resolution refutation of `F_rho` has size at least

```text
L_rho.
```

### A4 — explicit residual proof size

`P_rho` has explicit encoded size `S_rho>=2`.

Then the established F3 transformation yields a local Resolution refutation of size at most

```text
S_rho ^ [ 7 * (b_rho+2)^(d_rho+1) ].
```

Consequently:

```text
L_rho
<= S_rho ^ [ 7 * (b_rho+2)^(d_rho+1) ].
```

### Proof

If the inequality failed, applying the F3 residual macro-cut elimination to `P_rho` would produce a local-functional Resolution refutation strictly shorter than the assumed lower bound `L_rho`, contradiction. QED.

This theorem is independent of the survival of any named pre-restriction extension variable.

## 5. D4-T1 — input-relative collective tradeoff

Suppose in addition that for a residual input encoding length `N_rho` there are universal fixed constants `eta,c>0` such that

```text
L_rho >= exp(N_rho^eta)
```

and

```text
S_rho <= N_rho^c.
```

Then D4-T0 implies

```text
N_rho^eta
<= 7*c*(b_rho+2)^(d_rho+1)*log N_rho.
```

Taking logarithms:

```text
(d_rho+1)*log(b_rho+2)
>= eta*log N_rho
   - log(7*c*log N_rho).
```

Hence

```text
(d_rho+1)*log(b_rho+2)
= Omega(log N_rho).
```

More precisely the lower bound is

```text
eta*log N_rho - O(log log N_rho).
```

### Meaning

A polynomial-size residual B2/ER3 proof of a residual hard instance cannot have both a narrow negative frontier and shallow polarity-inversion depth.

This is **collective residual survival**. It says nothing about which original extension definitions survive.

## 6. Why this bypasses D3-GUARD

D3-GUARD exhibits one crossing macro with tiny survival probability.

D4 permits that macro to disappear completely.

If the residual formula remains hard and the residual proof remains short, D4 forces *some* sufficient crossing/polarity structure to be present in the reachable residual proof, regardless of whether it descends from the fragile guard or from different definitions.

Therefore:

```text
PER_MACRO_SURVIVAL is unnecessary for D4-T0/T1.
```

## 7. Exact transfer gate D4-X — not yet closed

For the current JANUS line, A2/A3 must be tied to the exact source residual object.

The historical L1E theorem translated a direct root-only parity-NW CNF into Sokolov's local functional encoding for the unreduced hard family.

Under a source self-reduction, JANUS must still prove all of the following for the **restricted** object:

1. the restricted direct CNF `F|rho` is exactly, or polynomially reducible to, the intended residual direct encoding of the source PRG instance;
2. root clauses surviving restriction map into the residual functional encoding;
3. semantically local residual B2 macros map to legal residual local functions in the source functional language;
4. duplicate/alias residual functions can be identified in the proof transformation without altering the existence/size claim;
5. the residual source parameters still fall in a regime where the local Resolution lower bound has the required quantitative form;
6. `N_rho` is the actual encoded bit length of the residual direct input, not merely a graph parameter;
7. all polynomial exponents used in the transfer are universal fixed constants.

Until these are proved, D4-T1 is a conditional theorem, not an unconditional hard-family residual lower bound.

## 8. Immediate corollary in terms of total extension count K

Let `K_rho` be the number of proof-reachable residual extension definitions.

Because each frozen B2 extension has at most two incoming extension dependencies,

```text
b_rho <= 2*K_rho,
d_rho <= K_rho.
```

D4-T1 therefore gives only the coarse single-stage consequence

```text
(K_rho+1)*log(2*K_rho+2)
= Omega(log N_rho),
```

hence at best

```text
K_rho = Omega(log N_rho / log log N_rho)
```

from this counting alone.

This is **not** a superpolynomial extension-count lower bound.

## 9. Why repeated self-reduction does not automatically sum to a K lower bound

Suppose the source construction gives a chain

```text
rho_0 subset rho_1 subset ... subset rho_T
```

and D4 forces residual crossing complexity at many stages.

The same extension definition can remain semantically crossing and proof-reachable at many stages. Therefore

```text
SUM_i residual_complexity_i
```

cannot be charged injectively to distinct original extension variables without a separate lifetime theorem.

Freeze the exact next resource:

```text
lambda(e)
 := number of hard residual stages at which extension e
    (or its residual descendant/alias class) remains proof-reachable and crossing.
```

Then any additive charging argument requires an upper bound on these semantic lifetimes or a stronger notion of disjoint proof utility.

No such bound is assumed.

## 10. Next gates

```text
D4-T0 conditional collective residual theorem       = PROVED
D4-T1 quantitative tradeoff under A1-A4 + input map = PROVED CONDITIONALLY
D4-X exact residual direct-to-functional transfer    = OPEN / NEXT
D4-L extension semantic lifetime / amortization      = OPEN
D4-U proof-relevant utility versus merely surviving macro = OPEN
Issue #217 unrestricted ER3 extension-count          = OPEN
P_VS_NP                                               = OPEN
```

## 11. Falsifiers

### F-D4-01 — fragile guard disappearance

Delete the D3 guard under a restriction that kills it. D4 must still classify the whole residual proof independently rather than fail because one named macro vanished.

### F-D4-02 — irrelevant robust macro

Add a globally robust crossing extension that is unreachable from the final residual refutation. Pruning must remove it; it may not satisfy the collective requirement by mere existence.

### F-D4-03 — residual-size laundering

A proof polynomial in original `N` may not be called polynomial in `N_rho` unless a quantitative relation between `N` and `N_rho` is proved.

### F-D4-04 — source-object mismatch

A lower bound on the residual functional encoding may not be applied to a different restricted direct CNF without the D4-X reduction.

### F-D4-05 — lifetime double counting

One extension surviving `T` stages may not be counted as `T` distinct extensions.

## 12. Claim firewall

```text
COLLECTIVE_RESIDUAL_COMPLEXITY
!=
ORIGINAL_EXTENSION_COUNT_LOWER_BOUND

HARD_RESIDUAL_INSTANCE
!=
EXACT_RESIDUAL_DIRECT_ENCODING_WITHOUT_D4_X

SEMANTIC_LOCALITY_EXISTS
!=
POLYTIME_SEMANTIC_CLASSIFIER

SUM_OF_STAGE_COMPLEXITIES
!=
NUMBER_OF_DISTINCT_EXTENSIONS

D4_CONDITIONAL_THEOREM
!=
FULL_ER3_LOWER_BOUND

P_VS_NP = OPEN
```
