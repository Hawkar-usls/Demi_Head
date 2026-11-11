# JANUS TACHYON R3.9 — Independent new-device, blinded OCV relaxation handoff

**Protocol prepared, third-party custodian NOT connected. No real blind evaluation, neural retraining, or production promotion.**

## Goal and frozen baseline

R3.8's retrospectively selected diffusion-like tail won a public 8-device cross-validation against a 2RC double-exponential on 6/8 batteries, but produced 51.76% worse MAE on LI and 8.62% worse on AR. These are disqualifying reliability concerns. The prior dataset and all 8 device groups were seen by JANUS and are **ineligible as secret R3.9 evidence**.

R3.9 preregisters a **fixed candidate `diffusion_tail` and incumbent `double_exp`**. The actual inherited source files `tachyon/r38_battery_physical_crossval.py` and `tachyon/r37_real_ocv_evaluator.py` are pinned by exact Git blob SHA; the executor refuses changed bytes. These are empirical forecast structures, not universal electrochemistry or confirmed new physical laws. NO hyperparameter retuning, new symbolic candidate selection or old data calibration is allowed on new hidden outputs.

## Real external custodian, not GitHub Actions

An actual independent laboratory/reviewer must use **at least 12 never-before-seen rechargeable single-cell devices** from **at least two separately sourced studies** (minimum three devices per study) and at least two chemistries. They must document calibrated sensor data, uncertainty, sampling, time zero after disconnection, temperature/SOC, chemistry, instruments, sampling quality and data rights. The prior DOI `10.21227/651q-8v82` and previous APR/BSE/SG/LG/OEM/LI/AR/AU IDs are explicitly excluded. Because a device ID or study ID can be fabricated, technical assertions here are no substitute for actual external witness checks.

Sampling contract: **one 1441-point voltage time series per device at one-minute intervals from hour 0 to hour 24**, hours from disconnection, volts, within declared rechargeable battery voltage envelope 2–5.2 V. The input may be heterogeneous across new devices, but missing timestamps, nonfinite voltages, wrong units, duplicated IDs, insufficient new sources or repeated old devices are rejected. This intentionally strict contract might require a separately documented amendment for an instrument with a different sampling interval; it must not be silently interpolated after viewing outcomes.

### Private pack schema (fabricated example, NOT a real laboratory record)

```json
{
  "schema": "janus.tachyon.r39.private_external_new_devices.v1",
  "cohort_id": "CUSTODIAN_NEW_COHORT_001",
  "devices": [
    {
      "device_uid": "EXTERNAL_DEVICE_001",
      "source_study_id": "UNSEEN_STUDY_001",
      "chemistry": "LFP",
      "trace": [[0.0, 3.40], [0.0166666667, 3.399]]
    }
  ]
}
```

The example shows only the schema. A real pack must contain 12–40 devices with exactly **1441 voltage-time pairs each**, not the truncated two pairs shown above. Keep raw private pack, 256-bit random salt and future label measurements under **custodian-controlled encrypted storage**; NEVER commit, upload to public GitHub Actions or forward them to JANUS/Ocean. Early input 0–4h itself may be unpublished experimental data, so the question-only file must also remain private.

## External offline three-phase protocol

Independently generate a cryptographically random **256-bit salt** on the custodian's private machine and save its 64-hex-digit representation to `/private/custodian_salt.hex`; do not pass a literal salt via CLI arguments or print it in Actions logs.

**1. Freeze and seal by custodian, before candidate sees early data:**

```bash
python -m tachyon.r39_external_battery_custodian \
  --config data/tachyon/r39/independent_external_device_manifest.json seal \
  --private-pack /private/new_cohort_full_24h.json \
  --salt-file /private/custodian_salt.hex \
  --sealed-output /private/salted_commitment.json \
  --questions-output /private/early_only_questions.json
```

This creates a salted SHA-256 commitment to the entire private full-day pack, a public-safe commitment receipt carrying the frozen model/blob hashes and no raw answers, and a private *questions-only* bundle containing each pseudonymous device ID, 241 early t,V pairs and the 1200 future time indices **but no future voltage values**. Actual trusted independent timestamps/signatures must be obtained separately; the software does not invent or verify an external researcher identity.

**2. Run the pinned formula executor on an isolated candidate computer, not a public Actions runner:**

```bash
python -m tachyon.r39_external_battery_custodian \
  --config data/tachyon/r39/independent_external_device_manifest.json infer \
  --questions-only /private/early_only_questions.json \
  --predictions-output /private/frozen_predictions.json
```

It checks original R3.8/R3.7 code Git blob SHA, question-only SHA and field allowlists, then independently fits two predeclared model structures to each device's **241 early points only**. It emits each model's **1200 predicted future voltage values** with a SHA commitment. It never receives private future gold, nor calls any network API, optimizer or neural training code. An external custodian must independently witness and timestamp this execution before opening outcomes; an output JSON with hashes is not proof of who performed it.

**3. Open future gold locally at the custodian and score without learning:**

```bash
python -m tachyon.r39_external_battery_custodian \
  --config data/tachyon/r39/independent_external_device_manifest.json score \
  --private-pack /private/new_cohort_full_24h.json \
  --salt-file /private/custodian_salt.hex \
  --sealed /private/salted_commitment.json \
  --questions-only /private/early_only_questions.json \
  --predictions /private/frozen_predictions.json \
  --summary-output /private/r39_aggregate_score_only.json
```

The scorer requires an exact matching original salted pack commitment, original question transport, candidate+incumbent SHA and complete predictions. It produces **aggregate only**, no raw traces, private battery/study names or secret answer keys. It computes battery-equal MAE (volts), fraction of devices beating the incumbent, worst-device relative MAE regression, per-study gain count, and a clearly exploratory device-level paired bootstrap interval. No treating thousands of minute points as independent experimental replicates.

## Engineering thresholds — not automatic scientific approval

Before receiving any new data, R3.9 specifies all four criteria: ≥10% relative device-equal mean MAE reduction, ≥80% of distinct devices with strictly better MAE, ≤10% worse MAE on worst device, and positive mean gain within every contributing source study. Any failing criterion records a negative result. Even if all pass, the receipt remains `scientific_admission=HOLD`, `production_promotion=false`, `neural_weights_trained=false`: separate original-source rights and scientific calibration review, trusted identity+signature+timestamp, external replication and appropriate statistical assessment are mandatory.

## CI and reproducibility

Pull-request GitHub Actions tests a fabricated **12-device / two-study / two-chemistry** cohort with artificial voltage curves and keeps all fake gold/salt in a throwaway temporary environment. The public test DOES NOT fetch or upload real third-party private data, and synthetic fixture success is not an independent experiment. CI uses `contents:read` only, no Actions secrets, no external sources. It asserts no data leakage, distinct source IDs, frozen source SHA, no mutation, no self-promoted results and correct rejection of bad/changed measurements. Only the public protocol and synthetic test summary are published.

**NEXT gate:** arrange a verifiably independent custodian, review rights/sensor calibration, freeze a newly collected cohort and secure a signed timestamp; run local-only actual question+gold evaluation under custodian. Not possible to complete that from the current public JANUS GitHub repositories alone.

Current status: `R39_OFFLINE_CUSTODIAN_PROTOCOL_READY / REAL_EXTERNAL_DEVICE_DATA_NOT_PROVIDED / INDEPENDENT_BLIND_NOT_RUN / SCIENTIFIC_HOLD`.
