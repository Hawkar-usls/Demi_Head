# TACHYON R3.2 — independent-origin experimental measurements vs frozen R31B candidate

## Scientific scope and two genuinely new families

These sources contain **real measured instrument values** made by outside experimental teams, NOT pseudo-labels generated from two TACHYON training formulas. That is source independence, **not** independent blinding of this assessor.

1. **Muon decay and capture, Super-Kamiokande** — https://zenodo.org/records/15081911 (DOI 10.5281/zenodo.15081911). Published SK-VI stop-muon records from 2020–2022, 1,986,465 rows. CSV provides decay-electron momentum and detection delay plus optional tagged neutron times. Expected publisher MD5 59056d97657ed04b3d19c7766a976519, max download 30 MB. The auditor reports the count and uncorrected mean tagged delay, **NOT a direct estimate of the free-muon vacuum lifetime**: detector effects, muon capture and selection bias matter. Copyright/redistribution terms are not yet established, so no raw rows are committed or uploaded.
2. **Lithium-ion battery open-circuit voltage (OCV) vs state of charge (SOC)** — https://zenodo.org/records/13142016 (DOI 10.5281/zenodo.13142016), published by W. G. Bessler / Offenburg University, 2024, related paper DOI 10.1149/1945-7111/ad6938. Expected publisher MD5 6bb24aed4d06fb4df88de4a3f6a37f3, exact 1,001 rows and at most 200kB. The experimental source has CC BY-NC 4.0 and IP cautions concerning the authors' algorithms; only simple read-only descriptive statistics are generated, no proprietary method copied, raw data never embedded in GitHub artifacts.

These measurements belong to source families *entirely different* from the R31B neural regressor: that model only encodes an input scalar and a sign flag denoting **SR_PROPER_TIME_RATIO** or **TWO_LEVEL_BORN_PROBABILITY**. It has no representation or trained labels for muon capture or battery electrochemistry.

## What the automated GitHub Actions test does

- Download the exact frozen real R31B candidate from run 43057568871 and verify checkpoint SHA256 `b3b36dfb3e8c1d0d4a1ae1b867978cfa5f8f28d6768d1a42efac02a4d2e47f01` BEFORE source acquisition. No retraining, no gradient on measured data.
- Download exactly two explicitly allowlisted public Zenodo files, bounded to 30MB/200kB with no login, query parameters or user private content. A redirect must remain on `zenodo.org` and HTTPS. Respect the source's published MD5, then record full SHA256 of actual bytes. If Zenodo returns HTTP429/unavailable, log sanitized `PROVIDER_UNAVAILABLE`, never invent measurements; there are no aggressive retries.
- Strictly parse first two muon CSV columns and battery SOC/OCV rows, check expected complete row counts and reasonable units/ranges. Store only descriptive aggregates, exact source DOI/URL, SHA and statuses. Never republish raw measurements.
- The frozen two-family neural regressor is **not asked to extrapolate to new families**. The only scientifically honest outcome here is `ABSTAIN_UNSUPPORTED_PHYSICS_FAMILY` with no fabricated numeric answer. This proves a hard input-domain firewall, **not** new-family generalization or improved predictive physics.
- All hashes, failures, refusal coverage, experiment flags and parent checkpoint identity are serialized in one append-only witness artifact with `scientific_admission=HOLD` and `independently_blind=false`.

## Why this is NOT the requested final independent blind proof

Published datasets predate the model's training, and their measurement values are publicly available. No independent assessor has withheld a secret answer key; this assistant designed the parser and test. The program does not produce real neural forecasts for unseen physical laws. Therefore **no independent blinded out-of-family gain may be claimed** from successful source integrity or refusal.

### The genuine next custodian trial (separate human role)

1. An independent scientist/lab chooses previously unexposed problems or independently measured future observations from source families absent from the model's training; the custodian controls private question+gold-answer data outside candidate code and GitHub Actions logs.
2. Publish an SHA-256 commitment to the candidate checkpoint, a fixed model implementation and the scoring rubric *before any hidden question or gold answer disclosure*. Prevent model retraining/online lookup after freeze.
3. Custodian supplies question-only prompts in one controlled evaluation session, collects model predictions and abstentions as sealed SHA/UTC-stamped records; only then discloses the scoring key through a separate secured channel and verifies no data was leaked. If a public question is available earlier, it is not a secret blind challenge.
4. Compare raw model answers, exact standard formula engines, simple retrieval and abstention baselines. Assess calibration, units, errors and coverage, per-family results and paired uncertainty. Register all attempts, including failures. Do not repeat hidden tests until one looks positive.
5. Only independent assessor sign-off plus improved performance on genuinely unseen families can change `scientific_admission`, and that change requires a separate reviewed authorization. Current `scientific_admission=HOLD`; no production model or NAS changes.

## Scientific interpretation of prior v/c=0.94 failure

R31B reached a public-new-parameter MAE 0.012747526 overall but made a large high-speed SR error ~0.106 near beta=0.94, outside its highest SR training beta=0.83. Exact SR calculation is available and must always override this limited approximator for numerical physics; direct autonomous numerical use of this checkpoint remains blocked.

Status: `EXTERNAL_MEASUREMENT_SOURCE_AUDIT / OUT_OF_FAMILY_ABSTAIN / NO_BLIND_CUSTODIAN / SCIENTIFIC_HOLD`.
