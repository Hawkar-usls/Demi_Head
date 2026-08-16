# JANUS Nexus Dispatch v2 Adversarial Gate

`JANUS_NEXUS_LOOPBACK_DISPATCH_V2` is a candidate successor to the certified v1.5 local dispatcher. It exists to close one specific red-team gap before any loopback socket is considered: **dispatch identity must survive restart, concurrency and handler-version changes without permitting duplicate local execution.**

## New identity split

v1.5 used a dispatch key that included the handler identity. That is safe against repeating the exact same handler, but changing `handler_id` could create a new dispatch key for the same admitted frame.

v2 therefore separates:

```text
INTENT = frame + destination acceptance + payload + target head
DISPATCH = INTENT + exact handler id
```

`intent_sha256` is unique in the persistent ledger. Once an intent reaches `STARTED`, changing the handler version cannot create a second executable attempt.

```text
HANDLER VERSION CHANGE != NEW INTENT
EXISTING INTENT != REINVOKE PERMISSION
```

## Persistent ledger v2

`tools/nexus_dispatch_ledger_v2.py` uses a separate SQLite table so the certified v1.5 schema remains historically intact. The v2 table has both a primary `dispatch_sha256` and a unique `intent_sha256`.

The implementation keeps:

- WAL;
- `synchronous=FULL`;
- `BEGIN IMMEDIATE`;
- bounded configurable busy timeout;
- durable `STARTED`, `COMPLETED`, `FAILED_AMBIGUOUS` states;
- no automatic retry.

## Frozen adversarial cases

`fixtures/nexus_dispatch_adversarial_holdout_v1.json` defines the required cases. `tests/test_nexus_dispatch_adversarial_holdout.py` executes them against real temporary SQLite databases where applicable.

The holdout covers:

1. eight concurrent submissions of the same intent;
2. restart with a durable `STARTED` row;
3. same intent under a different handler version;
4. synthetic completion-write failure after handler return;
5. real SQLite write-lock contention;
6. corrupt database bytes;
7. unavailable storage path;
8. handler exception after possible partial local work.

## Fail-closed storage semantics

v2 does not silently fall back to an in-memory ledger when persistent storage is locked, corrupt or unavailable.

If the ledger cannot acquire the required write boundary before the handler, the dispatcher returns/propagates a fail-closed hold and the handler is not called.

If durable completion fails after the handler returns, the existing durable `STARTED` row remains the duplicate barrier. The system reports ambiguity and forbids automatic retry.

## Claim ceiling

Even if this adversarial gate passes:

```text
socket_listener_enabled = false
network_io_performed = false
cross_repository_delivery = false
guaranteed_delivery = false
exactly_once_delivery = false
external_effect_authority = false
authority_delta = 0
mass_effect_budget_delta = 0
```

Passing this gate would justify consideration of a **separate** localhost-only socket candidate, not activation of one.
