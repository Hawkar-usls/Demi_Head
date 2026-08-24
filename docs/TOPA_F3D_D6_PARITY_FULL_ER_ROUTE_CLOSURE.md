# TOPA F3D-D6 — Parity-NW Full-ER Route Closure

**Frozen:** 2026-08-24  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Status:** `PARITY_NW_FULL_ER_HARD_FAMILY_ROUTE_CLOSED_BY_POLYNOMIAL_UPPER_BOUND`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why this audit was necessary

The restricted JANUS line established strong lower bounds for Resolution / ER3 under locality restrictions on parity-NW formulas. D6-D2 then asked whether the same parity-NW family could serve as a candidate hard family for **unrestricted Extended Resolution**.

It cannot.

Parity-NW is a system of linear equations over `GF(2)`. Extended Frege can feasibly formalize Gaussian elimination, and Extended Resolution is p-equivalent to Extended Frege. In the JANUS direct-CNF regime the translation overhead from truth-table parity clauses to the linear-algebra representation is polynomial.

Therefore the parity-NW family is a useful restricted-system benchmark and escape-mechanism detector, but not an admissible candidate for proving a superpolynomial lower bound for full ER.

---

# 2. Frozen parity-NW object

Let root variables be `x_1,...,x_n` and let the NW outputs define linear equations

```text
A x = b   over GF(2),
```

where row `i` has support `N(i)` of size `d_i <= Delta`.

The JANUS direct encoding `F(A,b)` contains, for each row, the complete truth-table CNF of

```text
XOR_{j in N(i)} x_j = b_i.
```

If `b` is outside the image of the linear map `x -> Ax`, the system and the direct CNF are UNSAT.

---

# 3. Local translation from direct CNF to a parity circuit

For each row `i`, build a frozen extension circuit `p_i` computing the XOR of the `d_i` row variables, using the standard constant-size XOR-from-AND gadget iteratively.

Circuit size per row is

```text
O(d_i).
```

The direct truth-table CNF `F_i` is logically equivalent to the required output value of `p_i`.

An explicit Extended-Frege derivation of that local equivalence can be obtained by exhaustive proof over the `d_i` row variables with cost

```text
2^O(d_i) * poly(d_i).
```

This is not a free truth-table oracle: the full cost is charged.

Summed over all rows:

```text
LOCAL_TRANSLATION_COST
<= m * 2^O(Delta) * poly(Delta).
```

In the frozen JANUS full-ER comparison regime

```text
Delta <= C log n
```

for a fixed universal constant `C`, so

```text
2^O(Delta) = n^O(1).
```

Because the direct input explicitly contains all row truth-table clauses, this translation is polynomial in the actual encoded input length `N`.

---

# 4. Gaussian elimination has short uniform Extended-Frege proofs

Michael Soltys proved that correctness of Gaussian elimination has **uniform polynomial-size Extended-Frege proofs**, including over the field `Z_2 = GF(2)`.

Thus, for a concrete matrix `A` and vector `b`, Extended Frege can feasibly formalize the Gaussian-elimination computation reducing the augmented matrix `[A|b]` to row-echelon form.

If `Ax=b` is inconsistent, the computed row-echelon form contains a contradiction row

```text
0 ... 0 | 1.
```

The correctness proof plus the concrete polynomial-time elimination trace therefore yields a polynomial-size Extended-Frege derivation that the conjunction of the row equations is false.

This is an asymptotic literature-backed upper-bound route, not a finite-CI inference.

---

# 5. Transfer to Extended Resolution

Cook-Reckhow proof-system theory gives

```text
Extended Frege <->_p Extended Resolution.
```

Krajíček's 2025 Chapter 7 also explicitly treats EF and ER as p-equivalent strong proof systems.

Therefore the polynomial-size Extended-Frege refutation transfers with polynomial overhead to an Extended-Resolution refutation.

Combining Sections 3–5:

### Theorem D6-PARITY-ER-UPPER

For the frozen direct parity-NW family with

```text
Delta = O(log n),
m = poly(n),
```

there is a universal polynomial `p` such that every inconsistent instance has an Extended-Resolution refutation of size

```text
<= p(N),
```

where `N` is the actual encoded bit length of the direct CNF.

---

# 6. Consequence for the existing JANUS restricted lower bounds

The new theorem does **not** invalidate the established locality-restricted results.

Instead it identifies the escape mechanism precisely:

```text
NW-LOCAL / restricted Resolution
    cannot cheaply perform global parity aggregation,

FULL ER / EF
    can introduce global parity abbreviations
    and formalize Gaussian elimination.
```

Hence the earlier restricted superpolynomial extension-count / crossing / polarity tradeoffs remain valid within their stated restricted scope. They now serve as a controlled comparison showing which global derivational operation defeats the local obstruction.

---

# 7. Route closure

Freeze:

```text
PARITY_NW_AS_RESTRICTED_RESOLUTION_BENCHMARK = RETAIN
PARITY_NW_AS_FULL_ER_HARD_FAMILY_CANDIDATE   = CLOSED
```

The following research route is terminated:

```text
PARITY_NW
-> Sokolov local heavy width
-> unrestricted ER lower bound.
```

No future JANUS node may cite the restricted parity-NW lower bound as evidence that the same family could be superpolynomially hard for full ER unless it first overcomes the explicit Gaussian-elimination upper bound—which would be a contradiction.

---

# 8. Impact on D6-D2 Chapter-7 expansion branch

The Chapter-7 ER expansion criterion remains valid and valuable, but the hard family `H'` used for a genuine full-ER lower-bound attempt must **not** be this linear parity-NW family.

The tree-model warning found during the audit is consistent with the upper bound: parity constraints are algebraically transparent and locally testable. A polylogarithmic-query computation can evaluate one `O(log n)` parity neighborhood, while ER/EF can globally combine the equations by linear algebra.

Therefore D6-D2 must now split:

```text
D6-D2-PARITY = NEGATIVE CONTROL / ROUTE CLOSED
D6-D2-NEW-H  = search for a non-linear / ER-plausibly-hard H' compatible with the Chapter-7 expansion criterion.
```

---

# 9. What this does not establish

This polynomial upper bound does not establish universal ER p-boundedness.

It does not solve #217 positively for all CNFs.

It does not yield a deterministic polynomial SAT algorithm for arbitrary CNFs.

It does not imply `P=NP`.

It closes only the parity-NW family as a candidate for a **full ER lower bound**.

---

# 10. New hard-family admission rule

Before JANUS invests in a new candidate `H'` for full ER hardness, it must pass an **upper-bound kill sweep**:

1. no known polynomial EF/ER proof from linear algebra, counting, symmetry, BDDs or standard preprocessing;
2. no polynomial p-reduction to a family already known easy for EF/ER;
3. the candidate's global contradiction must not be decidable by a known polytime algorithm whose correctness is already known to have short EF proofs without a separate hardness barrier;
4. Chapter-7 expansion/tree-model falsifier must not have an obvious polylog-depth witness to an error;
5. all claims remain literature-checked and source-bound.

Passing this sweep is necessary, not sufficient, for full-ER candidacy.

---

# 11. Claim firewall

```text
PARITY_ER_UPPER_BOUND
!=
ER_P_BOUNDED_FOR_ALL_FORMULAS

PARITY_ROUTE_CLOSED
!=
ISSUE_217_CLOSED

RESTRICTED_NW_LOWER_BOUND
!=
FULL_ER_LOWER_BOUND

POLY_ER_FOR_PARITY
!=
P_EQUALS_NP

P_VS_NP = OPEN
```
