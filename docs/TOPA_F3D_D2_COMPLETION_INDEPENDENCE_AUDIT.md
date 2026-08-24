# TOPA F3D-D2 — Completion-Independence Audit of the Source Core

**Frozen:** 2026-08-24T22:31:00+03:00  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA`  
**Primary source:** Dmitry Sokolov, *Pseudorandom Generators, Resolution and Heavy Width*, CCC 2022, DOI `10.4230/LIPIcs.CCC.2022.15`.  
**Status:** `SOURCE_PROOF_AUDIT_COMPLETE_IN_STATED_READING__EXTERNAL_MACRO_SURVIVAL_STILL_COMPLETION_SENSITIVE`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Question

Algorithm 1 leaves two choices nonunique:

```text
line 11: choose a maximum-cardinality valid B_i;
line 12: choose a satisfying assignment nu_i for constraints in B_i.
```

TOPA's explicit F-D2-01/F-D2-02 fixture proves that these choices can change the residual semantics of an **external crossing B2 macro**.

The present audit asks a different question:

> Does the source proof of Lemma 22 / Theorem 23 itself depend on a particular completion of those choices?

## 2. Lemma 22 — self-reduction validity is completion-robust

### 2.1 Graph invariant and choice of B_i

Proposition 29 proves the two inductive invariants used by Lemma 22:

```text
G_i remains the required boundary expander;
|C_i| remains bounded.
```

The proof uses only that `B_i` is a valid set of **maximum cardinality** under the line-11 predicate.

In the final contradiction, if a bad witness set `S` existed then `S union B_{i-1}` would also satisfy the same boundary predicate and would be larger than `B_{i-1}`, contradicting maximality. No identity-specific or tie-break-specific property of `B_{i-1}` is used.

Therefore every maximum-cardinality line-11 choice satisfies the same graph-size argument.

### 2.2 Assignment nu_i

After the graph invariant is established, the Lemma-22 proof uses balancedness plus the expansion-derived ordering of vertices in `B_i` to prove that a satisfying assignment exists.

Algorithm 1 only requires `nu_i` to:

```text
assign N(B_i)
AND
satisfy every constraint from B_i.
```

The residual graph update in line 13 depends on `B_i` and its neighborhood, not on the Boolean values chosen by `nu_i`.

The self-reduction definition requires the selected constraints to be satisfied, not a unique satisfying assignment.

For future alive output bits, the proof controls **how many** neighborhood variables have been assigned. The balancedness hypothesis is quantified over all partial assignments of the allowed size, so it does not privilege one satisfying value pattern.

### D2-T2A

Under the published hypotheses, Lemma 22's self-reduction guarantee is invariant under:

- arbitrary choice among maximum-cardinality valid `B_i` sets;
- arbitrary compatible `nu_i` satisfying all constraints from the selected `B_i`.

This is a theorem about the source proof obligations, not about JANUS external crossing-macro survival.

## 3. Theorem 23 — heavy-width reduction is robust to adaptive valid completions

Theorem 23's probabilistic step keeps the explicit randomness from Algorithm 1 lines 7–8:

```text
v_i chosen uniformly among alive outputs;
sigma_i chosen uniformly from the current zero-preimage of p^i_{v_i}.
```

Fix any history up to iteration `i`, including any previous valid choices of `B_j` and `nu_j`.

If a clause's functional form still has heavy width at least `w`, the proof lower-bounds the conditional probability that the current random `v_i,sigma_i` kills it. The bound uses:

- the number of currently heavy alive output bits;
- uniform choice of `v_i`;
- uniform choice of `sigma_i` in the current preimage;
- balancedness of the residual base function.

The line-11/line-12 completion occurs after `sigma_i`. If `sigma_i` has already satisfied/killed the clause, extending the restriction by a valid `nu_i` cannot make the satisfied clause unsatisfied again.

The comparison between final and intermediate heavy width uses only nested restrictions `rho_i subseteq rho_l`, the number of assigned variables around alive output bits, and balancedness; it does not use a particular Boolean pattern for earlier `nu_j` values.

Therefore the same one-step conditional survival upper bound applies after every valid history. Multiplying conditional bounds (equivalently, iterating the tower rule) yields the same source survival estimate even when the valid completion rule for `B_i,nu_i` is deterministic or history-dependent.

### D2-T2B

Subject to retaining the source-specified randomness of `v_i` and `sigma_i`, the Theorem-23 size-to-heavy-width argument is robust under arbitrary history-dependent **valid** completions of line-11/line-12 choices.

This statement concerns the source Resolution/functional-encoding heavy-width theorem only.

## 4. Crucial separation

TOPA's completion-divergence fixture and D2-T2A/B are compatible:

```text
SOURCE CORE THEOREM VALIDITY
    = completion-robust

EXTERNAL JANUS CROSSING-MACRO SEMANTICS
    = completion-sensitive
```

The source theorem tracks its own local functional forms. It does not assert that an arbitrary crossing B2 macro introduced outside the source functional-variable language has completion-independent residual semantics.

Therefore the completion choice remains a real parameter for F3D-D3 semantic survival, even though it is not a loophole in Lemma 22 / Theorem 23.

## 5. Correct D3 quantifier

Because external macro survival can depend on completion while the source theorem survives every valid completion, the strongest clean next target is:

```text
For every source-valid completion C,
Pr_{rho generated with C}[
    semantic crossing complexity survives above frozen thresholds
] >= p(N).
```

Equivalently define the robust survival functional

```text
SURV_min(P;B0,D0)
 := inf_C Pr_{rho~D_C}[
      b_sem(P|rho)>=B0 AND d_sem(P|rho)>=D0
    ],
```

where `C` ranges over valid line-11/line-12 completion rules and the explicit line-7/line-8 randomness is retained.

A positive lower bound for `SURV_min` cannot be an artifact of favorable hidden tie-breaking.

## 6. Remaining algorithmic firewall

Completion robustness of the *proof* does not make the completion computationally cheap.

```text
ANY_MAXIMIZER_IS_PROOF_VALID
!=
MAXIMIZER_IS_POLYTIME_FINDABLE

ANY_SATISFYING_NU_IS_PROOF_VALID
!=
SATISFYING_NU_IS_POLYTIME_FINDABLE
```

If JANUS turns the source construction into an executable solver subroutine, search/sampling costs remain separately charged.

## 7. Status movement

```text
D2 source distribution uniquely specified        = NO
D2 source self-reduction theorem completion-robust = YES, IN STATED SOURCE-PROOF READING
D2 source heavy-width reduction completion-robust  = YES, WITH LINES 7-8 RANDOMNESS RETAINED
D2 external B2 macro survival completion-robust     = NO; explicit source-like divergence exists
D3 robust SURV_min lower bound                       = OPEN / NEXT
Issue #217 unrestricted ER3                          = OPEN
P_VS_NP                                              = OPEN
```

## 8. Claim firewall

```text
SOURCE_COMPLETION_ROBUSTNESS
!=
EXTERNAL_MACRO_SURVIVAL

THEOREM_PROOF_ACCEPTS_ANY_VALID_COMPLETION
!=
POLYTIME_COMPLETION_SELECTOR

D2_T2
!=
ER3_LOWER_BOUND

P_VS_NP = OPEN
```
