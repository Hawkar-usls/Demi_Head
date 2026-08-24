# TOPA F3D-D2 — Completion Choice Divergence Result

**Frozen:** 2026-08-24T22:31:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Parent:** `TOPA_F3D_D2_SOURCE_SELF_REDUCTION_PROOF_PROGRAM.md`  
**Status:** `SOURCE_LIKE_COMPLETION_DIVERGENCE_PROVED_BY_EXPLICIT_FINITE_CONSTRUCTION`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Source step being audited

Sokolov Algorithm 1 contains:

- line 11: choose a maximum-cardinality set `B_i` satisfying a boundary condition;
- line 12: choose an x-assignment `nu_i` on `N(B_i)` satisfying all constraints from `B_i`.

The published pseudocode does not specify tie-breaking among several maximizing `B_i`, nor a probability law among several satisfying `nu_i` assignments.

This result asks whether those choices can change the residual semantics of one external crossing frozen-B2 macro.

## 2. F-D2-01 — two valid line-11 maximizers

Freeze a line-11 graph state with left vertices

```text
a,b,c,d
```

and right adjacency

```text
a,b -> {y1,w1}
c,d -> {y2,w2}
```

with `r=2` and `epsilon=1/4`.

For the unique-neighbour boundary used by the source predicate:

```text
boundary({a,b}) = empty
boundary({c,d}) = empty
```

while every mixed pair has four unique boundary neighbours. Because `|B|<=2`, the exact maximum-cardinality valid sets are therefore

```text
B1={a,b}
B2={c,d}.
```

Each twin pair carries duplicate parity-zero constraints on its two neighbours. Freeze the same completion rule for both branches:

```text
nu(B) = lexicographically first satisfying assignment.
```

Then

```text
nu(B1): y1=w1=0
nu(B2): y2=w2=0.
```

Use the frozen-B2 target macro

```text
h := z1 AND z2
M := y1 AND h
```

with locality neighborhoods

```text
{y1,w1}, {y2,w2}, {z1}, {z2}.
```

Under `B1`, `M` residualizes to `0`.

Under `B2`, `y1,z1,z2` remain free and are semantically essential, so no listed neighborhood contains the essential support. Thus the same target remains `CROSSING`.

Therefore:

```text
same line-11 predicate
+ same deterministic nu completion rule
+ different valid max-B completion
=> CONST_0 versus CROSSING.
```

## 3. F-D2-02 — one fixed B, two valid line-12 assignments

Fix

```text
B={a,b}.
```

Its duplicate parity-zero constraints have exactly two satisfying assignments on `{y1,w1}`:

```text
nu0=(0,0)
nu1=(1,1).
```

Both satisfy every constraint from `B`.

For the same target macro `M`:

```text
M|nu0 = 0
M|nu1 = z1 AND z2.
```

Because `{z1,z2}` is not contained in any one frozen locality neighborhood, the second residual remains `CROSSING`.

Therefore:

```text
same B
+ two valid satisfying nu choices
=> CONST_0 versus CROSSING.
```

## 4. Theorem established in this scope

### Theorem D2-DIV

There exists an explicit finite source-like Algorithm-1 line-11/line-12 state and an explicit frozen-B2 crossing macro such that:

1. two valid maximum-cardinality line-11 completions produce opposite semantic survival outcomes under the same frozen rule for selecting `nu`; and
2. for one fixed valid `B`, two valid line-12 satisfying assignments produce opposite semantic survival outcomes.

Hence completion semantics are a real parameter for any new semantic-survival quantity layered on top of Algorithm 1.

## 5. What this does not establish

The fixture is intentionally narrower than Lemma 22. It does **not** establish that:

- the exact same divergence occurs in the full hard NW family used by the heavy-width theorem;
- every source-valid state satisfying all expander and balancedness hypotheses has ambiguous survival;
- an unrestricted ER3 proof can exploit these choices to obtain a polynomial refutation;
- any completion yields high-probability collapse in the hard family.

The correct next theorem must either quantify over **all source-valid completions** or construct a divergence/collapse escape inside the exact source-matched hard-family hypotheses.

## 6. Consequence for the survival functional

The notation

```text
SURV_P(B0,D0; D_source)
```

is not admissible as a unique probability until completion semantics are frozen.

Preferred robust object:

```text
SURV_min(P;B0,D0)
  := inf_C Pr_{rho~D_C}[semantic survival],
```

where `C` ranges over explicitly defined source-valid completions.

An existential or favorable completion may still be studied, but it must be labelled as such and cannot be laundered into a completion-independent theorem.

## 7. Complexity firewall

This result also does not make completion selection algorithmically free.

```text
VALID_COMPLETION_EXISTS != POLYTIME_FIND_COMPLETION
LEXICOGRAPHIC_COMPLETION_DEFINED != LEXICOGRAPHIC_COMPLETION_CHEAP
UNIFORM_OVER_COMPLETIONS_DEFINED != UNIFORM_SAMPLING_CHEAP
```

Any solver-level use must charge the search/sampling cost separately.

## 8. Next gate

```text
D2-DIV source-like completion dependence = PROVED IN EXPLICIT FINITE SCOPE
D2-T2 completion-independent Lemma-22 invariants = NEXT
D3-A adversarial-completion survival theorem = OPEN
D3-B exact hard-family completion-collapse escape = OPEN
ISSUE_217 unrestricted ER3 extension-count = OPEN
P_VS_NP = OPEN
```
