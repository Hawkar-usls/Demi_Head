# JANUS Tachyon — Beetle × TOPA × time-metrology bridge (v0.3 experimental)

## Real upstream contracts (not renamed copies)

- Producer: `Hawkar-usls/Janus-Demiurge`, branch `beetle-memory`, `data/beetle-runtime/CONTEXT.json`, schema `janus.beetle.runtime_context.v1`. This is a **triaged, source-unverified research projection**, *not* the sender's raw private inbox and not verified evidence. It remains addressed to `Janus-Demiurge`.
- Validator: `Hawkar-usls/TOPA` `integrations/janus-distributed-ai-swarm/topa_epistemic_router.py` at pinned commit `98a92e8abb4f05c41aae2921f0d956a210a74429` (v1.3 strict science).
- Consumer: `Hawkar-usls/Demi_Head` `tachyon/research_bridge.py`, read-only.

The manual workflow `.github/workflows/tachyon-lab-research.yml` checks out only the existing context projection, checks its canonical SHA-256, bounds/routes and original capabilities, then constructs **HYPOTHESIS_ONLY** TOPA envelopes. It invokes the *actual* pinned TOPA Python validator without altering it. A provider-free local invocation reports `NOT_CHECKED` rather than pretending TOPA accepted the claim.

`TRIAGED_TO_RESEARCH_CONTEXT_NOT_VERIFIED != SOURCE_FACT`. Beetle `score` is not a confidence for truth. `hypothesis_routes` are untrusted text: never treated as instructions, gradients, training labels, external effect authority, independent witnesses, or automatic source URLs to fetch. No echo of private receiver data.

## Published-clock benchmark

`python -m tachyon.clock_benchmark --out /tmp/clock.json`

- NIST 2010 / Chou et al: direction of redshift across 33 cm; **no numeric observation/error bars in our frozen summary**, thus *not scored*.
- University of Tokyo / RIKEN 2020 / Takamoto et al: optical clocks separated by 452.596 m. Published measured relative frequency difference `(49337.8 ± 4.3) × 10^-18`; geodesy-based prediction `(49337.1 ± 1.4) × 10^-18`. Combined residual z = **0.15479**. Local recomputation `g·Δh/c²` = **49337.076 × 10^-18**. This is a **published aggregate check**, not re-analysis of instrument time series.
- JILA/NIST 2022 / Bothwell et al: ~1 mm redshift at ~10^-19; **not quantitatively scored** without exact measured point and uncertainty.

Full titles/DOIs and source dates in `data/tachyon/experiments/published_clock_studies_v1.json`. All are out-of-training literature. Only one paper has a precise numeric measurement in this package; different institutions do not make two retellings into independent raw-data replication. The exact GR formula is more accurate than learned approximations on this task; **no neural advantage is claimed**.

## Explanation-learning v0.3 — measured negative gate

`python -m tachyon.explanations --epochs 25 --outdir artifacts/tachyon-explanations`

The candidate is a tiny Torch Transformer (23,046 parameters) classifying **six supplied mechanism families**, not writing free-form scientific explanations. The 60 human-curated synthetic questions split per family into 36 train, 12 tuning, 12 untouched template-holdout samples, with OOV on heldout phrases. Local seed 20261111: **94.44% training, 33.33% tuning, 33.33% heldout**, vs a 16.67% majority-class baseline. This is above trivial chance but **below the predeclared 65% candidate gate**. It remains **HOLD_NO_TEXT_GENERALIZATION_GAIN** and may not be promoted or treated as competent explanation generation. A future reworked model needs a *new truly independently frozen* out-of-distribution benchmark; do not optimize to this inspected holdout.

Model head evaluation and clock experiments are kept separate. The clock benchmark does not claim to evaluate the text model or Tachyon v0.2's coordinate-order classifier.

## Reproduction and admission

Local contracts without Torch:

```bash
python -m unittest discover -s tests -p 'test_tachyon_research_bridge.py' -v
python -m unittest discover -s tests -p 'test_tachyon_explanations.py' -v
python -m tachyon.clock_benchmark --out artifacts/tachyon-lab/clocks.json
```

Manual GitHub Action optionally installs Torch on a CPU runner; it has `contents: read`, no cron, no deployment token, no workflow dispatch from fetched text, no automatic mutation of Beetle, TOPA or Meta Registry, and no model promotion. Provider pinned, Beetle projection commit recorded. Failed input or failed test blocks it.

## Limits

`CLOCK_LAB_PUBLISHED_AGGREGATE != RAW_TIMESERIES`;
`NARRATIVE_SUMMARY != FULL_TRANSCRIPT`;
`TEXT_CLASSIFIER != SCIENTIFIC_UNDERSTANDING`;
`TACHYON_OUTPUT != EVIDENCE`;
`TOPA_COMPATIBLE_ENVELOPE != PROVIDER_PASS_UNTIL_REAL_ROUTER_RUNS`;
`BEETLE_CONTEXT != GRADIENT_SIGNAL`;
`RETROCAUSALITY_NOT_SHOWN`;
`AUTHORITY_DELTA=0`.
