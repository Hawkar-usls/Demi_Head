# TACHYON-R1: temporal evidence bus, not a second JANUS brain

This is a draft **read-only** time-evidence contract. JANUS-SPI remains the canonical event/forecast/resolution SQLite ledger. This package does not modify that ledger or train/deploy any model.

## Causal phase rules

| Kind | Mandatory ordering | Allowed result |
| --- | --- | --- |
| FEATURE | observed_at <= available_at <= feature_cutoff_at <= forecast_frozen_at < target_at | Pre-target feature candidate, never a resolved label |
| FORECAST | feature_cutoff_at <= forecast_frozen_at <= available_at < target_at | Frozen probability with observed_at=null, resolved_at=null and observed_label=null |
| RESOLUTION | feature_cutoff_at <= forecast_frozen_at < target_at <= observed_at <= available_at <= resolved_at | Linked outcome context, never an automatic training gradient |

All six UTC-Z fields are explicit. Unknown is null, never zero. An old physical observation published later is **not an admissible early feature**. available_at must mean evidence available to the model, rather than a timestamp asserted by a file's author.

The source is identified by repository, commit SHA, relative path, asserted source-byte SHA-256 and source_family_id. No source-byte download or trusted clock/witness verification occurs in R1; an asserted checksum alone does not authenticate the original experiment. The envelope has a canonical SHA256 for tamper detection only. For RESOLUTION the forecast_link_sha256 remains an *asserted pointer*: a separate gate must authenticate the referenced original frozen prediction before any scientific label admission.

- Executable contract: tachyon/temporal_evidence.py
- JSON Schema: contracts/TACHYON_TEMPORAL_EVIDENCE_V1.json
- Negative test suite: tests/test_temporal_evidence.py
- CI: .github/workflows/tachyon-r1-temporal-bus.yml

## Hard boundaries

STRUCTURAL_TIME_ORDER_PASS != VERIFIED_SOURCE_TRUTH
TIMESTAMP_ORDER != INDEPENDENT_WITNESS
HASH != EXTERNAL_SIGNATURE
RESOLUTION_CONTEXT != TRAINING_LABEL
MODEL_OUTPUT != PHYSICS
AUTOMATIC_DEPLOYMENT = FALSE

The workflow runs only on relevant PR changes or manual dispatch. It emits one synthetic test receipt, modifies no source data, and creates no recurring schedule. The existing Ocean 009B early/late protocol, TOPA/AIFC, Beetle queues, SQLite and model weights stay untouched.

The downstream JANUS-SPI sidecar consumes this contract in a separate draft branch and refuses duplicate source-family/target/kind entries and direct model training. Real clock and Ocean observational data require a later independently verified R2 adapter.
