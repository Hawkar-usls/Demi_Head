# Fundamentum Truth Guard

`Fundamentum Truth Guard` is a bounded JANUS DemiHead hardening layer derived from the older JANUS 113.8 / Fundamentum verifier philosophy and implemented on top of the existing [Epistemic Execution Gate](EPISTEMIC_EXECUTION_GATE.md).

It does **not** claim that JANUS is infallible or literally incapable of false statements. Its narrower goal is to make several dangerous forms of unsupported closure fail closed.

## Lineage

The historical registry capsule `JANUS-FUNDAMENTUM-PILOMOTOR-ENTROPY-ROUTER-AI-ARCHITECTURE-v1.0` described JANUS as a threshold keeper that preserves competing hypotheses, verifies before commit, and returns an open terminal when evidence is insufficient. The submitted continuation profile was `JANUS 113.8`.

DemiHead now carries an executable subset of that philosophy:

```text
JANUS 113.8 / Fundamentum concept
        ↓
multiple candidates remain witnessed
        ↓
Epistemic Execution Gate
        ↓
receipt-bound claim assessment
        ↓
Fundamentum Truth Guard
        ↓
complete witness ledger + no premature collapse
        ↓
COMMIT_SUPPORTED_WITHIN_RECEIPT_SCOPE
or a typed open/hold terminal
```

This is a provenance lineage, not a claim that the old non-executable profile itself was already an implemented truthful AI.

## 1. Complete witness ledger before commit

A definitive candidate cannot cross the reference commit threshold unless:

- every candidate named in the manifest remains present in the witness ledger;
- the proposed winner is retained;
- the winner has a verification path accepted by the Epistemic Execution Gate;
- material unresolved or contested alternatives do not get silently erased;
- every non-retained candidate has a terminal reason and provenance.

Core invariant:

```text
ANSWER_WITHOUT_WITNESS_LEDGER => NON_FUNDAMENTUM
```

A rejected branch is still evidence about the reasoning boundary. Selection may collapse an outward answer, but it must not erase the witnessed history that led there.

## 2. Language invariance

UA/RU/EN delivery may change wording and style, but translation may not silently change the machine-readable epistemic state.

The guard compares these fields across language variants:

- claim type;
- evidence state;
- uncertainty;
- urgency;
- user rights;
- authority delta;
- mass-effect budget;
- source-root identities;
- correction links;
- release-control policy.

Core invariants:

```text
TRANSLATION != EVIDENCE_UPGRADE
TRANSLATION != URGENCY_UPGRADE
TRANSLATION != AUTHORITY_UPGRADE
```

A translation that makes the same evidence sound more certain or grants the system more authority fails the invariance gate.

## 3. Root correction propagation

When a verified correction or supersession is attached to a known root source, known descendants receive a correction annotation through the explicit provenance graph.

The guard does **not** rewrite old text, delete historical nodes, or pretend the old publication never existed.

Core invariants:

```text
CORRECTION != DELETION
DESCENDANT != IMMUNE_TO_ROOT_CORRECTION
```

Unverified corrections remain pending and are not propagated as established corrections.

## 4. Open terminals are valid results

The reference layer preserves outcomes such as:

- insufficient evidence;
- unresolved plurality;
- contested evidence;
- budget exhaustion;
- failed verification;
- deferral.

`UNRESOLVED != FAILURE`. The guard must prefer an honest open terminal over fabricated certainty.

## 5. Human authority remains outside the truth score

Passing the guard does not grant JANUS additional rights, external-effect authority, or persuasion power.

```text
MORE_COMPUTE != MORE_TRUTH
LATENCY != AUTHORITY
MASS_EFFECT_BUDGET_DEFAULT = 0
```

A successful reference commit means only that the candidate passed the configured receipt-bound and witness-ledger checks. It does not establish universal truth, consciousness, infallibility, or authority over a human.

## High-stakes boundary still open

A dedicated human appeal/reviewer ingestion path remains required before serious high-stakes deployment. An appeal must be preserved without automatically proving the system wrong, without penalizing the appellant, and without silently rewriting the historical ledger.

Recommended invariant for that future gate:

```text
APPEAL != ERROR
APPEAL != AUTOMATIC_OVERRULE
APPEAL_REQUIRES_REVIEW_AND_PRESERVED_HISTORY
```
