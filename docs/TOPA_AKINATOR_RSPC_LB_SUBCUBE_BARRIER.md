# TOPA / JANUS — RSPC-LB Subcube Certificate Barrier

**Frozen:** 2026-08-25  
**Status:** `ANALYTICAL_BARRIER_FROZEN__FINITE_REPLAY_PENDING`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Next surviving certificate idea

After exact survival counting and single-witness discovery were shown to contain #SAT/SAT-search on a simple abstract locality image, the next sound incomplete idea is to certify a **region** of restrictions rather than count all surviving restrictions.

For the uniform distribution over assignments to `X={x_1,...,x_n}`, let a codimension-`k` subcube certificate specify `k` fixed root-variable values and leave all other `X` variables free. Its measure is exactly

```text
mu(R) = 2^{-k}.
```

A natural certificate claim is

```text
SUBCUBE_SURVIVAL(e,R):
for every alpha in R, the residual semantic macro e|alpha is CROSSING.
```

If valid, this proves the sound lower bound

```text
SURV(e) >= 2^{-k}.
```

The question is whether this certificate can be verified and discovered cheaply without smuggling semantic hardness or a large region search into the selector.

---

## 1. Barrier L1 — semantic verification of universal subcube survival is coNP-complete

Take an arbitrary CNF `H(X)` and compile its truth function into a polynomial frozen-B2 signed-AND DAG with output literal `h`, exactly as in the preceding RSPC survival-counting reduction.

Choose fresh roots `p,q` with no locality neighborhood containing both, and define

```text
g <-> (p AND q)
e <-> ((NOT h) AND g).
```

Use the **full X-cube** `R=*^n`, i.e. codimension `k=0`.

For each complete assignment `alpha` to `X`,

```text
H(alpha)=0  => e|alpha = p AND q => CROSSING
H(alpha)=1  => e|alpha = 0       => CONSTANT.
```

Therefore

```text
SUBCUBE_SURVIVAL(e,*^n)
iff
for every alpha, H(alpha)=0
iff
H is UNSAT.
```

The transformation is polynomial.

### Membership in coNP

If a claimed full-cube survival certificate is false, a complete assignment `alpha` is a polynomial witness: evaluate the B2 DAG under `alpha` and the four assignments to the two residual roots `p,q`; this determines whether the residual depends essentially on both roots and hence whether it is CROSSING in this fixed abstract locality model.

Thus the decision problem

```text
SEMANTIC_UNIVERSAL_SUBCUBE_SURVIVAL
```

is coNP-complete already for the codimension-zero certificate on this reduction image.

### Meaning

A certificate that merely names a large subcube and asks the verifier to semantically establish survival on all points is **not** a cheap proof-carrying certificate unless a separate derivation is supplied.

This is a complexity reduction, not an unconditional time lower bound; `P_VS_NP` remains open.

---

## 2. What proof-carrying must mean here

To keep verification polynomial without a semantic oracle, the certificate must carry an explicit derivation of the universal statement over the region, for example

```text
(R, proof_that_every_alpha_in_R_preserves_required_structure).
```

The verifier may check that supplied proof in polynomial time in its serialized length. But this immediately restores the previous discovery distinction:

```text
CHEAP_REGION_PROOF_VERIFIER
!=
CHEAP_REGION_PROOF_DISCOVERY.
```

The selector must still deterministically construct both the region and the proof within one fixed polynomial budget in the original input length.

---

## 3. Barrier L2 — exhaustive search over polynomial-measure subcubes is already superpolynomial

A codimension-`k` subcube over `n` variables is determined by:

1. choosing the `k` fixed variables;
2. choosing one of two values for each fixed variable.

Hence the exact number of codimension-`k` subcubes is

```text
C(n,k) * 2^k.
```

Suppose the desired survival lower bound is inverse-polynomial,

```text
mu(R) >= N^{-c}
```

for fixed `c>0`. Since `mu(R)=2^{-k}`, this permits

```text
k <= c log_2 N.
```

