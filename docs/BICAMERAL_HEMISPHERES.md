# DemiHead Bicameral Hemisphere Bridge

## Purpose

This bridge turns the existing HRain and iNaiHR relationship into an explicit, inspectable DemiHead contract.

The hemisphere terminology is a **software architecture metaphor**, not a neuroscience claim.

```text
HRain / LEFT
  explicit graph structure
  editable local context
  links, hierarchy, inspection
            |
            | read-only packet
            v
         DemiHead
   bind -> check -> compare
   preserve disagreement
   never manufacture authority
            ^
            | read-only packet
            |
iNaiHR / RIGHT
  semantic association
  remote/local synthesis
  alternative concept expansion
```

## Roles

### `LEFT_HRAIN`

Canonical software role: `STRUCTURAL_CONTEXT`.

HRain contributes what its current implementation actually has: a human-editable local graph, explicit node/link structure, JSON portability, local context and optional AI-assisted enrichment.

It does **not** become a truth engine.

### `RIGHT_INAIHR`

Canonical software role: `ASSOCIATIVE_CONTEXT`.

iNaiHR contributes semantic expansion from compact input, including clearly separated `REMOTE_AI` and deterministic `LOCAL_FALLBACK` generation paths.

Association is proposal material, not evidence.

## DemiHead is the corpus callosum + arbiter

DemiHead receives packets. It does not silently merge the two browser workspaces.

```text
LEFT_PACKET + RIGHT_PACKET
        |
        v
VALIDATE SOURCE/ROLE/CONTROL
        |
        v
PRESERVE PACKET SHA-256 RECEIPTS
        |
        v
COMPARE CONSERVATIVE LABEL KEYS
        |
        +--> overlap      -> BICAMERAL_OVERLAP_PRESENT
        |
        +--> no overlap   -> BICAMERAL_DIVERGENCE_PRESERVED
        |
        +--> one missing  -> DEGRADED_SINGLE_HEMISPHERE_HOLD
```

No output state authorizes an external effect.

## Browser transport

The first browser transport is intentionally narrow and read-only.

- HRain publishes `demihead.html` + `demihead-bridge.js` on its own GitHub Pages origin.
- iNaiHR publishes the same pair for its own workspace.
- [`../examples/bicameral_console.html`](../examples/bicameral_console.html) embeds the two sidecars and sends the explicit message `JANUS_DEMIHEAD_REQUEST_PACKET_V1`.
- A sidecar responds with `JANUS_DEMIHEAD_HEMISPHERE_PACKET_V1` only to an allowlisted requesting origin and targets the exact `event.origin`, never `*`.
- The console keeps the returned packets only in runtime memory and never writes back to either workspace.

```text
HEMISPHERE -> DEMIHEAD = READ_ONLY_PACKET
DEMIHEAD -> HEMISPHERE = PACKET_REQUEST_ONLY
DEMIHEAD -> WORKSPACE_MUTATION = FORBIDDEN_IN_V1
```

This means the arrows in the visual architecture are bidirectional only at the control-message level. Graph content itself flows into DemiHead; DemiHead does not mutate either graph.

## Provenance-aware nodes

The bridge requires each exported graph node to carry one of:

```text
USER
REMOTE_AI
LOCAL_FALLBACK
LEGACY_UNKNOWN
SYSTEM
```

This distinction is necessary because generated material must not silently become a human-authored fact or an independent witness.

Legacy nodes that predate the bridge are conservatively marked `LEGACY_UNKNOWN` unless their origin is already explicit. For legacy iNaiHR persistence, an existing `isAI=true` marker may be preserved as `REMOTE_AI`; old non-AI nodes remain `LEGACY_UNKNOWN` because the old persisted representation does not distinguish human input from deterministic fallback.

## Hard invariants

```text
HEMISPHERE_METAPHOR != NEUROSCIENCE_CLAIM
LEFT != MORE_RATIONAL
RIGHT != LESS_RATIONAL

BOTH_HEMISPHERES_AGREE != TRUTH
HEMISPHERE_COUNT != AUTHORITY
SOFTWARE_SURFACE_COUNT != INDEPENDENT_EVIDENCE_ROOT_COUNT
ASSOCIATION != EVIDENCE
STRUCTURE != COMMAND
REMOTE_AI_OUTPUT != INDEPENDENT_WITNESS
LOCAL_FALLBACK != MODEL_OUTPUT
LEGACY_UNKNOWN != USER_AUTHORED

PACKET_TRANSFER = READ_ONLY
DIRECT_CROSS_HEMISPHERE_MUTATION = FORBIDDEN
AUTOMATIC_GRAPH_MERGE = false
EXTERNAL_EFFECT_PERMITTED = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

## Conservative overlap

The reference bridge does not run an embedding model to decide that two concepts are equivalent. It only:

1. trims whitespace;
2. removes leading decorative symbol/emoji material;
3. case-folds the remaining label;
4. compares exact resulting strings.

Therefore `🧩 Context` and `Context` may overlap, while `Context` and `Contextual` do not.

This comparison is navigation metadata only.

## Packet contract

Schema: [`../schemas/hemisphere-packet.schema.json`](../schemas/hemisphere-packet.schema.json)

Reference packets:

- [`../examples/hemisphere_left_hrain.json`](../examples/hemisphere_left_hrain.json)
- [`../examples/hemisphere_right_inaihr.json`](../examples/hemisphere_right_inaihr.json)

Reference result schema: [`../schemas/bicameral-result.schema.json`](../schemas/bicameral-result.schema.json)

Live-console source: [`../examples/bicameral_console.html`](../examples/bicameral_console.html)

## Run

```bash
python tools/hemisphere_bridge.py --self-test

python tools/hemisphere_bridge.py \
  --left examples/hemisphere_left_hrain.json \
  --right examples/hemisphere_right_inaihr.json \
  --output /tmp/bicameral-result.json
```

The browser projects may export packets conforming to this contract. DemiHead can then bind them without needing provider secrets, shared mutable storage or registry write permission.

For the browser console, serve the repository over HTTP rather than opening the HTML with an opaque `file://` origin. The production sidecars are intended to live under `https://hawkar-usls.github.io/...`; localhost is supported by each sidecar for development.

## Failure / degraded mode

If either hemisphere is absent, malformed, mislabelled, requests direct mutation, carries a non-zero authority delta, or contains invalid topology, the bridge fails closed or enters the single-hemisphere HOLD path.

```text
ONE_HEMISPHERE_AVAILABLE != WHOLE_HEAD_CONFIDENCE
DEGRADED != FALSE
MISSING_HEMISPHERE != PERMISSION_TO_INVENT
```

## Claim ceiling

This bridge establishes a deterministic, provenance-aware transport and comparison contract between three repositories. It does **not** establish:

- biological hemispheric equivalence;
- consciousness or personhood;
- semantic correctness of either graph;
- truth from agreement;
- independent corroboration from two software surfaces;
- measured cognitive-performance improvement;
- autonomous external-action authority;
- production deployment.
