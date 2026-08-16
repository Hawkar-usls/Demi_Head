# DemiHead Mechanics Hardening v1.1

This layer polishes two concrete edge cases found during review without rewriting the already frozen v1 truth-guard implementation or its 17-case development holdout.

## 1. Reviewer dependency collapse

The v1 reviewer gate correctly prevented two submissions with the same declared `independence_root_id` from counting as two independent roots. However, structural independence could still be overstated when:

- the same `reviewer_id` appeared under two different declared roots; or
- two differently named roots shared one or more `evidence_root_ids`.

v1.1 therefore derives **effective review components**. Submissions are conservatively collapsed into the same component whenever they share a declared root, reviewer id, or evidence root.

Canonical laws:

```text
DECLARED_ROOT_ID != PROVEN_INDEPENDENCE
SAME_REVIEWER_ID => SAME_EFFECTIVE_REVIEW_COMPONENT
SHARED_EVIDENCE_ROOT => SAME_EFFECTIVE_REVIEW_COMPONENT
REVIEWER_COUNT != INDEPENDENT_ROOT_COUNT
STRUCTURAL_INDEPENDENCE != REAL_WORLD_IDENTITY_PROOF
```

Missing evidence-root metadata cannot produce a v1.1 consensus terminal. It remains an open review state.

This still does **not** prove reviewer identity, expertise, honesty, alias uniqueness, collusion resistance, organizational independence, or real-world independence.

## 2. Correction identifier immutability

The v1 correction propagator preserved history and safely handled cyclic provenance, but accepted a repeated `correction_id`. The same logical id could therefore appear both pending and verified or produce ambiguous duplicate annotations.

v1.1 rejects duplicate correction ids before propagation:

```text
CORRECTION_ID != REUSABLE_MUTATION_CHANNEL
DUPLICATE_CORRECTION_ID => INVALID_GRAPH
CORRECTION != DELETION
```

## Frozen-v1 boundary

The existing corpus at `holdout/truth_guard_v1/frozen_corpus.json` is not edited. Dedicated CI replays it at the original freeze SHA-256:

```text
4c658ea1532042e2c5db0298285335bbbb9e3e61ab21afd453ff0c846971201f
```

and still requires exactly `17/17 PASS`.

The v1.1 mechanics are a new versioned hardening layer, not a retroactive claim that the old frozen implementation already contained these protections.
