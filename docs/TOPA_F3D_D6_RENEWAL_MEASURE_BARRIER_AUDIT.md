# TOPA F3D-D6 — Renewal Measure Barrier Audit

**Frozen:** 2026-08-24T23:25:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D5_PARITY_LIFETIME_REUSE_BARRIER.md`  
**Status:** `D6_COFACTOR_AND_FIXED_PROOF_CUTSET_ROUTES_REFUTED__PROOF_SYSTEM_RELATIVE_MEASURE_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Goal

D5 refuted raw semantic lifetime as an amortization resource: one small global circuit can remain crossing through all hard residual stages.

D6 asks whether repeated restrictions force a genuinely renewed proof resource that can be charged to distinct extension gates rather than repeatedly charging the same reusable global circuit.

Two naive routes are now refuted.

## 2. D6-A — inner-product cofactor counterexample

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

### Theorem D6-A

```text
EXPONENTIALLY_MANY_DISTINCT_RESIDUAL_FUNCTIONS
!=
EXPONENTIALLY_MANY_EXTENSION_GATES.
```

A lower bound based only on counting distinct cofactor/semantic classes cannot force superpolynomial extension count.

## 3. Why D6-A is stronger than the earlier flat-case barrier

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

## 5. D6-B1 — fixed-proof extension cutset is not proof-system necessity

Define a tempting syntactic measure on one chosen proof DAG:

```text
CUT_EXT(P)
:= minimum number of crossing extension definitions whose removal
   disconnects the used derivation from root axioms to the empty clause.
```

This is a property of a representation of one proof, not automatically of the root formula or proof system.

### Exact frozen-calculus counterfixture

Use root CNF

```text
{x}
{~x}
{y}
```

and locality neighborhoods

```text
{x}, {y}.
```

The formula has the direct zero-extension Resolution refutation

```text
x, ~x -> empty.
```

Now introduce the crossing frozen-B2 extension

```text
e <-> (x AND y).
```

Its exact defining clauses include

```text
~e OR x
~e OR y
e OR ~x OR ~y.
```

A second exact Resolution refutation is:

```text
(e OR ~x OR ~y), x -> (e OR ~y)
(e OR ~y), y       -> e
(~e OR x), ~x      -> ~e
e, ~e              -> empty.
```

In this chosen proof `e` is an obvious one-extension bottleneck and is semantically crossing because its support `{x,y}` is not contained in either locality block.

But the same root CNF has a shorter proof with **no extensions at all**.

### Theorem D6-B1

A crossing-extension cutset of a chosen proof DAG is not a lower bound on extension resources necessary for the formula:

```text
CUTSET_OF_ONE_PROOF
!=
MINIMUM_EXTENSION_RESOURCE_OVER_ALL_PROOFS.
```

Syntactic routing can make a dispensable extension look globally central.

## 6. Consequence for any repaired cutset measure

To turn B1 into a proof-complexity invariant one would need to minimize over alternative proofs, for example

```text
CUT*_B(F)
:= min CUT_EXT(P)
   over all refutations P of F with size <= B.
```

This is mathematically well-defined, but it now quantifies over the very space of short proofs whose complexity JANUS is trying to lower-bound.

Therefore it may be useful as a target quantity but cannot be assumed to provide an easier route. Its algorithmic computation/search cost is not free and its lower bound may be essentially equivalent to a proof-complexity lower-bound problem.

## 7. Proof reachability is not proof utility

D4 correctly prunes definitions unreachable from the final residual refutation.

D6-B1 shows that even reachability/centrality in the selected derivation is not the same as necessity across alternative proofs.

Freeze:

```text
PROOF_REACHABLE
!=
FORMULA_NECESSARY

DERIVATION_BOTTLENECK
!=
PROOF_SYSTEM_BOTTLENECK.
```

## 8. Surviving D6 candidates

### B2 — budgeted indispensability

For size budget `B`, minimum extension resource required by **any** refutation of the residual formula of size at most `B`.

This has the right proof-system quantifier but may simply repackage the target lower-bound problem.

### B3 — partition-profile complexity

Associate to each used extension function a vector of communication/information values over the relevant NW output partitions and seek a direct-sum theorem for a complete residual refutation.

A scalar value is insufficient; a genuine proof-relative composition theorem is required.

### B4 — semantic influence on source heavy width

Measure how availability of a set of arbitrary B2 circuits changes the minimum achievable heavy width of refutations of the source formula.

This aligns most directly with Sokolov's invariant but requires extending the heavy-width formalism beyond local functional variables to arbitrary circuits.

## 9. Exact next decision

```text
D6-A cofactor-count renewal                  = REFUTED
D6-B1 fixed-proof extension cutset            = REFUTED
D6-B2 budgeted proof-system indispensability  = OPEN / POSSIBLY CIRCULAR
D6-B3 partition-profile direct sum            = OPEN
D6-B4 generalized heavy-width influence       = OPEN / PREFERRED NEXT FORMALIZATION
```

Preferred next move:

```text
Define B4 without heuristic semantics and ask whether one K-gate global extension circuit
can reduce source heavy-width obstruction by more than poly(K).
```

If a bound of the form

```text
HEAVY_WIDTH_DAMAGE <= poly(K)
```

survives adversarial testing, it could connect the source lower bound directly to extension count without lifetime summation.

No such bound is currently claimed.

## 10. Claim firewall

```text
MANY_COFACTORS
!=
MANY_EXTENSIONS

HIGH_COMMUNICATION_OF_ONE_FUNCTION
!=
SUPERPOLYNOMIAL_PROOF_SIZE

PROOF_REACHABILITY
!=
PROOF_SYSTEM_NECESSITY

CUTSET_OF_ONE_DERIVATION
!=
MINIMUM_CUTSET_OVER_REFUTATIONS

D6_CANDIDATE_MEASURE
!=
ER_LOWER_BOUND

P_VS_NP = OPEN
```
