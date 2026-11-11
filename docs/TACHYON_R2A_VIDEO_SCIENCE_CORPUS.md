# TACHYON-R2A — audited time-physics video → explanation instruction corpus

## Goal
Connect existing `Hawkar-usls/janus-meta-registry` audited **nonverbatim** scientific claims about [Homo Deus, PwOk0GKDv9c](https://www.youtube.com/watch?v=PwOk0GKDv9c) to the specialized Tachyon scientific-explanation **training-data catalog**, without changing the existing `v0.3` classifier or admitting any model.

### Upstream provenance (immutable source)
- Repository: `Hawkar-usls/janus-meta-registry`
- Pinned source commit: `a7f77b02ba6f66efc3a0df5d275de7e57eb0e28d`
- Science JSON: `data/experiments/JANUS-VIDEO-PWOK0GKDv9c-SCIENCE-CHAPTERS-CLAIMS-2026-11-11.json`
- Captions metadata: `data/experiments/JANUS-VIDEO-PWOK0GKDv9c-RU-CAPTIONS-HASH-INDEX-2026-11-11.json`
- Transcript identity SHA-256: `6891a1e2a01f274bc0eb0ec79d06b37e49ff9137ad9f408596a54e2a4ca56328`.
- All 254 cue metadata entries and 25 author chapter summaries must be present. The known **180 s** subtitle/video timeline discrepancy remains UNVERIFIED and the adapter explicitly rejects attempts to mark alignment as verified.

`python -m tachyon.video_science_corpus` generates **12 paraphrase-and-qualification instruction/answer training examples**. Input is "Explain the physical claim and its reliability limitations"; target is the existing audited paraphrase plus its explicitly published scientific qualification. Classification labels remain source labels — they are **not** physical ground-truth labels or a new TOPA decision. No original caption text is reproduced or rehosted.

All examples have `split=TRAIN` and the same `source_family_id=HOMO-DEUS-PWOK0GKDv9c`. There is **one** underlying media source. Do NOT split its 12 claims and call the result independently held-out scientific generalization.

The existing `data/tachyon/explanation_cards_v1.json`, `tachyon/explanations.py`, old v0.3 model weights/metrics, and negative result (`HOLD_NO_TEXT_GENERALIZATION_GAIN`) are **unchanged**. Its six-class question classifier is not a generative instruction-following model and should not be silently relabeled/fine-tuned with the 12 different scientific-assessment categories. This PR prepares a **new candidate corpus format**, not completed neural training.

## Independent laboratory holdout
The output excludes all clock-benchmark and laboratory numeric observations. The future independent benchmark remains wholly separate:

- `data/tachyon/experiments/WISCONSIN_ZHENG_2023_Fig3.csv`, exact SHA-256 `a4384040d5678893b4df15ea0be2980661023305f5009de876179fab1dea632f`;
- `data/tachyon/experiments/published_clock_studies_v1.json`;
- `data/tachyon/experiments/clock_benchmark_receipt_v1.json`;
- `data/tachyon/experiments/wisconsin_2023_fig3_replay_receipt_v1.json`.

The raw CSV is read only to verify its original SHA-256 when requested; not a single measured frequency or run-level value is included in the training pairs or passed as a feature. The existing 2020 and 2023 **published** measurements were previously examined in the Tachyon research branch; they are not pristine never-seen evaluations for the human investigators. A properly blinded, independent *new dataset* and predeclared performance protocol are still needed to measure true generalization.

## Run in GitHub Actions
The additive `.github/workflows/tachyon-r2a-video-science-corpus.yml` performs a SHA-pinned sparse checkout of only the two Meta Registry JSON files, runs the adversarial contract tests without Torch, verifies protected lab CSV bytes, builds the instruction corpus, validates the training-only claim ceilings and uploads a short-lived research artifact. PR events and manual dispatch only; no schedule, secrets, model deployment or cross-repository writes.

No AIFC/TOPA verdict, future signal, new physical theorem or independent scientific replication is established by this document and the CI PASS.

## Next gate (separate future work)
Construct an instruction-answer model or RAG evaluation pipeline with external physics expert labels, contradiction/counterexample prompts, and **new** independently held-out physics sources. Freeze the benchmark before model tuning and compare against simple retrieval + analytical formula baselines. Existing Wisconsin/Tokyo clock data can still serve provenance and deterministic replay controls, but cannot alone prove comprehension or neural advantage.
