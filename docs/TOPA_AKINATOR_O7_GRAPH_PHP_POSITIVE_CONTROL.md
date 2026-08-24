# TOPA / JANUS — Akinator O7 Graph-PHP Constructive Positive Control

**Frozen:** 2026-08-25  
**Status:** `ANALYTICAL_CONSTRUCTION_FROZEN__FINITE_REPLAY_PENDING`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Purpose

O5/plain Resolution is superpolynomial on the expander graph-PHP separator. This note asks whether O7, the B2/Extended-Resolution proof-carrying rung, can escape on the **same canonical family** without hiding an oracle in extension discovery.

The answer in the stated canonical graph-PHP scope is constructive: yes. The escape is family-specific and does **not** solve universal extension discovery for arbitrary CNF.

---

## 1. External source theorem: Cook PHP ER construction

Cook's classical Extended Resolution construction gives polynomial-size refutations of the standard pigeonhole principle. A modern explicit description is given by Grosof, Zhang and Heule, *Towards the shortest DRAT proof of the Pigeonhole Principle* (2022): Cook's proof has `O(n^4)` clauses and recursively reduces `PHP(n)` to `PHP(n-1)` using definitions

```text
x'_{ph} <-> x_{ph} OR (x_{nh} AND x_{pn}).
```

The proof schema is explicit and indexed by polynomially many pigeon/hole tuples, so the classical family is not merely existential: its proof skeleton is deterministically generable in polynomial time.

Source:
- https://arxiv.org/abs/2207.11284
- see its discussion of Cook's construction and Equation (2).

This source theorem is not a theorem about arbitrary CNFs.

---

## 2. Cook macro in frozen B2

Frozen B2 permits fresh extension variables of the form

```text
e <-> (a AND b)
```

for signed literals `a,b` with distinct variable ids and topological freshness.

For

```text
x' = a OR (b AND c)
```

introduce

```text
t <-> (b AND c)
u <-> ((NOT a) AND (NOT t))
```

and represent `x'` by the signed literal `NOT u`.

Indeed

```text
NOT u = NOT((NOT a) AND (NOT t)) = a OR t = a OR (b AND c).
```

Thus every Cook recursive macro has constant B2 extension overhead. In the PHP indexing, `b=x_{nh}` and `c=x_{pn}` are distinct variables, so the B2 distinct-operand gate is respected.

