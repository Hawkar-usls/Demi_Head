# JANUS Nexus Habitat

## Status

`JANUS_NEXUS_HABITAT_V1` is a **local deterministic coordination reference**, not a production message bus, autonomous agent society, or authority layer.

Its purpose is to let already-bounded JANUS heads describe how information may move between them without allowing connectivity to manufacture truth, permission, or external effects.

```text
HABITAT = DECLARED LOCAL COORDINATION ENVIRONMENT
NEXUS   = TYPED FAIL-CLOSED ROUTING CONTRACT
ROUTE   != DELIVERY
ROUTE   != TRUTH
ROUTE   != AUTHORITY
MORE CONNECTED HEADS != MORE RIGHTS
LINEAGE != RUNTIME OWNERSHIP
```

The existing `Janus_Genesis` Git Habitat remains the repository-constellation / rooms / memory / handoff environment. Nexus is a bounded typed coordination spine inside that constitutional environment; it does not replace Git Habitat.

## Why this layer exists

DemiHead already separates Observer and Guardian planes and already binds HRain/iNaiHR through a read-only bicameral bridge. The integration risk is architectural sprawl: every new JANUS subsystem could otherwise invent ad-hoc cross-module calls, payload meanings, retries, and implicit permissions.

Every Nexus hop therefore requires:

- a known source head and target head;
- a typed payload kind;
- a SHA-256 payload reference;
- an explicitly admitted `(source, target, kind)` route;
- a bounded hop lifetime;
- read-only transfer;
- zero authority delta;
- zero mass-effect-budget delta;
- no direct cross-head workspace mutation;
- no external-effect authorization.

## Initial habitat heads

| Head | Runtime role | Runtime repository | Lineage/reference |
| --- | --- | --- | --- |
| `PORTAL` | typed destination router | `Hawkar-usls/Janus` | — |
| `OBSERVER` | read-only environment observer | `Hawkar-usls/Demi_Head` | — |
| `HRAIN` | structural context | `Hawkar-usls/Hrain` | — |
| `INAIHR` | associative context | `Hawkar-usls/iNaiHR` | — |
| `BICAMERAL_BRIDGE` | read-only context binder | `Hawkar-usls/Demi_Head` | — |
| `FUNDAMENTUM` | `FUNDAMENTUM_GUARD` | `Hawkar-usls/Demi_Head` | `Hawkar-usls/Janus-Fundamentum` |
| `GUARDIAN` | bounded evidence-state head | `Hawkar-usls/Demi_Head` | — |
| `RELEASE_CONTROL` | stop-or-continue gate | `Hawkar-usls/Demi_Head` | — |
| `REGISTRY` | provenance archive | `Hawkar-usls/janus-meta-registry` | — |

`Janus-Fundamentum` is an independent scientific proof-search laboratory and methodological lineage source. It does **not** become the live Nexus guard merely because DemiHead adopts Fundamentum-style witness-ledger and falsification discipline. The executable guard-side code lives in DemiHead.

## Bicameral vertical

```text
HRAIN -----------\
                  > BICAMERAL_BRIDGE -> FUNDAMENTUM_GUARD -> GUARDIAN
INAIHR ----------/
```

`HRAIN` and `INAIHR` emit read-only `HEMISPHERE_PACKET` objects. The bridge can emit a `BICAMERAL_RESULT`, but overlap remains non-truth and divergence remains visible.

The Nexus adapter `tools/nexus_fundamentum_adapter.py` adds a stronger boundary:

```text
BICAMERAL_RESULT ALONE
-> HOLD_RECEIPT
-> CONTEXT_ONLY_NOT_EVIDENCE
```

It cannot create `EVIDENCE_RECEIPT` without a separately provenance-bound witness/evidence case. Therefore even a fixture in which both hemispheres contain keys such as `context` and `evidence` remains HOLD.

Frozen replay surfaces:

- `examples/hemisphere_left_hrain.json`
- `examples/hemisphere_right_inaihr.json`
- `examples/nexus_bicameral_result.json`
- `examples/nexus_bicameral_to_fundamentum.json`
- `examples/nexus_fundamentum_hold_receipt.json`
- `examples/nexus_fundamentum_to_guardian_hold.json`
- `tests/test_nexus_fundamentum_adapter.py`

