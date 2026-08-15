# Roadmap

The roadmap is gate-based. A later phase does not become current merely because its files exist.

## Phase 0 - Repository foundation

Status: `IMPLEMENTED`

- public maturity and claim boundary;
- architecture, glossary, security policy, and lineage record;
- draft JSON schemas and example configuration;
- automated contract and local-link validation;
- JANUS Meta Registry foundation report.

Exit condition: documents and JSON parse cleanly, links resolve locally, and the foundation is reviewable through a pull request.

## Phase 1 - Windows observer

Status: `NOT_STARTED`

- opt-in process allowlist;
- lifecycle-safe PID tracking;
- CPU, memory, and cumulative I/O samples;
- monotonic deltas and stale/reset handling;
- JSON Lines output;
- deterministic fixtures and unit tests.

Exit condition: one target can be observed without process modification, every frame validates, and all missing/stale cases fail closed.

## Phase 2 - Observer accounting

Status: `NOT_STARTED`

- DemiHead self-telemetry;
- configurable CPU, memory, I/O, and loop-lag budgets;
- hold and stop behavior;
- matched baseline protocol;
- machine-readable benchmark receipt.

Exit condition: overhead is measured under a frozen protocol. No particular direction of result is required.

## Phase 3 - First Storj profile

Status: `NOT_STARTED`

- identify the exact deployment form and documented observability surface;
- map only allowed counters into activity, stability, and freshness signals;
- avoid application payload, identity, secret, and private network capture;
- publish fixtures that do not contain user data.

Exit condition: a versioned profile works for one explicitly named Storj deployment and makes no universal compatibility claim.

## Phase 4 - Faces and triggers

Status: `NOT_STARTED`

- mirror face;
- DemiHead-only steward face;
- registry face;
- threshold, hysteresis, cooldown, and replay tests;
- face effect-scope enforcement.

Exit condition: replaying the same valid frames yields deterministic face outputs and no undeclared external side effect.

## Phase 5 - Service mode

Status: `NOT_STARTED`

- optional Windows service wrapper;
- bounded local retention;
- restart and crash recovery;
- explicit user-visible status;
- uninstall and data-removal path.

Exit condition: service lifecycle tests pass and the user can inspect, pause, and remove the runtime.

## Deferred

- network sinks and distributed routing;
- learned normalization;
- automated optimization claims;
- control of third-party processes;
- adapters that require undocumented or elevated access.

Deferred items require a new threat model and explicit project decision before implementation.
