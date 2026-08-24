# TOPA / JANUS — External P-vs-NP Claim Salvage Audit

**Frozen:** 2026-08-25  
**Purpose:** mine public closure claims for exact lemmas, counterexamples, and reusable failure laws.  
**Global ceiling:** `P_VS_NP = OPEN`.

## 0. Scientific law

```text
CLAIMED_CLOSURE != CLOSURE
FAILED_PROOF != USELESS_PROOF
PUBLICITY/CREDENTIALS != EVIDENCE
FINITE_REPLAY != ASYMPTOTIC_THEOREM
```

Clay Mathematics Institute currently lists P vs NP as **Unsolved**. Every item below is therefore treated as a claim/audit object, not as authority.

---

## 1. Frank Vega — “SAT in Polynomial Time: A Proof of P = NP” (2024–2025)

**Claim direction:** `P = NP`.  
**Route:** SAT -> 3SAT -> NAE variants -> 2MXSAT -> 3XSP -> 2XHS -> maximum independent set in an alleged line graph -> matching.

### Load-bearing claim

Theorem 6 asserts that every 2XHS instance in the paper's restricted class yields a graph `G=(U,C)` that is a line graph, hence maximum independent set is polynomial by matching.

### JANUS exact falsifier

By the paper's own Definition 2:
- `C` is a family of 2-element subsets of `U`;
- every element of `U` occurs in exactly three members of `C`;
- distinct sets intersect in at most one element.

Thus `G=(U,C)` is simply a finite simple **3-regular graph**.

Choose `G = K_{3,3}`.
- each vertex has degree 3, so every `u in U` occurs in exactly three 2-sets;
- every two distinct edges intersect in at most one vertex;
- hence this is a legal 2XHS instance under the stated definition.

But `K_{3,3}` is **not** a line graph: every line graph is claw-free, whereas any vertex of `K_{3,3}` together with its three pairwise nonadjacent neighbors induces `K_{1,3}`.

Therefore the universal line-graph premise in Theorem 6 is false.

```text
VEGA_THEOREM6_ALL_2XHS_GRAPHS_ARE_LINE_GRAPHS = REFUTED_BY_K33
VEGA_P_EQUALS_NP_ROUTE = CLOSED_AT_THEOREM6
```

### Provider receipt

Fundamentum independent finite replay:

```text
workflow = Validate External Vega K3,3 Claim Audit
run      = 32777580324
job      = 97592079452
result   = SUCCESS

EXT_VEGA_2XHS_K33_LEGAL = PASS
EXT_VEGA_K33_INDUCED_CLAW = PASS
EXT_VEGA_THEOREM6_ALL_2XHS_ARE_LINE_GRAPHS = REFUTED_BY_K33
P_VS_NP = OPEN
```

CI validates the explicit finite mechanics. The route refutation is the elementary graph argument above.

**Reusable law:** a polynomial algorithm for a restricted graph class cannot be imported until the reduction proves **exact object-class membership**. “Cubic” / degree-bounded != “line graph”.

---

## 2. Changryeol Lee — “Graph-Based Deterministic Polynomial Framework for NP Problems” (2025–2026)

**Claim direction:** `P = NP`.  
**Route:** merge certificate computations into a polynomial-size graph and replace certificate search by graph pruning / edge validation.

### Source facts now frozen

The public v8 preprint defines the raw computation graph extremely broadly: an edge `(u,v)` exists whenever the tape-cell indices differ by one. A **computation walk** is much stronger and additionally requires tier consistency, index-predecessor state/symbol history, head-state flow, cell-flow and displacement consistency.

Algorithm 8 `TakeArbitraryWalk()` claims to produce a computation walk by storing a transition surface and repeatedly taking the first graph-next edge “consistent with surface S.” Thus the critical equality to audit is not merely graph reachability; it is:

```text
ALGORITHM8_SURFACE_CONSISTENCY
<=>
ALL_DEFINITION18_COMPUTATION_WALK_CONSTRAINTS
```

The preprint later relies on this procedure inside the pruning logic and distinguishes ordinary graph walks from computation walks explicitly.

### External review signal — not imported as theorem