That does **not** make exhaustive region discovery polynomial. On explicit state families with `n=Theta(N)` and

```text
k = Theta(log N),
```

we have

```text
C(n,k) 2^k = exp(Theta((log N)^2)) = N^{Theta(log N)},
```

up to lower-order `log log N` terms.

Therefore the strategy

```text
enumerate every inverse-polynomial-measure subcube,
run a polynomial certificate verifier on each,
stop at the first PASS
```

is superpolynomial/quasipolynomial in the worst case for this candidate vocabulary.

This is a lower bound on the **explicit exhaustive-subcube enumeration strategy**, not on every possible constructor.

---

## 4. Stronger lesson: compression of the witness space is not enough

Moving from point witnesses to large regions can reduce the number of objects dramatically, but the remaining region language may still be too large:

```text
2^n point assignments
    ->
exp(Theta(log^2 N)) large subcubes
```

is a real compression but not a polynomial one.

Thus

```text
POLYNOMIAL_MEASURE_CERTIFICATE
!=
POLYNOMIALLY_DISCOVERABLE_CERTIFICATE.
```

The selector needs a **direct constructor theorem** for the right region/proof, not exhaustive enumeration of a compressed certificate space.

---

## 5. Source-matching firewall

As in the preceding RSPC counting reduction, the uniform X-assignment distribution here is an abstract constructed distribution. It is not claimed to be Sokolov's Algorithm 1/self-reduction relation.

Therefore we prove only that these two generic shortcuts are invalid as universal free primitives:

```text
SEMANTIC_SUBCUBE_SURVIVAL_VERIFICATION
and
EXHAUSTIVE_LARGE_SUBCUBE_DISCOVERY.
```

We do **not** prove that source-matched Sokolov region certificates are coNP-hard to verify or require quasipolynomial search.

---

## 6. Surviving certificate contract

The surviving positive object is now stricter:

```text
RSPC-LB-PROOF =
(region R,
 polynomial-size robustness proof Pi,
 explicit measure lower bound mu(R),
 deterministic constructor trace)
```

with all of the following required:

```text
VERIFY(R,Pi) = poly(N+|Pi|),
CONSTRUCT(R,Pi) = poly(N),
|Pi| = poly(N),
mu(R) >= 1/poly(N) or another proved globally sufficient bound,
no enumeration of exp(log^2 N) regions,
repeated certified moves imply one fixed polynomial global potential bound.
```

This is no longer a scoring rule. It is a constructive proof-search theorem.

---

## 7. Next exact attack

Freeze the next gate as

```text
AKINATOR-RSPC-PC
= PROOF-CARRYING ROBUST REGION CONSTRUCTOR
```

The two-sided attack is:

**Positive lane:** identify a structural family in which a large robust region and its proof are generated directly from the syntax/graph in polynomial time, then prove a global potential decrease.

**Adversarial lane:** construct instances where many polynomial-measure regions exist but locating any region with a short robustness proof encodes a hard search problem, or show that every certificate in a proposed restricted proof vocabulary requires too much size.

---

## 8. Claim ceiling

```text
SEMANTIC_UNIVERSAL_FULL_CUBE_SURVIVAL
= coNP_COMPLETE_IN_STATED_ABSTRACT_LOCALITY_MODEL

EXHAUSTIVE_CODIMENSION_THETA_LOG_N_SUBCUBE_SEARCH
= exp(Theta((log N)^2)) ON n=Theta(N) STATES

POLYNOMIAL_MEASURE_SUBCUBE
= NOT_SUFFICIENT_FOR_POLYNOMIAL_DISCOVERY

PROOF_CARRYING_ROBUST_REGION_CONSTRUCTOR
= OPEN / NEXT

SOKOLOV_SOURCE_MATCHED_REGION_VERIFICATION_HARDNESS
= NOT_PROVED

UNIVERSAL_PROOF_CARRYING_B2_SELECTOR
= OPEN

P_VS_NP
= OPEN
```
