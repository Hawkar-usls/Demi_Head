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

**Reusable law:** a polynomial algorithm for a restricted graph class cannot be imported until the reduction proves **exact object-class membership**. “Cubic” / degree-bounded != “line graph”.

---

## 2. Changryeol Lee — “Graph-Based Deterministic Polynomial Algorithm for NP Problems” (2025–2026)

**Claim direction:** `P = NP`.  
**Route:** merge all certificate computations into a polynomial-size graph and decide existence of a valid computation walk by pruning/reachability.

### Current status

Open preprint remains publicly available. A recent external machine review flags two load-bearing concerns:
1. local edge validity may not enforce global tape-history consistency along a path;
2. correctness arguments use the semantic set of valid walks while the algorithm itself must avoid enumerating that exponential object.

JANUS does **not** import that review as theorem.

### JANUS target

Construct the smallest deterministic verifier/tape fixture with a graph path consisting of locally valid transitions but whose revisit of a cell reads a symbol inconsistent with the last write on the same path.

Exit:

```text
LEE_SPURIOUS_WALK_EXPLICIT_FIXTURE = OPEN_HIGH_PRIORITY
```

If found, the route closes by finite semantic counterexample. If no such fixture exists, audit the exact pruning theorem next.

**Reusable idea:** shared transition structure is real compression, but local transition compatibility must be proved equivalent to global computation-history consistency.

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

## 6. Sergey V. Yakhontov — TCPE / linear-programming accepting-path construction (2012)

**Claim direction:** `P = NP`.

**Route:** encode accepting nondeterministic computations as tape-consistent paths in a polynomial-size DAG; formulate tape-consistent path existence as a fractional multi-commodity LP.

### Load-bearing proposition

The crucial statement is the claimed equivalence:

```text
TCPELP is feasible <=> there exists one tape-consistent path.
```

The proof moves from fractional flow feasibility to existence of a single path satisfying all tape-consistency relations.

### JANUS target

Build a minimal DAG where fractional commodity flows can satisfy the LP coupling while the required consistency pairs cannot all lie on one common path, or prove that the published equations prohibit such mixing.

```text
YAKHONTOV_PROP_3_9_FRACTIONAL_TO_SINGLE_PATH = OPEN_HIGH_PRIORITY
```

**Why valuable:** this is almost exactly our recurring hidden-exponent pattern:

```text
POLYNOMIAL LOCAL/FRACTIONAL REPRESENTATION
!=
ONE GLOBALLY CONSISTENT WITNESS
```

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

## 9. Priority order for JANUS salvage

```text
A1 VEGA_K33_LINEGRAPH_COUNTEREXAMPLE     = READY / EXACT FINITE REFUTATION
A2 LEE_SPURIOUS_WALK                     = NEXT EXPLICIT FALSIFIER
A3 YAKHONTOV_FRACTIONAL_PATH_MIXING      = NEXT LP FALSIFIER
A4 DENG_DU_GUBIN                         = IMPORT KNOWN FAILURE LAWS
A5 DEOLALIKAR_BLUM                       = LOWER-BOUND BARRIER LINEAGE
```

The aim is not to “combine failed proofs” indiscriminately. We extract only objects that survive an exact admission gate.

---

## 10. P-vs-NP closure firewall

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

P_VS_NP = OPEN
```
