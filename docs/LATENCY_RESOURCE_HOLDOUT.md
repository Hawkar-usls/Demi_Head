# Frozen latency/resource holdout

This gate measures performance only after the functional bicameral transport, bounded local reverse channel, and real-Chromium synthetic local acceptance path have been admitted separately.

## Frozen boundary

The performance protocol was committed before the benchmark runner was executed:

- freeze file: `holdout/latency_resource_v1/frozen_corpus.json`
- freeze-only first commit: `08c2fa29b9530bd29cb8e004a9fd523de8564c28`
- canonical freeze SHA-256: `e92f2441825cf56c8876cc522e056e21bd93bc9ceff7434aedde4cd29879efa3`
- parent DemiHead merge: `467e31ff3f6a2bb26af2aea21d97d20f2cc448c6`

The benchmark measures only code that exists on that merged parent:

- `hemisphere_bridge.combine_packets`
- `hemisphere_local_proposal.build_proposal` + `envelope`

Historical experimental flow/optimizer branches are not treated as current implementation knobs.

## Candidate grid

The frozen scheduling grid is:

| config | executor | workers | role |
| --- | --- | ---: | --- |
| `BASELINE_SEQ` | sequential | 1 | baseline |
| `THREADS_2` | `ThreadPoolExecutor` | 2 | candidate |
| `THREADS_4` | `ThreadPoolExecutor` | 4 | candidate |

All three configurations run on the calibration workload. Candidate selection uses calibration only, minimizing p95 wall time with the preregistered tie-break order. The independent holdout executes only `BASELINE_SEQ` and the already selected candidate. Holdout results may not change the selected candidate.

## Workloads

The generator is deterministic, synthetic, offline, and uses no live user data. The calibration set contains 18 cases. The independent holdout contains 16 separate cases with unseen graph sizes.

Every case repeatedly exercises either bicameral comparison or hash-bound non-mutating proposal construction. Threaded results are re-sorted into canonical case order before their semantic digest is computed.

## Measurements

The frozen measurement plan uses:

- wall clock: `time.perf_counter_ns`
- process CPU: `time.process_time_ns`
- separate peak Python allocation pass: `tracemalloc`
- nearest-rank p50/p95/p99
- 5 warmups
- 21 calibration repeats
- 31 independent holdout repeats
- 12 inner loops per case
- 5000 ms timeout boundary per repeat
- 21 paired observer-overhead measurements with alternating order

Observer overhead is reported separately and is not used for candidate selection or admission.

## Admission thresholds

A selected candidate is admitted only when every frozen condition passes on the independent holdout:

- p95 wall time improves by at least 5%;
- p99 wall regression is no more than 5%;
- p95 process CPU regression is no more than 5%;
- peak allocation regression is no more than 10%;
- timeout rate is zero;
- error rate is zero;
- canonical semantic output digest is exactly equal to baseline;
- protected constitutional boundary digest is exactly equal to baseline.

A faster result that changes evidence, provenance, effect permission, truth claims, direct-write permission, proposal controls, authority, or mass-effect budget is rejected.

## Negative result is valid

`NO_CANDIDATE_ADMITTED` is a valid scientific result and must not be converted into a CI failure. Slower or failed candidates remain in the calibration receipt. The thresholds and holdout workload must not be changed after seeing the result.

`BENCHMARK_INTEGRITY_FAIL` is different: it means the experiment itself lost semantic/provenance integrity and should fail CI.

## Claim ceiling

Even if a candidate is admitted, this gate does **not** establish production latency, cross-machine generalization, production readiness, universal speedup, biological equivalence, cognitive gain, truth, or authority.

The core laws remain:

```text
FASTER != TRUER
LATENCY != AUTHORITY
PERFORMANCE != EVIDENCE
OUTPUT_DRIFT => REJECT
PROTECTED_BOUNDARY_DRIFT => REJECT
NO_CANDIDATE_ADMITTED = VALID_RESULT
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```
