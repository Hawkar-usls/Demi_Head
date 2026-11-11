# JANUS Tachyon v0.2 — measured numerical generalization

**Status:** local experimental candidate. No new physics or physical signal in the past.

## Why this exists

Tachyon v0.1 trained on 34 narrative/video summary segments, reached 94.86% training accuracy and **50%** on an 11-segment disjoint chronological holdout. The order of topics in a single video is not a general physical law, so we do **not** claim to have repaired that semantic/video task.

The new `tachyon.causal` lane learns physically defined, numerical subproblems derived from the hash-pinned video JSON:

- Input `q=c Δt/Δx` and observer speed `β=v/c`, with positive time and spatial separation.
- Output #1: whether an inertial observer assigns the events reversed coordinate time order (`β > q`).
- Output #2: whether their separation is spacelike (`q < 1`).
- All training labels follow the **ordinary Lorentz transformation**, not machine-generated future signals.
- For a physical future-directed timelike or lightlike signal, ordinary relativity does not allow coordinate order reversal under subluminal boosts.
- The analytic equations are an exact **100% ceiling** on these synthetic tasks. The Transformer is an approximation, not an improvement over the analytic calculation.

## Reproduction

```bash
python -m pip install -r requirements-tachyon.txt
python -m unittest discover -s tests -p 'test_tachyon*.py' -v
python -m tachyon.causal --epochs 20 --train-n 7000 --outdir artifacts/tachyon-causal
```

Input JSON at `data/tachyon/source_video_relativity_20261111.json` must match SHA-256 `44c1030da28ecea4ca1fc6891dea34a63445f9a981e2387b1e4bf4d189f43409`. The code fails closed on a mismatch.

Training is CPU-only, deterministic-seeded, has no external communication, and imposes resource caps. The model selects a best epoch using a **tuning set**; frozen independently sampled test sets are not used for training or early stopping.

Four test distributions, specified ahead of evaluation:

1. `iid`: entirely new continuously sampled input values.
2. `new_beta_band`: speeds `0.85..0.98c`, while training was restricted to `0.03..0.85c`.
3. `order_boundary`: close to `β=q`; more challenging.
4. `lightcone_boundary`: close to `q=1`.

## First local result (2026-11-11; seed 20261111)

- Best epoch on tuning data: **7/20**. Parameters: **8,802**.
- Coordinate-order reversal accuracy on IID (2500 samples): **98.52%**; majority-class baseline 65.92%.
- Coordinate-order reversal accuracy on unseen-speed band (2000 samples): **97.50%**; majority-class baseline 53.85%.
- Coordinate-order reversal accuracy near order boundary (1500 samples): **93.40%**.
- Spacelike interval accuracy near light cone (1500 samples): **98.40%**.
- Six published source sweep cases: **6/6** matched labels, including one `β=0.9` beyond training domain.

The `RESEARCH_NUMERIC_GATE_PASS_NO_EXTERNAL_VALIDATION` gate reports accuracy of reproducing an exact mathematical rule in **synthetic** cases; it is NOT evidence of useful natural-language generalization, causal anomalies, real-world signal propagation, or time travel. Deployment and auto-promotion remain off. Keep v0.1 as a negative-control historical result. Do not compare a synthetic numerical task's 98% with the prior narrative task's 50% as if they were the same metric.

**Next:** a separately frozen natural-language paraphrase/hypothesis reasoning benchmark and real publicly dated physical measurements, with causal baselines, error bars and provenance. Do not retrain on test failures.
