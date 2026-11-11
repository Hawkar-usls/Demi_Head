# TACHYON R3.1 — source-anchored formula curriculum and strict public evaluation

## Scope

This candidate creates a small, separate, auditable **mathematical** training pack and public post-freeze parameter challenge; it does **not** train new neural weights or claim independent validation. The real TACHYON-R2H generator did not give usable numeric answers on public R2D development (0/8), so the first control is to evaluate its existing guarded formula path on NEW parameter values.

## Trusted explicit mathematical references

- Special relativity proper-time relation for inertial clocks, OpenStax University Physics vol.3 §5.3: https://openstax.org/books/university-physics-volume-3/pages/5-3-time-dilation . For 0≤β=v/c<1, dτ/dt=sqrt(1-β²).
- Two-level qubit projective measurement, IBM Quantum Learning: https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/general-measurements/formulations-of-measurements . For a normalized density matrix ρ and projector |0><0|, P(0)=Tr(ρ|0><0|)=ρ00.

These references substantiate two textbook equations, **not** laboratory measurement accuracy, anomalous photon response, backwards-in-time transmission, or universal physics understanding. Each training label is produced by the exact stated mathematical equation, not a physical clock or quantum processor.

## Strict split

`data/tachyon/r31/formal_reference_pack.json` keeps two source families with independent train values (16 tasks), calibration (8), and new public development values (12). The new values do not occur in either train/calibration or the known R2H training vectors / R2D public challenge numeric inputs. Six invalid/ambiguous/OOD questions test abstention. A validator fails closed on source-domain spoofing, repeated values, range violations or attempts to claim hidden independent validation.

The executable tool exports `r31-train-formal-only.json` containing only train rows and a separate `r31-public-development-eval.json`. Both reports carry canonical SHA-256 hashes and are archived in Actions. There are no confidential assessor keys, private atomic clock logs, or GDELT article snippets in this pack.

## Honest comparison

The candidate arm is the **already implemented deterministic R2E explicit formula + citation** mechanism, not a newly fine-tuned neural transformer. The baseline is a mean prediction from each family's **train** labels only. The score checks absolute tolerance 1e-6 and fail-closed abstention for six invalid/OOD prompts. A better rule-based score shows better use of an explicit equation on these parameter values; it does not demonstrate new neural generalization.

To prove model improvement rather than equation execution, train a separately reviewed TACHYON candidate on the train-only pack, freeze weights and SHA **before** a separately administered independent unseen challenge. Compare to deterministic formula, prior R2H neural models, and source-only retrieval. Independently verify actual physics interpretations with sources/experts; no scientific admission without external blinded test.

No merge to production, no NAS changes, no JANUS Ocean checkpoint rewrite. The existing R2H PR #79 and Meta Registry R3 provenance pipeline remain separate.

Target state: `FORMAL_REFERENCE_PACK_CREATED / PUBLIC_NEW_PARAMETERS_EVALUATED / NEURAL_RETRAIN_NOT_PERFORMED / SCIENTIFIC_HOLD`.
