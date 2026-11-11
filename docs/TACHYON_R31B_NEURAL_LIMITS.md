# TACHYON R3.1B — first real CPU neural approximation of two verified equations

**This is NOT a general physics assistant or a test of retrocausality.** It is a small train-only numerical neural regressor on author-generated examples from two public textbook equations. No private laboratory measurements, user data, external online news or hidden evaluation keys are involved.

## Reproducible method

Source pack: TACHYON R3.1 (OpenStax proper-time and IBM Quantum projector Born rule). Train: 16 formula examples (8 per family), calibration: 8 (4 per family); *public unseen developer challenge*: 12 different numeric parameters (6 per family). Six OOD/invalid controls were previously tested by the guarded R2E executor. Parameters in all splits disjoint from each other and from known R2D/R2H public examples.

Model: 2 inputs (normalized numerical parameter plus formula-family indicator), tanh hidden 24 -> tanh hidden 24 -> sigmoid scalar output. Fixed seed 20261111, max 1200 AdamW steps, one CPU thread. Best checkpoint selected **only by calibration MSE** every 20 steps. Checkpoint is SHA-256 content addressed and written before ANY public held-out questions are generated in the training function.

Comparisons: the newly trained neural regressor's mean absolute error on the 12 new parameter values; the constant family-training-label mean; and exact closed-form formulas (zero mathematical error by construction). Neural numerical score within absolute 0.015. This tests limited numerical generalization of a smooth function, not novel source-family generalization. If the regressor beats the mean but cannot beat exact formulas, that is the expected scientific interpretation.

The model has no domain knowledge, source verification, ambiguity handling or OOD abstention; these remain in a separate guarded routing stage. Never use the regressor to answer arbitrary user questions or override a correct deterministic formula. Positive public results do NOT warrant production rollout. Even if the model obtains a good score, independent external sealed physical data and genuinely new formula families are needed for scientific adoption.

Workflow: tachyon-r31b-neural.yml (read-only permissions, one bounded standard GitHub-hosted CPU job, no unbounded matrix, training report+weights downloadable as an artifact). Parent R3.1 source pack PR #81 is draft and stacked on R2H PR #79. JANUS Ocean's actual R3.1 retrospective heldout admission is separately implemented in Janus-Demiurge merged PR #528 and presently rejects Ocean candidate below baseline.

Status: `NEURAL_TRAINING_RESEARCH_ONLY / CALIBRATION_SELECTED / PUBLIC_DEV_NOT_BLIND / SCIENTIFIC_HOLD`.
