# TOPA F3D-D5 — Parity Lifetime / Reuse Barrier

**Frozen:** 2026-08-24T23:15:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D4_PARITY_RESIDUAL_TRANSFER.md`  
**Status:** `NAIVE_SEMANTIC_LIFETIME_AMORTIZATION_REFUTED`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. The route being tested

D4 yields a lower bound on **collective residual crossing/polarity complexity** whenever a source-valid restriction leaves a parity-NW residual instance in the hard parameter regime.

A tempting next step is to apply D4 at many nested self-reduction stages and sum the residual obligations. This would imply a large total number of original extension variables only if one original extension could be charged at few stages.

D5 tests that missing lifetime assumption.

## 2. Linear-size frozen-B2 parity circuit

Let roots be

```text
x1,...,xn.
```

Set `y1=x1`. For every `j=2,...,n`, implement XOR with three frozen-B2 AND gates:

```text
a_j := y_(j-1) AND x_j
b_j := (NOT y_(j-1)) AND (NOT x_j)
y_j := (NOT a_j) AND (NOT b_j).
```

Then

```text
y_j = x1 XOR ... XOR x_j.
```

The full network has `3(n-1)` extension gates.

## 3. Exact residual support of prefix parity

Let `rho` be any root restriction. For every prefix `j`,

```text
y_j | rho
```

is parity of the unassigned variables among `{x1,...,xj}`, possibly complemented by a constant determined by the assigned bits.

Therefore its exact essential support is

```text
Ess(y_j|rho)
=
{x_k : k<=j and x_k notin dom(rho)}.
```

This is exact semantics, not syntactic support.

If every locality neighborhood has size at most `Delta`, then

```text
|Ess(y_j|rho)| > Delta
=> y_j|rho is semantically CROSSING.
```

## 4. Many crossing prefixes survive every small restriction

Let

```text
t := |dom(rho)|.
```

For every `j>t+Delta`:

```text
|Ess(y_j|rho)|
>= j-t
> Delta.
```

Hence every such prefix parity is crossing.

There are at least

```text
n-t-Delta
```

crossing prefix outputs `y_j`.

Among indices `j>t+Delta`, at most `t` can have `x_j` assigned. Therefore at least

```text
n-2t-Delta
```

indices have both:

```text
y_(j-1)|rho crossing
AND
x_j free.
```

For each such index the residual XOR gadget still genuinely combines a crossing prefix with a new free root variable; it has not collapsed merely to a constant or root-fixed alias.

Thus when `n-2t-Delta>0`, a linear number of crossing-computation stages can coexist in the **same O(n)-gate circuit** after restriction.

## 5. Source self-reduction lifetime

For a Sokolov self-reduction, Definition 20 gives

```text
|L_rho| <= epsilon^2*r/16
```

and the restriction assigns exactly `N(L_rho)`. Since every left degree is at most `Delta`,

```text
t = |supp(rho)|
<= Delta*|L_rho|
<= epsilon^2*r*Delta/16.
```

Define

```text
T_root := epsilon^2*r*Delta/16.
```

Every intermediate assignment is nested inside the final self-reduction, so its root support size is at most `T_root` as well.

If

```text
2*T_root + Delta < n,
```

then at **every intermediate stage** the same original parity network contains at least

```text
n-2*T_root-Delta
```

late prefix stages that remain semantically crossing with a free new root input.

In common expander regimes where `T_root=o(n)` and `Delta=o(n)`, this is `Omega(n)` persistent crossing structure.

## 6. D5-A theorem — no short universal semantic lifetime bound

### Theorem D5-PARITY-LIFETIME

There exists a frozen-B2 network of `3(n-1)` extension gates such that, for every nested sequence of root restrictions with support size at most `T` at all stages and `2T+Delta<n`, the same network retains `Omega(n-2T-Delta)` semantically crossing prefix/XOR stages at every restriction stage.

Applying this with

```text
T = epsilon^2*r*Delta/16
```

shows that source self-reduction does not imply an `O(1)`, logarithmic, or other small universal lifetime for crossing extension structure whenever the stated parameter gap leaves `Omega(n)` free global support.

## 7. What this refutes

The following amortization rule is invalid in general:

```text
SUM_OVER_STAGES(crossing complexity)
/ small_universal_macro_lifetime
=> many distinct extension variables.
```

A single polynomial-size global circuit can remain semantically nonlocal throughout the entire sequence and be counted repeatedly.

Likewise:

```text
MANY_HARD_RESIDUAL_STAGES
!=
MANY_DISTINCT_GLOBAL_ABBREVIATIONS.
```

## 8. What it does not prove

The persistent parity network is not shown to be sufficient or useful for a short ER3 refutation of the NW formula.

Persistence alone is not proof utility.

D5 therefore does not give a polynomial upper bound, a polynomial refutation, or any evidence that ER is p-bounded.

It only kills the naive lifetime-amortization route to an ER lower bound.

## 9. New exact resource — proof-relative renewal

The next object cannot be raw semantic survival. It must measure what **new proof capability** is required after each hard restriction.

Freeze the distinction:

```text
SEMANTICALLY_SURVIVING_EXTENSION
!=
PROOF-ESSENTIAL_INFORMATION.
```

Candidate D6 target:

```text
RENEW(P,rho_i -> rho_j)
```

should count a checkably defined proof resource that cannot be supplied for many residual stages by the same fixed set of global extension functions unless those functions already encode a correspondingly strong global object.

Possible exact formulations to test, not assume:

1. minimum number of extension definitions whose removal destroys every residual refutation below a frozen size bound;
2. minimum crossing-extension cutset separating residual axioms from the empty clause in the proof DAG;
3. minimum number of distinct semantic cofactor classes actually used on proof paths after restriction;
4. communication/information measure of the residual extension functions relative to NW output partitions.

Each candidate must first survive explicit parity/reuse falsifiers before promotion.

## 10. Claim firewall

```text
LONG_SEMANTIC_LIFETIME
!=
SHORT_ER_PROOF

PERSISTENT_PARITY_NETWORK
!=
USEFUL_REFUTATION

REPEATED_D4_OBSTRUCTION
!=
DISTINCT_K_LOWER_BOUND

D5_BARRIER
!=
ER_LOWER_BOUND

P_VS_NP = OPEN
```
