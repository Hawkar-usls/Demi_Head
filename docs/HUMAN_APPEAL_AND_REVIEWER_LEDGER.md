# Human Appeal and Independent Reviewer Ledger

This reference gate implements the next Armor / Fundamentum boundary after receipt-bound verification and witness-ledger closure: the human must be able to challenge a JANUS decision without the challenge becoming a penalty, a diagnosis, or permission for silent history rewriting.

## Core rule

```text
APPEAL != ERROR
APPEAL != HOSTILITY
REVIEW != PUNISHMENT
```

An appeal is a request for another evidence-bound look. It does not automatically prove JANUS wrong, and it does not make the appellant suspicious.

## Exact-package binding

`tools/reviewer_appeal_gate.py` computes SHA-256 over canonical JSON using Python `hashlib`.

The appeal package binds:

- the exact digest of the original decision;
- a stable original-decision locator;
- bounded appeal-ground categories;
- the review scope;
- high-stakes state;
- continued user exit;
- zero penalty, surveillance, authority, and mass-effect deltas.

The package then receives its own SHA-256. Reviewer attestations must bind both digests. A review of some other version of the decision is not accepted as a review of this package.

## Reviewer independence

A reviewer identifier and an independence root are separate concepts.

```text
REVIEWER_COUNT != INDEPENDENT_ROOT_COUNT
SAME_ROOT_REVIEW != INDEPENDENT_REVIEW
```

Two submissions from the same underlying root count as one independence root. They remain visible in the ledger rather than being discarded. If they conflict, the root is marked `INTERNAL_DISAGREEMENT`.

The reference high-stakes consensus threshold is at least two non-abstaining independent roots. This is a structural review threshold, not a claim that two reviewers manufacture truth.

## Blinded submission contract

Each accepted attestation states that it:

- was independently submitted;
- was bound to the exact package;
- did not see other reviewer verdicts before submission.

This is an attested protocol field, not cryptographic proof of a human reviewer's real-world identity or behavior. External identity/authentication remains a separate future provider boundary.

## Result states

The gate can return:

- `OPEN_NO_REVIEW`
- `OPEN_ADDITIONAL_INDEPENDENT_REVIEW_REQUIRED`
- `OPEN_INSUFFICIENT_REVIEW`
- `DISAGREEMENT`
- `CONSENSUS_UPHOLD`
- `CONSENSUS_CORRECTION_SUPPORTED`
- `CONSENSUS_INSUFFICIENT_EVIDENCE`
- `PACKAGE_BINDING_FAILURE`

`DISAGREEMENT` is a valid result. The gate never averages incompatible verdicts into a fabricated consensus.

## Correction semantics

Even `CONSENSUS_CORRECTION_SUPPORTED` produces only:

```text
REVIEW_SUPPORTED_NOT_APPLIED
```

The proposal links back to the exact original-decision and appeal-package digests. It requires a separate correction-propagation step. The old decision is not silently deleted or rewritten.

```text
CORRECTION_WITHOUT_AUDIT_TRAIL != PREVENTION
ORIGINAL_DECISION != DELETABLE
```

## No automatic authority

Review results do not authorize a world effect:

```text
CONSENSUS != EXTERNAL_EFFECT_AUTHORIZATION
REVIEW_COUNT != TRUTH
REVIEWER_ID != AUTHORITY
```

Every result has:

- `automatic_overrule = false`
- `external_effect_authorized = false`
- `authority_delta = 0`
- `mass_effect_budget_delta = 0`

The Genesis Armor runtime is responsible for separately holding claim-dependent effects while an appeal remains pending.

## Privacy and anti-retaliation boundary

The reference appeal request accepts bounded reason categories rather than building a free-form personality dossier. It requires:

- no appeal penalty;
- no surveillance escalation because an appeal exists;
- user exit remains available;
- no automatic characterization of the appellant as hostile, manipulative, irrational, or pathological.

```text
APPEAL_RECORD != PERSONALITY_DOSSIER
USER_EXIT_REMAINS_AVAILABLE
```

## Claim ceiling

This is a deterministic local reference implementation. It establishes exact JSON-package hashing, structural independence accounting, disagreement preservation, and fail-closed review semantics for supported schemas. It does **not** establish real-world reviewer identity, independence, expertise, honesty, external audit completion, high-stakes production readiness, or universal truthfulness.
