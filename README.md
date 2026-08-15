<div align="center">

# Janus DemiHead
### Ambient process telemetry adapter for structured, resource-aware signals

![Status](https://img.shields.io/badge/status-work%20in%20progress-f0ad4e)
![Mode](https://img.shields.io/badge/mode-read--only%20observer-2f81f7)
![Scope](https://img.shields.io/badge/scope-local--first-6e7681)

`observe` · `normalize` · `gate` · `project`

</div>

> **Status: Work in Progress.** The repository foundation and data contracts are present. The runtime collector, Storj adapter, and overhead benchmarks are not implemented yet.

[Русская версия](docs/README.ru.md)

## Abstract

DemiHead is a proposed local-first adapter that turns operating-system telemetry from already running processes into bounded, machine-readable signals and triggers for the Janus ecosystem.

An observed application continues to run unchanged. DemiHead reads only explicitly allowed counters, derives deltas and normalized state, applies freshness and resource-budget gates, and projects the result through pluggable output views called **faces**.

The project does not assume literal zero-cost observation. Its own CPU, memory, disk, and timing cost must be measured and kept inside a declared budget.

## Current state

| Surface | Status |
| --- | --- |
| Public project boundary | `IMPLEMENTED` |
| Architecture and terminology | `DRAFTED` |
| JSON signal / face contracts | `DRAFTED` |
| Contract validation and CI | `IMPLEMENTED` |
| Runtime process collector | `NOT_IMPLEMENTED` |
| Storj-specific adapter | `NOT_IMPLEMENTED` |
| Measured overhead | `NOT_PERFORMED` |
| Autonomous control of external processes | `NOT_CLAIMED` |

Machine-readable status: [`PROJECT_STATUS.json`](PROJECT_STATUS.json)

## Core model

```text
existing process
      |
      | OS-exposed, allowlisted counters only
      v
source adapter -> observation window -> normalization -> safety gate
                                                       |
                           +---------------------------+------------------+
                           |                           |                  |
                           v                           v                  v
                      mirror face                steward face       registry face
                   normalized state          DemiHead pacing       evidence record
```

A useful number is not an arbitrary hash. It is a bounded derived signal with provenance:

```text
signal = f(metric_delta, local_baseline, freshness, confidence, observer_budget)
```

Missing or stale measurements remain unknown. They are never silently converted to zero.

## Faces

A face is a deterministic projection of one shared signal frame. Face names are provisional until the first vertical slice is implemented.

- **Mirror** exposes normalized process state without issuing commands.
- **Steward** adjusts DemiHead's own sampling pressure or emits advisory hold/resume triggers.
- **Registry** emits bounded JSON evidence for later inspection.

The v0.1 contract does not authorize a face to inject into, impersonate, hide from, or control an observed process.

## First vertical slice

The first implementation target is deliberately narrow:

1. observe one opt-in Windows process through ordinary OS counters;
2. sample CPU, memory, and cumulative I/O counters at a conservative interval;
3. derive rate, stability, freshness, and activity signals;
4. emit JSON Lines conforming to the published schemas;
5. measure DemiHead's own overhead and fail closed when its budget is exceeded.

Storj is the first candidate adapter, but its application semantics and network payloads remain outside the observer boundary unless a documented public API is explicitly selected later.

## Boundary

```text
MATURITY = WORK_IN_PROGRESS
OPERATING_MODE = READ_ONLY_OBSERVER
ZERO_OVERHEAD = NOT_CLAIMED
EXTERNAL_PROCESS_INJECTION = FORBIDDEN
MEMORY_SCRAPING = FORBIDDEN
CREDENTIAL_OR_PAYLOAD_CAPTURE = FORBIDDEN
STEALTH_OR_CONTROL_BYPASS = FORBIDDEN
AUTONOMOUS_EXTERNAL_PROCESS_CONTROL = NOT_IMPLEMENTED
PROFIT_OR_EFFICIENCY_GAIN = NOT_ESTABLISHED
```

Read [`SECURITY.md`](SECURITY.md) before adding a source adapter.

## Reviewer path

1. [`PROJECT_STATUS.json`](PROJECT_STATUS.json) - maturity and claim boundary.
2. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - pipeline, contracts, and failure behavior.
3. [`docs/GLOSSARY.md`](docs/GLOSSARY.md) - translation from project metaphors to engineering terms.
4. [`docs/CROSS_REPO_LINEAGE.md`](docs/CROSS_REPO_LINEAGE.md) - inherited Janus patterns and explicit exclusions.
5. [`docs/ROADMAP.md`](docs/ROADMAP.md) - gated implementation sequence.
6. [`schemas/`](schemas/) - machine-readable contracts.

Run the same contract check used by CI with `python tools/validate_repository.py` after installing [`requirements-dev.txt`](requirements-dev.txt).

## Janus lineage

DemiHead reuses bounded design patterns from sibling repositories: observer-first measurement from `janus-io-public`, explicit protocol boundaries from `janus-distributed-ai-swarm`, fail-closed evidence discipline from `AIFC` and `Janus-Fundamentum`, portable JSON contracts from `Janus_Genesis`, and resource-monitoring lessons from the legacy `Janus-Demiurge` sandbox.

No sibling source code has been copied into this repository at the foundation stage. See the [lineage record](docs/CROSS_REPO_LINEAGE.md).

## Naming

The public display name is **Janus DemiHead**. The repository is still named `Demi_Head` while the final slug is discussed. The current recommendation is `Janus-DemiHead` for clear ecosystem ownership and readable GitHub URLs.

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

Presentation follows the account's [public repository standard](https://github.com/Hawkar-usls/Janus/blob/main/docs/PUBLIC_REPOSITORY_PRESENTATION_STANDARD.md). No affiliation with MIT is implied by the presentation style.
