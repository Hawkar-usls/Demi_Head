# TACHYON R3.8 — richer physics-inspired battery relaxation, 8-device public validation

**Status: public-retrospective source study, NOT independent blind science, NO neural training.**

## Source and prior exposure

Reuse the SAME eight independently manufactured battery specimens and 16 CC BY 4.0 CSV source files already verified in R3.7: [24-hour OCV battery relaxation dataset](https://github.com/BulyK47/battery-datasets), DOI 10.21227/651q-8v82, Voicila, Enache, Vilciu, Seritan, POLITEHNICA Bucharest. Dataset and conditions: measured 24-hour open-circuit voltage traces after charge/discharge; 60s cadence, ~23±2 °C. File authenticity: exact source Git blob hashes from prior manifest checked on download and raw SHA256 of all 16 originals recorded in receipt. No raw measured observations are uploaded into our repository or evidence artifacts.

R3.7 examined two public heldout devices and saw the best double-exponential baseline beat challengers. R3.8 studies all eight distinct **devices**, including those previously examined. They are independent devices in the experimental source, but **NOT eight new sources or secret independent blind trials**. We explicitly report the retrospective reuse, and make no claimed generalization to previously unknown chemistry/devices.

## Models with the same early-information budget

All six models only fit coefficients from time 0–4 hours of EACH individual trace, then predict the measured 4–24 hour voltage. Model selection never sees the heldout device within each cross-validation fold.

| Model | Engineering role | Mathematical form |
| --- | --- | --- |
| Persistence | Baseline | `V(t)=V(4h)` |
| Single exponential (1RC) | Strong baseline | `V∞+a exp(-t/τ)` |
| Double exponential (2RC) | Strong baseline, R3.7 champion | `V∞+a exp(-t/τ1)+b exp(-t/τ2)` |
| Triple exponential (3RC) | Stronger RC-inspired challenger | `V∞+Σ aᵢ exp(-t/τᵢ)`, 3 positive ordered timescales |
| Stretched exponential | Empirical fractional-like challenger | `V∞+a exp(-(t/τ)^β)` with fixed bounded β |
| Diffusion-like tail | Empirical slow diffusion surrogate | `V∞+a /√(1+t/τ)` |

The triple-exponential approach extends established multi-time-constant RC equivalent-circuit relaxation: [Fast characterization of battery relaxation](https://www.mdpi.com/2313-0105/2/2/7) and [double-exponential isolation of relaxation times](https://pmc.ncbi.nlm.nih.gov/articles/PMC10182328/). Diffusion and fractional-time responses are physically motivated but our **simple tail and stretch expressions are empirical approximations**, NOT exact solutions of Fick's electrochemical diffusion PDE or newly discovered physical laws. Relevant context: [exact rest-period electrochemical solution](https://pmc.ncbi.nlm.nih.gov/articles/PMC12639891/) and [fractional-order system identification](https://doi.org/10.1016/j.arcontrol.2025.101017).

Candidate parameter grids, time constants, loss penalties and model families are fixed in code and preregistered before looking at R3.8 results. Unlike free-form 'AI formula generation', this is a bounded symbolic **family comparison**. We do not run unconstrained expression code, auto-retry until a win or self-label from generated model predictions.

## Eight leave-one-battery-out public folds

For each heldout battery B in {APR,BSE,SG,LG,OEM,LI,AR,AU}: choose strongest incumbent and strongest challenger based on **battery-averaged per-trace MAE over the other 7 devices**. Authorize challenger for that fold only if ≥5% lower validation MAE; otherwise select incumbent. Independently compute the heldout group's forecast MAE, recording both selected and baseline. A positive outer fold is challenger selected AND >5% lower test MAE. A descriptive `≥6/8` group-consistency gate is preregistered, but **it never by itself authorizes production, a new scientific discovery or neural retraining**.

Since all eight public devices are reused across different LOBO folds, these are **correlated cross-validation folds**, not eight statistically independent replication studies. No invented p-values or unwarranted confidence intervals. All per-device results, bad forecasts, selected family, original source SHA and failed model fit reasons must be preserved. Overall performance from this public dataset is susceptible to prior R3.7 design choices and should be treated as hypothesis-generating only.

## Genuine external custodian is a separate, not-yet-filled slot

The file `data/tachyon/r38/external_custodian_control_not_provided.json` explicitly records `NOT_PROVIDED_BY_INDEPENDENT_LAB`, null signed custodian identity, null independent original dataset DOI, null sealed gold-source commitments, null external timestamps and no laboratory prediction capture. The code rejects changing those fields to self-assert 'independent' or 'passed' status. The eight published battery groups are specifically ineligible as secret future samples.

The next independent custodian should choose *new* physical devices or a newly generated experimental cohort independently, pre-register measurement conditions and full model/baseline code SHA, hold its original voltage-time key privately, give the candidate only 0–4h measurements, capture predictions before opening 4–24h values, then compare with unit-matched strong baselines and device-level uncertainty estimates. Independent source/rights audit and signed timestamp separate from GitHub/AI author are prerequisites.

## Data governance and scientific gate

All source files are publicly licensed CC BY 4.0 with correct author attribution; R3.8 fetches for research scoring, not model training. It trains **zero neural weights**, does not modify R3.5 weights, JANUS Ocean, production chat gateway or NAS. No generated predictions are used as new ground-truth observations. Only reviewed, rights-cleared and scientifically independent data + significant reliable gain against strong physically appropriate baselines can open a *separate* bounded neural-training request.

**Status `R38_PUBLIC_EIGHT_DEVICE_CROSSVAL / PHYSICS_INSPIRED_BASELINES / EXTERNAL_CUSTODIAN_NOT_CONNECTED / NEURAL_TRAINING_DISABLED / SCIENTIFIC_HOLD`.**
