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

## Robustness audit (three additional unselected training seeds)

Three further complete CPU runs used seeds `20261112`, `20261113`, `20261114`, the same frozen protocol and independent heldout sampling per seed; **no champion was picked**. All three passed the predeclared research numeric gate:

| Metric | Minimum | Mean | Maximum |
| --- | ---: | ---: | ---: |
| IID coordinate reversal | 99.36% | 99.57% | 99.76% |
| Unseen 0.85–0.98c reversal | 96.10% | 98.17% | 99.20% |
| Close order boundary | 99.73% | 99.84% | 100.00% |
| Close lightcone boundary | 85.87% | 95.22% | 100.00% |

These repetitions improve confidence in the numerical approximation across random initializations. They do not constitute external experimental validation or proof of any anomalous signal. See `data/tachyon/generalization_seed_robustness_20261111.json` for every score, including the weakest cases. The first seed's weights remain the reference candidate; there is no post-hoc selection of the strongest run.

## Reproducible pinned checkpoint in DemiHead

The reference seed 20261111 checkpoint is stored as compressed base64 text in
`data/tachyon/weights/tachyon_v02_seed_20261111.pt.gz.b64`, with explicit SHA-256
and scientific-admission restrictions in `tachyon_v02_manifest.json`. The
representation is for GitHub UTF-8-file compatibility only. It is decoded and
checked before being loaded with PyTorch's `weights_only=True`:

```python
import torch
from tachyon.load_causal import load_candidate
model = load_candidate()  # research only; offline
with torch.no_grad():
    # q = cΔt/Δx; beta = v/c
    result = torch.sigmoid(model(torch.tensor([[0.5, 0.8]], dtype=torch.float32)))
    print(result)  # [coordinate-order-reversal probability, spacelike probability]
```

Do **not** interpret a model probability as a measurement or an FTL transport
instruction. For real decisions, use the analytic Lorentz formula directly.

## Standard repository CI compatibility

The general DemiHead `Validate repository contracts` job does not install the
optional PyTorch dependency. In general CI, checksum and provenance tests in
`tests/test_tachyon_artifacts.py` run using standard library only, and Torch-only
test modules explicitly skip when the dependency is absent. The dedicated
manual Tachyon workflow installs the pinned PyTorch CPU package and runs all
16 Tachyon tests. This keeps the repository's general verification lightweight
without silently treating a Torch-free run as a model training pass.
