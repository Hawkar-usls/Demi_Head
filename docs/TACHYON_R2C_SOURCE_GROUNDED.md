# TACHYON-R2C — source-grounded explanatory Transformer (RESEARCH ONLY)

## Training change

R2C adds six DOI-identified primary-source families: Einstein (1905), Shapiro (1964), Bell (1964), Hensen et al (2015), Ghirardi/Rimini/Weber (1986), and Caves/Fuchs/Schack (2002). Source bibliographic metadata was verified on publisher or PubMed pages on 2026-11-11. Short Russian questions and explanations are original paraphrases, NOT copyrighted full texts, and are not independently peer-reviewed explanations.

The independent R2C checkpoint uses 36 training pairs: original pinned R2B 24 pairs plus 12 new pairs (2 per paper), with 13 source families. A new CPU-only encoder-decoder Transformer is trained from scratch; R2B stays frozen and unchanged.

## Source-grounded response

Deterministic retrieval chooses DOI-anchored source summaries from the public training cards, records lexical support and can abstain. The separate neural explanation draft is always labeled UNVERIFIED, even if fluent or similar to the paraphrase. Retrieval is NOT equivalent to scientific truth. Each answer requires reviewer approval, and the research code has no deployment capability.

A deterministic sanity layer checks selected mathematical identities: time-dilation ratio at v/c=0.6; Shapiro delay dimensionality for GM/c^3; classical deterministic CHSH; a two-level Born-rule probability example. These tests check elementary identities only, NOT full theory derivations, causal communication, or new physics.

## Blind assessment separation

The prior R2B public source-family evaluation is not an independently administered blind test. The new protocol file data/tachyon/r2c/blind_assessment_protocol.json is only a public preregistration; there are no secret labels or laboratory measurements in the R2C training path.

An external independent custodian must construct at least 60 novel hidden cases after checkpoint freeze, commit a blinded SHA-256 to the record, retain private answers outside this repository, and score all frozen arms: R2C neural text, source-grounded retrieval, R2B, lexical retrieval, and formula baseline. Evaluate physical reasoning, dimensional consistency, citation support, causal claims, abstention, and failure cases. Do not retrain on blind holdout. No promise of success and no scientific admission until external review. Original clock-lab data remain isolated from training.

## Baseline archival receipt

The exact ZIP from R2B run #43015290827 was downloaded; its SHA-256 equals the GitHub artifact digest and its internal checkpoint hash equals the CI receipt. Copied to connected Google Drive, existing JANUS Research folder; Drive metadata verifies the size, 642391 bytes. No content re-download verification was done after upload.

Original ZIP SHA256:
aa15e1d3794806f69b274e6cf6a8763e9761d6e8f21ad8ba0f1503c199966a0d

Internal model SHA256:
3adbf7b11a0f4275ab565ea833c7d415fc0e6727ddddf48e5a27f04346350f9c

Google Drive archive:
https://drive.google.com/file/d/1dsfinukmbf7e4ZQptZDpbbAzfD5SYYFK/view?usp=drivesdk

See the immutable-receipt candidate at data/tachyon/r2c/r2b_archive_receipt.json.

## Boundary and CI

R2C runs in an isolated draft PR stacked on R2B (#71), which itself is stacked on R2A (#70). The only automated action is bounded CPU training plus public nonblind diagnostics, which cannot authorize admission. No main branch edits, no production deployment, no JANUS Ocean changes.

Status: TACHYON_R2C / SOURCE_CORPUS_AND_CODE_READY / BLIND_ASSESSOR_PENDING / SCIENTIFIC_HOLD.
