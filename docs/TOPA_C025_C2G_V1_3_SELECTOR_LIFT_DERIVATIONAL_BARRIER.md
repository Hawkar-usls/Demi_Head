# TOPA C025-C2G v1.3 — Selector-Lift Derivational Barrier

**Frozen:** 2026-08-24T23:17:00+03:00  
**Parent:** `TOPA_C025_C2G_V1_2_LAMINAR_FORK_CHARGE.md`  
**Status:** `SHORT_LAMINAR_REASON_GEOMETRY_DOES_NOT_REMOVE_DERIVATIONAL_HARDNESS`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Purpose

C2G v1.2 proves a useful counting theorem: if actual binary forks can be charged to fresh laminar root reasons of width `O(log N)`, then the explored state count is polynomial.

The next question is whether short width and laminar geometry make those reasons cheap to prove/discover.

They do not.

This note isolates the derivational barrier by a selector lift.

---

# 2. Selector-lift construction

Let

```text
H = {C_1,...,C_m}
```

be any CNF over root variables `X`.

Introduce one fresh root variable `s` and define

```text
Sel_s(H) := { (s OR C_i) : i=1,...,m }.
```

The lifted formula is always satisfiable by setting `s=1`.

### Theorem C2G-S1 — unit implicate equivalence

```text
Sel_s(H) |= s
iff
H is UNSAT.
```

**Proof.**

If `H` has a model `alpha`, then `s=0` together with `alpha` satisfies every `(s OR C_i)`, so the lifted formula does not imply `s`.

If `H` is UNSAT`, then no model of `Sel_s(H)` can set `s=0`, because restriction `s=0` yields exactly `H`. Hence every model has `s=1`. □

Therefore deciding whether the width-1 clause `(s)` is a valid root reason for `Sel_s(H)` is coNP-complete under the usual polynomial reduction from CNF-UNSAT.

The lifted formula is SAT; the hardness is entirely in recognizing/proving the forced selector value.

---

# 3. Plain-Resolution derivational equivalence

Let `pi` be a Resolution refutation of `H`.

Replace every root clause `C_i` in `pi` by `(s OR C_i)` and every derived clause `D` by `(s OR D)`.

Resolution is preserved:

```text
(s OR A OR x), (s OR B OR ~x)
--------------------------------
          (s OR A OR B).
