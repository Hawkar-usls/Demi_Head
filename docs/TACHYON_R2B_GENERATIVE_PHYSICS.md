# TACHYON-R2B — separate generative physics explanation candidate

This research PR adds a small encoder-decoder Transformer trained from scratch. Unlike existing v0.3, it generates text, not a six-class label. It is not a pretrained general-purpose GPT.

## Training data

- Twelve instruction-answer pairs from the audited nonverbatim Homo Deus time-physics video claim record. The exact Meta Registry commit is a7f77b02ba6f66efc3a0df5d275de7e57eb0e28d. Generated using the existing R2A source-bound adapter; the entire video is ONE secondary source family.
- Twelve hand-paraphrased questions from six primary theoretical physics papers: Alcubierre 1994; Hawking 1992; Morris/Thorne/Yurtsever 1988; Finazzi/Liberati/Barceló 2009; Visser 1993; Misra/Chiu/Sudarshan 1977. IDs, DOIs and paraphrases live in data/tachyon/r2b/primary_papers_train.json. Their concepts overlap with the secondary video: source names do not establish scientifically independent facts.
- No copyrighted transcripts or journal texts copied.

## Model and source-family holdout

The source training stage reads only the generated R2A corpus and the theory-paper paraphrase file; it saves an integrity-bound candidate checkpoint before anything reads holdout answers. One encoder/decoder Transformer layer, width 64, 4 heads, 35 epochs, source-token length 58 and target-token length 78; CPU PyTorch.

A separate evaluation command then reads six published-atomic-clock explanation questions grouped by three paper families:
- Chou et al 2010, DOI 10.1126/science.1192720;
- Bothwell et al 2022, DOI 10.1038/s41586-021-04349-7;
- Zheng et al 2023, DOI 10.1038/s41467-023-40629-8.

The original Wisconsin 2023 processed measurement CSV, plus other time-metrology research artifacts, are strictly excluded from training. The workflow checks the original CSV SHA-256 a4384040d5678893b4df15ea0be2980661023305f5009de876179fab1dea632f without sending any measurements to the network.

Recorded metrics: generated text unigram token F1, simple nearest-training-question retrieval baseline F1, diagnostic coverage of physics-mechanism word stems, and individual generated answers for further audit.

These metrics do NOT measure independent physics truth, human-level explanation understanding, actual time prediction, or a physical retrocausal channel. The holdout source families are distinct from training, but this is not an independently administered blind scientific trial. The earlier human-constructed clock texts are not pristine unseen evidence to the project as a whole.

The validation job is read-only, bounded, PR-triggered, with an optional manual dispatch; it does not merge, deploy, rewrite Ocean trials, touch production SQLite or change models in other repositories. All weights remain research-only on HOLD until independent scientific review.

Next: external assessor issues new, unseen physical questions and dated measurement problems; compare against theoretical formula and retrieval baselines and preregister scoring before tuning. Preserve negative results.
