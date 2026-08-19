# JANUS Nexus v2.3 — AIFC witness evidence

Status: **candidate under frozen contract**.

This additive layer inherits promoted Nexus v2.2 and adds one evidence-source route:

```text
AIFC_WITNESS -> FUNDAMENTUM : EVIDENCE_CANDIDATE
```

## Frozen AIFC baseline

- repository: `Hawkar-usls/AIFC`
- source SHA: `221a523a1befd1423a8fd3165018336f7853b577`
- evidence-grades blob: `0b8ff69112a4a037f09ff69bdc9511829a5cfd37`
- draft-spec blob: `399ceacc0e97045eda61a270290c556e7ef0ce3e`

AIFC v1 is a draft protocol and is not yet externally bench-frozen. The route preserves that status.

## Evidence package semantics

The adapter accepts only a terminal package summary with the complete declared mandatory-gate map. Missing, unknown or contradictory gates remain explicit.

Grades are validated against their own bounded semantics:

- `NOT_ADMITTED`: at least one mandatory gate is non-PASS.
- `STRUCTURAL_MATCH_ONLY`: no independent-future admission.
- `FORWARD_NULL_COMPATIBLE`: admitted, all mandatory gates PASS, frozen threshold not crossed.
- `FORWARD_NULL_INCOMPATIBILITY_CANDIDATE`: admitted, all mandatory gates PASS, threshold crossed.
- `EXTERNAL_REPLICATION_REQUIRED`: Grade-3 class plus internal adversarial audit, fewer than two independent replications.
- `REPLICATED_FORWARD_NULL_INCOMPATIBILITY`: at least two independent replications under the declared evidence assumptions.
- `PHYSICAL_MECHANISM_UNRESOLVED`: replicated anomaly class with mechanism still unresolved.

No grade can set `physical_retrocausality_claimed=true` or `mechanism_established=true` at this routing boundary.

## Permanent laws

```text
EVIDENCE_CANDIDATE != EVIDENCE_ADMISSION
EVIDENCE_GRADE != WORLD_TRUTH
GRADE_3 != RETROCAUSALITY_PROVED
GRADE_5 != PHYSICAL_MECHANISM_PROVED
ROUTE_RECEIPT != FUNDAMENTUM_VERDICT
SIGNATURE_OR_HASH != TRUTH_OF_CONTENT
MISSING_OR_CONTRADICTORY_GATE FAILS CLOSED
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

Fundamentum remains responsible for its own evaluation. Nexus only preserves and transports the bounded evidence candidate.
