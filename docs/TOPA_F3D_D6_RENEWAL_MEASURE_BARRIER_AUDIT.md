# TOPA F3D-D6 — Renewal Measure Barrier Audit

**Frozen:** 2026-08-24T23:25:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D5_PARITY_LIFETIME_REUSE_BARRIER.md`  
**Status:** `D6_NAIVE_COFACTOR_RENEWAL_REFUTED__PROOF_RELATIVE_MEASURE_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Goal

D5 refuted raw semantic lifetime as an amortization resource: one small global circuit can remain crossing through all hard residual stages.

D6 asks whether repeated restrictions force the same extension circuit to expose many **distinct residual semantic functions**, and whether that number can be charged to extension count.

The first naive route is refuted below.

## 2. Inner-product cofactor counterexample

Let roots be split into

```text
X={x1,...,xk},
Y={y1,...,yk}.
```

Define

```text
IP_k(X,Y)
:= XOR_{i=1}^k (x_i AND y_i).
```

A frozen-B2 circuit computes each product `p_i=x_i AND y_i` with one AND gate and combines the products with the standard 3-AND XOR gadget. Total extension count is `O(k)`.

Now fix the entire `X` half to a vector

```text
a in {0,1}^k.
```

The residual function on `Y` is

```text
IP_k(a,Y)
=
XOR_{i:a_i=1} y_i.
```

For two distinct vectors `a!=a'`, these residual functions are distinct because their symmetric difference contains some coordinate `j`; changing only `y_j` distinguishes the two parity functions.

Therefore one `O(k)`-gate B2 circuit has exactly

```text
2^k
```

distinct cofactors under the `2^k` restrictions fixing `X`.

### D6-A theorem

```text
EXPONENTIALLY_MANY_DISTINCT_RESIDUAL_FUNCTIONS
!=
EXPONENTIALLY_MANY_EXTENSION_GATES.
```

A lower bound based only on counting distinct cofactor/semantic classes cannot force superpolynomial extension count.

## 3. Why this is stronger than the earlier flat-case barrier

The old class-count/parity barrier showed that exponentially many flat CNF/DNF cases can be compressed by a small extension circuit.

D6-A shows the same compression survives **across restrictions**:

```text
one compact circuit
-> exponentially many distinct exact residual functions.
```

Thus a renewal measure must not count each new cofactor as a newly paid proof object.

## 4. Communication-value caution

A natural repair is to assign an information/communication complexity value to each residual function.

This may be scientifically useful, but a scalar communication value alone does not automatically yield a superpolynomial extension-count lower bound:

- every Boolean function on `n` root bits has deterministic two-party communication complexity at most `n+1` for any fixed partition by sending one side's entire input;
- hence one fixed-partition scalar is at most linear in root count;
- summing such a scalar over polynomially many explicit NW neighborhoods/partitions remains polynomial in the ordinary input parameters.

To prove a superpolynomial B2 gate lower bound, a communication-style measure would need a **composition/direct-sum theorem tied to the proof**, not merely a high value for one macro.

No such theorem is assumed.

## 5. Proof reachability is not yet proof utility

D4 correctly prunes definitions unreachable from the final residual refutation.

However syntactic reachability alone is not a quantitative information-renewal theorem. A macro may occur on proof paths while carrying a reusable global function that serves many restrictions.

The next resource must be proof-relative and must survive the following adversarial question:

```text
Can the same small global circuit be reused to satisfy the proposed measure
at polynomially many residual stages?
```

If yes, the measure cannot be summed to obtain a distinct-`K` lower bound.

## 6. Candidate D6-B objects — test before promotion

The following are candidates only.

### B1 — extension cutset

Minimum number of crossing extension definitions whose removal disconnects all residual axiom-to-empty-clause derivation paths in a fixed proof DAG.

Risk: purely syntactic routing may be gameable by proof rewrites and may not be invariant under p-equivalent proofs.

### B2 — budgeted indispensability

For size budget `B`, minimum number of extension definitions that must be available to obtain *any* refutation of the residual formula of size at most `B`.

This is proof-relative in the right sense, but its definition quantifies over alternative proofs and may essentially restate the target proof-complexity problem.

### B3 — partition-profile complexity

Associate to each used extension function a vector of communication/information values over the relevant NW output partitions and seek a direct-sum lower bound for a complete residual refutation.

This has the best chance to penalize reusable global macros, but no valid direct-sum theorem is currently established.

### B4 — semantic influence on source heavy width

Measure how much removing/restricting an extension can reduce the minimum achievable heavy width of functional forms of the proof.

This aligns most directly with Sokolov's source invariant but requires extending the heavy-width formalism beyond local functional variables to arbitrary B2 circuits.

## 7. Exact next decision

```text
D6-A cofactor-count renewal                 = REFUTED
D6-B1 syntactic cutset                       = CANDIDATE / ADVERSARIAL TEST NEEDED
D6-B2 budgeted indispensability              = CANDIDATE / MAY BE CIRCULAR
D6-B3 partition-profile direct sum            = CANDIDATE / OPEN
D6-B4 generalized heavy-width influence       = CANDIDATE / OPEN
```

Priority order:

```text
1. Attack B1 with proof-rewrite falsifiers.
2. If B1 dies, test whether B4 can be defined semantically without a free classifier.
3. Keep B3 as a bridge to known communication/interpolation techniques, but require a direct-sum theorem before any counting claim.
```

## 8. Claim firewall

```text
MANY_COFACTORS
!=
MANY_EXTENSIONS

HIGH_COMMUNICATION_OF_ONE_FUNCTION
!=
SUPERPOLYNOMIAL_PROOF_SIZE

PROOF_REACHABILITY
!=
PROOF_INFORMATION_RENEWAL

D6_CANDIDATE_MEASURE
!=
ER_LOWER_BOUND

P_VS_NP = OPEN
```
