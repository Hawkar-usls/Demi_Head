# JANUS Nexus v2.4 — I0 measurement receipt

Status: **candidate under frozen contract**.

This additive layer inherits promoted Nexus v2.3 and adds a two-stage measurement membrane:

```text
I0_MEASUREMENT -> MEASUREMENT_BROKER : MEASUREMENT_RECEIPT
MEASUREMENT_BROKER -> FUNDAMENTUM     : EVIDENCE_CANDIDATE
```

## Frozen source baseline

- repository: `Hawkar-usls/janus-io-public`
- source SHA: `7d02fb08fa9defd71297f8c5c4c9ac9d6be76316`
- `PROJECT_STATUS.json` blob: `df92b16ab1cc62183de1d667576e57c82c10dc3c`
- `docs/proof-of-observation.md` blob: `f7fcd76c376b17b4b001094355e17e517b7cb84c`
- `docs/current-engineering-capabilities.md` blob: `e60d5ffe8aae8de0a9d946460244a22f16e29112`

## Why a broker exists

Proof-of-Observation explicitly separates facts, derived metrics and claims. A measurement receipt therefore remains a measurement object. `MEASUREMENT_BROKER` may project its bounded evidence controls into an `EVIDENCE_CANDIDATE`, but it cannot change values, fill unknowns, delete stale/contaminated fields, promote a claim or admit evidence for Fundamentum.

## Measurement states

```text
OBSERVED | UNKNOWN | STALE | CONTAMINATED
```

Rules:

- `OBSERVED` requires a current numeric value and unit.
- `UNKNOWN` requires `value=null` and `current=false`; it must never be zero-filled.
- `STALE` may preserve a historical numeric value, but `current=false` is mandatory.
- `CONTAMINATED` may preserve a value for provenance, but cannot support `CONFIRMED`.

A `CONFIRMED` Proof-of-Observation summary additionally requires integrity, comparability, untouched holdout replication and at least one independent replication.

## Permanent claim ceiling

The receipt and its evidence projection do not establish:

- SHA-256 predictability or weakness;
- increased proof probability;
- mining advantage or profitability;
- wall-energy savings;
- extended hardware lifetime;
- production readiness;
- source truth merely from a valid hash chain.

## Permanent laws

```text
MEASUREMENT_RECEIPT != EVIDENCE_ADMISSION
MEASUREMENT != INFERENCE
INTEGRITY != TRUTH
MISSING != ZERO
STALE != CURRENT
OVERLAPPING_VIEW != INDEPENDENT_REPLICATION
EVIDENCE_PROJECTION != CLAIM_PROMOTION
ROUTE_RECEIPT != DELIVERY
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```
