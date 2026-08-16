# Reviewer Collection and Disagreement Gate

This gate reuses bounded review methodology from Fast-CAT-SHAiTan without transferring feline evidence or biological claims.

The software answers two questions only:

1. Is the submitted reviewer collection structurally admissible for the same frozen case package?
2. If enough admissible reviewer bundles exist, which declared fields are exactly unanimous?

It does not prove that a reviewer is a real independent human, competent, honest, institutionally independent, or free from off-channel coordination.

## Collection states

```text
0 admissible reviewers -> WAITING_FOR_FIRST_REVIEWER
1 admissible reviewer  -> WAITING_FOR_SECOND_REVIEWER
>= required reviewers  -> READY_FOR_CONSENSUS
any binding failure     -> INVALID_COLLECTION
```

Waiting is a valid state, not a failed experiment.

## Bundle requirements

Each reviewer bundle declares:

- `reviewer_id`
- `attestation_id`
- the exact `frozen_package_id`
- `verifier_status = PASS`
- `declared_independent = true`
- `labels_frozen_before_model_reveal = true`
- all fields named by the frozen `review_fields` policy

Reviewer IDs and attestation IDs must be distinct.

These declarations and identifiers are software-checkable artifacts. They are not personhood or independence proofs.

## Exact-unanimity rule

For each review field independently:

```text
all reviewer values identical -> preserve that value
anything else                  -> DISAGREEMENT
```

There is no majority vote, averaging, model completion or adjudication in v1.

A 2-to-1 split among three reviewers is therefore still:

```text
DISAGREEMENT
```

not the majority value.

## Constitutional boundary

```text
DISAGREEMENT != ERROR
REVIEWER_COUNT != TRUTH_WEIGHT
REVIEWER_ID != INDEPENDENCE_PROOF
ATTESTATION != PERSONHOOD_PROOF
UNANIMITY != OBJECTIVE_TRUTH
WAITING != FAILURE
MODEL_MAY_NOT_FILL_DISAGREEMENT
REVIEW_COLLECTION != WORLD_AUTHORITY
```

The gate keeps:

```text
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

## First Portal relationship

The JANUS First Portal may route the user or an application toward a review workflow, but routing does not create consensus:

```text
PORTAL_ROUTE != REVIEW_CONSENSUS
```

## Claim ceiling

Synthetic reviewer fixtures establish software behavior only. They are not real reviewer evidence.

A future real deployment must bind reviewer submissions to an independently defined frozen package and must separately define reviewer recruitment, competence, privacy, conflict-of-interest and human-governance procedures.
