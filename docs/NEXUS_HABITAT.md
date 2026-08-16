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
```

## Why this layer exists

DemiHead already separates Observer and Guardian planes and already binds HRain/iNaiHR through a read-only bicameral bridge. The next integration risk is architectural sprawl: every new JANUS subsystem could otherwise invent its own ad-hoc cross-module calls, payload meanings, retries, and implicit permissions.

Nexus Habitat narrows that risk by requiring each coordination hop to declare:

- a known source head;
- a known target head;
- a typed payload kind;
- a SHA-256 payload reference;
- an explicitly admitted `(source, target, kind)` route;
- bounded hop lifetime;
- read-only transfer;
- zero authority delta;
- zero mass-effect-budget delta;
- no direct cross-head workspace mutation;
- no external-effect authorization.

## Initial habitat heads

| Head | Role | Repository |
| --- | --- | --- |
| `PORTAL` | typed destination router | `Hawkar-usls/Janus` |
| `OBSERVER` | read-only environment observer | `Hawkar-usls/Demi_Head` |
| `HRAIN` | structural context | `Hawkar-usls/Hrain` |
| `INAIHR` | associative context | `Hawkar-usls/iNaiHR` |
| `BICAMERAL_BRIDGE` | read-only context binder | `Hawkar-usls/Demi_Head` |
| `FUNDAMENTUM` | witness-ledger truth guard | `Hawkar-usls/Janus-Fundamentum` |
| `GUARDIAN` | bounded evidence-state head | `Hawkar-usls/Demi_Head` |
| `RELEASE_CONTROL` | stop-or-continue gate | `Hawkar-usls/Demi_Head` |
| `REGISTRY` | provenance archive | `Hawkar-usls/janus-meta-registry` |

Repository names describe provenance and intended ownership. This reference does not prove that every repository currently exposes a live adapter.

## First admitted verticals

### Context vertical

```text
HRAIN -----------\
                  > BICAMERAL_BRIDGE -> FUNDAMENTUM -> GUARDIAN -> RELEASE_CONTROL
INAIHR ----------/
```

`HRAIN` and `INAIHR` can emit read-only `HEMISPHERE_PACKET` objects toward the bridge. The bridge may emit a `BICAMERAL_RESULT`; agreement remains non-truth and divergence remains visible. Fundamentum remains the witness/commit guard rather than being bypassed by context plurality.

### Observer vertical

```text
LOCAL TELEMETRY
      |
      v
   OBSERVER -> GUARDIAN
      |
      +------> REGISTRY
```

This is where the historical SysEar/router line belongs after normalization.

The intended evolution is:

```text
router/syslog or other allowlisted telemetry
-> redaction
-> bounded observation window
-> normalized signal frame
-> freshness / quality / spoofability gate
-> OBSERVATION_SIGNAL
-> Nexus read-only envelope
-> GUARDIAN and/or REGISTRY
```

Raw packet contents, credentials, private addresses, MAC addresses, or deployment-specific secrets are not Nexus payloads by default.

Network timing variability may be recorded as an environmental entropy candidate, but Nexus does not promote it to quantum randomness, cryptographic entropy, truth, or direct model-temperature authority.

### Evidence vertical

```text
FUNDAMENTUM -> GUARDIAN -> RELEASE_CONTROL
       |            |
       v            v
    REGISTRY      REGISTRY
```

A valid route only proves that an envelope conforms to the declared coordination contract. It does not establish that the referenced evidence is true, that the target received it, or that any effect occurred.

## Route contract

Reference implementation:

- `tools/nexus_habitat.py`
- `schemas/nexus-envelope.schema.json`
- `tests/test_nexus_habitat.py`

Example control block:

```json
{
  "read_only_transfer": true,
  "direct_workspace_mutation": false,
  "external_effect_permitted": false,
  "authority_delta": 0,
  "mass_effect_budget_delta": 0,
  "ttl_hops": 4
}
```

The Python reference performs a second semantic validation beyond JSON Schema: source emit type, target accept type, and the exact source-target-kind edge must all be admitted.

## Habitat availability

A habitat snapshot may mark each head as:

```text
READY
DEGRADED
HOLD
OFFLINE
UNKNOWN
```

Missing is not silently interpreted as healthy. A degraded or offline head is not silently replaced by another head merely to preserve throughput.

This preserves the existing JANUS degraded-mode doctrine:

```text
MISSING != SUCCESS
STALE != CURRENT
FALLBACK != ORIGINAL SOURCE
AVAILABILITY != AUTHORITY
```

## Security boundary

Nexus Habitat does **not** provide:

- arbitrary URL proxying;
- arbitrary repository execution;
- secret transfer;
- process injection;
- memory scraping;
- covert network interception;
- automatic external publication;
- autonomous identity creation;
- mass persuasion;
- automatic retry of ambiguous external effects;
- permission inheritance between heads;
- a model-writable constitution.

A future live transport adapter must separately specify authentication, endpoint identity, replay protection, freshness, backpressure, rate limits, retention/redaction, and reconciliation after partial failure.

## First next gate

The reference contract should be considered only a **coordination spine** until a real end-to-end fixture proves one complete path on exact repository revisions.

Recommended first fixture:

```text
SYSEAR_SANITIZED_FIXTURE
-> OBSERVER NORMALIZER
-> OBSERVATION_SIGNAL
-> NEXUS ENVELOPE
-> GUARDIAN READ-ONLY INGEST
-> REGISTRY RECEIPT
```

Acceptance criteria:

1. no raw private network identifiers in the committed fixture;
2. deterministic canonical SHA-256 binding;
3. stale and malformed observations fail closed;
4. forged authority or mass-effect deltas are rejected;
5. route receipt is not represented as delivery;
6. Guardian output remains bounded and read-only;
7. Registry receives provenance, not operational secrets;
8. exact test corpus and expected receipts are frozen before the final run.

Only after that slice is green should a second transport connect the bicameral result path through Fundamentum and Guardian.

## Canonical laws added by Nexus Habitat

```text
CONNECTIVITY != AUTHORITY
ROUTE_COMPATIBILITY != ROUTE_ADMISSION
ROUTE_RECEIPT != DELIVERY_RECEIPT
DELIVERY_RECEIPT != TRUTH
HEAD_AVAILABILITY != HEAD_CORRECTNESS
HEAD_COUNT != FAILURE_DOMAIN_COUNT
FALLBACK != SOURCE_IDENTITY
HABITAT != MONOLITH
NEXUS != COMMAND_BUS
```
