# JANUS Epistemic Execution Gate

## Purpose

This gate hardens DemiHead against a specific language-model failure mode: **a fluent answer can look like a completed computation, lookup, verification, or factual check even when no such operation actually occurred**.

The defense does not assume malicious intent. It treats unsupported certainty as an engineering provenance failure.

```text
FLUENT_TEXT != EXECUTION
PLAUSIBLE_VALUE != COMPUTED_VALUE
MODEL_OUTPUT != EXECUTION_RECEIPT
HASH_SHAPE != HASH_VERIFIED
CLAIM_OF_VERIFICATION_REQUIRES_RECEIPT
```

A language model may propose a value, explanation, hypothesis, or next step. A tool-augmented system may also execute deterministic code or retrieve sources. JANUS must keep those two events visibly distinct.

## Threat model

The gate covers at least these failure classes:

1. **Fake computation** — a model emits an arithmetic result, digest, checksum, statistic, conversion, or other exact value without a bound execution.
2. **Fake verification** — text says “checked”, “verified”, “matches”, or equivalent even though no admissible receipt exists.
3. **Source hallucination** — a current or external factual claim is presented as checked even though no source retrieval is bound to the claim.
4. **Format pressure** — the system prefers a concrete-looking answer over `EVIDENCE_INSUFFICIENT` because the conversational format appears to demand completion.
5. **Self-certification** — model-generated text fabricates a receipt or treats its own assertion that a tool ran as proof that the tool ran.
6. **Freshness collapse** — an old/stale observation is silently presented as current state.
7. **Conflict collapse** — two admissible receipts disagree but the system chooses the nicer answer instead of preserving the disagreement.

## Claim classes

The reference gate distinguishes four classes.

### `EXACT_COMPUTATION`

Examples: SHA-256, exact arithmetic, deterministic transforms, checksums.

A definitive value requires a bound execution receipt. A correctly formatted output is not enough.

### `EXTERNAL_FACT`

Examples: a fact read from a document, repository, database, instrument, or external service.

A factual claim requires a source receipt with a locator and observed value. Retrieval proves what the source returned; it does not make the source infallible.

### `CURRENT_STATE`

Examples: “the service is online now”, “this branch currently points to SHA X”.

The source receipt must additionally be current for the declared scope. Stale data fails closed.

### `INTERPRETATION`

Symbolic, theological, artistic, or analytical interpretation may remain meaningful without pretending to be factual verification. It must stay visibly labeled as interpretation.

## Fail-closed states

```text
EVIDENCE_INSUFFICIENT
CONTESTED_EXECUTION
CONTESTED_SOURCES
REFUTED_BY_EXECUTION_RECEIPT
CONTRADICTED_BY_SOURCE_RECEIPT
```

`EVIDENCE_INSUFFICIENT` is a valid terminal state. It is not a conversational failure and does not authorize guessing.

```text
TOOL_UNAVAILABLE != PERMISSION_TO_GUESS
FORMAT_PRESSURE != PERMISSION_TO_GUESS
NO_EVIDENCE -> EVIDENCE_INSUFFICIENT
```

## Real SHA-256 path

`tools/epistemic_execution_gate.py` includes an actual deterministic SHA-256 execution path using Python's `hashlib.sha256`.

Examples:

```bash
python tools/epistemic_execution_gate.py --sha256-text JANUS
python tools/epistemic_execution_gate.py --sha256-file path/to/file.bin
python tools/epistemic_execution_gate.py --sha256-file path/to/file.bin --expected <64-hex-digest>
```

The emitted receipt records:

- operation and execution engine;
- execution state;
- input kind and byte length;
- computed value;
- optional expected value;
- `MATCH`, `MISMATCH`, or `NOT_REQUESTED`;
- a claim ceiling.

A SHA-256 receipt proves only the digest of the bytes processed by that execution. It does **not** establish truth, authorship, safety, freshness, provenance outside the bound input, or semantic correctness.

```text
HASH_INTEGRITY != TRUTH
```

## Receipt assessment

A generic case can be assessed with:

```bash
python tools/epistemic_execution_gate.py --assess examples/epistemic_model_only_hash_claim.json
```

A model-only “hash matches” case must return:

```text
EVIDENCE_INSUFFICIENT
DO_NOT_GUESS_A_VALUE
```

A receipt whose `origin` is `model_output`, `assistant_text`, or `untrusted_narrative` cannot self-certify execution.

## Interaction with other DemiHead layers

The gate is independent from Face routing and capabilities.

```text
RECENTER != VERIFICATION
CAPABILITY != EVIDENCE
THIRD_WISH_REQUEST != EXECUTION_RECEIPT
FACE_AGREEMENT != FACT_VERIFICATION
```

`HEAR -> CHECK -> WIDEN -> RELEASE` may restore process quality, but it cannot turn an unsupported claim into evidence.

A Third Wish capability may make a real verification route available, but availability alone is not evidence that the route was executed.

## Required response behavior

When exact verification is unavailable, the preferred output is semantically equivalent to:

> I cannot verify that value from the evidence currently bound to this claim. A real execution/source check is required.

The system should never manufacture a substitute digest, citation, status, file content, tool result, or current-state answer merely to complete the conversational form.

## Constitutional invariants

```text
MODEL_OUTPUT != EXECUTION_RECEIPT
PLAUSIBLE_FORMAT != COMPUTED_VALUE
HASH_SHAPE != HASH_VERIFIED
CLAIM_OF_VERIFICATION_REQUIRES_RECEIPT
TOOL_UNAVAILABLE != PERMISSION_TO_GUESS
FORMAT_PRESSURE != PERMISSION_TO_GUESS
NO_EVIDENCE -> EVIDENCE_INSUFFICIENT
SOURCE_RETRIEVAL != SOURCE_TRUTH
AUTHENTIC_RECEIPT != WORLD_TRUTH
RECENTER != VERIFICATION
CAPABILITY != EVIDENCE
```

## Scope boundary

This is a reference enforcement layer, not a complete solution to language-model hallucination. It can make certain unsupported promotions structurally harder and testable. It does not guarantee that every natural-language claim has been correctly classified, nor does a structurally valid receipt prove that an external source itself is correct.
