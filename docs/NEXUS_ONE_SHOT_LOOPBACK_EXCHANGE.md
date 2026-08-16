# JANUS Nexus One-Shot Authenticated Loopback Exchange

`JANUS_NEXUS_ONE_SHOT_LOOPBACK_EXCHANGE_V1` is a candidate transport layer built strictly on the already-certified localhost socket admission, authenticated frame validator, persistent replay guard and intent-guarded local dispatcher.

It is intentionally **not** a daemon and not a general network service.

```text
BOUND LOOPBACK LISTENER
-> ACCEPT EXACTLY ONE LOOPBACK PEER
-> RECEIVE EXACTLY ONE BOUNDED REQUEST
-> VALIDATE WIRE FRAMING
-> HMAC / EPOCH / FRESHNESS / REPLAY ADMISSION
-> CURRENT PRINCIPAL REVALIDATION
-> PAYLOAD SHA-256 BINDING
-> INTENT-GUARDED LOCAL DISPATCH
-> SEND ONE COMPACT RECEIPT
-> CLOSE CONNECTION AND LISTENER
```

## Wire format

Each packet is:

```text
4-byte unsigned big-endian JSON length
+ exactly that many UTF-8 JSON bytes
```

The maximum JSON payload is 65,536 bytes. Length `0`, oversized lengths, malformed UTF-8, malformed JSON and partial bodies fail closed.

The request has exactly three top-level fields:

```json
{
  "schema": "janus.demihead.nexus_loopback_exchange_request.v1",
  "frame": {"...": "authenticated Nexus transport frame"},
  "payload": {"...": "content-addressed local payload"}
}
```

The frame is not replaced by a new socket-specific authentication scheme. It is validated by the existing `JANUS_NEXUS_LOCAL_TRANSPORT_V1` HMAC/epoch/freshness/replay path.

## Loopback boundary

The server only operates on a listener already admitted by `JANUS_NEXUS_LOOPBACK_SOCKET_ADMISSION_V1`. After `accept()`, the peer literal must exactly match the listener literal:

```text
127.0.0.1 -> peer 127.0.0.1
::1       -> peer ::1
```

The client helper also refuses any non-loopback literal before `connect()`.

## One-shot semantics

A bound listener accepts one connection and processes at most one request. The server closes both accepted socket and listening socket after the exchange or hold.

There is no retry loop, keep-alive, second request, reconnect policy, background daemon or auto-start path in the candidate.

## Authentication and replay

Before local dispatch, the frame must pass the already-existing transport validator:

- HMAC-SHA256;
- key ID to sender/source-head binding;
- key epoch;
- key not-before/not-after window;
- revocation state;
- TTL/future-skew checks;
- persistent replay nonce consumption.

A stale, tampered or replayed frame never reaches the local handler.

If transport succeeds but `payload` no longer matches `envelope.payload_ref.sha256`, local dispatch rejects it. The transport nonce remains consumed; correcting the payload does not grant reuse of the same authenticated frame.

## Dispatch boundary

The server calls the certified intent-guarded local dispatch design. The persistent intent ledger remains defense-in-depth even if a replay database is lost or replaced: the same admitted frame/payload/target intent cannot invoke the handler twice through the dispatch ledger.

## Receipt privacy

Only a compact receipt is returned over the loopback socket. Handler output remains local. The wire receipt contains status and content hashes, not the handler result body.

```text
handler_output_transmitted = false
```

Validation rejection receipts disclose only the failed stage, not HMAC keys, secrets or detailed validator error text.

## Frozen holdout

`fixtures/nexus_one_shot_loopback_holdout_v1.json` and `tests/test_nexus_loopback_exchange.py` cover:

- real authenticated TCP roundtrip on `127.0.0.1`;
- HMAC tamper;
- stale frame;
- persistent replay on a second listener;
- replay-ledger loss with intent-ledger defense-in-depth;
- payload hash mismatch after transport admission;
- oversized declared length;
- partial body;
- malformed JSON;
- client disconnect;
- client-side refusal of non-loopback destinations.

## Claim ceiling

A successful holdout would establish only **authenticated one-shot loopback frame exchange**.

It would not establish:

```text
cross_host_transport
general_network_service
multi_request_session
automatic_retry
external_effect_authority
production_readiness
```

The next gate after exact-head certification should be an adversarial one-shot transport gate covering replay-store failure, response-send ambiguity, concurrent listener attempts and explicit startup lifecycle controls before any persistent local daemon is considered.
