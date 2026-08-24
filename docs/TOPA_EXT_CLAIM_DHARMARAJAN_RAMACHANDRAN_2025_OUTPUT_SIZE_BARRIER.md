# TOPA EXT Claim Audit — Dharmarajan & Ramachandran 2025 Power-Set Route

**Source:** public preprint `A Problem in Power Sets Shows P Does Not Equal NP`, v2 (2025).  
**Status:** `P_NOT_EQUAL_NP_CONCLUSION_NOT_ESTABLISHED_BY_OUTPUT_SIZE_ARGUMENT`.  
**Global ceiling:** `P_VS_NP = OPEN`.

## 1. What the source proves about the computation task

The paper defines the power-set computation problem: given a finite nonempty set `X`, output its full power set `P(X)`.

For `|X|=n`, the output contains `2^n` subsets. Therefore any explicit-output algorithm must perform at least output-linear work in the number of emitted atomic objects. The paper's Proposition 4.2 uses exactly this observation to conclude that the full-enumeration task cannot run in time polynomial in `n`.

As an output-size lower bound for the **function/enumeration problem**, this observation is elementary and valid under the stated explicit-output model.

## 2. Category mismatch at the P-vs-NP conclusion

The classes `P` and `NP` in the standard P-vs-NP question are classes of **decision languages**. The paper itself separately defines computation/optimization and decision variants.

To establish `P != NP`, one must exhibit a decision language `L` satisfying

```text
L in NP
L notin P.
```

But the lower-bound proof in Proposition 4.2 does not prove a time lower bound for the decision language. It returns to the full-output computation task and argues that a solver must output all subsets of `P(X)`.

A yes/no decider does not have to emit those `2^n` objects. Therefore

```text
EXPONENTIAL_EXPLICIT_OUTPUT_SIZE
```

does not transfer to

```text
DECISION_LANGUAGE_REQUIRES_EXPONENTIAL_TIME.
```

### Exact invalid transfer

```text
FULL_POWER_SET_ENUMERATION_NOT_POLYTIME_IN_n
-X->
DECISION_VARIANT_NOT_IN_P
```

No reduction/theorem in the cited argument closes this gap.

Hence Proposition 4.2 cannot supply the `L notin P` premise needed for the stated P-vs-NP conclusion.

```text
DHARMARAJAN_RAMACHANDRAN_2025_OUTPUT_LOWER_BOUND = VALID_FOR_EXPLICIT_ENUMERATION_SCOPE
DHARMARAJAN_RAMACHANDRAN_2025_DECISION_LOWER_BOUND = NOT_PROVED
DHARMARAJAN_RAMACHANDRAN_2025_P_NOT_EQUAL_NP_ROUTE = NOT_ESTABLISHED
```

## 3. Additional input-size firewall

For NP verification, running time is polynomial in the total encoded input length, including the certificate. Any construction that permits a certificate object whose own representation is exponential in `n` cannot simply charge verification only in `n` and call that the standard NP definition. A separate encoding-size audit is required.

This is secondary to the main category mismatch above but must be enforced in all JANUS imports.

## 4. Reusable JANUS law

```text
OUTPUT_SIZE_LOWER_BOUND_FOR_FUNCTION
!=
DECISION_TIME_LOWER_BOUND

FUNCTION_PROBLEM
!=
LANGUAGE_WITHOUT_A_PROVED_REDUCTION

CERTIFICATE_VERIFICATION_COST_MUST_BE_MEASURED_IN_TOTAL_ENCODED_INPUT
```

This law is now a mandatory falsifier for future P-vs-NP closure claims based on enumeration, listing, generation, or explicit construction of exponentially large objects.

`P_VS_NP = OPEN`.
