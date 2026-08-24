# TOPA C025-C2 — ER Automatability / Cryptographic Barrier

**Frozen:** 2026-08-24  
**Arbiter home:** `Hawkar-usls/Demi_Head`  
**Scientific lineage:** `Hawkar-usls/TOPA` + `Hawkar-usls/Janus-Fundamentum`  
**Status:** `CONDITIONAL_EXTERNAL_BARRIER_RECORDED__C2_REMAINS_OPEN`  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. Why this gate matters

The constructive Policy-0B closure route needs more than short B2/ER proof objects. It needs a deterministic algorithm that finds the required extensions/proof in total work polynomial in original input length.

This is the C025-C2 proof-discovery gate.

Since frozen B2 and Extended Resolution are p-equivalent to Extended Frege, proof-search results for EF/ER are directly relevant to the scale of this obligation.

## 2. Known conditional hardness of efficient proof search

The classical line initiated by Krajíček and Pudlák and developed by Bonet, Pitassi and Raz shows conditional non-automatability results for strong Frege systems: under standard cryptographic security assumptions such as security of RSA or Diffie-Hellman, Extended Frege cannot be efficiently/weakly automated in the relevant sense.

Modern work on automatability continues to cite this result as the classical strong-system barrier.

Because

```text
EF <->_p ER,
```

a generic automatability theorem transfers between the p-equivalent systems with polynomial overhead.

Therefore, conditional on the cited cryptographic assumptions, a general efficient ER proof-search algorithm of the corresponding strength does not exist.

## 3. Correct JANUS interpretation

This is **not an unconditional lower bound** on Policy-0B discovery.

Cryptographic security is an assumption, not a theorem of mathematics.

Moreover if JANUS eventually proved

```text
P = NP,
```

then the standard one-way-function/cryptographic assumptions underlying the barrier would themselves fail. Thus there is no logical contradiction between the project target and the conditional literature.

The correct conclusion is only:

```text
C2 IS NOT AN ORDINARY ENGINEERING GAP.
```

A positive universal polynomial C2 theorem would have consequences strong enough to invalidate widely used cryptographic assumptions.

## 4. Relation to the Closure Gate

The constructive closure chain remains:

```text
short proof/certificate objects
+
poly active representation
+
deterministic poly discovery (C2)
+
frozen total solver
+
poly total bit complexity
=> P = NP.
```

The cryptographic barrier does not remove C2 from this chain and cannot replace its proof.

It serves only as an external scale marker:

```text
A CLAIM THAT C2 IS SOLVED MUST BE STRONG ENOUGH
TO SURVIVE THE KNOWN AUTOMATABILITY LITERATURE.
```

## 5. Search-vs-verification firewall

Freeze permanently:

```text
ER_CERTIFICATE_CHECKING_IN_POLY(|pi|)
!=
ER_PROOF_SEARCH_IN_POLY(N)

ER_P_BOUNDEDNESS
!=
ER_AUTOMATABILITY

SHORT_PROOF_EXISTS
!=
POLYTIME_DISCOVERY.
```

A future positive proof-size theorem does not automatically close C2.

## 6. Allowed future results

### C2-POSITIVE
A deterministic algorithm with a proved universal fixed-polynomial bound in original input length that discovers all objects required by the frozen Policy-0B machine.

This would be a major complexity result and would simultaneously imply failure of the cryptographic assumptions used in the conditional non-automatability results once the rest of the P=NP closure chain is proved.

### C2-NEGATIVE-CONDITIONAL
A cryptographic-assumption-based impossibility result.

Useful as an external barrier but insufficient to prove `P!=NP`.

### C2-NEGATIVE-UNCONDITIONAL
An unconditional lower bound against the exact discovery model. Such a result must state its implication to P-vs-NP separately; a lower bound on one solver architecture alone does not imply `P!=NP`.

## 7. Claim firewall

```text
CRYPTOGRAPHIC_NON_AUTOMATABILITY
!=
UNCONDITIONAL_C2_LOWER_BOUND

RSA_SECURITY_ASSUMPTION
!=
MATHEMATICAL_AXIOM

C2_HARD_UNDER_CRYPTO
!=
P_NOT_EQUAL_NP

C2_OPEN
!=
P_VS_NP_CLOSE

P_VS_NP = OPEN
```
