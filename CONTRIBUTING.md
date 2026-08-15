# Contributing

DemiHead is currently a work-in-progress systems adapter. Contributions should make one narrow behavior easier to inspect, replay, or falsify.

## Before changing behavior

- Read [`PROJECT_STATUS.json`](PROJECT_STATUS.json), [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md), and [`SECURITY.md`](SECURITY.md).
- State the source surface, effect scope, and expected resource cost.
- Keep observed-process integration read-only unless a future project decision explicitly changes the boundary.
- Preserve missing, stale, negative, and budget-failure outcomes.

## Change requirements

An adapter, transform, trigger, or face should include:

- a versioned input/output contract;
- synthetic fixtures without private user data;
- tests for success, missing data, stale data, reset/PID reuse, and budget exhaustion;
- deterministic replay where practical;
- an update to the project status or roadmap when maturity changes;
- a provenance note for code imported from another repository.

## Claim discipline

```text
SCHEMA_VALID != SOURCE_TRUE
HASH_MATCH != CLAIM_TRUE
TEST_PASS != PRODUCTION_READY
LOW_OVERHEAD_ON_ONE_RUN != ZERO_OVERHEAD
ONE_PROCESS_PROFILE != UNIVERSAL_ADAPTER
CORRELATION != CAUSATION
```

Null and negative results are valid contributions. Do not remove them merely to make a benchmark look cleaner.

## Local checks

Until runtime code exists, validate every JSON file and inspect Markdown links. Runtime-specific formatting, linting, and test commands will be added with the first implementation.
