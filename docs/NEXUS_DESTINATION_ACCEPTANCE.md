# JANUS Nexus Destination Acceptance

## Purpose

This layer separates three statements that must never collapse into one another:

```text
TRANSPORT FRAME AUTHENTICATED
!= DESTINATION ACCEPTED
!= PAYLOAD DELIVERED OR EXECUTED
```

`JANUS_NEXUS_DESTINATION_ACCEPTANCE_V1` verifies endpoint ownership of a `target_head` after transport admission. `JANUS_NEXUS_DESTINATION_REVALIDATION_V1` then rechecks current key policy so a key revoked, expired, disabled or rolled to a new epoch after transport admission cannot silently continue to destination acceptance.

## Required chain

```text
VALID NEXUS ENVELOPE
-> HMAC / PRINCIPAL / KEY-EPOCH TRANSPORT ADMISSION
-> ENDPOINT POLICY MATCH
-> CURRENT PRINCIPAL REVOCATION + EPOCH RECHECK
-> DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH_REVALIDATED
```

Even the terminal state above does **not** mean delivery or execution.

## Endpoint policy

A reference endpoint declares only:

- `endpoint_id`;
- `enabled`;
- explicit `accepted_target_heads`;
- `local_dispatch_only=true`;
- `external_effect_permitted=false`;
- zero authority and mass-effect deltas.

The committed example in `configs/nexus_endpoints.example.json` contains no socket addresses and does not create a network listener.

## Revocation-in-flight defense

Transport admission proves that a principal was acceptable at admission time. That fact can become stale.

Before destination acceptance, the revalidation layer checks current public policy for the same:

- `key_id`;
- `sender_id`;
- `source_head` permission;
- `epoch`;
- `enabled` state;
- `revoked` state;
- validity window.

A revocation, expiry or epoch rollover between transport admission and destination acceptance fails closed.

```text
PAST ADMISSION != CURRENT KEY VALIDITY
REVOCATION MUST BE RECHECKED AT ACCEPTANCE
```

No secret material is required for this second check; it consumes public principal metadata only.

## Receipts

Base acceptance:

```text
janus.demihead.nexus_destination_acceptance.v1
DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH
```

Revalidated acceptance:

```text
janus.demihead.nexus_destination_acceptance_revalidated.v1
DESTINATION_ACCEPTED_FOR_LOCAL_DISPATCH_REVALIDATED
```

Both preserve:

```text
delivery_performed = false
target_execution_performed = false
external_effect_permitted = false
automatic_retry_permitted = false
authority_delta = 0
mass_effect_budget_delta = 0
```

## Not yet a dispatcher

This layer performs no target function call, filesystem mutation, Git write, socket I/O or cross-repository delivery. A future dispatcher must be introduced as a separately versioned contract after exact-head tests and partial-delivery red-team work.
