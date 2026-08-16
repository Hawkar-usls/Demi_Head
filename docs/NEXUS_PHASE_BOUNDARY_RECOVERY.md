# JANUS Nexus Phase-Boundary Crash Recovery

`JANUS_NEXUS_PHASE_BOUNDARY_RECOVERY_V1` is a manual recovery layer above the certified v1.9 one-shot lifecycle gate.

It is deliberately **not** a watchdog, supervisor, daemon or automatic restart controller. Its purpose is narrower: when a process disappears and leaves a non-terminal lifecycle row, classify the persisted phase against durable dispatch evidence before an operator is allowed to terminalize that stale instance.

## Core rule

```text
PROCESS DISAPPEARED != SAFE TO RETRY
STALE LIFECYCLE != PERMISSION
```

Recovery requires both:

```text
--operator-ack
--process-dead-attested
```

The process-dead attestation is explicitly recorded as an operator claim. This reference does not independently prove OS process death.

## Pre-dispatch recovery

The current certified call ordering persists `DISPATCH_STARTED` **before** entering the intent-guarded dispatcher. Therefore these phases are classified as pre-dispatch for this exact implementation:

```text
STARTING
LISTENER_BOUND
ACCEPTING
CONNECTED
REQUEST_RECEIVED
TRANSPORT_ADMITTED
DISPATCH_HOLD_NO_INVOCATION
```

Even these phases can be closed clean only if read-only inspection of the persistent dispatch ledger finds **zero entries bound to the lifecycle frame**.

If dispatch evidence unexpectedly exists while the lifecycle claims a pre-dispatch phase, the recovery tool refuses mutation:

```text
HOLD_UNEXPECTED_DISPATCH_EVIDENCE
```

This turns an ordering contradiction into evidence instead of guessing which record is correct.

## Post-dispatch and execution-uncertain recovery

The following stale phases are never converted directly to `CLOSED_CLEAN`:

```text
DISPATCH_STARTED
DISPATCH_AMBIGUOUS
DISPATCH_COMPLETED
RECEIPT_PENDING
RECEIPT_SENT
UNKNOWN_FAIL_CLOSED
```

They become:

```text
CLOSED_AMBIGUOUS
manual_ack_required = true
```

This remains true even if the dispatch ledger currently contains zero rows. A crash can occur after control entered a handler but before the next durable observation, so absence of completion evidence is not proof that execution never occurred.

If dispatch evidence exists, its state (`STARTED`, `COMPLETED`, `FAILED_AMBIGUOUS`) is attached to the recovery receipt but never used to grant automatic retry.

## Evidence stores are immutable boundaries

Recovery does not delete, reset, vacuum-as-reset, rewrite or rotate either the dispatch ledger or replay ledger.

```text
MANUAL RECOVERY != DISPATCH INTENT RESET
MANUAL RECOVERY != REPLAY RESET
```

If the dispatch evidence database is unavailable or unreadable, recovery fails closed and leaves the lifecycle row unchanged.

## Unknown phases

A phase introduced by a future implementation has no implicit recovery semantics. The reference returns:

```text
HOLD_UNKNOWN_PHASE_NO_MUTATION
```

This prevents old recovery code from guessing about a new execution boundary.

## Frozen crash-boundary corpus

`fixtures/nexus_phase_boundary_crash_recovery_holdout_v1.json` contains 13 cases and was frozen before first exact-head CI execution.

Freeze SHA-256:

`e3946b4f95262598203f46c46ca2998ffffaa26a9124b52a877424acc963452d`

The corpus covers clean manual recovery at stale pre-dispatch boundaries, conservative ambiguity at dispatch/post-dispatch boundaries, contradictory dispatch evidence, missing operator attestation, wrong instance identity, unavailable dispatch evidence and unknown future phases.

These are deterministic persisted-phase simulations. They are **not** evidence that a real operating system `SIGKILL`, power loss, filesystem failure or hardware crash has been exhaustively tested.

## Operator CLI

The reference CLI is intentionally explicit:

```text
python tools/nexus_lifecycle_recovery.py \
  --lifecycle-db <path> \
  --dispatch-db <path> \
  --service-id <service> \
  --expected-instance-id <instance> \
  --operator-ack \
  --process-dead-attested
```

Omitting either acknowledgment prevents mutation.

## Claim ceiling

Passing this gate may establish deterministic manual recovery semantics for persisted one-shot lifecycle states and read-only dispatch-ledger reconciliation.

It does not establish:

```text
independent proof of process death
real power-loss safety
real SIGKILL coverage
filesystem corruption tolerance
exactly-once delivery
semantic duplicate prevention
automatic restart
automatic retry
persistent daemon
cross-host transport
external-effect authority
production recovery readiness
```

The next gate after exact-head certification should inject real subprocess termination at selected pre-dispatch boundaries and verify durable ledger state from a second process, while retaining manual-only recovery and zero authority escalation.
