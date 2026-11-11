# TACHYON R3.5 — dimension-aware numerical physics research model

**Status: research sandbox only. External-science and production HOLD.**

## What changed compared with the R31B two-family scalar regressor

1. Inputs carry `name`, numeric `value`, `unit`, `family` and exact `source_url`. SI dimension vectors cover mass, length, time and current. Registered units include `%`, A/mA, Ω/kΩ, V/mV, s/ms/µs, m/cm, m/s/km/h, W and MeV/c for momentum. Every conversion is explicit and dimension-checked; `Ω` cannot be silently treated as `s`, MeV/c as velocity, or W as V. Unknown units and out-of-domain values fail closed.
2. Each neural input includes normalized physical values, role one-hot, dimension vector and source-family one-hot plus target dimension vector. The supervised model is a small genuine CPU Torch network (2 hidden tanh layers of 48, 2 seeds, max 1200 AdamW steps each). It is NOT a language model and cannot infer arbitrary natural-language units.
3. **Four explicit families trained from textbook equations only:** special relativity proper-time ratio, projective Born probability, Ohmic voltage V=I×R and constant 1D displacement ∆x=v∆t. Sources: [OpenStax time dilation](https://openstax.org/books/university-physics-volume-3/pages/5-3-time-dilation), [IBM Quantum measurement](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements), [OpenStax Ohm](https://openstax.org/books/college-physics-2e/pages/20-2-ohms-law-resistance-and-simple-circuits) and [OpenStax kinematics](https://openstax.org/books/college-physics-2e/pages/2-3-time-velocity-and-speed). These are author-created mathematical examples, **not actual lab observations**.
4. **Fifth whole source-family held out**: electric power P=I×V from [OpenStax section summary](https://openstax.org/books/college-physics-2e/pages/20-section-summary). The exact formula is available as a deterministic baseline but the neural surrogate must abstain from numerical predictions because it was never trained to represent this family. No false claim of new-family transfer.

## Split, evaluation, baselines

The source manifest pins 48 TRAIN, 16 CALIBRATION and 30 public developer test cases (24 heldout parameter combinations in the four trained families; six examples from the entire never-trained electric-power family). Inputs have alternating SI/milli/kilo, km/h/ms and percentage units that map to the same SI dimension features. Train and public developer parameter tuples do not overlap.

Two neural candidates train **only on the 48 sandbox examples**, with fixed seeds 20261111 and 20261112. Candidate and best step are chosen ONLY by calibration mean squared error. Both checkpoint files and SHA-256 are committed to the Actions artifact **before** public development scoring. The report records per-family neural MAE in proper SI units, train-family-mean baseline, exact equation baseline (zero algebraic error by construction), worst error, and six correct whole-family refusals. **Averages of different SI dimensions are not scientific global metrics**: judge per family instead.

Public developer results do not establish external blinding, transfer to unseen physical laws or independent accuracy. No automatic deployment even when a model beats the train-mean baseline, because the exact formula remains a stronger baseline.

## Real experimental data interface with separate admission

`typed_lab_observation` converts independently published data shapes to typed SI observations with strict original dataset SHA. Supported read-only examples: Super-K SK-VI muon electron momentum in MeV/c and tagged delay in µs; Offenburg OCV/SOC in V and %. The exact source hashes were established in R3.2, but **checksum integrity is not independent scientific review or a licence to train**.

Both original source files remain in the public Zenodo host; no raw measurements are copied into the new corpus. For each observation, provenance URL, SHA, sample ID, original units and SI target dimension can be recorded without granting gradient authorization. `refuse_lab_training()` fails closed even for a correct digest and a forged `curator_approved=True` flag. Before real measured labels can enter training, a separately controlled source/rights/family review must issue a signed, curator-approved, immutable research pack with independent holdout and its own scoped PR and policy. **R3.5 deliberately DOES NOT train on Super-K or battery observations.**

## Safety and performance

PR GitHub Actions has read-only permissions; 12-minute timeout, a single CPU-hosted job and no private secrets. There is no unbounded runner fan-out, no training from GDELT or quarantined Meta Registry observations, no production JANUS Ocean/NAS modifications and no user-facing deployment. Records, including weak outcomes, retain a content hash and run ID.

**Additional gate:** an independent assessor must seal novel source-family questions and lab measurements on an external machine and compare the trained candidate with exact physics baselines and source-only retrieval. The R3.3/R3.4 custodian contract is available but **no actual independent experiment has been performed**.

Expected state: `R35_SI_TYPED_ARCHITECTURE / AUTHOR_MATH_RESEARCH_TRAINING / LAB_MEASUREMENT_READ_ONLY / NOVEL_FAMILY_HOLD / SCIENTIFIC_HOLD`.
