# TOPA / JANUS — Akinator O5 Bounded-Width Contraction Theorem

**Frozen:** 2026-08-25  
**Status:** `PROVED_IN_STATED_SCOPE__CI_PASS__ENCODING_BOUND_REPAIRED`  
**Global ceiling:** `P_VS_NP = OPEN`

## 0. Question attacked

Can repeated bounded-width Resolution contractions evade a Resolution width lower bound merely by being applied adaptively under partial assignments?

Answer in the frozen O5 model:

```text
ROOT_GLOBAL_BOUNDED_WIDTH_CONTRACTIONS
=> ONE_BOUNDED_WIDTH_RESOLUTION_DERIVATION

CONTEXTUAL_BOUNDED_WIDTH_CONTRACTIONS + BRANCH_DEPTH d
=> ROOT_RESOLUTION_WIDTH <= max(w0(F), w + d)
```

Moreover a complete exact O5 execution compiles to an ordinary Resolution refutation with proof size bounded by the total number of local Resolution inference lines plus branch-composition overhead. Therefore an exponential Resolution-size lower bound is an unconditional total-work lower bound for this O5 lane.

This result does **not** apply to proof rules stronger than ordinary Resolution, e.g. unrestricted B2/Extended Resolution, algebraic proof systems, or semantic oracles.

---

## 1. Frozen definitions

Let `F` be a CNF. Let `w0(F)` be the maximum width of an input clause.

For a partial assignment `rho`, let `F|rho` denote the usual restriction of `F`: satisfied clauses are deleted and falsified literals are deleted from surviving clauses.

Define the blocking clause of `rho`:

```text
B(rho) = OR_{rho(x)=0} x  OR  OR_{rho(x)=1} not x.
```

Thus exactly the total assignments extending `rho` falsify `B(rho)`.

### O5(w) local contraction

At a node with context `rho`, O5 may add a clause `D` only if there is a pure Resolution derivation of `D` from the current residual clauses with every derived/residual line of width at most `w` (input residual clauses are accounted for separately by `w0(F)`). Previously admitted O5 clauses may be reused only because their derivations are part of the proof transcript.

No heuristic score has proof authority.

### O5 exact question tree

An internal branch asks one root-variable question `x=0 / x=1`. Both logically live children remain part of the exact execution unless one side is killed by a proof-carrying consequence. A leaf closes only by an admitted exact contradiction proof.

Let `d` be the maximum number of branch decisions on a root-to-leaf path.

---

## 2. Lemma A — root-global flattening

If every O5 clause is derived at root by a width-`w` Resolution derivation from `F` plus earlier O5 clauses, then concatenating the derivations gives one Resolution derivation from `F` of width at most

```text
max(w0(F), w).
```

If the process reaches the empty clause, it is simply a width-bounded Resolution refutation.

Therefore repeated root-global O5 contractions do not constitute a proof system stronger than Resolution.

---

## 3. Lemma B — pure context lift with width accounting

Suppose `F|rho` has a pure Resolution derivation of a residual clause `D` in width at most `w`.

Then `F` has a pure Resolution derivation of some clause

```text
E subseteq D OR B(rho)
```

with width at most

```text
max(w0(F), w + |rho|).
```

In particular, if `F|rho` is refuted in width `w`, then `F` derives a subclause of `B(rho)` within the same width bound.

### Proof

Induct on the restricted Resolution derivation.

**Restricted root axiom.** A surviving restricted axiom is `A|rho` for some root clause `A` not satisfied by `rho`. The original `A` is exactly `A|rho` plus literals falsified by `rho`, hence

```text
A subseteq (A|rho) OR B(rho).
```

Use `A` itself as the lifted line. Its width is bounded by `w0(F)` and also by residual width plus at most `|rho|` deleted context literals.

**Resolution step.** Let residual line `D` be obtained by resolving `D1` containing pivot `p` with `D2` containing `not p`. Since `p` survives the restriction, `p` is not assigned by `rho`.

By induction derive

```text
E1 subseteq D1 OR B(rho)
E2 subseteq D2 OR B(rho).
```

If `E1` omits `p`, then `E1` is already a subclause of `D OR B(rho)` and can be reused. The same holds symmetrically for `E2` if it omits `not p`.

Otherwise resolve `E1,E2` on `p`. The resolvent is a subclause of `D OR B(rho)`. Since `B(rho)` is shared rather than duplicated, its width is at most `|D|+|rho| <= w+|rho|`.

At terminal residual line `D=empty`, obtain a subclause of `B(rho)`.

No weakening rule is required.

---

## 4. Theorem C — adaptive O5 tree compiles to Resolution

Let a complete exact O5(w) execution for UNSAT `F` have maximum branch depth `d`.

Then `F` has a pure Resolution refutation of width at most

```text
W_compiled <= max(w0(F), w + d).
```

### Proof sketch

At every closed leaf with context `rho`, Lemma B yields a root derivation of a subclause of `B(rho)` using width at most `max(w0,w+|rho|) <= max(w0,w+d)`.

Move upward in the question tree. Suppose a parent context `rho` branches on `x`.

The `x=0` child yields a clause contained in

```text
B(rho) OR x,
```

and the `x=1` child yields a clause contained in

```text
B(rho) OR not x.
```

If either child clause already omits its branch literal, it is a valid parent blocking subclause. Otherwise resolve the two child clauses on `x`; the result is a subclause of `B(rho)`.

Repeat to the root, where `B(empty)=empty`.

Thus the whole adaptive contraction/branching process is still an ordinary Resolution refutation; branch context only appears as additive width budget.

