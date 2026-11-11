# TACHYON-R2E — safeguarded formula-first explanation layer

## What R2D demonstrated

On an 18-case author-created **PUBLIC development** challenge, the originally frozen tiny R2B and R2C models generated correct numeric answers on 0/8 numeric cases, and neither abstained on 4 out-of-domain questions. The lexical source retriever chose the expected DOI family in 6/6 conceptual cases and abstained on all 4 out-of-domain prompts. The exact formula baseline solved 8/8 numeric examples **by construction**, not through learning. These are not blind scientific results.

## Research-only R2E design

R2E is a controlled *non-neural* route selector around the trained system, not a newly capable Transformer. It uses the unchanged original R2C source-card SHA-256 and the public R2D formula engine. For an explicitly recognizable special-relativity v/c input (0≤β<1), it computes sqrt(1-β²) and returns its theoretical assumptions and the Einstein DOI. For a two-level Born projector with a valid ρ00 input, it returns tr(ρP)=ρ00 and the corresponding DOI. This verifies arithmetic consistent with selected formula assumptions; it is NOT a confirmation by lab data or a peer-reviewed physical expert.

Malformed values, simultaneous incompatible rule inputs, no confident source, and out-of-scope questions produce **ABSTAIN**. For conceptual questions covered by source cards, R2E returns the curated original Russian paraphrase as SOURCE_PARAPHRASE_REQUIRES_REVIEW, with an exact DOI and still requiring independent science review. It never promotes the raw neural draft into an asserted physical claim.

## Validation

The R2E public diagnostic reuses the same 18 developer-authored R2D cases to verify routing behavior. Expected routes: 8 deterministic formula cases, 6 cited source paraphrases, 4 abstentions. This is intentionally an implementation regression test and does not constitute an independent evaluation or demonstrate generalization.

No automatic scientific admission, no model checkpoint replacement, no R2B/R2C retraining, no Ocean integration, no production deployment, and no changes to main. External sealed 60+ unseen questions and independent laboratory-physics review still remain pending in GitHub issue #74.

Status: `TACHYON_R2E / SAFE_ROUTING_RESEARCH_ONLY / NO_NEURAL_SUPERIORITY_CLAIM / SCIENTIFIC_HOLD`.
