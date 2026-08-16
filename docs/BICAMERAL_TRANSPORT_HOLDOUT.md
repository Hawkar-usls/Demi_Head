# JANUS DemiHead — Frozen Bicameral Transport Holdout v1

Status: **FROZEN CANDIDATE; admission requires exact-head CI**.

This gate tests the transport boundary between the bounded software-role hemispheres:

- `LEFT_HRAIN / STRUCTURAL_CONTEXT`
- `RIGHT_INAIHR / ASSOCIATIVE_CONTEXT`
- DemiHead as request binder, packet validator, comparison arbiter and HOLD controller.

The hemisphere names are an architecture metaphor, not a neuroscience claim.

## Frozen dependency line

The preregistered corpus binds these revisions before first execution:

- DemiHead base: `5f6fb1fa40558659beba25837f0b059dfdccdcda`
- HRain request-bound bridge: `c1c4e61e18e1adf15ed1d43da51129b262119985`
- iNaiHR request-bound bridge: `a79cc9affa733bf3d2d6b0ed4815fccf938f3292`

Frozen corpus:

- `holdout/bicameral_transport_v1/frozen_corpus.json`
- canonical `freeze_payload` SHA-256: `d33077fbd0d244bf0ae6d678894bdc9a8eddcf0d779ce11b85e39eeff6143883`
- cases: **18**
- timeout: **2000 ms** in the synthetic event timeline
- quantiles: nearest-rank

The freeze hash is checked independently in Python and Node before the test result is admitted.

## Why request binding was added first

The original browser bridge already checked `event.origin` and iframe `event.source`, but an old response from an earlier request cycle had no request/session identifier. A delayed old message could therefore be confused with a response to a later request.

The v1.1 sidecars now require and exactly echo a bounded `request_id`. DemiHead accepts a response only when its request id matches the current active request.

This is freshness/session binding only:

```text
REQUEST_ID_ECHO != AUTHENTICATION
```

It does not authenticate a person, provider, browser, repository revision or external service.

## Preregistered adversarial cases

The frozen corpus exercises:

1. nominal overlap;
2. nominal divergence;
3. left-only timeout;
4. right-only timeout;
5. no-hemisphere timeout;
6. wrong origin followed by valid traffic;
7. wrong iframe/source followed by valid traffic;
8. stale request replay followed by valid traffic;
9. malformed schema followed by valid traffic;
10. non-zero authority delta followed by valid traffic;
11. direct-mutation request followed by valid traffic;
12. hemisphere packet presented by the wrong frame;
13. duplicate hemisphere response;
14. response arriving after the deadline;
15. wrong message type followed by valid traffic;
16. unknown provenance origin followed by valid traffic;
17. missing request id followed by valid traffic;
18. request-session rotation with an old reply arriving after rotation.

Failed/refused/ignored events are retained in the result ledger. The corpus is not edited after first execution to make a failing case pass.

## Exact frozen sidecar verification

CI also checks out the exact frozen HRain and iNaiHR commits into isolated directories and executes their real `demihead-bridge.js` implementations. The verifier checks:

- exact request-id echo;
- expected hemisphere, role and repository identity;
- provenance normalization;
- read-only transfer;
- direct mutation disabled;
- authority delta = 0;
- mass-effect budget delta = 0;
- no local-storage write API in the sidecar;
- no network-fetch/API write surface in the sidecar;
- no wildcard packet response target.

This prevents the central transport test from silently assuming behavior that the frozen hemisphere code does not implement.

## Latency semantics

The holdout records p50/p95/p99 over **synthetic event timestamps** only. These values test deterministic deadline/ordering logic.

They are **not** browser, network, GitHub Pages or production latency measurements:

```text
FROZEN_SYNTHETIC_EVENT_TRACE != REAL_BROWSER_NETWORK_LATENCY
```

A later browser/network benchmark must use measured wall-clock observations and a separately frozen workload before any real latency claim is allowed.

## Constitutional boundary

```text
BOTH_HEMISPHERES_AGREE != TRUTH
HEMISPHERE_COUNT != AUTHORITY
SOFTWARE_SURFACE_COUNT != INDEPENDENT_EVIDENCE_ROOT_COUNT
ASSOCIATION != EVIDENCE
STRUCTURE != COMMAND
REQUEST_ID_ECHO != AUTHENTICATION
PACKET_TRANSFER = READ_ONLY
DIRECT_CROSS_HEMISPHERE_MUTATION = FORBIDDEN
AUTOMATIC_GRAPH_MERGE = false
EXTERNAL_EFFECT_PERMITTED = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

Passing this holdout does not establish biological equivalence, consciousness/personhood, independent corroboration, measured cognitive gain, real-world effectiveness or production readiness.

## Next gate after admission

Only after this frozen transport gate is admitted should the reverse-channel candidate be developed:

```text
DemiHead
   ↓
NON_MUTATING_PROPOSAL
   ↓
explicit local HUMAN_ACCEPT event
   ↓
hemisphere-owned local mutation adapter
```

The reverse channel must preserve:

```text
DEMIHEAD_PROPOSAL != WORKSPACE_MUTATION
HUMAN_ACCEPT_EVENT != DEMIHEAD_ASSERTED_FLAG
NO_ACCEPT_EVENT => NO_MUTATION
CROSS_HEMISPHERE_WRITE = FORBIDDEN
```
