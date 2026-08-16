# JANUS Nexus Loopback Dispatcher

## Status

`JANUS_NEXUS_LOOPBACK_DISPATCH_V1` is the first reference layer that performs an actual **local in-process delivery** after the certified Nexus v1.4 transport and destination-acceptance gates.

The first unguarded candidate (`823cd640…`) passed all four repository workflows, but red-team review found an important gap: an already-created transport admission could be reused to call the local dispatcher again. The current design therefore requires a crash-safe dispatch ledger and refuses an in-memory-only dispatch guard.

```text
ROUTE ADMITTED
!= TRANSPORT ADMITTED
!= DESTINATION ACCEPTED
!= DISPATCH STARTED
!= LOCAL HANDLER COMPLETED
!= EXTERNAL DELIVERY
!= WORLD EFFECT
```

## Pipeline

```text
Nexus envelope
-> authenticated transport admission
-> current key / epoch / revocation revalidation
-> unique enabled local endpoint selection
-> payload SHA-256 binding
-> safe LocalHandler descriptor
-> persistent dispatch STARTED commit
-> deep-copied local payload
-> one in-process handler invocation
-> COMPLETED or FAILED_AMBIGUOUS durable state
-> content-addressed dispatch result
```

Reference implementation:

- `tools/nexus_loopback_dispatcher.py`
- `tools/nexus_dispatch_ledger.py`
- `tests/test_nexus_loopback_dispatcher.py`
- `tests/test_nexus_dispatch_ledger.py`
- `schemas/nexus-loopback-dispatch-result.schema.json`
- `schemas/nexus-dispatch-ledger-entry.schema.json`

## Persistent attempt ledger

The SQLite ledger uses:

```text
WAL
synchronous=FULL
busy_timeout
BEGIN IMMEDIATE
```

A dispatch key binds:

- transport frame SHA-256;
- current destination-acceptance SHA-256;
- payload SHA-256;
- exact local handler identity.

Before any handler can run, the ledger atomically creates:

```text
STARTED
```

If that dispatch key already exists in any state, reinvocation is refused.

Successful handler completion becomes:

```text
COMPLETED
```

A handler exception or inadmissible handler output becomes:

```text
FAILED_AMBIGUOUS
```

Neither `STARTED` left behind by a crash nor `FAILED_AMBIGUOUS` permits an automatic second attempt.

## Why this is conservative

The design deliberately trades liveness for duplicate suppression. A process can crash after durable `STARTED` but before the handler actually begins. On restart the system cannot prove whether invocation happened, so it does **not** guess and does not retry automatically.

```text
UNKNOWN COMPLETION != SAFE RETRY
DUPLICATE SUPPRESSION != GUARANTEED DELIVERY
DUPLICATE SUPPRESSION != EXACTLY ONCE
```

This establishes crash-safe local duplicate-attempt suppression for callers that use the certified dispatcher and its persistent ledger. It does not establish guaranteed delivery or exactly-once semantics.

## Hard boundary

The dispatcher rejects or holds before handler invocation when:

- payload hash does not match `envelope.payload_ref.sha256`;
- endpoint catalog exposes live network endpoints;
- multiple enabled endpoints claim the same target head;
- no enabled endpoint is available;
- no handler is registered;
- handler descriptor permits network I/O, filesystem I/O or external effects;
- current principal is revoked, disabled, outside its validity window or on another epoch;
- no persistent dispatch ledger is supplied;
- the same content-addressed dispatch has already been started.

A handler receives a deep copy of the payload. Mutation of handler input cannot mutate the caller's payload object.

## Failure semantics

A handler exception records `FAILED_AMBIGUOUS` and returns:

```text
HOLD_HANDLER_FAILURE
automatic_retry_permitted = false
```

An invalid handler output records `FAILED_AMBIGUOUS` and returns:

```text
HOLD_HANDLER_OUTPUT_INVALID
automatic_retry_permitted = false
```

If the handler returns but durable completion cannot be finalized, the system returns:

```text
HOLD_LEDGER_FINALIZATION_FAILURE
automatic_retry_permitted = false
```

The durable `STARTED` row remains the conservative duplicate barrier.

## What successful dispatch proves

A successful `LOOPBACK_DISPATCH_COMPLETED_LOCAL` proves, within the current local process and ledger boundary:

- one enabled endpoint was selected unambiguously;
- payload matched the envelope content hash;
- current principal policy was revalidated;
- destination acceptance succeeded;
- a zero-authority local handler descriptor passed the gate;
- `STARTED` was durably committed before handler invocation;
- the handler returned a bounded JSON result;
- `COMPLETED` was durably recorded;
- the same dispatch key will not be automatically reinvoked through this ledger, including after restart.

## What it does not prove

Even on success:

```text
socket_listener_enabled = false
network_io_performed = false
external_delivery_performed = false
world_effect_performed = false
automatic_retry_permitted = false
authority_delta = 0
mass_effect_budget_delta = 0
```

And the claim ceiling remains:

- guaranteed delivery: not established;
- exactly-once delivery: not established;
- process isolation: not established;
- handler side-effect attestation: not established;
- cross-repository delivery: not established;
- human identity: not established;
- world-effect authorization: not established.

## Next gate

Before a real loopback socket exists, red-team the persistent ledger under:

1. process restart after `STARTED`;
2. handler exception after partial local work;
3. completion-write failure;
4. concurrent duplicate submissions;
5. SQLite lock contention;
6. database corruption / unavailable storage;
7. handler-version change producing a different dispatch key.

Only after those cases are frozen and replayed should a listener limited to an OS loopback interface be considered.
