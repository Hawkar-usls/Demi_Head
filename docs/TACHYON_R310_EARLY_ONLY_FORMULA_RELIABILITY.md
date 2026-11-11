# JANUS TACHYON R3.10 — recognize when an empirical formula is unreliable

**Status: public retrospective, R3.9 independently frozen, no scientific admission, no automatic training.**

## Why

R3.8's diffusion-like voltage relaxation model beat the strong two-RC double exponential on 6 of 8 *previously seen* public batteries, but got 51.76% WORSE MAE on LI and 8.62% worse on AR. An overall average cannot justify using it on a new individual device.

R3.10 adds a **selective risk wrapper** around the original, SHA-pinned R3.8 `diffusion_tail` and R3.7 `double_exp` code. It does NOT change these frozen formula functions or the independent R3.9 branch, model weights, or production systems.

## Three possible decisions

1. `CANDIDATE_DIFFUSION_TAIL`: admit the optional new formula only when an *early-only* risk score is low enough according to a calibration threshold chosen on seven OTHER battery groups.
2. `FALLBACK_DOUBLE_EXP`: use the established baseline if the early-only risk proxy suggests elevated uncertainty or development observations do not show acceptable device-level risk.
3. `ABSTAIN`: refuse to forecast when early time grid or physical voltage values are invalid, a formula cannot fit, or it extrapolates into an invalid range. Report refusal separately; it is not counted as a correct forecast.

### Strict information boundary

The risk calculator receives **exactly 241 time/voltage pairs** (0–4h), never the 1200 true future voltage values. It fits both frozen formula families to those 241 records, forecasts the following 1200 times, and computes:

```
normalized disagreement = mean(|candidate future forecast - baseline future forecast|) / mean(early observed voltage)
normalized early-fit penalty = max(0, candidate early RMSE - baseline early RMSE) / mean(early observed voltage)
risk score = disagreement + early-fit penalty
```

This is a **heuristic proxy**, not a probability of correctness or an independently calibrated uncertainty interval. It can be systematically wrong under chemistry or instrument shift. The later-only scorer receives the actual future labels and evaluates choices only after early predictions exist.

## Device-disjoint public retrospective development

