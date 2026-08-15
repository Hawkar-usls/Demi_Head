# Roadmap

The roadmap is gate-based. File presence does not promote a later phase into an implemented capability.

## G0 — Repository / constitutional foundation

Status: `IMPLEMENTED`

- public maturity and claim boundary;
- security policy and cross-repository lineage;
- observer architecture preserved;
- Guardian Mesh / KETO architecture added;
- machine-readable project status;
- contract and local-link validation.

Exit condition: reviewer can identify what DemiHead may do, what it may not do, and which claims remain unestablished.

## K1 — Local Evidence Graph MVP

Status: `IMPLEMENTED_REFERENCE_VERTICAL_SLICE`

- `janus.demihead.keto_case.v1` schema;
- synthetic claim/presentation fixture;
- declared root collapse;
- stale/current separation;
- official-position separation;
- authenticated-independence counter;
- support/contradiction preservation;
- bounded evidence-state output;
- mass-effect budget fixed to zero;
- release-control recommendation;
- unit tests and CI execution.

Exit condition: synthetic fixture deterministically demonstrates that many derivative presentations do not become many independent witnesses, stale evidence is not counted as current, and support + contradiction remains `CONTESTED`.

## K2 — Evidence / independence receipts

Status: `NEXT`

- versioned result schema;
- provenance edges beyond declared `root_id`;
- correction / supersession edges;
- authenticated source identity;
- failure-domain annotations;
- deterministic independence receipt;
- append-only case ledger;
- replay verifier;
- tamper fixtures.

Borrowed patterns: AIFC witness lifecycle and canonicalization, Connection authenticated-independence receipts, Fast-CAT disagreement preservation.

Exit condition: two apparent witnesses count as independent only when the receipt proves the required distinct identities/failure domains under the frozen policy.

## K3 — Read-only public-source gateway

Status: `NOT_STARTED`

- one narrowly scoped public source adapter;
- frozen source identity and expected fields;
- freshness/cache semantics;
- correction polling;
- timeout/degraded-mode tests;
- source payload stored as typed data, never privileged instruction;
- no platform write capability.

Exit condition: adapter failure, stale cache, malformed data and source disagreement all fail closed without inventing a current answer.

## K4 — Human-visible Guardian interface

Status: `NOT_STARTED`

- HRain-compatible evidence graph projection;
- UA and EN full-fidelity renderings;
- optional RU post-irony only outside high-stakes modes;
- source-root / presentation counts visible;
- official / independent / contradiction / unknown columns;
- user correction and appeal input;
- release-control / finite-session UX;
- accessibility review.

Exit condition: language or tone changes do not change machine evidence state, uncertainty, safety urgency or user rights.

## K5 — User-invoked platform / edge interfaces

Status: `NOT_STARTED`

Candidates:

- public PWA/web;
- user-invoked Telegram bot or Mini App;
- non-emergency SMS short-code bootstrap design;
- call-center/operator read-only view;
- local/edge client for degraded connectivity.

Hard boundaries:

```text
NO COVERT PERSONAS
NO AUTONOMOUS ASTROTURF
NO UNSOLICITED POLITICAL OUTREACH
NO PLATFORM RULE BYPASS
NO MASS EFFECT FROM FACE CONSENSUS
```

Exit condition: adapters are transparent, user-invoked where appropriate, authenticated, rate-limited, auditable and preserve opt-out.

## K6 — Civic / government pilot governance

Status: `DESIGN_ONLY`

Before any public-sector pilot:

- legal/privacy/security review;
- independent source-selection-bias audit;
- independent language-invariance audit;
- human-rights and accessibility review;
- public correction/appeal ledger design;
- bounded retention / deletion policy;
- two-key governance for any admitted high-impact public communication;
- red-team against covert persuasion, identity spawning, emergency-power creep and automated punitive use.

Exit condition: external reviewers, not internal Faces, establish that the pilot satisfies the frozen governance gates.

## Observer track — preserved in parallel

The original DemiHead telemetry project remains a valid lower-layer research track.

### O1 — Windows observer

Status: `NOT_STARTED`

Opt-in allowlisted process counters, lifecycle-safe PID tracking, CPU/memory/I/O deltas, stale/reset handling and JSON Lines output.

### O2 — Observer accounting

Status: `NOT_STARTED`

DemiHead self-telemetry, resource budgets, matched baselines, hold/stop behavior and overhead receipt.

### O3 — Domain-specific observer profile

Status: `DEFERRED`

A Storj-specific or other application profile may be added only through documented public/OS observability surfaces with no payload, credential, memory or control-channel capture.

## Permanent deferred / forbidden without a new constitution

- covert mass persuasion;
- self-spawning public identities;
- political psychographic targeting;
- autonomous astroturf;
- model-written constitutional overrides;
- AI-only punitive/legal decisions;
- third-party process control from untrusted information;
- undocumented/elevated access adapters;
- treating internal consensus as independent external evidence.

## Success criterion

The project does not succeed by maximizing sessions or convincing the user.

A good terminal state is:

```text
THE CASE IS STRUCTURED
THE ROOTS ARE VISIBLE
THE UNCERTAINTY IS VISIBLE
THE USER CAN CHOOSE
THE SESSION CAN END
```
