# TACHYON R3.7 — genuine measured battery open-circuit voltage relaxation

**Scientific state: RESEARCH_ONLY / REAL_MEASUREMENTS_ORIGINAL / EXTERNAL_BLIND_NOT_DONE / NO_NEURAL_TRAINING / SCIENTIFIC_HOLD**

## Original source, rights and attribution

Dataset: [24-hour Raw OCV Relaxation Dataset for Rechargeable Batteries with Different Chemistries](https://github.com/BulyK47/battery-datasets), DOI [10.21227/651q-8v82](https://doi.org/10.21227/651q-8v82), research team Iulian-Teodor VOICILA, Bogdan-Adrian ENACHE, Irina VILCIU and George-Calin SERITAN at the National University of Science and Technology POLITEHNICA Bucharest. Accompanying journal article: [Enhanced OCV Estimation in LiFePO4 Batteries, 2025](https://www.mdpi.com/2313-0105/11/5/186). The repository publishes the 16 CSV time series under **CC BY 4.0** (attribution required); dataset contains 8 batteries, chemistry-dependent OCV, 30 separate voltage traces covering charge/discharge states over 24 hours at 60 s cadence. This is external *measured* material, not author-generated equation labels.

Source file names, sizes and public GitHub blob SHA-1 commitments are captured from the original repository's file API at preregistration and saved in `data/tachyon/r37/real_ocv_group_holdout_manifest.json`. The runtime rejects changes in the source even if the branch `main` moves: compute SHA-1 of `blob <length>\0<bytes>`, compare it to the pinned source blob digest, and record SHA-256 of every downloaded CSV. Fixed `https://raw.githubusercontent.com` host, bounded <=120000 bytes per CSV, no redirects, no user authentication, no replay to arbitrary URLs, no raw measurements committed to JANUS or uploaded to Actions artifact.

## Explicit *prospective within-job* held-out structure

Battery group partitions are pinned **before** the GitHub run:

| Role | Battery groups | Used for |
| --- | --- | --- |
| Train / developer checks | APR, BSE, SG, LG | fixed algorithm and test sanity, not learned neural weights |
| Validation | OEM, LI | choose model family and threshold |
| Test | AR, AU | strictly untouched until validation-only choice is written to a SHA-sealed file |

For each voltage trace, the prediction method may fit model coefficients to time `0–4 hours` of that trace. It must then forecast observed voltage during `(4,24] hours` without seeing those later values while fitting. This is a **per-device early-window calibration**, which is allowed for every test device; it should not be confused with source-family-generalization without calibration. The fitted early parameters are conditioned on that battery's early measurement; only the structure is selected globally on different validation batteries.

The pretest selection JSON is **written to disk before downloading the TEST battery group files**. This gives a narrow within-workflow ordering control; an independently trusted external custodian is still absent. The source data are public and these exact battery group identities are visible to authors, so **do not describe this as an independently blinded evaluation**.

## Baseline models and challengers

Strong standard comparators:

1. **Persistence**: forecast voltage at the last observed time `t=4 h` for the next 20 hours.
2. **Single exponential relaxation**: `V(t)=c+a exp(-t/τ)`; choose τ on the first four hours from a fixed grid, fit coefficients by regularized least squares.
3. **Double exponential / two-RC relaxation**: `V(t)=c+a exp(-t/τ1)+b exp(-t/τ2)`; fit grid-restricted τ1 < τ2 using early data only. This is a physically motivated strong benchmark, not an intentionally weak constant baseline.

Additional symbolic candidate families:

4. **Logarithmic relaxation**: `V(t)=c+a log(1+t/τ)`.
5. **Exponential with drift**: `V(t)=c+a exp(-t/τ)+b t/24`.

The code fits the five defined families with a small bounded grid, no open-ended symbolic expression search and no arbitrary code evaluation. Model structure is chosen by **unweighted per-trace voltage MAE on VALIDATION battery groups**, and a challenger is selected only when it beats the strongest baseline by at least 5% in validation. On TEST groups it must beat the same strongest baseline overall by >5% **and** on both held-out test batteries to earn a research-only `positive_new_symbolic_forecast_gain_both_batteries=true`. Inability to beat the best baseline, file failures, missing cells or weird measurement ranges must be preserved as negative or incomplete outcomes.

MAE and RMSE in volts are reported per model and per battery (not mixed SI dimensions). A 2-battery heldout set is too small for a general statistical claim; no p-value or confidence interval may be invented. Test traces may be temporally autocorrelated, so treating all 1200 points as independent replications would be false.

## Training boundaries

Fitting two/three parameters on a trace's early original real measurements is **research-only statistical calibration**; it is NOT permission to train the R3.5 neural model or to automatically admit empirical physics formulas to the production JANUS scientific knowledge registry. R3.7 does **not** train any neural network or modify existing R3.5/R3.6 checkpoints. `neural_training_authorized=false`, `scientific_admission=HOLD`, `production_model_promoted=false` are hard-gated.

Any future bounded neural learning needs independent source quality and rights audit, explicit train/validation/source-family/test separation, a novel source-family evaluation, a real third-party custodian whose key is outside public Actions, and benchmark improvement versus physically motivated baselines. No training from a model's own predictions as if they were measured gold.

## Physical interpretation and limitations

OCV relaxation reflects redistribution of charge, diffusion, electrochemical hysteresis and slow processes, and the simple scalar forecast families are *empirical approximations*, not fundamental laws. Individual cells undergo different conditioning, SOC and chemistry. There is no measured current during the 24h open-circuit relaxation because the source/load is disconnected, so do not apply the R3.6 synthetic `V=IR(1+αΔT)` law as if it described these battery observations. R3.6's 99.1% result was wholly synthetic; **R3.7 is the first separate external real-data audit**, not an implicit transfer of that result.

The source repo is a public mirror; full scientific provenance of each sensor/calibration, right to adapt per CC BY and correct attribution are separate from cryptographic file integrity. This read-only code is scoped to research and cannot autonomously claim a new physical law or approved new neural weights.
