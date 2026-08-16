# JANUS Nexus Loopback Dispatcher

## Status

`JANUS_NEXUS_LOOPBACK_DISPATCH_V1` is the first reference layer that performs an actual **local in-process delivery** after the already-certified Nexus v1.4 transport and destination-acceptance gates.

It still performs no socket I/O, no cross-repository delivery, no external effect and no authority increase.

```text
ROUTE ADMITTED
!= TRANSPORT ADMITTED
!= DESTINATION ACCEPTED
!= LOCAL DISPATCH
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
-> deep-copied local payload
-> one in-process handler invocation
-> content-addressed dispatch result
```

Reference implementation:

- `tools/nexus_loopback_dispatcher.py`
- `tests/test_nexus_loopback_dispatcher.py`
- `schemas/nexus-loopback-dispatch-result.schema.json`

## Hard boundary

The dispatcher rejects or holds before handler invocation when:

- the payload hash does not match `envelope.payload_ref.sha256`;
- the endpoint catalog exposes live network endpoints;
- multiple enabled endpoints claim the same target head;
- no enabled endpoint is available;
- no handler is registered;
- a handler descriptor permits network I/O, filesystem I/O or external effects;
- the current principal is revoked, disabled, outside its validity window or on a different epoch.

A handler receives a deep copy of the payload. Mutation of the handler input therefore cannot mutate the caller's payload object.

## Failure semantics

A local handler exception produces:

```text
HOLD_HANDLER_FAILURE
automatic_retry_permitted = false
completion_established = false
```

The dispatcher does not automatically invoke the handler a second time. This matters because v1 does **not** establish process isolation, side-effect attestation or exactly-once semantics.

```text
AMBIGUOUS HANDLER FAILURE != RETRY PERMISSION
```

## What successful dispatch proves

A successful `LOOPBACK_DISPATCH_COMPLETED_LOCAL` proves only that, within the current process:

- one enabled endpoint was selected unambiguously;
- the supplied payload matched the envelope content hash;
- current principal policy was revalidated;
- destination acceptance succeeded;
- a zero-authority local handler descriptor passed the gate;
- that handler returned a bounded JSON result.

The result records SHA-256 bindings for the frame, envelope, acceptance, payload and handler output.

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

- exactly-once delivery: not established;
- process isolation: not established;
- handler side-effect attestation: not established;
- cross-repository delivery: not established;
- human identity: not established;
- world-effect authorization: not established.

## Next gate

Before a real loopback socket exists, the next version should add a persistent local dispatch ledger with:

1. dispatch intent;
2. acceptance hash;
3. payload hash;
4. handler identity;
5. started/completed state;
6. crash recovery semantics;
7. explicit duplicate and ambiguous-completion handling.

Only after that ledger survives restart/red-team testing should a listener limited to the OS loopback interface be considered.
