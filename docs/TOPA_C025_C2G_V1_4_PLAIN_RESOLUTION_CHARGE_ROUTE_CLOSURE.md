# TOPA C025-C2G v1.4 — Plain-Resolution Charge Route Closure

**Frozen:** 2026-08-24  
**Parents:** `TOPA_C025_C2G_V1_3_SELECTOR_LIFT_DERIVATIONAL_BARRIER.md`, `TOPA_POLICY0B1_RESOLUTION_LOWER_BOUND_ROUTE_CLOSURE.md`  
**Status:** `PLAIN_RESOLUTION_FORK_CHARGE_POLY_ROUTE_REFUTED`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Goal

C2G v1.2 shows that short laminar fork charges would give a polynomial state bound. v1.3 shows that even a width-1 charge can hide the entire original proof complexity.

This note turns that observation into an unconditional route closure for **plain Resolution proof-carrying reasons** using the classical pigeonhole lower bound.

---

# 2. Selector-lifted pigeonhole family

Let

```text
H_n := PHP_{n+1}^n
```

be the standard pigeonhole-principle CNF, with all its variables renumbered above `1`.

Let fresh selector `s` have root id `1`, and define

```text
F_n := Sel_s(H_n)
     := { (s OR C) : C in H_n }.
```

Properties:

```text
F_n is SAT by s=1;
F_n|s=0 = H_n is UNSAT;
F_n |= s.
```

Haken's theorem gives

```text
RES_SIZE(H_n) >= 2^(Omega(n)).
```

By the selector-lift theorem, any plain Resolution derivation

```text
F_n |- s
```

restricts at `s=0` to a Resolution refutation of `H_n`, and conversely. Therefore

```text
RES_SIZE(F_n |- s) >= 2^(Omega(n)).
```

---

# 3. Why Policy-0B.1 actually reaches the selector fork

Policy-0B.1 root preprocessing performs only a fixed polynomial amount of explicit Resolution/UP work in the root input size.

If root preprocessing derived unit `(s)`, its recorded Resolution-contained derivation would yield a polynomial-size Resolution proof of `(s)` from `F_n`.

Restricting `s=0` would give a polynomial Resolution refutation of `H_n`, contradicting Haken for sufficiently large `n`.

Hence for all sufficiently large family members root preprocessing reaches a non-conflicting fixpoint without deriving `(s)`.

Because `s` has the smallest root id and occurs in the residual formula, the frozen branch rule selects `s`.

False-first execution:

```text
first child s=0 -> H_n -> UNSAT;
second child s=1 -> all lifted root clauses satisfied -> SAT.
```

Thus the root is an actual binary fork in the explored Policy-0B.1 execution.

---

# 4. The charge clause is forced

At the moment the first child returns UNSAT, the root decision context is exactly

```text
rho = {s=0}
```

(up to no other root decisions at this root fork).

C2G requires the charge root clause to be falsified by the first-child root context.

A partial assignment falsifies a clause only if it assigns and falsifies **every** literal of that clause.

Since `rho` assigns only root `s`, every nonempty non-tautological root clause falsified by `rho` must be exactly

```text
(s).
```

Therefore the charge geometry has no alternative:

```text
C_root = (s).
```

Its width is `1`; laminarity is trivial. The only remaining cost is its derivation.

---

# 5. Plain-Resolution proof-byte lower bound

Any standalone plain-Resolution proof-carrying certificate for the required charge `(s)` has size at least

```text
2^(Omega(n)).
```

Thus the v1.2 coupled requirement

```text
POLYNOMIAL TOTAL CHARGE-PROOF BYTES
```

fails for the plain-Resolution reason language on the selector-PHP family.

A deterministic algorithm cannot output an exponential certificate in polynomial bit time. Therefore universal polynomial-time plain-Resolution charge discovery also fails on this family.

### C2G-R1 — plain-reason route closure

```text
C2G_WITH_PLAIN_RESOLUTION_REASONS
```

cannot satisfy the universal polynomial proof-byte/discovery gates required for the constructive closure route.

This is an unconditional proof-system-specific lower bound.

---

# 6. Why B2 / Extended Resolution is not closed by this theorem

Haken's original result and subsequent proof-complexity literature explicitly contrast the exponential Resolution lower bound with polynomial-size Extended-Resolution / stronger Frege-style proofs of pigeonhole formulas.

Therefore the selector-PHP family does **not** establish an analogous B2/ER charge-proof lower bound.

Instead it cleanly separates the architecture:

```text
PLAIN RESOLUTION CHARGE     -> exponentially large proof on selector-PHP
B2 / EXTENDED RESOLUTION    -> proof-size escape is available for PHP
```

The remaining B2 problem is deterministic discovery/global amortization, not this plain proof-size obstruction.

---

# 7. Project consequence

Policy-0B.2 cannot reach the constructive `P=NP` closure route by combining:

- Policy-0B.1 branching;
- the C025-B plain Resolution reason language;
- laminar charge accounting;

alone.

A genuinely stronger reason/discovery mechanism is necessary.

The frozen B2 extension-aware language is the current admitted stronger candidate, but its universal proof-size and deterministic discovery gates remain open.

---

# 8. Status

```text
C2G_SELECTOR_PHP_ROOT_FORK                     = PROVED_FOR_SUFFICIENTLY_LARGE_n
C2G_SELECTOR_PHP_ONLY_CONTEXT_CHARGE            = (s)
C2G_PLAIN_RES_CHARGE_PROOF_SIZE                 = 2^Omega(n)
C2G_PLAIN_RES_POLY_PROOF_BYTES                  = REFUTED
C2G_PLAIN_RES_POLY_DISCOVERY                    = REFUTED
C2G_B2_ER_CHARGE_PROOF_SIZE                     = NOT_REFUTED_BY_PHP
C2G_B2_ER_DETERMINISTIC_DISCOVERY               = OPEN / NEXT
P_VS_NP                                         = OPEN
```

---

# 9. Claim firewall

```text
PLAIN_REASON_ROUTE_CLOSED
!=
B2_ER_ROUTE_CLOSED

PHP_RESOLUTION_LOWER_BOUND
!=
ER_LOWER_BOUND

POLICY0B2_NEEDS_STRONGER_REASONING
!=
P_EQUALS_NP

P_VS_NP = OPEN
```

## Literature anchor

A. Haken, *The intractability of resolution*, Theoretical Computer Science 39 (1985), 297–308: exponential Resolution lower bound for pigeonhole formulas; the abstract notes polynomial-length Extended-Resolution proofs are available for the same formulas.
