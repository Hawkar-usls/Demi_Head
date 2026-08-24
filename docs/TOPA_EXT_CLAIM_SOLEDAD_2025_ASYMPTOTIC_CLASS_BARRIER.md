# TOPA EXT Claim Audit — Soledad Terrazas 2025 P != NP

**Source:** public preprint `Why P≠NP: A Natural Language Explanation with Mathematical Appendix` (2025).  
**Status:** `MAIN_ASYMPTOTIC_INFERENCE_NOT_ESTABLISHED`.  
**Global ceiling:** `P_VS_NP = OPEN`.

## Load-bearing step

The appendix states, for 3-SAT, a bound of the form

```text
D_G(R_phi) >= D_V(R_phi) + Omega(n / log n)
```

and then promotes this to a claim that the generation-verification gap is

```text
omega(poly(n))
```

(super-polynomial), which is used in the final contradiction with `P=NP`.

## Exact asymptotic failure

The displayed lower bound does not imply the claimed class.

For all sufficiently large `n`,

```text
n / log n <= n.
```

Thus `n/log n` is polynomially bounded. A lower bound

```text
Omega(n/log n)
```

states only that the quantity is at least on the order of a polynomially bounded function. It gives **no** super-polynomial lower bound.

Even a stronger statement such as `Omega(n)` would still not imply

```text
omega(poly(n)).
```

To conclude a super-polynomial lower bound one would need a statement such as

```text
for every fixed c, f(n) / n^c -> infinity
```

(or an equivalent universal-over-polynomials formulation), which is not supplied by `Omega(n/log n)`.

Therefore the final contradiction does not follow from the displayed asymptotic estimate.

```text
SOLEDAD_2025_OMEGA_N_OVER_LOGN_TO_SUPERPOLY = INVALID_INFERENCE
SOLEDAD_2025_P_NOT_EQUAL_NP_ROUTE = NOT_ESTABLISHED
```

This verdict does not require judging the paper's linguistic/definitional framework; the numerical asymptotic promotion already fails at the load-bearing step.

## Reusable JANUS law

```text
LOWER_BOUND_MAGNITUDE_MUST_MATCH_THE_CLAIMED_COMPLEXITY_CLASS

Omega(poly-bounded function)
!=
superpolynomial lower bound
```

Every future JANUS lower-bound promotion must state its quantifiers over exponents explicitly.

`P_VS_NP = OPEN`.
