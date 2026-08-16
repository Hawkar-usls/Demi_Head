# JANUS Nexus One-Shot Response Ambiguity & Lifecycle Gate

`JANUS_NEXUS_ONE_SHOT_LIFECYCLE_GATE_V1` is the adversarial layer above the certified one-shot authenticated loopback exchange.

It does **not** create a daemon. It makes the one-shot lifecycle explicit and persistent enough to fail closed around startup races, timeouts, replay-store outages and the hardest acknowledgment edge: local dispatch may have completed even when the client never receives the response receipt.

```text
EXPLICIT START GRANT
-> PERSISTENT LIFECYCLE LEASE
-> LOOPBACK BIND
-> BOUNDED ACCEPT
-> BOUNDED READ
-> AUTHENTICATED TRANSPORT / PERSISTENT REPLAY
-> INTENT-GUARDED LOCAL DISPATCH
-> RECEIPT PENDING
-> BOUNDED WRITE
-> CLOSED_CLEAN | CLOSED_AMBIGUOUS
```

## Default startup state

The lifecycle policy defaults to:

```text
startup_enabled             = false
automatic_start_permitted   = false
automatic_restart_permitted = false
automatic_retry_permitted   = false
max_connections             = 1
max_requests_per_connection = 1
```

A caller must explicitly enable the policy **and** provide the runtime start grant. Configuration presence alone cannot start a listener.

## Persistent lifecycle lease

Before socket bind, `SqliteLifecycleLedger.begin()` atomically reserves a `service_id` for one `instance_id`.

A second one-shot instance for the same service is rejected while the first is in a non-terminal phase. This remains true even if the first process disappears after binding: a stale `LISTENER_BOUND`, `ACCEPTING`, `DISPATCH_STARTED` or other non-terminal row is not interpreted as permission to restart.

Clean terminal state permits a later *explicit* instance. There is no background restart loop.

## Response ambiguity

The critical edge is:

```text
handler completed
-> dispatch ledger durably COMPLETED
-> response send fails / client disappears
```

The server cannot infer from a failed `sendall()` that the client received nothing, and the client cannot infer from a missing receipt that the handler did not run.

Therefore the lifecycle records:

```text
CLOSED_AMBIGUOUS
DISPATCH_COMPLETED_RECEIPT_UNCONFIRMED
manual_ack_required = true
automatic_retry_permitted = false
```

A new lifecycle instance for that service is blocked until explicit ambiguity acknowledgment.

Acknowledgment **does not erase** the dispatch intent ledger. If the replay database is later lost and the same authenticated intent is presented again, the independent persistent intent guard still rejects reinvocation as `HOLD_DUPLICATE_INTENT`.

## Replay-store failure

Replay persistence is a security dependency, not an optimization. If the replay guard is unavailable or raises while the frame is being admitted, the gate returns a transport hold and never reaches the local handler.

```text
REPLAY STORE UNKNOWN/FAILED -> HOLD
UNKNOWN REPLAY STATE != PERMISSION
```

No fallback to an in-memory replay guard occurs automatically.

## Timeouts

The lifecycle adds separate bounded waits for accept, request read and receipt write. Each is capped at 5 seconds by policy; the reference holdout uses much shorter values.

An accept timeout closes the listener as a clean no-peer terminal state. A read timeout closes without dispatch. A write failure after completed dispatch becomes an ambiguous terminal state rather than a retry trigger.

## Frozen adversarial holdout

`fixtures/nexus_one_shot_lifecycle_holdout_v1.json` was frozen before exact-head CI. It contains nine cases: startup disabled; concurrent lifecycle lease collision; crash-like non-terminal restart; accept timeout; read timeout; replay-store outage; completed dispatch followed by receipt-send failure; manual ambiguity acknowledgment with independent intent-ledger duplicate suppression; and a clean authenticated roundtrip.

Freeze SHA-256:

`21b49045bea3853f53112f1ec4917d40b37a9fc4a13ce63dea80a19bb09e1dd6`

## Claim ceiling

Passing this gate may establish only a bounded one-shot localhost lifecycle with explicit startup, persistent concurrency suppression, fail-closed replay dependency and preserved response ambiguity.

It does not establish:

```text
exactly_once_delivery
response_delivery_guarantee
cross_host_transport
general_network_service
persistent_daemon
automatic_restart
automatic_retry
external_effect_authority
production_readiness
```

The next gate, if this candidate passes exact-head CI, should focus on operator recovery semantics for stale pre-dispatch lifecycle rows and crash injection at phase boundaries before any long-lived local service is considered.