```

The final empty clause of `pi` becomes the unit clause `(s)`.

Thus a Resolution refutation of `H` of size `L` yields a Resolution derivation

```text
Sel_s(H) |- s
```

with linear overhead.

Conversely, restrict any Resolution derivation of `(s)` from `Sel_s(H)` by `s=0`. Root axioms become exactly the clauses of `H`, Resolution is closed under restrictions, and the final unit `(s)` becomes the empty clause.

Hence the minimum proof lengths are equivalent up to ordinary linear/constant representation overhead.

### C2G-S2

```text
RES_SIZE(H |- contradiction)
<->_poly
RES_SIZE(Sel_s(H) |- s).
```

A width-1 conclusion may therefore require all the derivational work of the original refutation.

---

# 4. B2 / Extended-Resolution version

The same selector lift is compatible with the frozen B2 / ER language.

## Reverse direction

Any accepted B2/ER proof

```text
Sel_s(H) |- s
```

restricts under `s=0` to an ER refutation of `H`:

- lifted root clauses become `H`;
- conservative extension definitions restrict to valid extension definitions / simplified Boolean identities;
- Resolution steps restrict soundly;
- final `(s)` becomes the empty clause.

## Forward direction

Given an ER refutation of `H`, retain the same extension definitions. Lift the root-dependent Resolution derivation by adjoining `s` to the clauses descended from root axioms. Extension axioms need not be lifted; resolving a clause carrying `s` with an extension axiom preserves `s` in the resolvent. Conservative extension axioms alone cannot refute a satisfiable empty-root theory, so the root-dependent contradiction path yields the final unit `(s)`.

After ordinary DAG cleanup this translation has polynomial overhead.

### C2G-S3 — selector proof equivalence in the current strong reason language

Up to the already frozen polynomial encodings,

```text
B2/ER_REFUTATION_SIZE(H)
<->_poly
B2/ER_DERIVATION_SIZE(Sel_s(H) |- s).
```

This does not prove either side superpolynomial; it identifies the same proof-complexity resource.

---

# 5. Consequence for C2G v1.2

For a selector fork on `s`:

- first child `s=0` is exactly `H`;
- if `H` is UNSAT, the ideal charge clause is the width-1 reason `(s)`;
- its falsifying cube is a half-cube and has perfect compact geometry;
- with one fork, laminarity is trivial.

Nevertheless constructing the proof certificate for `(s)` can require the full B2/ER derivational complexity of `H`.

Thus:

```text
WIDTH / LAMINAR GEOMETRY
```

and

```text
DERIVATIONAL COMPLEXITY
```

are independent gates.

---

# 6. Exact complexity consequence for a total discovery oracle

Consider a deterministic total procedure

```text
DISCOVER_SELECTOR_REASON(H)
```

that, in time polynomial in `|H|`:

- returns a verifier-accepted proof of `Sel_s(H) |= s` when the implication is true;
- returns `NONE` when it is false.

By C2G-S1 this decides CNF-UNSAT in polynomial time.

Therefore such a universal total exact selector-reason discovery procedure would imply

```text
coNP subseteq P,
```

and hence

```text
P = NP = coNP.
```

### C2G-S4 — discovery closure implication

A universal deterministic polynomial-time exact discovery algorithm even for this **width-1 selector-reason subclass** is already strong enough to imply `P=NP`.

This is an implication theorem, not evidence that such an algorithm exists.

---

# 7. Impact on the project closure map

C2G has now cleanly separated three resources:

```text
GEOMETRY:
laminar O(log N)-width charges -> polynomial number of forks

PROOF SIZE:
short charge clause does not imply short proof certificate

DISCOVERY:
short proof existence does not imply deterministic polynomial extraction
```

The selector lift shows the latter two are not secondary engineering details. They already contain the original complexity problem in a width-1 special case.

---

# 8. Scientific next front

The constructive route can no longer hope to prove `P=NP` merely by finding a clever universal charge geometry.

The next admissible questions are:

1. Does Policy-0B have a special **syntactic/proof-producing invariant** that constructs selector-like conflict proofs directly without solving arbitrary ER proof search?
2. Can one prove a globally polynomial bound on the derivation ledger produced by the exact machine, not merely on clause width?
3. Can deterministic conflict analysis be shown to satisfy a structural direct-progress theorem that bypasses generic proof enumeration?

Any positive answer strong enough for arbitrary selector lifts would itself constitute progress directly toward `P=NP` and must be evaluated at that claim scale.

---

# 9. Status

```text
C2G_SELECTOR_UNIT_IMPLICATE_RECOGNITION       = coNP-COMPLETE
C2G_PLAIN_RES_SELECTOR_PROOF_EQUIVALENCE      = PROVED
C2G_B2_ER_SELECTOR_PROOF_EQUIVALENCE          = PROVED_UP_TO_FROZEN_POLY_ENCODING
C2G_WIDTH1_REASON_CAN_HIDE_FULL_PROOF_COST     = PROVED
C2G_POLY_TOTAL_SELECTOR_DISCOVERY_IMPLIES_PNP = PROVED_AS_IMPLICATION
C2G_UNIVERSAL_POLY_DISCOVERY                   = OPEN
P_VS_NP                                       = OPEN
```

---

# 10. Claim firewall

```text
DISCOVERY_WOULD_IMPLY_P_EQUALS_NP
!=
DISCOVERY_EXISTS

WIDTH_1_REASON
!=
SHORT_PROOF

SHORT_PROOF
!=
CHEAP_DISCOVERY

SELECTOR_REDUCTION
!=
P_EQUALS_NP_PROOF

P_VS_NP = OPEN
```
