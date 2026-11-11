# TACHYON R3.3 — independent external custodian handoff (OFFLINE)

**Prepared contract, NOT a completed blind scientific experiment.** Neither GitHub Actions nor JANUS automatically becomes an independent observer simply because hashes were generated. An external scientific custodian must independently operate the protocol, control private labels, verify the frozen model/runner, sign timestamps and own all challenge material.

## 1. Scope and frozen candidate

Frozen neural weights from TACHYON-R31B GitHub Actions run #43057568871: `b3b36dfb3e8c1d0d4a1ae1b867978cfa5f8f28d6768d1a42efac02a4d2e47f01`. That network is only a scalar regressor with a 2-family sign input; it cannot genuinely answer out-of-family muon or electrochemistry questions. A proper blind 60-case test is likely to reveal poor coverage; never map unknown families to a known sign or fake a model answer. Abstain.

An independent scientific evaluator chooses at least **60 unpublished challenges**, comprising >=20 numeric/dimensional, >=20 conceptual/causal/source and >=20 OOD/adversarial, with novel physical source families, authentic primary measurements and appropriate rights. None of the question/answer material may be selected by the model authors, pre-disclosed through public datasets or used for further training. Existing public Zenodo muon and battery data are **public source integrity samples, not hidden labels**.

## 2. Custodian-private JSON format

Keep this file ONLY on the external custodian's protected system; never paste or upload it into the public GitHub repository or Actions logs. Example item layout (illustrative, not an actual gold label):

```json
{
  "schema": "janus.tachyon.r33.private_challenge.v1",
  "items": [
    {
      "case_id": "numeric_000",
      "category": "NUMERIC",
      "family": "NEW_PHYSICS_FAMILY",
      "question": "What is the measured quantity, with physical units?",
      "source_url": "https://example.org/primary-source",
      "gold": {"kind": "numeric", "value": 1.0, "unit": "m/s"}
    }
  ]
}
```

The full private pack must contain at least 20 examples of **each** category. Conceptual `gold` is `{"kind":"conceptual", "rubric":"Independent assessor detailed grading criteria ..."}`; OOD `gold` is `{"kind":"abstain"}`. DOI/source attribution must be independently verified by the custodian; the tool only validates a safe field shape, not the existence or scientific value of a URL. Real external intellectual property and personally sensitive information should not be included.

## 3. Local salted seal before questions are shown

Generate 32 cryptographically random bytes of salt offline on the CUSTODIAN'S machine, then write the 64-digit hex salt to a PRIVATE file. Do not place the salt, gold, answer-key or questions-only transport in GitHub or JANUS/Ocean inputs. For example, on the custodian's POSIX host: `python -c 'import secrets; print(secrets.token_hex(32))'` and save output into a private `.txt` with appropriate file permissions. Do not include the value in shell command history.

```bash
python -m tachyon.r33_external_custodian seal \
  --private /private/challenge_with_answers.json \
  --salt-file /private/custodian_salt_hex.txt \
  --frozen-model /private/r31b_math_neural_research_only.pt \
  --public-commitment-out /private/commitment_only.json \
  --questions-only-out /private/question_transport.json
```

The seal commits to `SHA256(secret_salt || canonical_full_private_pack)`, the frozen candidate SHA and fixed scoring-rubric SHA. The public commitment contains **neither salt nor gold**. The questions-only transport intentionally omits `gold` and is provided only to the independent scorer/model operator after sealing. The local ISO-UTC time inside this JSON is an untrusted machine clock; an independent timestamp and a separately signed human custody attestation remain necessary.

## 4. Freeze prediction session and assess

Record a candidate inference container SHA, GPU/CPU implementation, model file SHA, temperature/seeds (if applicable), blocked online retrieval, all model responses, and independently timestamp the predictions **before unlocking the private gold**. The R31B regressor cannot parse arbitrary free-text questions, so it must honestly output ABSTAIN for unsupported categories; the actual authenticated execution must be performed and attested by the external custodian, not assumed from a JSON assertion.

After candidate predictions have been frozen, locally generate a prediction file in this shape:

```json
{
  "schema": "janus.tachyon.r33.custodian_collected_predictions.v1",
  "candidate_weights_sha256": "b3b36dfb3e8c1d0d4a1ae1b867978cfa5f8f28d6768d1a42efac02a4d2e47f01",
  "items": [
    {"case_id":"numeric_000", "kind":"abstain"}
  ]
}
```

All original case IDs must appear exactly once; a partial prediction set is rejected rather than scored on an artificially favorable subset. The external scorer uses the private source pack and salt only OFFLINE:

```bash
python -m tachyon.r33_external_custodian score \
  --private /private/challenge_with_answers.json \
  --salt-file /private/custodian_salt_hex.txt \
  --frozen-model /private/r31b_math_neural_research_only.pt \
  --sealed /private/commitment_only.json \
  --predictions /private/frozen_predictions.json \
  --public-summary-out /private/score_summary_only.json
```

Numerical scoring requires matching units and `abs(model - gold) <= max(0.0001, 0.01 * abs(gold))`. OOD correct behavior is abstention. Conceptual answers **require independent manual review** and are deliberately not auto-scored. The report records all denominator counts, holds and risks; it cannot automatically assert scientific admission or custodian signature. Since the independent challenges contain previously unseen source families, refusal may be the correct safety outcome and does NOT prove new-family generalization.

## 5. Audit trail / privacy / scientific gate

Publish to Meta Registry only a signed commitment, model SHA, rubric SHA, frozen predictions SHA, approved source attribution and aggregated results under another review-only PR. NEVER publish the raw gold or salt before final independent verification. A randomly salted hash resists trivial guessing of small answer sets but does not prove when or by whom data were committed: independent timestamp, custody chain, tool execution evidence and researcher signature remain separate conditions.

PR CI runs **synthetic tests only**; it must never access actual private challenge/answer files. The evaluation tool implements no optimizer and cannot train on hidden data. GitHub Actions, JANUS Ocean and NAS production services remain unchanged.

**Scientific result today: `EXTERNAL_CUSTODIAN_NOT_CONNECTED / INDEPENDENT_BLIND_NOT_DONE / SCIENTIFIC_HOLD`.**
