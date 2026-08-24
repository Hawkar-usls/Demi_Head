# TOPA F3D-D6-D1 — Global Satisfaction Circuit Re-encoding Equivalence

**Frozen:** 2026-08-24T23:45:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D6_GLOBAL_CONTRADICTION_CIRCUIT_BARRIER.md`  
**Status:** `POLYNOMIAL_REENCODING_EQUIVALENCE_PROVED_IN_DIRECT_PARITY_REGIME`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Objects

Let `F` be the direct truth-table CNF of a parity-NW instance:

```text
F = AND_i F_i,
```

where `F_i` encodes the parity equation on one neighborhood of size at most `Delta`.

Construct a frozen-B2 circuit `G_F`:

1. for every output `i`, a circuit `g_i` computes whether the parity equation `F_i` is satisfied;
2. a binary AND tree computes

```text
G_F = AND_i g_i.
```

Let `Def(G_F)` be the exact conservative B2 definitional CNF for all circuit gates.

Define the circuit-output encoding

```text
T_F := Def(G_F) union {G_F}.
```

`T_F` asserts that the global satisfaction circuit outputs 1.

For an UNSAT hard instance, both `F` and `T_F` are UNSAT.

## 2. Size of the circuit encoding

Each parity satisfaction bit uses `O(Delta)` frozen-B2 gates with the standard XOR construction. The final AND tree uses `O(m)` gates.

Hence

```text
|Def(G_F)| = O(m*Delta)
```

clauses/gates up to fixed constants.

In the direct parity regime `F` already has roughly `m*2^Delta` truth-table clauses, so `T_F` is polynomially bounded in the original encoded input length.

## 3. Translation A — from a refutation of T_F to a refutation of F

Assume a B2/ER refutation `Pi_T` of `T_F`.

To use it under root CNF `F`, derive the unit `G_F` from `F` plus the same circuit definitions.

### 3.1 Derive each local satisfaction bit g_i

`F_i` semantically forces `g_i=1`.

Because the parity neighborhood and its local circuit use only `O(Delta)` Boolean variables/gates, there is an explicit exhaustive Resolution derivation of `g_i` from

```text
F_i union Def(g_i)
```

of size

```text
2^O(Delta).
```

One construction is to refute `F_i union Def(g_i) union {~g_i}` by complete branching on the `O(Delta)` local root/gate variables and reverse-lift the final conflict over the assumption `~g_i`.

This is a proof-existence/translation statement with explicit cost, not a free semantic oracle.

### 3.2 Assemble G_F

For every AND gate

```text
p <-> (a AND b)
```

the defining clause

```text
p OR ~a OR ~b
```

plus units `a,b` yields unit `p` by two Resolution steps.

Thus all leaf units `g_i` derive `G_F` through the AND tree in `O(m)` additional steps.

### 3.3 Graft

Replace the root unit `{G_F}` used by `Pi_T` with the derivation above. All other `Def(G_F)` axioms are legal extension definitions in the B2/ER proof of `F`.

Therefore

```text
size_ER(F)
<= size_ER(T_F) + m*2^O(Delta).
```

## 4. Translation B — from a refutation of F to a refutation of T_F

Assume a B2/ER refutation `Pi_F` of the direct CNF `F`.

We derive every direct root clause of every `F_i` from `T_F` with polynomial overhead, then graft `Pi_F`.

### 4.1 Push G_F=1 down to every g_i=1

For an AND definition

```text
p <-> (a AND b),
```

the defining clauses include

```text
~p OR a
~p OR b.
```

Unit `p` therefore derives both child units in one Resolution step each.

Starting from root unit `G_F`, descend the AND tree to derive every `g_i` in `O(m)` steps.

### 4.2 Derive one truth-table clause of F_i

Fix one assignment `alpha` to the neighborhood of output `i` that violates its parity equation. Let `C_alpha` be the direct blocking clause falsified exactly by `alpha`.

Under assumptions fixing the roots according to `alpha`, deterministic unit evaluation of the local parity circuit plus unit `g_i` reaches a conflict because the circuit computes `g_i=0` on `alpha`.

Reverse unit-conflict lifting eliminates the temporary root assumptions and derives the globally implied clause

```text
C_alpha
```

from

```text
Def(g_i) union {g_i}.
```

The proof uses `O(poly(Delta))` local Resolution nodes for this one assignment.

There are exactly `2^(d_i-1)` violating assignments for a `d_i`-variable parity constraint, hence all clauses of `F_i` are derived in

```text
2^O(Delta)
```

steps.

Across all outputs:

```text
all root clauses of F
```

are derivable from `T_F` in

```text
m*2^O(Delta)
```

Resolution work.

### 4.3 Graft

Replace every root-axiom occurrence of `Pi_F` by the corresponding derivation from `T_F`. Hence

```text
size_ER(T_F)
<= size_ER(F) + m*2^O(Delta).
```

## 5. D6-D1 theorem

Combining both directions:

```text
size_ER(F)
<= size_ER(T_F) + m*2^O(Delta)
```

and

```text
size_ER(T_F)
<= size_ER(F) + m*2^O(Delta).
```

Therefore in any regime with

```text
Delta = O(log n)
```

and `m=poly(n)`, the direct parity CNF and the global-circuit output encoding are p-equivalent under B2/Extended Resolution:

```text
F  <=>_p  Def(G_F) union {G_F}.
```

The translation polynomial has a universal fixed exponent once the asymptotic constants in `Delta<=C log n` and `m<=n^c` are frozen.

## 6. Interpretation

The global satisfaction circuit compresses the **description** of the conjunction of all parity constraints, but it does not remove proof complexity.

The hard fact simply moves to:

```text
Def(G_F) union {G_F} is UNSAT.
```

Additional extension variables may then compress this new refutation, exactly as they could compress the original one.

Thus recursively introducing a global contradiction circuit is a polynomial re-encoding of the same ER problem, not a shortcut around it.

## 7. Consequence for D6

The remaining unrestricted question cannot be solved by semantic representation alone.

Any proposed derivational invariant must be stable under polynomial re-encodings such as

```text
F <->_p T_F,
```

otherwise a global circuit wrapper merely moves the apparent obstruction to another representation.

This is a strong filter for future D6 measures.

## 8. Claim firewall

```text
POLYNOMIAL_REENCODING_EQUIVALENCE
!=
POLYNOMIAL_REFUTATION

GLOBAL_OUTPUT_ENCODING_SMALL
!=
DERIVATION_SMALL

F <->_p T_F
!=
ER_P_BOUNDED

D6_D1
!=
P_VS_NP_RESOLUTION

P_VS_NP = OPEN
```