The number of recursive macro definitions is polynomial (`O(n^3)` across all reduction layers); the source proof has polynomial total derivation size (`O(n^4)` in Cook's construction).

---

## 3. Why arbitrary restriction closure is NOT imported

Graph-PHP is syntactically the restriction of full PHP obtained by setting every non-edge variable `x_{ph}` to false. However, Extended Resolution / Extended Frege do not satisfy the strongest generic closure-under-restrictions property merely by definition. We therefore do **not** infer the graph-PHP result from a free restriction oracle.

Reference for this firewall:
- Emre Yolcu et al., *Exponential separations using guarded extension variables* (discussion of strong closure under restrictions and Extended Frege/Extended Resolution).
- https://emreyolcu.com/research/guarded-extension.pdf

Instead we construct the missing false variables inside B2 and use an explicit strengthening simulation.

---

## 4. B2 FALSE gadget respecting `abs(a) != abs(b)`

Choose two distinct surviving root variables `a,b`. Introduce

```text
t1 <-> (a AND b)
t2 <-> ((NOT a) AND b)
z0 <-> (t1 AND t2)
```

Semantically `z0=0` for every root assignment.

More importantly, `NOT z0` has a short pure-Resolution derivation from the extension clauses:

```text
(NOT z0 OR t1), (NOT t1 OR a)
    -> (NOT z0 OR a)

(NOT z0 OR t2), (NOT t2 OR NOT a)
    -> (NOT z0 OR NOT a)

resolve on a
    -> (NOT z0)
```

For every missing edge variable create a distinct placeholder

```text
m_{ph} <-> (z0 AND a)
```

and derive `(NOT m_{ph})` from `(NOT z0)` and `(NOT m_{ph} OR z0)`.

This uses `O(n^2)` B2 extensions in the worst case and is fully deterministic.

---

## 5. Full-PHP axioms receive stronger graph-derived substitutes

Treat each allowed edge variable as the original graph-PHP root variable and each non-edge variable as its false placeholder `m_{ph}`.

For every full PHP pigeon axiom

```text
x_{p1} OR ... OR x_{pn},
```

the graph-PHP root pigeon clause containing only allowed neighbors is a **subclause** and therefore a stronger premise.

For every full collision axiom

```text
NOT x_{ph} OR NOT x_{qh},
```

- if both edges are allowed, the exact graph-PHP collision clause exists;
- if at least one edge is missing, the already derived unit `(NOT m_{ph})` or `(NOT m_{qh})` is a subclause of the full collision clause.

Hence every root axiom expected by the full Cook proof has a derivable stronger substitute in the graph-PHP+B2 extension environment.

---

## 6. Strengthening/subsumption simulation lemma

Let a Resolution DAG derive clause `C` from axioms `A_i`. Suppose for every `A_i` we can derive a clause `A'_i subseteq A_i`.

Then node-by-node we can construct a Resolution DAG deriving some `C' subseteq C` with no more Resolution nodes than the source DAG, apart from the derivations of the stronger premises.

Induction on the source DAG:

- axiom: use `A'_i`;
- source resolution on pivot `p`: by induction obtain `D1 subseteq C1`, `D2 subseteq C2`;
  - if `p` disappeared from `D1`, reuse `D1`, which is already a subclause of the source resolvent;
  - if `NOT p` disappeared from `D2`, reuse `D2`;
  - otherwise resolve `D1,D2` on `p`, obtaining a subclause of the source resolvent.

At a source empty clause, the only subclause is the empty clause. Therefore refutation is preserved.

The same strengthening transform is applied after translating each Cook extension definition into the frozen B2 representation above. Missing variables are earlier B2 extension literals, so freshness/topological legality is preserved.

---

## 7. Constructive complexity bound

For canonical graph-PHP with graph parameter `n`:

```text
false placeholder extensions = O(n^2)
Cook recursive B2 macros      = O(n^3)
Cook source derivation        = O(n^4) clauses
strengthening transform       = linear in translated proof size
```

All transformations are fixed syntactic loops over explicit indices and proof nodes. Since any explicit canonical graph-PHP input has `N >= Omega(n)`, every `n^{O(1)}` bound is also `N^{O(1)}`.

Therefore, in this stated canonical family:

```text
CANONICAL_GRAPH_PHP_HAS_DETERMINISTIC_POLY_B2_PROOF_GENERATOR
= PROVED_FROM_COOK_SCHEMA + B2_MACRO_ENCODING + FALSE_PLACEHOLDERS + STRENGTHENING_SIMULATION
```

This is a family-specific generator, not a universal SAT solver.

---

## 8. Separator result

Combined with the O5 theorem:

```text
GRAPH_PHP under O5/plain Resolution
    -> superpolynomial total work

THE SAME canonical GRAPH_PHP under O7/B2
    -> deterministic polynomial proof generator
```

Hence graph-PHP is a clean JANUS separator demonstrating that the extension rule is not merely representational decoration: a known, explicitly generated extension schema can remove the Resolution bottleneck on this family.

---

## 9. Where the hidden exponent moved

This positive control kills a false generalization:

```text
"extension discovery is necessarily exponential even on PHP-like hard Resolution families"
= FALSE
```

For canonical graph-PHP, a polynomial schema is known and constructible.

The universal closure burden is now sharper:

```text
KNOWN FAMILY-SPECIFIC POLY SCHEMA
!=
UNIVERSAL DETERMINISTIC POLY SCHEMA SELECTION
```

A naive global search over extension sequences is not polynomial merely because each next extension has a polynomial-size description.

If `K` extension gates are allowed and at least two choices remain genuinely live at each of `K` stages, exhaustive sequence search has at least

```text
2^K
```

branches. More generally, with `M_i` candidates at stage `i`, sequence enumeration costs `product_i M_i`.

Thus the next exact Akinator gate is **schema selection with certified progress**, not proof existence on graph-PHP.

---

## 10. Claim ceiling

```text
COOK_STANDARD_PHP_POLY_ER = SOURCE_THEOREM
COOK_MACRO_TO_B2_CONSTANT_OVERHEAD = PROVED_IN_STATED_SCOPE
B2_FALSE_PLACEHOLDER_GADGET = PROVED_IN_STATED_SCOPE
RESOLUTION_STRENGTHENING_SIMULATION = PROVED_IN_STATED_SCOPE
CANONICAL_GRAPH_PHP_POLY_B2_GENERATOR = PROVED_FROM_STATED_COMPONENTS
O7_GRAPH_PHP_FINITE_MECHANICS = CI_PENDING
UNIVERSAL_B2_SCHEMA_SELECTION = OPEN
DETERMINISTIC_POLY_DISCOVERY_FOR_ARBITRARY_CNF = OPEN
P_VS_NP = OPEN
```
