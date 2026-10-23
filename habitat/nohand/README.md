# DemiHead NOHAND Habitat Peer v1

Status: **CANDIDATE / branch-only / not merged**.

This exchange is the Git-side peer of the NAS `janus_habitat_terminal` NOHAND reconciler.

## Paths

- `habitat/nohand/inbox/` — hash-bound NAS observations/forecast requests.
- `habitat/nohand/outbox/` — create-only DemiHead advice/forecast receipts.
- `habitat/nohand/outcomes/` — NAS outcomes bound back to requests.
- `habitat/nohand/settled/` — create-only settlement receipts.
- `habitat/nohand/state/snapshots/` — create-only predictor state snapshots.

## Authority

DemiHead is `DEMIHEAD_ARBITER / BICAMERAL_ARBITER` and retains `authority_weight=0`.

`PEER_ADVICE != NAS_PERMISSION`

`PREDICTION != COMMAND`

`CALIBRATION != TRUTH`

`SHA256_RECEIPT != DIGITAL_SIGNATURE`

The peer may challenge, forecast, rank, or recommend HOLD. The NAS terminal still applies its own preservation policy and Guardian chain. No source repository is mutated by this module; it only writes peer exchange artifacts on this branch.

GoldPrompt parent main pin: `f2074ca833692f4c2a9f1cb1f5cf723c873d3211`.

GoldPrompt contract digest: `3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8`.
