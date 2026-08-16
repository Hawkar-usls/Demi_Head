# JANUS DemiHead — Local Acceptance Browser Holdout v1

Status: **frozen candidate until exact-head CI, PR replay and merge-commit replay**.

This gate moves the already-admitted local reverse proposal architecture from pure/in-memory compatibility tests into a real headless Chromium session with real browser `localStorage` — but only on an isolated localhost fixture origin and only with synthetic workspaces.

## Frozen before first Chromium execution

- corpus: `holdout/local_accept_browser_v1/frozen_corpus.json`
- freeze SHA-256: `f44263abaf0fa23c0344f4c68719e1a695d122c251fc373e732724d7958f2c49`
- preregistered cases: **17**
- DemiHead: `fc542466279bd15bceb7171514a84d1c1d002a11`
- HRain: `ceb81210c2f70b71d6c941e0b088a68969ead7b9`
- iNaiHR: `b27cd8732b3137caea1036024acc1778ea02213a`
- browser engine: Chromium
- fixture server: `http://127.0.0.1:8765`
- live user data: **false**
- external network effects: **false**

The canonical freeze payload hash is checked in the normal Python repository validator, independently in the browser workflow before Chromium starts, and again by the Node runner.

## What the browser holdout actually exercises

The test uses the real merged HTML/JavaScript surfaces, not just imported pure functions:

1. seed synthetic HRain and iNaiHR workspaces into real browser storage;
2. open the exact merged read-only hemisphere sidecar;
3. read the packet from its UI;
4. open the real DemiHead Proposal Lab;
5. load that packet through the file input;
6. build a proposal in the browser;
7. exercise the browser download path;
8. load the downloaded JSON into the exact merged hemisphere-owned apply page;
9. verify preview changes no storage;
10. verify DECLINE changes no storage;
11. repeat and explicitly ACCEPT LOCALLY;
12. verify exactly one admitted `ADD_NODE` change;
13. reload and verify provenance persistence;
14. change the base graph after preview and verify the accept-time recheck refuses it;
15. tamper with proposal content while leaving the old proposal hash and verify refusal;
16. verify HRain and iNaiHR do not mutate each other's storage keys despite sharing one web origin;
17. for iNaiHR, perform a narrow core-style serializer roundtrip in the real browser storage and verify sidecar metadata restores SYSTEM provenance only for a graph node that still exists.

## Same-origin problem is part of the test

The localhost fixture deliberately serves DemiHead, HRain and iNaiHR from one origin, mirroring the important GitHub Pages fact that project paths under `hawkar-usls.github.io` are not separate origins.

The holdout therefore verifies **key isolation**, not fictitious origin isolation:

```text
GITHUB_PAGES_PROJECT_PATH != ORIGIN_ISOLATION
SHARED_ORIGIN != SHARED_STORAGE_KEY
```

HRain may write only its admitted HRain key. iNaiHR may write only its graph key plus its local DemiHead provenance metadata key. Cross-key mutation fails the holdout.

## Network boundary

The Playwright context blocks and records any HTTP(S) request whose origin differs from the frozen localhost fixture origin. Admission requires zero attempted external network requests.

This is a functional browser gate, not a production networking benchmark.

```text
LOCALHOST_CHROMIUM_HOLDOUT != PRODUCTION_NETWORK_VALIDATION
```

No browser/network latency claim is made from this gate.

## Human/crypto claim ceiling

The holdout genuinely exercises a browser button click and a real browser localStorage mutation, but the automated test click is not human identity and the content hash is not a signature:

```text
AUTOMATED_BROWSER_CLICK != VERIFIED_HUMAN_IDENTITY
SHA256_BINDING != SIGNATURE
```

The test establishes that the UI path requires a distinct accept action and that no mutation occurs on preview/decline. It does not establish who clicked in a real deployment.

## Constitutional boundary

```text
PROPOSAL != WORLD_EFFECT
DEMIHEAD_PROPOSAL != WORKSPACE_MUTATION
NO_ACCEPT_EVENT => NO_MUTATION
DECLINE != PENALTY
DIRECT_CROSS_HEMISPHERE_WRITE = FORBIDDEN
EXTERNAL_NETWORK_EFFECT = FORBIDDEN
LIVE_USER_DATA = false
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

Passing this holdout may support the narrow claim that the frozen local UI flow functions in CI Chromium on synthetic data. It does not establish production readiness, authenticated human authorization, digital signatures, real-user safety, independent evidence, biological equivalence, consciousness/personhood, measured cognitive gain or production network performance.
