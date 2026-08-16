# Frozen Truth-Guard Adversarial Holdout v1

This directory freezes a synthetic adversarial corpus **before its first scored execution**.

Freeze identity:

```text
SHA-256 4c658ea1532042e2c5db0298285335bbbb9e3e61ab21afd453ff0c846971201f
cases   17
```

The SHA-256 is computed over canonical JSON of `freeze_payload` in `frozen_corpus.json`. The runner verifies the digest before executing any case. Any mutation to a payload, expected result, case identity, count, or claim ceiling invalidates the freeze and stops the run.

The corpus attacks the current local reference chain across these failure families:

- model-only fake verification;
- real execution-receipt acceptance;
- stale current-state evidence;
- missing witness-ledger entries;
- premature collapse while material alternatives remain live;
- translation-induced urgency escalation;
- translation-induced authority escalation;
- verified correction propagation to descendants;
- correction-graph cycles;
- unverified correction promotion;
- appeal-package tampering;
- reviewer-count inflation from one independence root;
- preservation of independent disagreement;
- correction consensus without automatic rewrite/effect;
- punishment for appeal;
- surveillance escalation for appeal;
- reviewer-count-to-authority multiplication.

The acceptance rule is intentionally exact:

```text
17 / 17 PASS
```

There is no score averaging and no post-hoc threshold tuning in this corpus.

## Claim ceiling

A PASS establishes only that the current deterministic local implementations satisfy these pre-frozen synthetic cases at the tested commit. It does **not** establish universal truthfulness, real-world reviewer independence, external validation, misinformation-detection effectiveness, production readiness, consciousness, or authority over a human.

A future genuinely independent holdout must be authored outside this frozen development corpus and must remain blinded until the implementation and expected evaluation policy are sealed.
