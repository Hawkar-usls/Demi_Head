# TACHYON-R3.5B — frozen typed SI candidate for an independent question-only handoff

Status: PUBLIC ENGINEERING CANARY ONLY / EXTERNAL SCIENTIFIC CUSTODIAN NOT CONNECTED / SCIENTIFIC HOLD.

## Frozen model and provenance

Candidate is the best calibration-seed R3.5 4-family SI-dimension-aware surrogate from GitHub Actions [run #43073429418](https://github.com/Hawkar-usls/Demi_Head/actions/runs/43073429418). Full checkpoint SHA256 `b631748974acd786f8ede06c5e016cbb5e41015f362e03fa3288b2c95d01234a`; source-author textbook manifest SHA256 `b959ac81019872a15c4487caba57749a1b8da90b19b2a096e8c0e7abc6e4d34a`. Both hashes are pinned in `tachyon/r35b_frozen_typed_inference.py`, not supplied by the question sender.

`torch.load(..., weights_only=True)` is followed by strict model/schema, dimension width, trained family, fixed seed and scientific HOLD checks. No training, optimizer, unseen answers, private salt, external search or NAS access. This is the exact R3.5 candidate, not a surrogate invented for the test.

## Strict typed question-only interface

JSON schema `janus.tachyon.r35b.typed_question_only.v1` contains ONLY `schema`, `candidate_checkpoint_sha256`, `case_count`, `items`, `contains_gold_answers=false`, and `questions_sha256`. Each item contains ONLY case ID, task kind, family, typed physical `inputs`, output unit, source URL and (for published real measured family metadata only) the known dataset SHA. The input never has target values or correct answers.

Canonical source/family/units/dimensions are checked before any forward call. Legal known families use R3.5's exact SI quantity encoder (normalized physical values, quantity roles, dimension signatures and target dimensions). Unknown unit, wrong unit (e.g., seconds as amperes), source spoof, dataset SHA mismatch, extra solution/answer field, duplicate ID, altered questions SHA or swapped checkpoint immediately fails closed.

Only the four already trained textbook families can generate a numeric neural estimate. The entire electric-power family (with exact equation baseline) and both published experimental families (Super-K muon stop delays and Offenburg SOC/OCV) are **ABSTAIN** because no new-family gradients were allowed. These refusals are correct engineering behavior, NOT positive numerical scientific generalization.

## External handoff protocol

1. External qualified scientist privately selects new unseen physical questions, records true experimental values, and seals full questions+gold with independent signature and timestamp. They must not upload raw gold, salt, hidden questions or private certificates into public GitHub repositories/Actions. Source/rights reviews are separate.
2. Supply ONLY an approved typed question transport, the frozen candidate checkpoint and this code to a network-isolated candidate executor. The executor verifies both SHA identifiers, produces prediction rows and a receipt hash. It must be under independent custodian supervision; a GitHub Actions self-test cannot prove an external operator actually ran the model.
3. Custodian independently rechecks model output commitment and evaluates numeric errors, exact textbook baselines, abstention coverage, calibration and actual measurement uncertainty. External signatures and score-key opening are handled on the custodian's system, **not by this public code**. The older R3.3 60-case custodian protocol pins a different R31B candidate and MUST NOT be silently reused as R3.5 scoring evidence.
4. A future dedicated R3.5 private scorer must bind the candidate and questions SHA to an independently sealed key and support SI target units. Until that tool and independent custodian are verified, don't call this a completed end-to-end external blinded trial.

## Public real checkpoint canary

`tachyon-r35b-typed-inference.yml` downloads the actual pinned two-model artifact from the preceding R3.5 GitHub run, selects the fixed SHA from calibration, and runs exactly four PUBLIC canaries: two typed numerical textbook questions (one SR, one Ohm) that must call the neural network, plus one entirely withheld electric-power family and one synthetic battery-SOC question. Both latter cases must abstain. No experimental numeric gold or private salt is present in the output archive.

Legacy R31B had source-family-specific high-beta error. R3.5 remains a numerical approximator and still errs by about 0.149 at beta 0.96. Exact SR formula must be preferred for real user answers; no neural auto-promotion and no application to live medical/laboratory/power systems.

Status: `R35B_REAL_FROZEN_TYPED_INFERENCE / STRICT_NO_GOLD_TRANSPORT / SCIENCE_HOLD / EXTERNAL_ASSISTANT_PENDING`.
