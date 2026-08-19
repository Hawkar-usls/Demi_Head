# JANUS Nexus v2.2 — Swarm edge observation

Status: **candidate under frozen contract**.

This layer inherits promoted Nexus v2.1 and adds one edge-telemetry source:

```text
SWARM_EDGE -> OBSERVER : TELEMETRY_SAMPLE
```

## Frozen source baseline

- repository: `Hawkar-usls/janus-distributed-ai-swarm`
- source SHA: `43eb173e28f4a8b3e396efc1466db1da02b3c1c7`
- `docs/swarm-critical-rules.md` blob: `f2f1fbc38ff84856f7558ac86ac3b00c1c9f8916`
- `docs/architecture.md` blob: `20585721b4e4b2db6fd6bbee25d9fec950b4cbce`
- `docs/current-swarm-state.md` blob: `f7a05fdb2b8db78427c3f92b73a50a70c4f57cc7`

The source baseline requires heartbeat/SwarmSense/P-N visibility, stale/absent sensor semantics, no fake sensor values, preserved node identity, observer-only zero submit pressure, and frozen SHA/pool truth.

## Integration summary

The integration boundary consumes `janus.demihead.swarm_edge_summary.v1`, not raw ESP-NOW/Stratum packets. This avoids treating every firmware ABI as one universal wire contract.

Required packet-family summary labels are `JANUS`, `S/S`, or `P/N`. Freshness must be one of:

```text
FRESH | STALE | ABSENT | RECOVERING | DEGRADED
```

A stale/absent/degraded sensor cannot carry a numeric value. A fresh sensor must carry a numeric value and unit. Fresh current presence can only come from `CURRENT_PACKET`, never from `MEMORY` or `PREDICTION`.

For observer-only summaries:

```text
submit_pressure = 0
```

## Permanent laws

```text
EDGE_TELEMETRY != COMMAND
EDGE_TELEMETRY != CURRENT_TRUTH_IF_STALE
NO_SOURCE != FALSE
OFFLINE != BLIND
STALE_SOURCE != CURRENT_SOURCE
OBSERVER_ONLY_SUBMIT_PRESSURE = 0
SENSOR_MEMORY_OR_PREDICTION != CURRENT_SENSOR_TRUTH
HASH_INTEGRITY != SOURCE_TRUTH
ROUTE_RECEIPT != DELIVERY
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

The route does not write firmware, flash devices, change ESP-NOW/Stratum behavior, increase submit pressure, or create command authority.
