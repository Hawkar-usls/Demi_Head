# JANUS DemiHead — Frozen Browser Performance Baseline v1

Status: **baseline-only candidate; no optimization claim is permitted from this document alone**.

This experiment is deliberately separate from the admitted functional Chromium/localStorage gate. The functional gate established that the frozen UI path works on synthetic localhost data. This experiment measures how long and how resource-intensive that same path is on one CI runner/browser configuration before any performance tuning is attempted.

## Frozen before first measurement

Protocol:

- `holdout/browser_performance_baseline_v1/frozen_protocol.json`
- canonical freeze SHA-256: `1434413edcc37317a0a1b748e074428b1c1ec9c4c58380871d3860d18a4e0da1`
- DemiHead: `467e31ff3f6a2bb26af2aea21d97d20f2cc448c6`
- HRain: `ceb81210c2f70b71d6c941e0b088a68969ead7b9`
- iNaiHR: `b27cd8732b3137caea1036024acc1778ea02213a`
- Playwright: `1.55.0`
- Chromium: headless runtime installed by Playwright
- fixture origin: `http://127.0.0.1:8766`
- live user data: `false`
- external network effects: `false`

Workload:

- 3 warm-up cycles per hemisphere, excluded from latency/resource admission samples;
- 20 measured cycles for `LEFT_HRAIN`;
- 20 measured cycles for `RIGHT_INAIHR`;
- 40 measured cycles total;
- synthetic workspace reset before every cycle;
- 100 observer/control-plane roundtrips measured separately and **not subtracted**.

Each measured cycle performs the same ordered UI path:

1. `sidecar_export`
2. `proposal_build`
3. `proposal_download`
4. `apply_preview`
5. `apply_decline`
6. `apply_repreview`
7. `apply_accept`
8. `reload_verify`
9. `full_validation_cycle` as the complete cycle wall-clock metric.

The workload is frozen before measurement and is not changed after observing baseline numbers.

## Wall-clock measurement

Operation timing uses Node `process.hrtime.bigint()` around each real Playwright/UI operation.

For every operation the receipt reports:

- `n`
- minimum
- mean
- p50
- p95
- p99
- maximum

Quantiles use the preregistered nearest-rank method.

There are intentionally **no latency thresholds** in the baseline protocol. A slow but correctly measured run is still a valid baseline.

```text
BASELINE_MEASUREMENT != PERFORMANCE_WIN
```

## Observer overhead

The harness measures 100 `page.evaluate(() => performance.now())` roundtrips as a separate control-plane/observer overhead distribution.

That overhead is reported and never subtracted from the measured operation values. No post-hoc correction is allowed.

## Resource measurements

The baseline samples Chromium process IDs using CDP `SystemInfo.getProcessInfo` after measured operations.

It reports:

- observed Chromium process CPU-time delta across samples;
- peak sum of Linux `/proc/<pid>/status` `VmRSS` for Chromium process IDs visible at a sample;
- peak page `JSHeapUsedSize`;
- peak page `JSHeapTotalSize`.

The CPU value is explicitly scoped to observed process lifetimes between samples; CPU used before a new process is first observed is not reconstructed. RSS is an observed peak at sampling points, not an omniscient continuous maximum.

These metrics are suitable for a frozen CI baseline and later same-protocol comparisons, not for claiming universal hardware resource usage.

## Admission semantics

The baseline gate requires:

- 40 measured cycles total;
- exactly 40 samples for every operation and the full cycle;
- zero harness errors;
- zero timeouts;
- zero browser page errors;
- zero attempted external HTTP(S) requests outside the localhost fixture origin;
- resource metrics present.

It does **not** require a particular latency or memory number.

The baseline cannot compare candidates and the protocol explicitly records:

```text
performance_tuning_permitted_before_baseline = false
candidate_comparison = false
latency_thresholds = null
resource_thresholds = null
```

## What may be claimed after a PASS

A PASS may establish only that, on the recorded GitHub Actions runner / Chromium execution, the frozen workload completed and produced a reproducible baseline receipt with wall-clock and observed resource metrics.

It does not establish:

- that DemiHead is “fast”;
- that a change made it faster;
- production network latency;
- production readiness;
- cross-machine or cross-OS generalization;
- authenticated human identity;
- anything about truth, evidence, authority or cognition.

```text
LATENCY != TRUTH_PRIORITY
FASTER != TRUER
MORE_COMPUTE != MORE_RIGHTS
```

## Next optimization gate

Only after this baseline is merged and post-merge replayed may a separate candidate grid be frozen.

That later gate must:

1. preserve this baseline result unchanged;
2. preregister candidate configurations before candidate results are observed;
3. compare candidates against the frozen baseline using an independent selection/holdout split;
4. retain failed and slower candidates;
5. reject any candidate that changes evidence, provenance, freshness, disagreement, user rights, authority or mass-effect controls;
6. make a speed/resource claim only if the preregistered comparison supports it.

Until then:

```text
FASTER_THAN_BASELINE_ESTABLISHED = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```
