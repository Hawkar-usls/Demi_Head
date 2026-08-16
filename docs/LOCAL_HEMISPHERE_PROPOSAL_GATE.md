# JANUS DemiHead — Local Hemisphere Proposal Gate v1

Status: **candidate until exact-head CI + exact external-merge replay + merge-commit CI**.

This gate is the first reverse channel after the admitted read-only bicameral transport boundary.

```text
DemiHead
   ↓
hash-bound NON_MUTATING_PROPOSAL JSON
   ↓
local file handoff
   ↓
hemisphere-owned apply page
   ↓
PREVIEW ──► DECLINE
   │
   └──► explicit ACCEPT LOCALLY
             ↓
       fresh base-graph recheck
             ↓
       local ADD_NODE mutation
             ↓
       mutation receipt
```

## Why the handoff is a local file

HRain and iNaiHR GitHub Pages are both served from `https://hawkar-usls.github.io`. Different project paths are not different web origins.

Therefore v1 deliberately does **not** expose a `postMessage APPLY` command between the DemiHead page and a hemisphere sidecar.

```text
GITHUB_PAGES_PROJECT_PATH != ORIGIN_ISOLATION
```

The proposal is downloaded/created as JSON and must be selected on the hemisphere-owned apply page. That page can preview or decline without writing anything.

## Frozen v1 mutation allowlist

Only one operation exists:

```text
ADD_NODE
```

Not admitted:

- edit/delete node;
- add/delete link;
- replace graph;
- arbitrary JSON Patch;
- execute code;
- provider/API action;
- network write;
- registry write;
- automatic apply.

A proposed node always has `origin = SYSTEM`. It is never retroactively labelled `USER`.

## Two independent hash bindings

A proposal contains:

1. `base_graph_sha256` — SHA-256 over the canonical normalized hemisphere graph that the proposal was made against;
2. `proposal_sha256` — SHA-256 over the canonical proposal itself.

The apply page verifies the proposal hash and re-computes the current base graph hash both during preview and again on the accept path. If the workspace changed after the proposal was created:

```text
BASE_WORKSPACE_CHANGED_REPROPOSE_REQUIRED
```

SHA-256 here provides deterministic content binding only:

```text
SHA256_BINDING != SIGNATURE
```

It does not establish signer identity or authorization.

## Explicit local acceptance

Selecting a file and seeing a preview performs no mutation. `DECLINE` performs no workspace write and carries no penalty.

The local write exists only in the hemisphere-owned `ACCEPT LOCALLY` handler.

```text
DEMIHEAD_PROPOSAL != WORKSPACE_MUTATION
NO_ACCEPT_EVENT => NO_MUTATION
DECLINE != PENALTY
```

The browser click is an explicit UI event, but it is not proof of a particular human identity:

```text
CLICK_EVENT != VERIFIED_HUMAN_IDENTITY
```

## HRain persistence

HRain already serializes its node objects. An accepted proposal adds a normal local HRain node plus:

- `origin: SYSTEM`;
- `demiheadProposalId`;
- `demiheadProposalSha256`.

These fields remain local workspace provenance.

## iNaiHR persistence

The current iNaiHR application intentionally serializes a narrow node form `{id,label,x,y,isAI}`. v1 does not change that core format.

Instead, proposal provenance is stored in a separate local metadata key:

```text
inaihr_demihead_provenance_v1
```

The read-only DemiHead sidecar overlays a metadata record only when the matching graph node actually exists. Orphan metadata cannot create a node.

```text
LOCAL_METADATA != TRUSTED_ATTESTATION
```

This metadata preserves local lineage through the current iNaiHR serializer; it is not independent evidence or a trusted signature.

## Mutation receipt

After an accepted mutation the hemisphere can emit:

```text
janus.hemisphere.local_mutation_receipt.v1
```

It records:

- exact proposal id/hash;
- target hemisphere/repository;
- operation + node id;
- before/after normalized graph SHA-256;
- local acceptance event type;
- local storage key(s);
- zero authority/mass-effect controls.

The receipt is provenance about a local transition. It does not turn the transition into truth, evidence, authorization, identity proof or external effect.

## Exact external implementation line for candidate CI

The central DemiHead candidate must verify the actual merged hemisphere implementations, not mocks:

- HRain merge: `ceb81210c2f70b71d6c941e0b088a68969ead7b9`
- iNaiHR merge: `b27cd8732b3137caea1036024acc1778ea02213a`

DemiHead CI generates proposals in Python, then the exact merged JavaScript adapters independently verify the same proposal hash/base graph and prepare the mutation in memory. CI does **not** write a real browser localStorage workspace.

## Constitutional boundary

```text
PROPOSAL != WORLD_EFFECT
DEMIHEAD_PROPOSAL != WORKSPACE_MUTATION
NO_ACCEPT_EVENT => NO_MUTATION
DECLINE != PENALTY
SHA256_BINDING != SIGNATURE
CLICK_EVENT != VERIFIED_HUMAN_IDENTITY
LOCAL_METADATA != TRUSTED_ATTESTATION
DIRECT_CROSS_HEMISPHERE_WRITE = FORBIDDEN
NETWORK_APPLY = FORBIDDEN
AUTO_APPLY = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

Passing this gate does not establish production readiness, authenticated human authorization, trusted digital signatures, independent evidence, biological equivalence, consciousness/personhood or real-world effectiveness.
