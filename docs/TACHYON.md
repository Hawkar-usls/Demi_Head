# Tachyon — JANUS DemiHead bounded chronology transformer

Tachyon is a **tiny trainable PyTorch Transformer Encoder** in the DemiHead
reference system. It learns **relative order of semantic video segments** as a
pair-classification problem. It does **not** predict future events, discover
faster-than-light communications, or provide evidence for retrocausality.

## Source

- `data/tachyon/source_video_relativity_20261111.json`
- canonical record: `JANUS-TIME-HOMODEUS-PwOk0GKDv9c-20261111`
- SHA-256: `44c1030da28ecea4ca1fc6891dea34a63445f9a981e2387b1e4bf4d189f43409`
- 37 narrative semantic paraphrases, **not the raw original subtitles**;
  advertisements excluded; one video is **one provenance root**.
- Timestamps exist only to construct targets and ensure chronological partition;
  timestamps themselves are not model features.

## Model and testing

1. Chronologically split segments, training on the early part and holding out
   the entire late part. Never split random pairs of the same segments.
2. Learn training-only vocabulary, build balanced `(A,B)->1` and `(B,A)->0`
   pair labels. No time metadata in text features.
3. Train one layer, two attention heads, 32-dimensional embeddings, sigmoid
   binary cross entropy / AdamW on CPU. Fixed seed and resource limits.
4. Compare unseen-segment accuracy, Brier score and log loss to constant 50%
   baseline. If accuracy <55% or Brier >=0.25: `HOLD_NO_HOLDOUT_GAIN`.
5. Save `candidate.pt` and `receipt.json` as experimental artifacts. Even a
   passing gate is **not** independent physical validation or permission to
   deploy. DemiHead authority and mass-effect budget remain zero.

## Run locally

```bash
python -m pip install -r requirements-tachyon.txt --index-url https://download.pytorch.org/whl/cpu
python -m unittest discover -s tests -p 'test_tachyon.py' -v
python -m tachyon.train --epochs 8 --outdir artifacts/tachyon
```

GitHub Actions workflow `JANUS Tachyon bounded research training` is
**workflow_dispatch only**, one CPU runner, 20-minute timeout, no periodic
scheduling and no write token. Artifacts expire in 14 days.

## Admission boundary

`SOURCE_SHA_MATCH != SCIENTIFIC_TRUTH`.
`NARRATIVE_ORDER_MODEL != TEMPORAL_PHYSICS_MODEL`.
`MODEL_OUTPUT != EVIDENCE`.
`TRAINING_SUCCESS != RETROCAUSAL_SIGNAL`.

Next research step: independent, preregistered physical measurements with
monotonic clocks, control for latency, drift, selection bias, and causal
baselines. Maintain immutable source hashes and negative results.