---

## 5. Size/work compilation

Let `L` be the total number of local Resolution inference lines actually executed across all O5 nodes, and `B` the number of binary branch-composition events.

The construction above can be represented as a Resolution DAG with size

```text
S_compiled = O(L + B)
```

up to ordinary pointer/serialization factors. Consequently

```text
Resolution-size lower bound on F
=> total O5 proof/branch work lower bound.
```

This is stronger than a depth statement: a thin linear-depth tree could still be polynomial, but it cannot evade a superpolynomial Resolution-size lower bound if every inference remains in this O5/Resolution calculus.

---

## 6. Graph-PHP consequence

Ben-Sasson and Wigderson prove for graph pigeonhole formulas over suitable bipartite expanders that the required Resolution width is large. In their Theorem 4.15, for an `(m,n,d,r,e)` expander,

```text
W(PHP(G)) >= r*e/2.
```

For `m=n+1`, constant left degree and `r=Theta(n)` with constant expansion surplus, there are instances with

```text
w0 = O(1)
number_of_variables = |E| = Theta(n)
W(PHP(G)) = Omega(n).
```

Source:
- Eli Ben-Sasson and Avi Wigderson, *Short Proofs are Narrow — Resolution Made Simple*, JACM 2001 / ECCC TR99-022.
- https://eccc.weizmann.ac.il/eccc-reports/1999/TR99-022/

Therefore every O5(w) adaptive tree on this family obeys

```text
d >= W(PHP(G)) - w = Omega(n) - w.
```

For fixed `w` or `w=O(log N)`, the decision depth is linear in the graph parameter.

More importantly, the same width lower bound combined with the Ben-Sasson–Wigderson size-width relation yields exponential Resolution size in the graph parameter. Since O5 execution compiles to Resolution with only transcript-linear proof overhead,

```text
O5_TOTAL_WORK >= 2^{Omega(n)}
```

in the usual literal-unit model.

### Conservative encoded-input map

Constant **left** degree gives `|E|=O(n)`, but by itself does not bound every right degree. If `r_h` denotes the degree of hole `h`, the number of collision clauses is

```text
sum_h binom(r_h,2) <= O((sum_h r_h)^2) = O(n^2).
```

Thus without importing an additional bounded-right-degree expander construction, the safe explicit binary-identifier encoding bound is

```text
N = O(n^2 log n).
```

Therefore

```text
n = Omega(sqrt(N / log N))
```

for this encoding upper bound, and the source-derived exponential lower bound implies the conservative input-relative statement

```text
O5_TOTAL_WORK >= 2^{Omega(sqrt(N/log N))},
```

which is still superpolynomial in the actual encoded input length `N`.

The earlier stronger shorthand `2^{Omega(N/log N)}` is **not used** unless bounded right degree is separately established.

Hence:

```text
AKINATOR_BASE0_O5_PLAIN_RESOLUTION_ONLY_UNIVERSAL_POLY_ROUTE
= REFUTED_ON_EXPANDER_GRAPH_PHP
```

within the stated O5 calculus.

---

## 7. Independent finite mechanics receipt

Dedicated GitHub Actions replay:

```text
workflow = Validate Akinator O5 Width Context
head     = a8cd65acf3e171fe50003dc790bab97bccd96fa6
run      = 32783967221
job      = 97611853242
result   = SUCCESS

AKINATOR_O5_CONTEXT_AXIOM_LIFT_SHAPE = PASS
AKINATOR_O5_SINGLE_CONTEXT_WIDTH_BOUND = PASS bound=2 actual=2
AKINATOR_O5_NESTED_TREE_WIDTH_BOUND = PASS bound=2 actual=2
AKINATOR_O5_ROOT_GLOBAL_FLATTEN = PASS width=2
AKINATOR_O5_BRANCH_COMPOSITION = PASS
CLAIM_CEILING = FINITE_MECHANICS_ONLY
P_VS_NP = OPEN
```

CI also parsed `docs/TOPA_PVSNP_EVENT_JOURNAL_2026-08-25.json` successfully. The asymptotic graph-PHP lower bound is source-derived from Ben-Sasson–Wigderson plus the analytical compilation theorem above; CI does not prove that asymptotic theorem.

---

## 8. What this does NOT close

The result does not refute the full JANUS Akinator closure program.

It closes the false road:

```text
"repeat cheap bounded-width ordinary-Resolution contractions long enough"
```

as a universal polynomial escape.

It does not cover:
- B2 / Extended Resolution extension definitions;
- algebraic certificates;
- a new exact polynomial observable not p-simulable by ordinary Resolution;
- a deterministic polynomial discovery theorem for stronger proof-carrying reasons.

Those are precisely where the next candidate escape must live.

---

## 9. Claim ceiling

```text
O5_CONTEXT_LIFT_WIDTH_THEOREM = PROVED_IN_STATED_SCOPE
O5_ADAPTIVE_TREE_TO_RESOLUTION = PROVED_IN_STATED_SCOPE
O5_FINITE_MECHANICS = PROVIDER_CI_PASS
O5_GRAPH_PHP_UNIVERSAL_POLY_ROUTE = REFUTED_FROM_BSW_LOWER_BOUND + OUR_COMPILATION
O5_INPUT_RELATIVE_LOWER_BOUND = 2^{Omega(sqrt(N/log N))}  # conservative encoding map
BASE0_FULL_PORTFOLIO = NOT_REFUTED_BY_THIS_NOTE
B2_ER_ROUTE = OPEN
P_VS_NP = OPEN
```
