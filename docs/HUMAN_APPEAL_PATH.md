# Human Appeal Path

The Human Appeal path is a governance receipt, not an automatic override mechanism.

A person may contest a bounded DemiHead decision/review receipt. The appeal is bound to the exact submitted decision by canonical SHA-256 and the original decision is preserved append-only alongside the appeal and any later resolution.

```text
APPEAL != ADMISSION_OF_ERROR
APPEAL_REQUEST != OUTCOME_OVERRIDE
HUMAN_REVIEW != SILENT_HISTORY_REWRITE
```

## Grounds

The v1 reference gate accepts bounded grounds:

- `SOURCE_MISSING`
- `SOURCE_MISATTRIBUTED`
- `CORRECTION_MISSING`
- `LANGUAGE_SEMANTIC_DRIFT`
- `REVIEW_DISAGREEMENT`
- `PROVENANCE_MISMATCH`
- `OTHER_EXPLAINED`

`OTHER_EXPLAINED` requires a non-empty statement.

## Requested actions

- `INSPECT`
- `CORRECT_LINEAGE`
- `REVIEW`
- `NO_ACTION`

A requested action is a request, not effect authority.

## States

Without a resolution:

```text
APPEAL_RECORDED_NEEDS_HUMAN_REVIEW
```

A bound resolution may produce:

```text
APPEAL_RESOLVED_NO_CHANGE
APPEAL_RESOLVED_NOTE_ADDED
APPEAL_RESOLVED_CORRECTION_LINKED
```

Invalid bindings or resolution semantics produce:

```text
INVALID_APPEAL
```

## Correction linking

A `CORRECTION_LINKED` resolution records a correction identifier only.

It does not apply the correction and does not mutate the underlying evidence state. Application belongs to the already-separated Correction Propagator:

```text
APPEAL_RESOLUTION
    -> correction_id
    -> KETO_CORRECTION_PROPAGATOR
```

Therefore:

```text
CORRECTION_LINK != CORRECTION_APPLICATION
RESOLUTION_LINK != EVIDENCE_MUTATION
```

## Human boundary

The reference gate can require a resolver identifier and verifier `PASS`, but software does not prove that the resolver is a human person, qualified, independent or authorized under a future real institution's governance policy.

Those operational requirements must be defined and audited separately before high-stakes deployment.

## First Portal relationship

The First Portal may expose a route to the appeal path only after an explicit user request. The Portal does not file appeals autonomously and does not decide them.

```text
PORTAL_OPENS_THE_DOOR
APPEAL_PATH_PRESERVES_THE_RECORD
```

## Constitutional boundary

```text
APPEAL != ADMISSION_OF_ERROR
APPEAL_RIGHT != MODEL_DISCRETION
CONTESTED != CLOSED
HUMAN_REVIEW != SILENT_HISTORY_REWRITE
APPEAL_REQUEST != OUTCOME_OVERRIDE
APPEAL_SUBMISSION != EFFECT_AUTHORITY
ORIGINAL_DECISION_ALWAYS_PRESERVED
```

The reference gate keeps authority and mass-effect deltas at zero.

## Claim ceiling

The current implementation can establish only software binding, append-only preservation and bounded resolution-link behavior on submitted fixtures. It does not establish a real public appeals office, legal due process, real human reviewer identity, response-time guarantees or correctness of appeal outcomes.
