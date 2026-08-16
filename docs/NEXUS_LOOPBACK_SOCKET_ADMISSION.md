# JANUS Nexus Localhost Socket Admission Candidate

This layer is a **socket admission boundary**, not a network transport authority.

`JANUS_NEXUS_LOOPBACK_SOCKET_ADMISSION_V1` can prepare a TCP listener only when both of these conditions are true:

1. the public configuration explicitly has `listener_enabled=true`;
2. the runtime caller separately supplies `explicit_enable=true`.

The repository example remains disabled.

## Address boundary

Only literal loopback addresses are admitted:

```text
127.0.0.1
::1
```

The following are rejected rather than resolved or interpreted:

```text
0.0.0.0
::
localhost
LAN addresses
other 127/8 aliases
hostnames
```

Using literal addresses avoids DNS/hosts-file ambiguity and prevents a configuration from silently becoming a wildcard or non-loopback bind.

## Current capability

The candidate can perform only:

```text
socket()
bind(exact literal loopback)
listen(bounded backlog)
```

It does **not** call `accept()`, does not read a frame, does not write a frame and does not dispatch anything through the socket.

A successful bind receipt therefore says:

```text
BOUND_LOOPBACK_LISTENER
accept_performed = false
frame_received = false
network_delivery_established = false
```

The actual bound address is checked after `getsockname()` and must equal the requested literal.

## Defaults and limits

The checked-in example uses:

```text
listener_enabled = false
host = 127.0.0.1
port = 0
backlog = 4
accept_timeout_ms = 250
max_frame_bytes = 65536
automatic_retry_permitted = false
external_effect_permitted = false
authority_delta = 0
mass_effect_budget_delta = 0
```

Backlog is capped at 16 and timeout at 5 seconds.

## Tests

`tests/test_nexus_loopback_socket_guard.py` verifies:

- disabled-by-default means no socket creation;
- a configured listener still needs explicit runtime enable;
- wildcard/LAN/hostname binds fail closed;
- a real ephemeral IPv4 bind lands exactly on `127.0.0.1`;
- IPv6 binds only to `::1` when the platform supports it;
- automatic retry, external effect and authority escalation are rejected;
- backlog, timeout and frame limits are bounded.

## Claim ceiling

Even after a successful loopback bind test:

```text
authenticated_frame_exchange = false
destination_dispatch_over_socket = false
cross_host_delivery = false
external_effect_authority = false
```

The next gate is a **one-shot authenticated frame exchange holdout** that must reuse the already-certified HMAC/epoch/replay transport semantics and v1.6 intent-guarded dispatch. It must remain loopback-only and must not auto-start from repository configuration.