Canonical fixture hashes:

```text
BICAMERAL_RESULT_SHA256 = 527483db3e5970ea9cfe3fba69a80a70a757b00e9a060cdea1dac023f78f5566
FUNDAMENTUM_HOLD_SHA256 = 434b78adb5a04253cbe9c5317d4c2ada1487c9a32e435b03999706be27273679
```

## Observer / SysEar vertical

```text
LOCAL ROUTER TELEMETRY
      |
      v
REDACTION + NORMALIZATION
      |
      v
   OBSERVER -> GUARDIAN
      |
      +------> REGISTRY
```

The historical SysEar/router line belongs here only after normalization. Raw packet contents, credentials, private addresses, MAC addresses, exact deployment identifiers and raw firewall lines are not Nexus payloads by default.

Network timing variability may be recorded as an environmental entropy candidate, but Nexus does not promote it to quantum randomness, cryptographic entropy, truth, or direct model-temperature authority.

Current sanitized fixture surfaces:

- `examples/sysear_sanitized_observation.json`
- `examples/nexus_sysear_observer_to_guardian.json`

## Route contract

Reference implementation:

- `tools/nexus_habitat.py`
- `tools/nexus_fundamentum_adapter.py`
- `schemas/nexus-envelope.schema.json`
- `tests/test_nexus_habitat.py`
- `tests/test_nexus_fundamentum_adapter.py`

A route is admitted only if source emit type, target accept type, and the exact source-target-kind edge all match the allowlist. A route receipt remains a routing statement only:

```text
ROUTE_RECEIPT != DELIVERY_RECEIPT
DELIVERY_RECEIPT != TRUTH
```

## Habitat availability

A habitat snapshot may mark each head as:

```text
READY
DEGRADED
HOLD
OFFLINE
UNKNOWN
```

Missing is not silently interpreted as healthy, and a degraded/offline head is not silently impersonated by another head.

```text
MISSING != SUCCESS
STALE != CURRENT
FALLBACK != ORIGINAL SOURCE
AVAILABILITY != AUTHORITY
LINEAGE_REPOSITORY != RUNTIME_PROVIDER
```

## Security boundary

Nexus Habitat does **not** provide arbitrary URL proxying, arbitrary repository execution, secret transfer, process injection, memory scraping, covert network interception, automatic publication, autonomous identity creation, mass persuasion, permission inheritance, or a model-writable constitution.

A future live transport adapter must separately specify authentication, endpoint identity, replay protection, freshness, backpressure, rate limits, retention/redaction and reconciliation after partial failure.

## Current gates

Two local reference slices now exist:

```text
SYSEAR_SANITIZED_FIXTURE
-> OBSERVER
-> NEXUS ROUTE
-> GUARDIAN TARGET
```

and

```text
HRAIN + INAIHR
-> BICAMERAL_RESULT
-> FUNDAMENTUM_GUARD HOLD_RECEIPT
-> NEXUS ROUTE
-> GUARDIAN TARGET
```

Neither slice currently proves live cross-repository delivery or Guardian ingestion. The next engineering gate is to implement a bounded Guardian read-only ingress/receipt and freeze the first full local end-to-end receipt chain before adding a live transport.

## Canonical laws

```text
CONNECTIVITY != AUTHORITY
ROUTE_COMPATIBILITY != ROUTE_ADMISSION
ROUTE_RECEIPT != DELIVERY_RECEIPT
DELIVERY_RECEIPT != TRUTH
ASSOCIATION != EVIDENCE
CONTEXT != WITNESS
BOTH_HEMISPHERES_AGREE != TRUTH
LINEAGE != RUNTIME_OWNERSHIP
HEAD_AVAILABILITY != HEAD_CORRECTNESS
HEAD_COUNT != FAILURE_DOMAIN_COUNT
FALLBACK != SOURCE_IDENTITY
HABITAT != MONOLITH
NEXUS != COMMAND_BUS
```
