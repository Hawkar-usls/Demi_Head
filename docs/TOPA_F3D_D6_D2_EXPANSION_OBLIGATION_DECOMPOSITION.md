# TOPA F3D-D6-D2 — Expansion Obligation Decomposition

**Frozen:** 2026-08-24  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Primary source:** Jan Krajíček, *Proof Complexity Generators*, Chapter 7, 2025.  
**Parent:** `TOPA_F3D_D6_D2_ER_EXPANSION_BRIDGE_PROOF_PROGRAM.md`  
**Status:** `EXPANSION_OBLIGATIONS_DECOMPOSED__MODEL_EXTENSION_CORE_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Purpose

Theorem 7.2.1 expresses ER hardness through existence of an expansion by an evaluation map `E` satisfying three source obligations:

```text
(E-H) E satisfies root CNF H;
(E-C) E respects every instruction of circuit C;
(E-S) the image of proof sequence S under E satisfies the induction axiom.
```

At first sight these look like three separate hard construction problems.

The source proof of `hardness -> expansion` shows they are not independent once the correct model extension has been obtained.

---

# 2. Source decomposition

Assume the source hard-set hypothesis and let `A_W` be a pseudofinite `L_ER` structure in a nonstandard model `M` as in Theorem 7.2.1.

The proof passes to the canonical small model `M_m` and uses the absence of a short ER refutation to obtain an extension

```text
M' |= PV1
```

in which the encoded root formula `alpha_H` is satisfied by a truth assignment

```text
e in M'.
```

The source then states two consequences.

## 2.1 Circuit evaluation is determined

Because `PV1` holds in `M'`, the root evaluation `e` extends to a **unique evaluation of circuit C**.

Thus `(E-C)` is not a second independent search once the model and root assignment exist.

Freeze:

```text
PV1_MODEL_EXTENSION + ROOT_ASSIGNMENT
=> UNIQUE_CIRCUIT_EVALUATION.
```

## 2.2 Sequence induction follows from the ambient theory

The proof has `S` already inside the canonical model and hence inside `M'`. Since `PV1` proves open induction, the required `S`-induction axiom is satisfied in the expansion.

Thus `(E-S)` is also not an independent combinatorial search in this route.

Freeze:

```text
PV1_MODEL_EXTENSION + S_IN_MODEL
=> REQUIRED_OPEN_INDUCTION_ON_S.
```

---

# 3. D6-D2-O theorem — one genuine core obligation

For the Chapter-7 ordinary-structure route, once one has an appropriate extension `M'` satisfying the source arithmetic theory and a truth assignment `e` satisfying the encoded root CNF `H`, the circuit-evaluation and proof-sequence-induction components of the expansion follow by the source argument.

Therefore the genuinely new obstruction can be isolated as:

```text
MODEL-EXTENSION CORE:
construct / guarantee the required theory-preserving extension
in which the pseudofinite UNSAT formula H acquires a satisfying assignment.
```

This is a decomposition of the imported criterion, not a proof that the core obligation is satisfiable for the parity-NW family.

---

# 4. Why finite self-reduction does not solve the core

Every standard finite member of `H'_NW` is UNSAT. A standard finite root assignment cannot satisfy it.

Sokolov self-reductions produce smaller residual UNSAT PRG instances and prove Resolution lower bounds for those finite objects; they do not produce a standard satisfying assignment to the original hard CNF.

Hence:

```text
FINITE_SOURCE_SELF_REDUCTION
!=
NONSTANDARD_MODEL_EXTENSION_SATISFYING_H.
```

Any attempted D6-D2 bridge that simply turns a random/self-reduced finite restriction into `E` fails by object type before proof details are considered.

This is an exact theorem-transfer firewall.

---

# 5. Boolean-valued route

Krajíček Theorem 7.3.1 gives a more flexible sufficient condition:

1. construct a Boolean-valued elementary extension `K` of the original `L_ER` structure;
2. expand `K` by an evaluation `E` so that every axiom of `T'` has Boolean truth value `1`.

This route explicitly allows the required satisfaction/evaluation object to live in a Boolean-valued extension rather than as a standard finite assignment.

For JANUS this suggests the exact new branch:

```text
D6-D2-BV:
Can the parity-NW pseudofinite ER structures be embedded into a
Boolean-valued structure in which the root-satisfaction component
and therefore the full T' expansion can be realized?
```

No such construction is currently proved.

---

# 6. Admission consequences

Future proposals must classify which layer they address.

### TYPE-A — finite combinatorial result
Examples: expansion, balancedness, restrictions, parity residuals.

These can constrain the encoded `H` but do not themselves satisfy the model-extension core.

### TYPE-B — model-extension theorem
A theorem producing the required nonstandard/Boolean-valued satisfying environment for `H`.

This can close D6-D2-E4 if all Chapter-7 hypotheses are matched.

### TYPE-C — circuit/proof evaluation mechanics
Once TYPE-B supplies the correct environment, source theory already provides the continuation to `C` and `S`; a separate asymptotic lower-bound argument is not needed for these two parts.

---

# 7. New exact killer gate

Replace the vague gate

```text
NW -> Chapter7 expansion
```

by the narrower gate:

```text
ER-EXP-NW-CORE:
Find the required nonstandard or Boolean-valued model extension
for every relevant pseudofinite parity-NW L_ER structure,
with the encoded H satisfiable in the extension,
while preserving T_ER / elementary-extension obligations.
```

If this is proved in the form required by Theorem 7.2.1 or 7.3.1, the remainder of the source expansion argument supplies circuit evaluation and sequence induction.

---

# 8. Hidden-exponent firewall

The core is a mathematical existence theorem, not automatically an algorithm.

Even a successful model-extension proof would establish ER hardness through the Chapter-7 theorem, not provide a polynomial-time constructor of the extension.

Therefore:

```text
MODEL_EXTENSION_EXISTS
!=
POLYTIME_MODEL_EXTENSION_CONSTRUCTION.
```

For the negative ER-lower-bound route the existence theorem is sufficient. For the constructive `P=NP` route it is not a solver primitive.

---

# 9. Status

```text
D6-D2 exact ER expansion criterion specialized to H'_NW = PASS
D6-D2 obligation decomposition                         = PROVED
D6-D2 circuit evaluation once model exists             = SOURCE-PROVED
D6-D2 sequence induction once PV1 model exists          = SOURCE-PROVED
D6-D2 finite self-reduction -> model extension           = REFUTED AS DIRECT OBJECT TRANSFER
D6-D2 ER-EXP-NW-CORE                                    = OPEN / NEXT
D6-D2 Boolean-valued route                              = OPEN / NEXT
ER hardness of H'_NW                                    = OPEN
Issue #217                                              = OPEN
P_VS_NP                                                 = OPEN
```

---

# 10. Claim firewall

```text
OBLIGATION_DECOMPOSITION
!=
MODEL_EXTENSION_CONSTRUCTION

FINITE_RESTRICTION
!=
NONSTANDARD_SATISFYING_ASSIGNMENT

BOOLEAN-VALUED_ROUTE_IDENTIFIED
!=
BOOLEAN-VALUED_EXPANSION_PROVED

ER_EXPANSION_CORE
!=
P_VS_NP_CLOSE

P_VS_NP = OPEN
```
