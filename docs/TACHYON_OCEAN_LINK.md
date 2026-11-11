# JANUS Tachyon × JANUS Ocean: time-order research bridge

**Experimental research only, no model promotion.**  This integrates the
Demi_Head Tachyon research head with the existing Janus-Demiurge JANUS Ocean
`OPEN-FUTURE-009B` 128-round drand cohort protocol.  It does not rewrite the
pre-registered November 12–19, 2026 cohorts or the frozen Ocean model.

## Why connect

Ocean supplies frozen model forecasts and later independently signed randomness
receipts; Tachyon checks the chronology, model lineage and causal interpretation.
TOPA v1.3 assesses the resulting falsifiable research question as **HYPOTHESIS_ONLY**.
The Beetle remains a separate unverified discovery stream (via the existing
`tachyon.research_bridge`), never gradients or independent evidence.

```text
Ocean early precommit (128 rounds, GitHub artifact timestamp)
      |
      v
Tachyon read-only gate: immutable hash / correct round list / before-release
      |
      +--> TOPA v1.3: HYPOTHESIS_ONLY, no auto-promotion
      |
      v
Ocean late score (ONLY after all 128 round releases)
      |
      v
Tachyon checks score / optional signed source data / uncertainty
      |
      v
Research questions + bounded feedback artifact for Ocean (not gradient input)
```

The interface validates the **existing** Ocean 009B `early_009b_128_bit_model_forecast.json`
against `janus.ocean.open_future_009b.v1`, its canonical SHA-256 and its
previously frozen model metadata. Optional late input is the unmodified
`009b_128_verified_bit_score.json` plus the provider's
`signed_128_future_rounds.json`. Its cryptographic BLS pairing is
**not independently verified** by the Tachyon Python adapter; signed source
content and binomial/Brier arithmetic can be replayed, while the native Ocean
workflow is responsible for checking BLS signatures with pinned drand-client.

**No cross-contamination:** Tachyon v0.3 text classifier is on HOLD (33.33%
heldout on small curated tasks), and v0.2 numerical Lorentz classifier does not
apply to drand round identifiers. Neither receives future labels in the early
forecast. The new sidecar only audits and proposes tests; it neither changes
Ocean weights nor selects a favorable cohort. The early and late stages run
without arbitrary outcome filtering or re-use of synthetic validation data.

## Local checks

```bash
python -m unittest discover -s tests -p 'test_tachyon_ocean_link.py' -v
python -m tachyon.ocean_link \
  --precommit /path/to/early_009b_128_bit_model_forecast.json \
  --ocean-commit <exact-40-hex-commit> \
  --github-created-at '2026-11-11T09:00:00Z' \
  --topa-router /pinned/topa_epistemic_router.py \
  --output /tmp/tachyon-ocean-audit.json
```

The GitHub timestamp must be extracted from the matching **Ocean Actions
artifact metadata**, not copied from a model-produced field. The bridge records
that a timestamp was supplied but cannot itself establish its provenance. The
Ocean-side manually dispatched workflow is responsible for that independent
lookup. There is no scheduled runner cost by default.

## Admission and scientific meaning

- EARLY_PRECOMMIT: only target metadata and the frozen probabilities; never
  fetch future outcomes at this stage.
- PENDING_FUTURE_OUTCOMES: valid result before late evidence exists, not a failure.
- UPSTREAM_REPORT_ONLY_NO_INDEPENDENT_RECALC: late report available but no
  signed-round bytes; remain explicit about this limitation.
- SIGNATURE_DIGESTS_AND_SCORE_RECOMPUTED: all 128 rows present, SHA-256 of
  signature and reported score replay; BLS verification still delegated to Ocean.
- Every report carries `physical_retrocausality_established=false`,
  `automatic_deployment=false`, `authority_delta=0`.
- No change to JANUS Ocean early/late forecast workflows, production model or
  existing Beetle/TOPA receivers; a separate manual audit is the integration.
- Actual effect can only be claimed after a prospective independent physical
  experiment, not after fitting a public random sequence or replaying a paper.