Source: the same 16 original checksum-pinned files, eight physical battery groups and 30 measured traces from the [CC BY 4.0 battery OCV dataset, DOI 10.21227/651q-8v82](https://github.com/BulyK47/battery-datasets) attributed to Voicila, Enache, Vilciu and Seritan, POLITEHNICA Bucharest. This is a **retrospective re-analysis** of data previously inspected in R3.7 and R3.8, not a new source, blind experiment or eight independent replications.

For each of the eight leave-one-battery-out folds, the threshold is selected from the **seven other battery groups'** outcomes. The fixed permitted risk thresholds are `[0, 0.002, 0.005, 0.01, 0.02, 0.04, 0.08, 0.16]`. The training-only objective maximizes device-equal improvement compared with using the two-RC baseline everywhere, requiring both >=15% candidate coverage and no more than 10% relative MAE regression on **any** of the seven development devices. If no acceptable threshold exists, the model uses the stronger baseline everywhere on the held-out device.

Threshold selection never sees the heldout battery's late-voltage labels or scores, and there is **no battery-specific rule targeting LI or AR**. Nevertheless, all data were public in R3.8 before this wrapper was conceived. Therefore the overall 8-fold result is NOT unbiased new statistical evidence. We label the LI regression-motivated risk objective as retrospective engineering, and any success still requires an independent new device cohort.

Report all accepted-candidate traces, strong-baseline fallbacks, explicit abstentions, device-balanced selected MAE, baseline MAE, per-battery and worst-device regressions, all threshold trials and exact hashes. Accepting fewer predictions may reduce coverage, so a lower MAE with many abstentions is NOT automatically better. A fallback decision should not be credited as an accurate neural-model forecast.

## Prospective external science boundary (R3.9 untouched)

The existing independent [TACHYON R3.9 draft PR #91](https://github.com/Hawkar-usls/Demi_Head/pull/91) is frozen for its future external custodian test with >=12 genuinely novel devices. **Do not substitute this R3.10 risk wrapper into that preregistered trial.** R3.10 will require a new separately sealed, externally approved device cohort and a new independent protocol if its selective policy is to be evaluated prospectively.

No real new measurements received; no external custodian witness or signatures, no hidden gold, no R3.5 neural retraining, no learning on model-generated predictions, no production automation or NAS/Ocean changes. Under `scientific_admission=HOLD` no risk threshold can promote a new formula to accepted physics.

## Verification

The GitHub Actions job runs isolated negative-policy tests, downloads only the exact original public CC BY source CSVs with pinned Git blob SHA, recomputes early-only predictions on all 30 real traces, calibrates thresholds on the other seven device groups and reports all eight heldout decisions. Resource limits are one runner and 15 minutes with source raw files excluded from artifacts. There is no repeated auto-tuning until it passes.

Expected: `R310_EARLY_ONLY_RISK_POLICY / VALIDATION_ON_PUBLIC_PRESEEN_DEVICES / SCIENCE_HOLD / R39_FROZEN_AND_UNTOUCHED`.

## First real run and transparent corrective change (not a new blind trial)

The first public R3.10 check, [Actions #43103537561](https://github.com/Hawkar-usls/Demi_Head/actions/runs/43103537561), passed 10/10 tests and evaluated the 30 original published voltage curves. The conservative calibrator accepted **0/30 candidate** forecasts, fell back to 2RC on **26/30**, and abstained on **4/30**. On scored cases its device-equal MAE was **0.009283682467 V**, exactly the 2RC comparison, with **0% gain**. This was an engineering negative result, and the original run is retained.

Upon inspecting this initial outcome, we corrected a safety design flaw **after the first public evaluation**: an invalid *optional candidate* prediction should not cause full abstention if the strong incumbent 2RC remains physically valid. The protected baseline is now fit and range-checked first. If only diffusion-tail fails, output `CANDIDATE_UNSAFE_BASELINE_AVAILABLE` and use 2RC; abstain when the early inputs or even the fallback baseline are invalid. Added a dedicated injected-failure unit test and preserved the initial 10-test receipt. This is a posthoc engineering correction, **not** an unbiased prospective improvement or an alteration of R3.9.

Calibration thresholds and original source formulas remain unchanged. No new candidate has earned scientific admission; even a zero-regression baseline fallback is not evidence that the neural/symbolic formula learned better physics.

## Second observed run: four abstentions traced to a mixed-chemistry source range error

[Actions #43104335926](https://github.com/Hawkar-usls/Demi_Head/actions/runs/43104335926) passed 11/11 tests but still had **0 accepted candidate**, **26 fallback**, **4 abstained** and 0% improvement. The added explicit refusal-audit found `R310_EARLY_TIME_OR_PHYSICAL_VOLTAGE_REJECT: 4`, and **zero** cases of an invalid diffusion candidate while the baseline remained valid.

A direct read-only check of the **original pinned Git blob CSVs** established that four low-voltage traces are normal for the original AR/AU battery groups: AR charge 1.391–1.471 V, AR discharge 0.902–1.169 V, AU charge 1.389–1.455 V, AU discharge 1.003–1.217 V during first 4h. The R3.10 bounds 2–5.2V were wrongly borrowed from a lithium-oriented private R3.9 input contract, despite R3.7/R3.8 using multiple chemistries.

**Posthoc engineering fix, NOT independent evaluation:** R3.10 only now uses a source-compatible 0.5–5.5V physical-envelope precheck for these public mixed-chemistry measurements, with explicit manifest declaration and unit test. This broad range is a basic data-integrity check, not proof that every value in it is safe for every chemistry; chemistry-specific laboratory range approval remains necessary for new live use. The original two CI receipts and negative results remain unchanged in their historical GitHub runs. The R3.9 independent external battery protocol remains frozen with its original voltage criteria, and future external participants must explicitly review those criteria **before** any data are used.

## Third public run — actual retrospective reliability failure, do not auto-promote

After the **explicitly posthoc** mixed-chemistry voltage range correction, [Actions #43104817265](https://github.com/Hawkar-usls/Demi_Head/actions/runs/43104817265) passed **12/12** contract tests, all 16 original source hashes and all 30 physical voltage traces. The policy selected the diffusion-tail candidate on only **2 traces**, the double-exponential baseline on **28**, and abstained on **zero**. The device-equal baseline MAE was **0.00944983899245 V**, and the selective policy MAE **0.01024528502096 V**, or **8.41756% worse**. The worst battery's MAE was **51.75662% worse**, matching the original LI instability.

**Scientific conclusion: current early-only risk indicator FAILED to consistently detect dangerous cases.** Its decision rule is insufficiently discriminative for the publicly explored mixed-chemistry cohort, even if it safely falls back for the majority of traces. Do not claim a calibrated failure probability, significant improvement, or readiness for production. Keep all three original CI runs and negative results, and do not tune thresholds by repeatedly reading the same heldout AR/AU/LI error values.

Correct next input would be additional independently curated, prospective cells with chemistry, state-of-charge, temperature, aging, measurement noise and instrument metadata; a *separate* preregistered device-disjoint policy and a new blinded custodian-led evaluation are required. R3.9 still exists unchanged as its own frozen comparison of original R3.8 formulas, **not** an evaluation of this posthoc R3.10 selector.
