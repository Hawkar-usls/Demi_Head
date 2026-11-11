# JANUS TACHYON R3.6 — generate candidate formulas; verify before research-only learning

**Engineering goal**: move beyond a scalar numerical surrogate by searching for explicit, unit-consistent scientific **candidate relations**, fitting coefficients from recorded observations, comparing against the known law and a future chronological holdout, and refusing to promote spurious improvements. A generated candidate is NOT a new law of physics.

## Why exact formulas cannot be 'beaten' on their own mathematical labels

If labels are generated from y=IR exactly, y=IR has mathematical error zero; no predictive model can improve that metric. It is possible to outperform the **incomplete** idealized relationship y=IR on new real or simulated observations if the apparatus depends on temperature, losses, aging, geometry or unmodelled conditions. But this is **an empirical model improvement for a specified experimental regime**, not a discovery that Ohm's law is universally wrong or proof of unknown physics.

R3.5 revealed that its neural surrogate can return about 13.89 V where 0.5 A×20 Ω=10 V. R3.5B now uses the exact formula in known-law responses and records the neural error separately. R3.6 will not incorrectly claim this old error is scientific progress.

## Controlled proof-of-method — not experimental measurements

The script `tachyon/r36_symbolic_discovery.py` generates two author-written, simulator-labelled sources with bounded deterministic pseudo-noise:

- Positive incomplete-baseline control: **synthetic thermal resistor**, fake measured volts from `V=I×R×(1+0.004 ΔT/K)+noise`. The formula search receives (I in A, R in Ω, ΔT in K, measured volts) and the *incomplete* known baseline `V=IR`, **not the true coefficient**. It may discover a conditional correction that beats the incomplete baseline on withheld parameter examples.
- Negative control: the same generator but exact `V=IR+noise`, with no temperature effect. An added correction should not be considered an improvement merely because it fits random training noise.

The selected candidate comes from 16 possible low-complexity structures: zero correction (baseline), five one-term candidates, ten two-term candidates. Each correction term is built from **dimensionless** quantities `ΔT/20K`, its square, `(I-1A)/1A`, its square or their product. Thus every candidate output remains in volts `V=IR(1+Σ c_j t_j)`. Arbitrary text/code evaluation, dimensional sums and unbounded expression trees are disabled.

The algorithm fits coefficients from exactly **84 TRAIN simulator observations**, selects structure by **42 CALIBRATION** examples with a fixed complexity penalty and requires at least 20% calibration RMSE improvement. It then refits coefficient values on train+calibration and *freezes both coefficients and source SHA* before the 54 future-heldout values are generated, requiring at least 15% relative RMSE reduction on these unseen simulator observations. It saves **all 16 trials**, selected equation, train/cal case ID digests, candidate SHA and every future-heldout predicted and simulated measured value. No experimental task is repeated until it luckily passes; both negative and positive outcomes are logged.

Here 'immediate learning' means fitting equation coefficients against **original measured (here simulated) labels**, not generating new labels from the model's own guesses. The model is NOT allowed to feed its own predictions into its gold training data. The candidate can be an experimental **sandbox-only** formula receipt after the gates. It is **not** deployed, not fed into JANUS Ocean, not scientific admission. An independent checker must confirm the actual physical source, calibration, units and reproducibility.

## Real laboratory gate remains strictly closed

Super-K muon timing and Offenburg battery SOC/OCV source checks (R3.2) established raw file integrity and typed SI interface (R3.5), but they have different target quantities and are **not** automatically trainable via this Ohmic temperature simulator. License and independent source-curation have not been approved. `admit_training_source` refuses their real URLs even if a caller supplies `curator_signed=True` because self-asserted approval is not a third-party signature.

**Next real-world milestone:** prepare an *independent reviewed* dataset of real I–V–temperature observations with units, instrument uncertainties, timestamp and calibration settings, explicit license, treatment of measurement errors and physically meaningful drift. Use separate time/batch/group heldout experiments and compare exact temperature-adjusted known physics plus strong alternatives—not only the incomplete V=IR baseline. An external custodian must freeze model/checkpoint/formula before the lab holdout is unveiled; publish every trial and failures, not cherry-pick positive results. Independent adjudication is needed before any physical formula gets scientific or production admission.

Resource gate: one short Python-standard-library Actions job (`contents:read`), fixed candidate grammar, max two coefficients, bounded dataset counts, no multiple runners/retries, no external secrets, no NAS modifications, no auto-merge. Reports are append-only SHA-linked JSON artifacts.

Status: `R36_SYMBOLIC_DISCOVERY_SANDBOX / POSITIVE_AND_NEGATIVE_CONTROLS / PROSPECTIVE_EXTERNAL_LAB_NOT_RUN / SCIENTIFIC_HOLD`.
