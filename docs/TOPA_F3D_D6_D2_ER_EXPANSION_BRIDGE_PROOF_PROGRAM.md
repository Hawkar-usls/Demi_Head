# TOPA F3D-D6-D2 — ER Expansion Bridge Proof Program

**Frozen:** 2026-08-24  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Primary source:** Jan Krajíček, *Proof Complexity Generators*, Chapter 7, “The Case of ER”, Cambridge University Press, 2025.  
**Status:** `EXACT_ER_CRITERION_IMPORTED__NW_SPECIALIZATION_FROZEN__EXPANSION_THEOREM_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why D6-D2 exists

The D3–D6 line refuted a sequence of candidate lower-bound resources:

```text
per-macro survival,
semantic lifetime,
number of residual cofactors,
fixed-proof extension cutsets,
Boolean representation size of the global contradiction.
```

D6-D1 further proved, in the direct parity regime, that wrapping the whole formula into one polynomial-size global satisfaction circuit is only a polynomial ER/B2 re-encoding:

```text
F  <->_p  Def(G_F) union {G_F}.
```

The remaining target must therefore measure **derivational complexity of the proof system itself** and survive polynomial re-encodings.

Krajíček's 2025 Chapter 7 provides an exact criterion for ER hardness in terms of expansions of pseudofinite structures. D6-D2 specializes that criterion to the JANUS hard parity-NW family. No new ER lower bound is claimed here.

---

# 2. Frozen JANUS hard family

Let

```text
H'_NW = { F_n : n in I }
```

be the explicitly frozen infinite family of UNSAT direct parity-NW CNFs used by the established JANUS/Sokolov restricted lower-bound line, with all asymptotic parameters, graph existence conditions, forbidden outputs and direct-CNF encodings specified by the corresponding receipts.

Every `F_n` is a CNF in `UNSAT`.

ER refutations of `F_n` are equivalently ER proofs of the tautology

```text
not F_n.
```

Define

```text
not H'_NW := { not F : F in H'_NW }.
```

The global unrestricted target #217 is stronger than any local restricted theorem and asks, in effect, whether these or another explicit family can force superpolynomial ER/B2 resources.

---

# 3. Imported source theorem — exact criterion

Krajíček Theorem 7.2.1 states, for any `H' subseteq UNSAT`, an equivalence between:

1. `not H'` being hard for Extended Resolution; and
2. an expansion property for pseudofinite `L_ER` structures encoding formulas from `H'` and hypothetical short ER refutations.

The source construction represents a hypothetical ER refutation by an `L_ER` structure

```text
A_W = ([n], 0,1,<=, H, C, S),
```

where:

- `H` encodes the root CNF;
- the initial part `C_0` encodes all extension variables and their defining circuit;
- `C` extends `C_0` by circuit instructions evaluating proof clauses and prefix conjunctions along the refutation;
- `S` encodes the sequence used to enforce the proof/induction condition.

The expansion language adds an evaluation map `E`. The target theory `T'` requires, in source terms, that:

- `E` satisfies the encoded root formula;
- `E` respects all circuit instructions;
- `E` satisfies the required induction condition on the encoded proof sequence.

Theorem 7.2.1 makes existence of such expansions equivalent to ER hardness of the chosen formula set.

This theorem is imported as a literature result; JANUS does not re-prove it by CI.

---

# 4. D6-D2A — exact specialization to parity-NW

Instantiate Theorem 7.2.1 with

```text
H' := H'_NW.
```

Then:

```text
not H'_NW is hard for ER
```

if and only if the corresponding pseudofinite `L_ER` structures whose `H` relation encodes members of the parity-NW family satisfy the expansion criterion of Theorem 7.2.1.

### D6-D2A theorem

The unrestricted ER-hardness problem for the frozen parity-NW family can be transferred **exactly** to the Chapter-7 pseudofinite expansion problem.

This is a theorem-transfer specialization, not a proof that the expansion property holds.

---

# 5. Why the imported object survives our D6 falsifiers

## 5.1 Arbitrary extension reuse is internalized

The relation/circuit `C_0` contains all extension definitions of the hypothetical ER proof itself.

A parity circuit, inner-product circuit, global guard, long-lived macro or global satisfaction wrapper therefore does not sit outside the criterion. If a short proof uses it, it appears inside `C`.

Thus the criterion does not assume:

```text
short semantic lifetime,
few cofactors,
large representation complexity,
or a particular extension syntax beyond ER simulation.
```

## 5.2 Fixed-proof cutset decoration is irrelevant to the target

The criterion quantifies through ER proof length/hardness, not through centrality of one chosen proof DAG. Rewriting a proof so that an unnecessary extension appears syntactically central does not by itself alter whether polynomial-size ER proofs exist.

## 5.3 Polynomial global-circuit wrapping is absorbed

D6-D1 showed that, for the parity regime,

```text
F <->_p T_F := Def(G_F) union {G_F}.
```

A short ER proof after this wrapper is still a short ER proof represented by some `C` in the Chapter-7 structure. The expansion criterion targets the proof-system resource after re-encoding, not the apparent surface size of the CNF.

## 5.4 No general semantic classifier is required

The criterion is a mathematical existence statement about structures/expansions. It does not require JANUS to run the coNP-hard D1 exact semantic classifier on every extension node as an algorithmic step.

Therefore D1's complexity firewall is preserved.

---

# 6. D6-D2B — exact relation to #217

Recall the established JANUS chain:

```text
B2 refutations <->_p Extended Resolution
ER <->_p ER3
ER3 proof size is polynomially controlled by extension count K
once K itself is polynomially bounded.
```

Therefore an actual proof that `not H'_NW` is hard for ER would refute a universal polynomial ER3-extension-count theorem for this family and would close #217 negatively.