A recent machine review reports a possible spurious-walk/local-vs-global defect. JANUS treats this only as a falsifier target.

### JANUS target

Either:
1. construct a smallest graph/surface fixture that Algorithm 8 admits although it violates Definition 18; or
2. prove from the exact primitive predicate “consistent with surface” that every returned sequence satisfies all Definition-18 conditions.

Until this exact equivalence is settled:

```text
LEE_ROUTE = OPEN_FOR_EXACT_AUDIT
LEE_ALGORITHM8_SURFACE_TO_GLOBAL_WALK_EQUIVALENCE = OPEN_HIGH_PRIORITY
```

**Reusable idea:** a polynomial shared transition graph can be a legitimate representation compression. The unresolved burden is whether the polynomial local verifier certifies a **single globally coherent history** rather than compatible fragments from different histories.

---

## 3. Zikang Deng — “P=NP” via SDP for degree<=4 3-coloring (2024)

**Claim direction:** `P = NP`.  
**Route:** graph 3-colorability <-> boundedness/optimum of a polynomial-size semidefinite program.

A 2025 arXiv critique identifies a specific fatal error: the argument conflates **subgraphs** with **induced subgraphs**. The claimed equivalence therefore fails.

```text
DENG_ROUTE = PUBLICLY_REFUTED
```

**Reusable law:** optimization relaxations/reductions must preserve the exact combinatorial object and quantifier domain; subgraph != induced subgraph.

---

## 4. Lizhi Du — polynomial-time 3-SAT / Hamilton-cycle route (2010; revised 2023)

**Claim direction:** `P = NP`.

A 2024 arXiv critique gives an infinite family of satisfiable 3-CNF formulas that Algorithm 1 incorrectly labels unsatisfiable. The failing step intersects “useful unit” information across clauses and deletes globally valid possibilities.

```text
DU_ALGORITHM1 = REFUTED_BY_INFINITE_SAT_FAMILY
DU_P_EQUALS_NP_ROUTE = CLOSED
```

**Reusable law:** pairwise/local consistency propagation can destroy a globally consistent witness. This is directly relevant to JANUS local-vs-global proof/search audits.

---

## 5. Sergey Gubin — compatibility-matrix SAT algorithms (2007)

**Claim direction:** `P = NP` (and stronger claims in some versions).

Public counterexample and later critique papers explicitly refute the proposed 3-SAT algorithm and the claimed SAT->2SAT reduction.

```text
GUBIN_ROUTE = PUBLICLY_REFUTED
```

**Reusable law:** compatibility/depletion based on bounded/local consistency is not automatically equivalent to global satisfiability. Preserve this lineage as a negative-control family for any future matrix/compression method.

---

## 6. Sergey V. Yakhontov — TCPE / linear-programming accepting-path construction (2012–2014)

**Claim direction:** `P = NP`.

**Route:** encode accepting nondeterministic computations as tape-consistent paths in a polynomial-size DAG; formulate tape-consistent path existence as a fractional multi-commodity LP.

### Load-bearing proposition

The crucial statement is the claimed equivalence:

```text
TCPELP is feasible <=> there exists one tape-consistent path.
```

In the published proof of Proposition 3.9, feasibility of the fractional network systems is used to choose a path for one commodity and then assert that the same path is also a path in other commodity graphs. That inference is not a generic consequence of independent fractional network-flow conservation: different commodities can route their positive flow on different paths.

JANUS does **not** yet call this a refutation, because the remaining cross-commodity equations may impose additional synchronization. The exact next obligation is therefore:

```text
DO_THE_FULL_TCPELP_CROSS_COMMODITY_EQUATIONS_FORCE_ONE_COMMON_INTEGRAL_PATH?
```

### JANUS target

Build a minimal DAG where all published equations admit a fractional solution whose commodity supports cannot be realized by one common tape-consistent path, or prove an integrality/common-path theorem for the exact polytope.

```text
YAKHONTOV_PROP_3_9_FRACTIONAL_TO_SINGLE_PATH = OPEN_HIGH_PRIORITY
```

**Reusable law candidate:**

