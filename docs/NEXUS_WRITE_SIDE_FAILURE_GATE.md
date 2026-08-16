# JANUS Nexus Write-Side Persistence Failure Gate

`JANUS_NEXUS_WRITE_SIDE_FAILURE_HOLDOUT_V1` exercises persistence failures around the already-certified one-shot loopback path without adding any recovery or retry authority.

The fault adapters in `tools/nexus_write_fault_injection.py` are **test-only** subclasses of the real SQLite lifecycle and dispatch ledgers. They preserve the production type boundary while deterministically failing selected durable operations. One case uses a real SQLite `BEGIN IMMEDIATE` lock instead of injected failure.

## Execution boundary law

The gate separates failures by whether durable intent admission and handler invocation may already have occurred.

```text
DISPATCH BEGIN NOT DURABLE
-> handler must not run
-> HOLD

DURABLE STARTED
-> handler may run
-> finalization write fails
-> execution/completion uncertainty remains
-> HOLD / AMBIGUOUS
-> NO RETRY

DURABLE COMPLETED
-> later lifecycle or receipt persistence fails
-> COMPLETED evidence remains authoritative about the local dispatch result
-> outer lifecycle remains fail-closed / ambiguous
-> NO RETRY
```

A storage error is therefore never treated as a reason to repeat the handler.

## Frozen cases

`fixtures/nexus_write_side_failure_holdout_v1.json` was frozen before first execution and contains ten cases:

```text
WRITE-01 lifecycle BEGIN persistence failure before socket bind
WRITE-02 dispatch BEGIN injected persistence failure before handler
WRITE-03 dispatch BEGIN blocked by a real SQLite write lock
WRITE-04 handler failure + durable FAILED_AMBIGUOUS
WRITE-05 handler failure + FAILED_AMBIGUOUS write failure
WRITE-06 handler success + COMPLETED write failure
WRITE-07 lifecycle DISPATCH_STARTED write failure before dispatcher entry
WRITE-08 lifecycle DISPATCH_COMPLETED write failure after durable dispatch completion
WRITE-09 lifecycle RECEIPT_PENDING write failure after durable dispatch completion
WRITE-10 healthy one-shot write path
```

Freeze SHA-256:

`4297fd48ccff1d32fee9d9729759afba37345b69fe51c0cc40e0647ef3dcb41e`

## Real SQLite lock case

`WRITE-03` initializes the real intent-guarded dispatch ledger with a short busy timeout, then holds a separate `BEGIN IMMEDIATE` transaction against the same database. The dispatcher must return `HOLD_LEDGER_UNAVAILABLE` without invoking the handler.

This tests local lock contention only. It does not establish general database availability behavior under every filesystem or storage engine.

## Test-only injected failures

The injected failure classes can fail:

```text
dispatch.begin
dispatch.complete
dispatch.fail_ambiguous
lifecycle.begin
lifecycle.transition(<specific phase>)
```

They are not runtime feature flags and are not wired into the normal Nexus configuration. Their only role is to make boundary failures deterministic and replayable in CI.

## Durable evidence monotonicity

A later persistence failure cannot erase an earlier durable state.

If dispatch `COMPLETED` is already committed and lifecycle persistence later fails at `DISPATCH_COMPLETED` or `RECEIPT_PENDING`, the test requires:

```text
dispatch ledger state = COMPLETED
handler invocation count = 1
automatic_retry_permitted = false
```

The outer lifecycle result may be `UNKNOWN_FAIL_CLOSED`; that uncertainty concerns lifecycle/receipt progress, not permission to erase the durable dispatch fact.

## Claim ceiling

Passing this gate may establish only the frozen write-failure semantics around SQLite-backed one-shot execution.

It does not establish:

```text
real ENOSPC behavior
real read-only filesystem behavior
real device I/O errors
WAL corruption safety
power-loss atomicity
kernel-panic durability
cross-host database behavior
exactly-once delivery
automatic recovery
automatic restart
automatic retry
persistent daemon authority
external-effect authority
```

The next storage boundary after certification should validate physical WAL sidecar envelopes and then add narrowly scoped fault cases for damaged/truncated WAL files. Those tests must remain read-only and fail closed rather than attempting WAL repair.
