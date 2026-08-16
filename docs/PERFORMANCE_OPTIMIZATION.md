# Bounded Performance and Optimization

This document records the small operational layer added after the KETO/CALAMAR cross-repository audit.

The purpose is not to make evidence "win faster." It is to reduce avoidable operational work while preserving exactly the same evidence, provenance, authority and user-rights boundaries.

```text
FASTER != TRUER
FLOW_CONTROL != EVIDENCE_CONTROL
QUEUE_PRIORITY != TRUTH_PRIORITY
BEST_SCORE != TRUTH
OPTIMIZE_OPERATION != OPTIMIZE_BELIEF
```

## KETO flow gate

Source pattern: `Hawkar-usls/janus-io-public` at audit snapshot `1b53c367d480598398f2d91427ce4669b8aa7c62`.

The source repository demonstrated a domain-specific admission/drain sequence in its own PoW experiment. DemiHead does **not** import mining semantics or the source repository's performance claims. It reuses only the bounded scheduling shape:

```text
OPEN
-> exact bounded admission
-> HOLD
-> DRAIN
-> CLEAN_VALLEY
-> REOPEN if another bounded wave is allowed
```

The reference implementation is [`../tools/flow_gate.py`](../tools/flow_gate.py).

It is a deterministic state/accounting model; it does not sleep and it does not claim wall-clock acceleration. Work outside the configured wave budget remains explicitly `deferred` rather than becoming false, failed or erased.

Hard boundary:

```text
DEFERRED != FALSE
MISSING_LATENCY != ZERO
SCHEDULING != EVIDENCE
```

## Constitution-bound optimizer admission

Source pattern: `Hawkar-usls/Janus-Demiurge` at audit snapshot `e837431bb788a873b07d672667d8a8506baabcdc`.

Only the ordinary operational pattern is retained:

```text
candidate configuration
-> frozen evaluation
-> tell observed operational metrics
-> preserve trial history
-> rank admitted candidates
```

The legacy `tachyonic`, digital-root and `filter_37` heuristics are not inherited. The broad input/audio/screen monitoring surfaces of the legacy sandbox are also not inherited.

The reference admission layer is [`../tools/constitution_optimizer.py`](../tools/constitution_optimizer.py). It currently ranks already-measured frozen trials deterministically. A GP/EI proposer is intentionally **not** implemented in this gate.

Allowed objectives are operational quantities such as latency, CPU time, memory, timeout rate and operational error rate. The following classes of objective are fail-closed:

```text
engagement
belief_change
persuasion
political_conversion
compliance
source_suppression
user_vulnerability
truth_score
authority_score
```

Any provenance loss, freshness-policy violation, evidence-state mutation, constitutional violation, authority growth or mass-effect growth rejects the candidate regardless of operational score.

## Why the proposer comes later

`MEASURE_BEFORE_OPTIMIZING` applies to the optimizer itself.

Before comparing GP/EI, random search, grid search or another proposer, DemiHead first needs a stable admission boundary that makes unsafe objectives impossible to promote. The proposer can then compete behind the same boundary on a frozen benchmark.

This ordering also makes a negative result meaningful: if no candidate beats baseline under the constitutional constraints, the correct result is `NO_OPERATIONAL_IMPROVEMENT_ESTABLISHED`.

## Shaitan trace

Fast-CAT-SHAiTan remains a source of blinded-review and disagreement-preservation methodology. The cat tribute is deliberately nonfunctional:

```text
THE_CAT_MAY_PURR; THE_RECEIPT_STILL_HAS_TO_VERIFY
```

It changes no evidence weight, authority or mass-effect budget.

## Claim ceiling

The current reference heads establish deterministic scheduling/accounting and optimizer-admission behavior only. They do **not** establish that DemiHead is faster, cheaper or more resource-efficient.

A performance claim requires a separately frozen benchmark with at least a baseline, candidate configurations, exact workload identity, repeated measurements, p50/p95/p99 latency, resource measurements, failure accounting and an independent holdout that was not used to tune the candidate.