Conversely, a proof that #217's universal polynomial extension-count bound holds for all CNFs would imply polynomial ER proof size and hence would contradict ER-hardness of `H'_NW`.

### Claim boundary

```text
D6-D2 expansion criterion
!=
proof that H'_NW is ER-hard.
```

The new bridge gives a new exact target, not the target's solution.

---

# 7. The new expansion obligation

The next non-circular mathematical target is now:

### ER-EXP-NW

Find a non-standard model `M` of true arithmetic satisfying the exact condition in Theorem 7.2.1 such that every pseudofinite `L_ER` structure `A_W in M` with

```text
A_W |= T_ER
and
M |= alpha_H in H'_NW
```

has an expansion satisfying the source theory `T'`.

Equivalently, use the theorem's universal-model formulation if that is more convenient.

The expansion must handle **arbitrary circuit C coming from a hypothetical polynomial-size ER proof**. This is precisely what makes the target resistant to the D6 representation/reuse counterexamples.

---

# 8. Candidate bridge from the existing NW machinery — not assumed

The current JANUS/Sokolov line supplies strong combinatorial facts about parity-NW residual formulas:

- expansion of the dependency graph;
- exact self-reduction;
- residual parity balancedness;
- local-functional Resolution heavy-width lower bounds;
- exact direct-CNF to residual parity transfer.

These facts may help construct the required Chapter-7 expansion `E`, but no implication is automatic.

Freeze the required missing theorem:

```text
NW_COMBINATORIAL_SELF_REDUCTION
+
PARITY_RESIDUAL_HARDNESS

?=>

CHAPTER7_PSEUDOFINITE_ER_EXPANSION.
```

This implication is OPEN.

It is forbidden to claim that Sokolov heavy width already supplies the Chapter-7 expansion, because Sokolov controls Resolution over local functional variables while Chapter 7 must absorb arbitrary ER extension circuits.

---

# 9. Falsifier/admission suite for any proposed ER-EXP-NW construction

Any proposed expansion construction must survive all of the following.

## F-D6D2-01 — global parity reuse

`C` contains the O(n)-gate long-lived global parity network from D5. Expansion must still exist if the theorem is claimed universally.

## F-D6D2-02 — inner-product cofactor multiplexer

`C` contains the O(k)-gate inner-product network with exponentially many distinct cofactors. No counting of residual semantic classes may be used as if each required a new extension.

## F-D6D2-03 — global satisfaction wrapper

Replace root formula by the p-equivalent `T_F=Def(G_F) union {G_F}` from D6-D1. A valid invariant/expansion argument must not disappear merely because the surface encoding changed polynomially.

## F-D6D2-04 — decorative proof bottleneck

A proof circuit contains a dispensable crossing extension that is syntactically central. The construction may not infer proof-system necessity from this decoration.

## F-D6D2-05 — semantic-oracle laundering

No step may require a polynomial-time exact determination that an arbitrary extension circuit is constant/local/equivalent unless an appropriate certificate or restricted tractable subclass is proved.

## F-D6D2-06 — finite-to-nonstandard laundering

Finite CI/model experiments may test syntax and small instances only. They cannot establish the nonstandard expansion condition of Theorem 7.2.1.

---

# 10. D6-D2C — relation to proof complexity generators

Krajíček's broader framework studies proof-complexity generators and their hardness. Chapter 7 explicitly treats ER as the pivotal strong proof system and reformulates ER lower-bound questions by pseudofinite/Boolean-valued expansion methods.

JANUS may use this as a new research branch:

```text
PARITY-NW HARD FAMILY
-> tau/generator presentation where exact
-> ER expansion criterion
-> attempt expansion construction / obstruction.
```

However the fact that NW-type generators are candidates for strong proof-system hardness is not itself a hardness theorem for the JANUS parity family.

No generator-hardness claim is promoted without an exact theorem.

---

# 11. Relationship to actual P-vs-NP closure

A successful ER-EXP-NW theorem proving superpolynomial ER hardness would be a major proof-complexity breakthrough and would close the current B2/#217 route negatively.

It would **not by itself** set

```text
P_VS_NP = CLOSE__P_NOT_EQUAL_NP.
```

As emphasized in the 2025 source, it is not known that ER not p-bounded implies `NP != coNP`, hence certainly no direct implication to `P != NP` may be assumed.

The constructive Policy-0B branch remains the route that could yield `P=NP` if proof-object viability, representation size, deterministic discovery and total runtime are all proved polynomial.

---

# 12. Exit criteria

```text
D6-D2-E1 exact Theorem-7.2.1 object map frozen            = PASS
D6-D2-E2 specialization H'=H'_NW                          = PASS
D6-D2-E3 D3-D6 falsifier compatibility written            = PASS
D6-D2-E4 exact NW -> Chapter7 expansion theorem            = OPEN / KILLER GATE
D6-D2-E5 finite mechanics fixture                           = OPTIONAL / NON-PROVING
D6-D2-E6 ER-hardness conclusion                             = BLOCKED BY E4
D6-D2-E7 #217 negative closure                              = BLOCKED BY E4
P_VS_NP                                                     = OPEN
```

---

# 13. Claim firewall

```text
ER_EXPANSION_CRITERION
!=
ER_EXPANSION_PROPERTY_PROVED

PSEUDOFINITE_REFORMULATION
!=
FINITE_ALGORITHM

NW_LOCAL_HEAVY_WIDTH
!=
FULL_ER_EXPANSION

ER_HARDNESS
!=
P_NOT_EQUAL_NP

D6_D2_BRIDGE
!=
P_VS_NP_CLOSE

P_VS_NP = OPEN
```
