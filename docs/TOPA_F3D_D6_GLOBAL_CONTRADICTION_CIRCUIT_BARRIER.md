# TOPA F3D-D6 — Global Contradiction Circuit: Representation != Derivation

**Frozen:** 2026-08-24T23:35:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Status:** `GLOBAL_SEMANTIC_REPRESENTATION_BARRIER_EXPOSED`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Question

After D5/D6 refuted lifetime, cofactor-count and fixed-proof-cutset amortization, one might hope to prove that a polynomial number of extension gates cannot even represent the global semantic object needed to compress the hard NW contradiction.

For parity-NW this hope is false.

## 2. Polynomial B2 circuit for every individual constraint

Let the direct parity-NW formula contain output constraints

```text
PARITY(N(i)) = b_i,
for i=1,...,m,
```

with left degree at most `Delta`.

Using the standard frozen-B2 XOR gadget, compute the parity of the `Delta` (or fewer) neighborhood variables in `O(Delta)` AND-extension gates. Complement if necessary according to `b_i`.

Let

```text
g_i(x)=1
```

iff the i-th output constraint is satisfied.

Total extension gates for all `g_i` are

```text
O(m*Delta).
```

## 3. Polynomial global satisfaction circuit

Aggregate the constraint bits with a binary AND tree:

```text
G_F(x)
:= AND_{i=1}^m g_i(x).
```

This costs another `m-1` frozen-B2 gates.

Therefore the whole global formula-satisfaction predicate has a B2 representation of size

```text
K_global = O(m*Delta).
```

In the frozen polynomial-input parity regime this is polynomial in the original encoded input length.

## 4. The output is identically zero on the hard instance

The PRG formula states that the forbidden output string `b` is in the image of the NW map.

For `b` outside the image, no root assignment satisfies all output constraints. Hence

```text
for every root assignment x:
G_F(x)=0.
```

Thus

```text
G_F ≡ CONST_0.
```

A polynomial-size extension circuit can therefore represent the **entire global contradiction predicate**.

## 5. Why this is not a polynomial ER refutation

Frozen extension axioms are conservative definitions. Introducing `G_F` proves only that the new variable equals the named circuit function.

The proof must still derive a clause forcing

```text
~G_F
```

(or otherwise derive the empty clause from the root formula plus definitions).

The fact

```text
G_F ≡ 0
```

is exactly a global semantic UNSAT fact. D1 already exposes that constant-zero recognition for general B2 circuits is coNP-complete and is not a free polynomial-time semantic operation.

Therefore:

```text
SMALL_GLOBAL_CIRCUIT
!=
SHORT_PROOF_OF_ITS_FORCED_VALUE.
```

## 6. D6-C theorem — representation-only lower-bound routes are blocked

Any proposed unrestricted-ER extension-count lower bound based solely on one of the following is insufficient for this parity-NW family:

- inability to represent the conjunction of all constraints;
- inability to define one global semantic macro;
- size of the Boolean circuit computing formula satisfaction;
- semantic support/globality of the named contradiction predicate.

All of these admit an `O(m*Delta)` frozen-B2 circuit.

The remaining resource is **derivational**:

> how expensive is it in Resolution + extension axioms to derive the logically forced consequence `~G_F` (or an equivalent contradiction) from the root axioms?

## 7. Exact relation to the ER frontier

A short derivation of the required forced value, together with the polynomial extension circuit above, would constitute a short Extended-Resolution-style refutation.

A superpolynomial lower bound on all such derivations is therefore not a mere Boolean representation lower bound; it is the Extended Resolution proof-size problem itself.

This explains why purely semantic/circuit-description counting kept failing in D3–D6.

## 8. Implication for the next front

The next admissible object must measure **derivational compression**, not semantic representation.

Candidate question:

```text
Given a polynomial-size conservative extension circuit C(x)
whose value is logically forced by root CNF F,
what is the minimum Resolution derivation cost of the forced output clause
from F plus the extension definitions?
```

For the global satisfaction circuit `G_F`, the target clause is `~G_F`.

Any tractable special-case theorem must state its restriction explicitly; the unrestricted version is already at the ER proof-complexity frontier.

## 9. Claim firewall

```text
GLOBAL_CONTRADICTION_HAS_SMALL_CIRCUIT
!=
GLOBAL_CONTRADICTION_HAS_SMALL_ER_PROOF

SEMANTIC_CONST_0
!=
CHEAP_CONST_0_DERIVATION

REPRESENTATION_COMPLEXITY
!=
DERIVATIONAL_COMPLEXITY

D6_C_BARRIER
!=
ER_LOWER_BOUND

P_VS_NP = OPEN
```