```text
POLYNOMIAL LOCAL/FRACTIONAL REPRESENTATION
!=
ONE GLOBALLY CONSISTENT INTEGRAL WITNESS
```

unless an integrality/synchronization theorem is proved.

---

## 7. Vinay Deolalikar — claimed `P != NP` (2010)

**Claim direction:** `P != NP`.

The manuscript received serious expert attention but consensus rapidly formed that the proof was fatally flawed. Public analyses identified problems both with using solution-space structure to separate k-SAT from easier problems and with the finite-model-theory argument.

```text
DEOLALIKAR_CLOSURE_CLAIM = REFUTED_AS_WRITTEN
```

**Reusable residue:** statistical-physics / solution-space and finite-model viewpoints may still generate restricted hypotheses, but no theorem may be transferred to unrestricted P vs NP without repairing the identified locality/definability gaps.

---

## 8. Norbert Blum — claimed `P != NP` (2017)

**Claim direction:** `P != NP`.

Blum attempted to extend monotone CNF/DNF approximation lower bounds to non-monotone circuits. A Tardos monotone polynomial-time function provides a sanity counterexample to the claimed transfer; public discussion localizes a flaw in Theorem 6, Step 1. Blum withdrew the manuscript and stated that the proof was wrong.

```text
BLUM_2017_CLOSURE_CLAIM = WITHDRAWN_AND_REFUTED
```

**Reusable law:** every purported lower-bound transfer from a restricted circuit class to general circuits must pass known polynomial-time monotone functions such as the Tardos example before promotion.

---

## 9. Ted Swart -> Yannakakis — canonical productive failed proof lineage

**Claim direction:** `P = NP` (1986–1987).

Swart proposed polynomial-size linear programs for TSP. The concrete closure claim failed. Instead of endlessly patching individual formulations, Yannakakis developed a structural barrier: every **symmetric** extended formulation of the TSP polytope requires exponential size. Later work removed the symmetry restriction for natural TSP extension formulations and developed the modern theory of extension complexity.

This is the exact salvage pattern JANUS wants:

```text
FAILED_CLOSURE_ATTEMPT
-> IDENTIFY_THE_SHARED_STRUCTURAL_ASSUMPTION
-> PROVE_A_BARRIER_FOR_THE_ENTIRE_ROUTE_CLASS
-> REAL_THEOREM
```

Scott Aaronson has described Swart's attempt as possibly the most productive failed P=NP proof because it helped inspire this line.

```text
SWART_P_EQUALS_NP = FAILED
SWART_TO_YANNAKAKIS_SALVAGE = MAJOR_REAL_THEOREM_LINEAGE
```

**JANUS lesson:** when a public proof dies, ask whether the failed constructions share a common representation class. If yes, proving a lower bound for that class can be more valuable than repairing one manuscript.

---

## 10. Priority order for JANUS salvage

```text
A1 VEGA_K33_LINEGRAPH_COUNTEREXAMPLE     = CLOSED / PROVIDER PASS
A2 LEE_SURFACE_TO_GLOBAL_WALK            = ACTIVE EXPLICIT FALSIFIER / PROOF GATE
A3 YAKHONTOV_FRACTIONAL_COMMON_PATH      = ACTIVE LP INTEGRALITY GATE
A4 SWART_YANNAKAKIS_PATTERN              = IMPORT AS SALVAGE TEMPLATE
A5 DENG_DU_GUBIN                         = IMPORT KNOWN FAILURE LAWS
A6 DEOLALIKAR_BLUM                       = LOWER-BOUND BARRIER LINEAGE
```

The aim is not to “combine failed proofs” indiscriminately. We extract only objects that survive an exact admission gate.

---

## 11. P-vs-NP closure firewall

```text
ONE EXTERNAL ROUTE REFUTED
!=
P_VS_NP PROGRESS THEOREM

ONE REUSABLE LEMMA
!=
P_EQUALS_NP

ONE LOWER-BOUND IDEA
!=
P_NOT_EQUAL_NP

FAILED_PROOF_SALVAGE
CAN
PRODUCE_REAL_NEW_THEOREMS

P_VS_NP = OPEN
```
