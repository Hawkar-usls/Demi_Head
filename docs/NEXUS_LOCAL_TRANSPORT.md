# JANUS Nexus Local Transport

## Status

`JANUS_NEXUS_LOCAL_TRANSPORT_V1` is an **offline transport-admission reference**. It authenticates and validates frames but intentionally exposes no socket listener and performs no network I/O.

```text
AUTHENTICATED FRAME != DELIVERED FRAME
KEY POSSESSION != HUMAN IDENTITY
LOCAL PRINCIPAL BINDING != WORLD-EFFECT AUTHORIZATION
AUTHENTICATION != AUTHORITY
```

Reference surfaces:

- `tools/nexus_local_transport.py`
- `tools/nexus_transport_keyring.py`
- `tools/nexus_replay_ledger.py`
- `tests/test_nexus_local_transport.py`
- `tests/test_nexus_transport_keyring.py`
- `tests/test_nexus_replay_ledger.py`
- `schemas/nexus-transport-frame.schema.json`
- `configs/nexus_transport.principals.example.json`

## Frame boundary

A transport frame binds one already-valid `JANUS_NEXUS_HABITAT_V1` envelope, its canonical SHA-256, `sender_id`, `key_id`, issue time, bounded TTL, nonce, zero-authority controls and an HMAC-SHA256 tag.

Maximum canonical frame size is 64 KiB. Default TTL is 30 seconds; v1 refuses TTL above 120 seconds and rejects timestamps more than 5 seconds in the future.

## Principal binding

The validator does not accept a naked `key_id -> key` mapping. Each principal binds:

```text
key_id
-> externally supplied key material
-> enabled state
-> exact sender_id
-> allowlisted source_head set
```

A correctly signed frame is rejected if the principal is disabled, the claimed sender differs from the binding, or the Nexus envelope's `source_head` is outside that principal's allowlist.

This blocks a valid key from silently impersonating another Nexus organ. It still does **not** establish a human identity and does not authorize an external effect.

## Secret boundary

No production transport key belongs in Git, a fixture, Registry object, Habitat state file or Nexus receipt.

`tools/nexus_transport_keyring.py` separates public policy from secret material:

```text
PUBLIC CONFIG
  key_id
  sender_id
  allowed_source_heads
  secret_env NAME
  enabled

RUNTIME ENVIRONMENT
  actual secret bytes
```

Inline fields such as `key`, `secret`, `token`, `password` and `key_material` are rejected by the public config validator. The committed example contains only environment-variable names. Missing or too-short secrets fail closed.

The reference supports raw UTF-8, `hex:` and `base64:` environment values; this is a loading convention, not a claim of a production secret manager.

## Replay and freshness

The transport requires a replay guard with an atomic `consume()` operation. Admission occurs only after freshness checks and successful nonce consumption.

Two reference guards exist:

- `MemoryReplayGuard` — bounded by process lifetime; useful for tests/light local runs;
- `SqliteReplayGuard` — local crash-safe persistence using SQLite WAL, `synchronous=FULL` and `BEGIN IMMEDIATE`.

The SQLite ledger stores only:

```text
SHA256(sender_id:key_id:nonce)
expires_at_ms
recorded_at_ms
```

The raw replay key is not stored. Expired entries are pruned. A duplicate survives process restart and is rejected until expiry.

This establishes a **local persistent replay reference**, not distributed replay consensus or production database hardening.

## Backpressure

If queue depth reaches capacity, validation returns `HOLD_BACKPRESSURE`.

No delivery occurs and automatic retry permission remains false. The replay nonce is deliberately **not consumed** while the frame is held by backpressure, because no admission occurred. A later attempt remains a separately controlled action rather than an automatic retry.

```text
BACKPRESSURE != FAILURE
AMBIGUOUS DELIVERY != RETRY PERMISSION
```

## Admission order

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
-> BACKPRESSURE
-> ATOMIC REPLAY CONSUME
-> ADMISSION RECEIPT
```

An admitted receipt still states, semantically:

```text
delivery_performed = false
target_execution_performed = false
network_io_performed = false
human_identity_established = false
world_effect_authorization_established = false
authority_delta = 0
mass_effect_budget_delta = 0
```

## Still not implemented

- OS keychain or dedicated secret-manager adapter;
- rotation epochs and overlap windows;
- durable key-revocation policy across deployments;
- key-expiry policy;
- process or hardware attestation;
- mTLS;
- distributed replay consensus;
- endpoint listener;
- destination acceptance/delivery receipts;
- live cross-repository delivery.

## Next transport gate

Before any listener is enabled:

1. confirm exact-head CI for principal/keyring/replay-ledger tests;
2. add explicit key epochs and revocation state without storing key material;
3. bind destination endpoint identity and delivery/acceptance receipts;
4. red-team restart, duplicate, partial-delivery, clock and key-rotation cases;
5. only then consider a loopback-only transport adapter as a new version.
