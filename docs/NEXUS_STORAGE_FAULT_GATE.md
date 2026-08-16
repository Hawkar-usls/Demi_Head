# JANUS Nexus Storage Fault Gate

`JANUS_NEXUS_STORAGE_FAULT_GATE_V1` places a read-only integrity/schema boundary in front of manual recovery.

The goal is to prevent a dangerous failure mode: a missing or damaged evidence database must never be interpreted as an empty, clean database and therefore as permission to recover or retry.

## Evidence stores

The gate treats three SQLite stores as one recovery evidence set:

```text
lifecycle -> nexus_one_shot_lifecycle + nexus_one_shot_lifecycle_events
dispatch  -> nexus_dispatch_ledger_v2
replay    -> nexus_replay_ledger
```

Before guarded recovery, every store must already exist as a regular file and pass a read-only SQLite inspection.

## Read-only preflight

The reference opens each database with SQLite URI `mode=ro`, enables `query_only`, runs `PRAGMA quick_check`, and checks that the required tables already exist.

It does not create a missing database, replace a corrupt database or run schema migration.

```text
MISSING STORE != EMPTY STORE
CORRUPT STORE != EMPTY STORE
TRUNCATED STORE != EMPTY STORE
VALID SQLITE + WRONG SCHEMA != MIGRATION PERMISSION
```

The preflight records a SHA-256 of each readable database before and after inspection so the frozen tests can verify that the inspection did not rewrite the main database bytes.

## Guarded recovery

`storage_guarded_recovery()` first requires all three stores to pass.

Only after that does it reopen the certified lifecycle and dispatch ledgers and delegate to v1.10 manual phase-boundary recovery semantics.

The replay store is required even though the v1.10 reconciliation algorithm does not directly consume replay rows. This is deliberate: terminalizing a stale lifecycle while replay evidence is missing or corrupted could create an unsafe future restart context.

Therefore:

```text
LIFECYCLE HEALTHY + DISPATCH HEALTHY + REPLAY BROKEN -> HOLD
```

and the lifecycle row remains unchanged.

## Frozen storage corpus

`fixtures/nexus_storage_fault_holdout_v1.json` contains ten frozen cases:

```text
STOR-01 healthy stores
STOR-02 missing lifecycle store
STOR-03 corrupt lifecycle store
STOR-04 truncated lifecycle store
STOR-05 missing dispatch store
STOR-06 corrupt dispatch store
STOR-07 missing replay store
STOR-08 corrupt replay store
STOR-09 valid SQLite file with wrong schema
STOR-10 healthy storage-guarded manual recovery
```

Freeze SHA-256:

`1e7939a1572d7b91fc9711041153b1ad1f32be496f92015287d979ef44662046`

## Fail-closed laws

```text
UNKNOWN STORAGE STATE != PERMISSION
MISSING EVIDENCE != ZERO EVIDENCE
CORRUPTION != RESET PERMISSION
SCHEMA MISMATCH != AUTO MIGRATION PERMISSION
REPLAY EVIDENCE HEALTH IS REQUIRED BEFORE GUARDED RECOVERY
STORAGE PREFLIGHT != STORAGE REPAIR
```

## Claim ceiling

Passing this gate would establish only the frozen read-only integrity/schema checks and fail-closed recovery precondition behavior.

It does **not** establish:

```text
full filesystem health
future write success
ENOSPC tolerance
real disk-full behavior
real read-only filesystem behavior
power-loss durability
kernel-crash durability
WAL corruption recovery
SQLite semantic correctness beyond required schema/integrity checks
production storage readiness
```

The next gate should exercise write-side storage failure with explicit fault injection, including failed lifecycle transition, failed dispatch STARTED/COMPLETED persistence, SQLite lock/busy behavior, and WAL-side damage. Any uncertainty after a possible handler invocation must remain ambiguous and must never trigger automatic retry.
