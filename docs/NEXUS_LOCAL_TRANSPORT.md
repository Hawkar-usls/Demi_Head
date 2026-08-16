# JANUS Nexus Local Transport

## Status

`JANUS_NEXUS_LOCAL_TRANSPORT_V1` is an **offline transport-admission reference**. It authenticates and validates frames in memory but intentionally exposes no socket listener and performs no network I/O.

```text
AUTHENTICATED FRAME != DELIVERED FRAME
KEY POSSESSION != HUMAN IDENTITY
LOCAL PRINCIPAL BINDING != WORLD-EFFECT AUTHORIZATION
AUTHENTICATION != AUTHORITY
```

Reference implementation:

- `tools/nexus_local_transport.py`
- `tests/test_nexus_local_transport.py`
- `schemas/nexus-transport-frame.schema.json`

## Frame boundary

A transport frame binds:

- one already-valid `JANUS_NEXUS_HABITAT_V1` envelope;
- its canonical SHA-256;
- `sender_id`;
- `key_id`;
- issue time and bounded TTL;
- nonce;
- zero-authority transport controls;
- HMAC-SHA256 authentication tag.

Maximum canonical frame size is 64 KiB. Default TTL is 30 seconds; v1 refuses TTL above 120 seconds and rejects timestamps more than 5 seconds in the future.

## Principal binding

The validator does not accept a naked `key_id -> key` mapping. Each in-memory principal binds:

```text
key_id
-> key material
-> enabled state
-> exact sender_id
-> allowlisted source_head set
```

A correctly signed frame is rejected if the key is disabled, the claimed sender differs from the principal, or the Nexus envelope's `source_head` is outside that principal's allowlist.

This prevents one valid local transport key from silently impersonating another Nexus organ.

It still does **not** establish a human identity and does not authorize an external effect.

## Replay and freshness

The reference rejects:

- stale frames;
- excessive future clock skew;
- nonce replay present in the supplied replay cache;
- malformed or semantically unadmitted Nexus routes;
- HMAC tampering;
- oversized frames.

The current replay cache is supplied by the caller and may be process-local. **Persistent crash-safe replay protection is not established.** A production transport must define a bounded persistent replay ledger, retention horizon and restart behavior before enabling live delivery.

## Backpressure

If queue depth reaches capacity, validation returns:

```text
HOLD_BACKPRESSURE
```

The reference does not perform delivery and does not grant automatic retry permission. A later scheduler may issue a fresh frame only under a separately defined policy.

```text
BACKPRESSURE != FAILURE
AMBIGUOUS DELIVERY != RETRY PERMISSION
```

## Secrets and key lifecycle

No production transport key belongs in this repository, a fixture, a registry record, a Habitat state file or a Nexus receipt.

The current reference accepts key material only from the caller's in-memory principal lookup. Test-only byte strings exist solely inside unit/self-test code and have no deployment authority.

Not implemented in v1:

- OS/keychain/secret-manager adapter;
- rotation epochs;
- revocation persistence;
- key-expiry policy;
- process attestation;
- mTLS;
- hardware-backed keys;
- persistent replay ledger;
- socket listener;
- live cross-repository delivery.

These are separate gates rather than assumptions hidden behind HMAC.

## Admission order

The validator conceptually performs:

```text
FRAME SIZE
-> FRAME CONTRACT
-> PRINCIPAL LOOKUP
-> HMAC
-> NEXUS ENVELOPE SEMANTICS
-> ENVELOPE HASH
-> SENDER BINDING
-> SOURCE-HEAD BINDING
-> ZERO-AUTHORITY TRANSPORT CONTROL
-> FRESHNESS
-> REPLAY
-> BACKPRESSURE
-> ADMISSION RECEIPT
```

An admission receipt still reports:

```text
delivery_performed = false
target_execution_performed = false
network_io_performed = false
human_identity_established = false
world_effect_authorization_established = false
authority_delta = 0
mass_effect_budget_delta = 0
```

## Next transport gate

Before any listener is enabled:

1. freeze exact-head CI for principal-binding tests;
2. add a secret-provider interface with no committed key material;
3. add persistent replay/revocation state with bounded retention;
4. bind endpoint identity and destination acceptance receipts;
5. red-team restart, duplicate, partial-delivery and key-rotation cases;
6. only then consider a loopback-only transport adapter as a new version.
