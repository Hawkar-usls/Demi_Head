# TACHYON-R2D — Frozen Answer Audit / Public Development Check

## Research objective

R2C generated scientific explanations but its previous equation sanity tests did **not** inspect the generated text. R2D evaluates the exact frozen R2B and R2C neural weights from earlier GitHub Actions runs on post-freeze questions, with retrieval and theoretical formula baselines. No retraining, no optimizer, no admission, no production access.

### Checkpoint freezes

- R2B checkpoint SHA-256: `3adbf7b11a0f4275ab565ea833c7d415fc0e6727ddddf48e5a27f04346350f9c` (run #43015290827).
- R2C checkpoint SHA-256: `4fde3d9c46dd7a11913de97348e97eb11d6b48cbed4a14cee17963c040b8aae8` (run #43020959937).
- R2C public source cards SHA-256: `21a27ab618d94e1d15d586c20432b8e766cb947b1035a045ef764c8337e`.
- CI downloads each archived checkpoint from its *original* run and refuses execution if SHA-256 differs.

## Transparent public diagnostic (NOT a blind test)

18 questions, authored after the R2C checkpoint: 8 small numeric theory tasks (special-relativity proper time, 2-level Born rule), 6 conceptual questions, and 4 out-of-domain prompts. The questions and expected answers are public in this PR: they are **not** independently prepared scientific evidence. No laboratory clock traces or hidden holdout answers are used.

Separate processes: `split-public` creates a questions-only file and a public scoring key. `predict` rejects question inputs carrying labels, operates only on frozen checkpoints, and preserves raw generated texts. `score` reads the key afterward. Public key co-location in the same CI workspace is acceptable for this explicitly public developer probe, but it is NOT a secure independent blind environment.

Arms: R2B neural text, R2C neural text, R2C source-grounded card retrieval, and a deterministic physics formula baseline. For numeric outputs, the metric only detects **whether a displayed number matches the target within tolerance**. It does not certify causal explanation or correct derivation. The formula baseline's expected success is tautological because the case family and formula are known. For conceptual questions, automated DOI-family matching is *not* an evaluation of scientific correctness. Out-of-domain questions probe abstention. Suspected unsupported causal claims are red flags requiring independent human inspection.

The output includes model-specific hit rates, conservative Wilson intervals (where applicable), raw answers, and exact SHA-linked model provenance. It never sets `scientifically_admitted=true`.

## Actual independent blinded path — NOT YET PERFORMED

1. An **external assessor** receives a frozen model/checkpoint hash and the public evaluator. The assessor holds private questions and answers **outside this repository and outside the model developer's CI job**.
2. The assessor must seal SHA-256 of the scoring key *before* opening any predictions. The script checks a supplied `--committed-key-sha256` but **cannot authenticate who sealed it or when**: that needs an independent, dated signed record.
3. Private question-only input schema `janus.tachyon.r2d.questions_only.v1`, `scope=PRIVATE_EXTERNAL`; at least 60 new cases: 20 numeric, 20 conceptual, 20 out-of-domain. Separate labelled scoring key schema `janus.tachyon.r2d.scoring_key.v1` is kept off GitHub and off the training runtime.
4. The assessor runs `predict` on exact frozen weights, and `score` in their independently controlled environment. The report may omit confidential answers; it includes case-ID hashes and only automatic diagnostics. Human correctness judgments, citation verification, clock lab/physics measurements and independent sign-off are still separately necessary.
5. Before any scientific admission: independent reviewer sign-off, full disclosure of numerical and conceptual failures, prospective preregistered acceptance threshold and comparison against baselines. Neither this script nor a self-signed receipt can confer admission.

## Reproducible local commands

```sh
python -m tachyon.r2d_audit split-public --fixture data/tachyon/r2d/public_dev_challenge.json --questions /tmp/q.json --key /tmp/public-key.json
python -m tachyon.r2d_audit predict --questions /tmp/q.json --cards data/tachyon/r2c/science_cards.json --r2b /path/to/original-r2b_candidate.pt --r2c /path/to/original-r2c_research_only.pt --out /tmp/pred.json
KEY_SHA=$(sha256sum /tmp/public-key.json | cut -d' ' -f1)
python -m tachyon.r2d_audit score --predictions /tmp/pred.json --key /tmp/public-key.json --committed-key-sha256 "$KEY_SHA" --out /tmp/score.json
```

Potential security limitation: frozen PyTorch checkpoint loading uses `weights_only=True` and digest checks, but this is not a full sandbox; only trusted pinned source/checkpoint artifacts should be loaded.

Current gate: `TACHYON_R2D / PUBLIC_DEVELOPMENT_ONLY / EXTERNAL_BLIND_PENDING / SCIENTIFIC_HOLD`. All PRs remain drafts and no running JANUS Ocean weights or main branches are changed.
