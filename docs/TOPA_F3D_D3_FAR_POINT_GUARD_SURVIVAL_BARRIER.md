# TOPA F3D-D3 — Far-Point Guard Survival Barrier

**Frozen:** 2026-08-24T22:45:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Primary source mechanics:** Dmitry Sokolov, *Pseudorandom Generators, Resolution and Heavy Width*, CCC 2022, DOI `10.4230/LIPIcs.CCC.2022.15`.  
**Status:** `UNIVERSAL_PER_MACRO_SURVIVAL_ROUTE_REFUTED_IN_SOURCE_MATCHED_FORM`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Target that is being falsified

A tempting D3 route would assert that every semantically crossing frozen-B2 macro in a polynomial-size proof has at least inverse-polynomial probability of remaining crossing/nonconstant under the source self-reduction.

This note refutes that route for **arbitrary external crossing macros**.

The counterexample does not require heuristic ranking, a favorable completion of Algorithm 1, or an inefficient semantic classifier.

## 2. Far forbidden points exist by counting

Let

```text
F : {0,1}^n -> {0,1}^m
```

be the source PRG map, with `m>n`.

Fix `0<delta<1/2` such that

```text
H_2(delta) + n/m < 1,
```

where `H_2` is binary entropy.

The image has at most `2^n` points. The number of `m`-bit strings within Hamming radius `delta*m` of the image is at most

```text
2^n * sum_{j<=delta*m} C(m,j)
<= 2^(n + H_2(delta)*m).
```

By the strict entropy inequality this is `<2^m`. Hence there exists a forbidden point `b` satisfying

```text
d_H(b, Im(F)) > delta*m.
```

In particular `b` is outside the image.

Sokolov's encoding is defined for arbitrary `b` outside the image; as in the source proof one may flip each output function by `b_i` and work with forbidden point zero. Output complementation preserves balancedness.

## 3. A polynomial-size globally guarded crossing macro

Choose an arbitrary root assignment

```text
a* in {0,1}^n.
```

Since `F(a*)` lies in the image,

```text
D := { i in [m] : F(a*)_i != b_i }
```

has size

```text
|D| > delta*m.
```

After output-flipping to forbidden zero, every `i in D` satisfies

```text
f'_i(a*|Vars_i) = 1.
```

Define the assignment-indicator guard

```text
G_a*(x)
 := AND_{j=1}^n l_j(x_j),

l_j(x_j) = x_j      if a*_j=1,
             NOT x_j if a*_j=0.
```

Frozen B2 implements this with `n-1` AND gates over signed root literals.

Its exact essential support is all `n` root variables: changing any one bit of `a*` changes the guard from `1` to `0`. Therefore, when every source locality neighborhood has size at most `Delta<n`, `G_a*` is semantically crossing.

## 4. One selected disagreeing output kills the guard

Run Algorithm 1 after the output flip.

Condition on the event that `G_a*` has survived up to the beginning of iteration `i`. Then every root variable already assigned by `rho_i` agrees with `a*`.

Suppose the random active output `v^i` lies in the still-alive part of `D`.

The current residual base function satisfies

```text
p^i_{v^i}(a* on its free coordinates) = 1.
```

But line 8 samples

```text
sigma_i <- (p^i_{v^i})^{-1}(0).
```

Therefore `sigma_i` cannot agree with `a*` on all newly assigned free neighbours of `v^i`. At least one root literal of the guard is made false, so

```text
G_a* | (rho_i union sigma_i) = 0.
```

Once false, later line-11/line-12 completions cannot restore the conjunction.

This implication is independent of which valid maximum `B_i` or satisfying `nu_i` is chosen.

## 5. How many disagreeing outputs can a completion hide?

Let

```text
C_i := union_{j<i} B_j.
```

Proposition 29 in the source proves

```text
|C_i| <= epsilon^2*r/32
```

throughout Algorithm 1.

Conditioned on guard survival, no vertex of `D` has previously been selected as an active `v^j`, because selecting one would have killed the guard. Thus disagreeing outputs can disappear from the active left side only by entering closure sets `B_j`.

Hence at every iteration

```text
|D intersect L_i|
>= delta*m - epsilon^2*r/32.
```

Since `v^i` is uniform in `L_i` and `|L_i|<=m`, the conditional probability that the next selected output kills the guard is at least

```text
delta_0
:= delta - epsilon^2*r/(32m).
```

Assume `delta_0>0`.

## 6. Survival bound

Algorithm 1 performs

```text
ell := epsilon^3*r/32
```

iterations.

Iterating the conditional bound gives

```text
Pr[G_a* survives all ell iterations]
<= (1-delta_0)^ell
<= exp(-delta_0*epsilon^3*r/32).
```

This upper bound is valid for every history-dependent valid completion rule for the nonunique line-11/line-12 choices, because Proposition 29 is completion-robust and the kill event occurs at the random line-8 assignment before the completion steps.

### Theorem D3-GUARD

For every source PRG instance with `m>n`, every `delta` satisfying `H_2(delta)+n/m<1`, and parameters with `delta_0>0`, there exists an `O(n)`-gate semantically crossing frozen-B2 macro whose survival probability under Algorithm 1 is at most

```text
exp(-delta_0*epsilon^3*r/32).
```

## 7. Input-relative consequence

If the concrete source/input parameterization satisfies

```text
r / log N -> infinity
```

and `delta_0,epsilon` are bounded below by positive constants, then

```text
exp(-Omega(r)) = N^{-omega(1)}.
```

Thus a polynomial-size crossing macro can have **superpolynomially small survival probability in original input length**.

This consequence is conditional on the stated parameter map; it is not silently assumed for every source regime.

## 8. What this refutes

The following universal route is false:

```text
SEMANTICALLY_CROSSING_MACRO
=> INVERSE_POLYNOMIAL_SOURCE_SELF_REDUCTION_SURVIVAL.
```

Also false is any attempt to lower-bound post-restriction F3 complexity by summing survival guarantees that apply uniformly to every pre-restriction crossing macro.

The guard has large semantic support, polynomial circuit size, and can nevertheless be killed with exponentially high probability in the self-reduction iteration count.

## 9. What this does not refute

This theorem does not show that a guarded macro is useful in a short ER3 refutation.

It does not construct a polynomial-size refutation of the hard formula.

It does not refute a **proof-level collective survival theorem** saying that a short refutation, as a whole, must retain enough crossing structure after a hard-instance-preserving restriction.

That distinction becomes the next gate.

## 10. Correct next front — proof-level collective survival

The scientifically viable replacement is not

```text
EVERY CROSSING MACRO SURVIVES.
```

It is a proof-relative dichotomy:

```text
If a short unrestricted B2/ER3 refutation P is restricted by a source-valid rho
and the residual source instance remains in the hard family,
then P|rho cannot become too local / too low-(b,d),
otherwise F3 cut elimination would produce a forbidden short local Resolution proof.
```

This asks for a lower bound on the **residual proof's collective semantic crossing complexity**, not on any named pre-restriction extension variable.

## 11. Claim firewall

```text
FRAGILE_CROSSING_MACRO
!=
USEFUL_SHORT_ER3_PROOF

PER_MACRO_SURVIVAL_REFUTED
!=
PROOF_LEVEL_SURVIVAL_REFUTED

EXP(-OMEGA(r))
!=
SUPERPOLYNOMIAL_IN_N_UNLESS_r/LOG_N_TO_INFINITY

D3_GUARD_BARRIER
!=
ER_LOWER_BOUND

P_VS_NP = OPEN
```
