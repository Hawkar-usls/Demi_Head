# JANUS Nexus v2 — Cosmos typed proof edge

Status: **candidate under frozen contract**.

This change does not rewrite `tools/nexus_habitat.py` (Nexus v1). It creates an additive v2 layer whose first new specialized provider is Janus-Cosmos.

## Frozen parent and provider

- DemiHead parent: `7c5e19f9ce3f4274cf6b83987f2204651b032eb0`
- Nexus v1 remains byte-unchanged.
- Janus-Cosmos provider: `c77f920d764229efb6932bc4ea522a4ec0342c64`
- Exposed operation: `VERIFY_CANONICAL_GATE`
- Frozen gate: `S𓂸ḥ/2`

The implementation reuses the already merged `cosmos_proof_adapter.py` request/receipt protocol. It does not invent a second Cosmos protocol.

## New heads

```text
PROOF_BROKER / DemiHead
  emits   COSMOS_PROOF_REQUEST
  accepts COSMOS_PROOF_RECEIPT

COSMOS / Janus-Cosmos
  accepts COSMOS_PROOF_REQUEST
  emits   COSMOS_PROOF_RECEIPT
```

## New routes

Only these routes are new:

```text
PROOF_BROKER -> COSMOS       : COSMOS_PROOF_REQUEST
COSMOS       -> PROOF_BROKER : COSMOS_PROOF_RECEIPT
```

No other route is implied by type compatibility.

## Semantic binding

A request route is valid only when the existing Cosmos adapter verifies the request and the Nexus payload reference equals the request's bound `request_sha256`.

A return route is valid only when the existing adapter verifies the exact request + exact Cosmos execution result + exact receipt, the receipt keeps the same GoldPrompt `intent_id`, the provider SHA is exact, and authority/effect deltas remain zero.

## Permanent boundaries

```text
TYPE_COMPATIBILITY != ADMITTED_ROUTE
ROUTE_RECEIPT != DELIVERY
ROUTE_RECEIPT != PROVIDER_EXECUTION
ROUTE_RECEIPT != TRUTH
ROUTE_RECEIPT != AUTHORITY
PROOF_OF_TASK_B != PROOF_OF_TASK_A
PROVIDER_PASS != WORLD_TRUTH
P_VS_NP = OPEN
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

The v2 route layer is local typed coordination. It is not a network delivery claim and does not grant Janus-Cosmos command, truth, permission, or external-effect authority.

## Promotion gate

Promotion requires:

1. frozen contract preserved;
2. Nexus v1 byte-unchanged;
3. v2 adversarial tests PASS;
4. existing Cosmos adapter tests PASS;
5. full existing DemiHead repository CI remains green;
6. exact provider checkout and real `S𓂸ḥ/2` execution PASS;
7. request and receipt route replay PASS;
8. no P-vs-NP or authority promotion.

A failed run remains a failed run and is not rewritten by later changes.
