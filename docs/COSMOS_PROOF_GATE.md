# JANUS Cosmos Proof Gate

DemiHead integrates `Hawkar-usls/Janus-Cosmos` as a **specialized proof provider**, not as a third hemisphere, truth authority, or external-effect authority.

```text
GoldPrompt intent anchor
        ↓
LEFT_HRAIN + RIGHT_INAIHR
        ↓
DemiHead arbitration
        ↓
intent-bound Cosmos request
        ↓
Janus-Cosmos / OSIRIS / S𓂸ḥ
        ↓
execution result + integrity digest
        ↓
DemiHead Cosmos proof receipt
        ↓
Epistemic Execution Gate / Fundamentum Truth Guard
```

## Exact provider pin

- repository: `Hawkar-usls/Janus-Cosmos`
- revision: `c77f920d764229efb6932bc4ea522a4ec0342c64`
- current canonical gate: `S𓂸ḥ/2`
- current supported integration operation: `VERIFY_CANONICAL_GATE`

The first vertical slice intentionally verifies the exact frozen canonical gate. It does **not** pretend that DemiHead already exposes a general arbitrary-CNF remote solver API.

## Intent continuity

The request carries the same valid `janus.goldprompt.intent_anchor.v1` used by the HRaiN/iNaiHR chain and adds a handoff for `COSMOS_PROOF_PROVIDER`.

```text
PROOF_OF_TASK_B != PROOF_OF_TASK_A
SAME_INTENT_REQUIRED_ACROSS_DEMIHEAD_AND_COSMOS
```

Changing the intent anchor, provider revision, input payload or input digest invalidates the request.

## Proof receipt boundary

A valid receipt binds:

- GoldPrompt `intent_id`;
- exact request digest;
- exact provider repository and commit;
- exact input digest;
- exact Cosmos execution-result integrity digest;
- the bounded Cosmos status;
- `P_VS_NP = OPEN`;
- zero authority and mass-effect deltas.

The receipt means only that the exact bound computation was executed and replay-verified within its declared scope.

```text
COSMOS_PASS != WORLD_TRUTH
COSMOS_PASS != P_EQUALS_NP
COSMOS_PASS != P_NOT_EQUALS_NP
COSMOS_PASS != AUTHORITY
MODEL_OUTPUT != EXECUTION_RECEIPT
```

## Current mathematical ceiling

`Janus-Cosmos` currently reports `S𓂸ḥ/2` as a passing finite bounded-K separator/holdout gate. That does not establish an arbitrary-CNF polynomial algorithm or either resolution of P versus NP.

```text
P_EQUALS_NP = NOT_ESTABLISHED
P_NOT_EQUALS_NP = NOT_ESTABLISHED
P_VS_NP = OPEN
```

## Failure behavior

The bridge fails closed on at least:

- intent substitution;
- provider-SHA substitution;
- input-hash substitution;
- execution-result integrity failure;
- attempted P-vs-NP claim promotion;
- attempted authority increase.

Future expansion to direct CNF proof requests must add a separately frozen request contract and must preserve the same receipt, budget and claim-ceiling discipline.
