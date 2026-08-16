# Security Policy

## Project boundary

DemiHead is a transparent, local-first Guardian Mesh reference head. The default runtime is read-only and has **zero mass-effect budget**.

The original process-observer boundary remains in force, and the Guardian extension adds a second boundary: **information analysis must not silently become authority over people or platforms.**

## Permanent prohibitions

The default project does not accept features that:

- inject code, hooks, libraries, or threads into another process;
- read process memory, credentials, tokens, private keys, environment secrets, or unrelated user payloads;
- intercept keystrokes, clipboard, private screen content, microphone, or decrypted network content without a separately reviewed explicit feature contract;
- bypass operating-system permissions, platform controls, rate limits, access controls, or terms of service;
- conceal the runtime from the machine owner or impersonate another human/service;
- automatically elevate privileges;
- create self-spawning public identities or autonomous astroturf;
- perform covert mass persuasion or unsolicited personalized political outreach;
- optimize on belief change, ideology shift, loyalty, or psychological vulnerability;
- treat Face multiplicity as public consent, external corroboration, or multiplied authority;
- treat model output as self-authenticating truth;
- treat official statements as exclusive objective truth by source class alone;
- automatically retry an ambiguous external side effect;
- let a model rewrite the constitution/policy that limits the model.

## Guardian source adapters

Every future live information-source adapter must document:

1. exact source/API and authentication mode;
2. fields collected and fields deliberately excluded;
3. whether the source is official, primary, independent, derivative, or unknown;
4. freshness and correction/supersession semantics;
5. provenance/root identity semantics;
6. retention and redaction behavior;
7. failure behavior for timeout, stale cache, revoked access and malformed output;
8. external side effects, which must default to none;
9. rate-limit and backpressure behavior;
10. fixtures for missing, contradictory and stale evidence.

Source adapters must not infer objective truth from HTTP success, signature validity, account reputation, or government ownership alone.

```text
AUTHENTIC != TRUE
AVAILABLE != CURRENT
SIGNED != INDEPENDENT
OFFICIAL != EXCLUSIVE_TRUTH
```

## Epistemic execution / fake-verification firewall

A language-model response must never be treated as evidence that a deterministic computation, lookup, source retrieval, repository read, or current-state check actually occurred.

For exact claims such as SHA-256, checksums, arithmetic outputs or deterministic transforms, a definitive result requires a bound execution receipt or a direct deterministic execution path. Correct-looking formatting is not evidence.

For factual/current-state claims, a definitive statement requires an admissible source receipt appropriate to the declared freshness scope. A stale source cannot certify a current-state claim.

```text
MODEL_OUTPUT != EXECUTION_RECEIPT
PLAUSIBLE_FORMAT != COMPUTED_VALUE
HASH_SHAPE != HASH_VERIFIED
CLAIM_OF_VERIFICATION_REQUIRES_RECEIPT
TOOL_UNAVAILABLE != PERMISSION_TO_GUESS
FORMAT_PRESSURE != PERMISSION_TO_GUESS
NO_EVIDENCE -> EVIDENCE_INSUFFICIENT
SOURCE_RETRIEVAL != SOURCE_TRUTH
RECENTER != VERIFICATION
CAPABILITY != EVIDENCE
```

A model-generated narrative that says a tool ran cannot self-certify that execution. Conflicting admissible receipts must remain contested. Missing verification must fail closed to `EVIDENCE_INSUFFICIENT`, not to a fabricated value.

The reference implementation is `tools/epistemic_execution_gate.py`; its SHA-256 mode performs real local computation through Python `hashlib.sha256` and emits a scoped execution receipt. That receipt establishes the digest of the bytes processed by that execution only; it does not establish semantic truth, authorship, safety, freshness or external provenance.

## External effects

The default repository permits local file/console output only.

Any future publication, messaging, platform posting, notification, account action, or government-system write requires a separate capability contract and authorization review.

High-impact capabilities must be fail-closed and separately authorized. Internal Face agreement cannot satisfy a human two-key or independent-failure-domain requirement.

```text
PROPOSAL != WORLD_EFFECT
MORE_FACES != MORE_RIGHTS
AMBIGUOUS_EFFECT != RETRY_PERMISSION
```

## Civic / government deployment boundary

A future civic deployment requires external legal, privacy, security, accessibility and human-rights review.

It must provide:

- visible source provenance;
- visible uncertainty;
- correction/appeal path;
- bounded retention and data minimization;
- user opt-out;
- ability to remove optional personalization context;
- independent audit of language invariance and source-selection bias;
- human review for defined high-stakes contested cases.

Forbidden even under an emergency label:

- indefinite suspension of user rights;
- political loyalty/social-credit scoring;
- AI-only punitive decisions;
- psychographic persuasion;
- covert identities;
- silent expansion of data collection;
- converting disagreement into a risk score.

Emergency mode may reduce capabilities; it must not permanently remove constitutional limits.

## Children

Youth-facing use requires a separately reviewed profile and stricter defaults. Sensitive inferred youth history must not silently become an adult psychographic profile.

No political microtargeting or vulnerability-targeted persuasion is admitted for children.

## Work/personal separation

Occupational research exposure must not be treated as personal endorsement. A future adapter that handles work accounts and personal accounts must keep their state and recommendation context separate by default.

## Data handling

- Keep raw output local by default.
- Do not commit real private telemetry, tokens, hostnames, usernames, personal identifiers, private endpoints, or sensitive user histories.
- Use synthetic fixtures in tests and documentation.
- Bound file size and retention before enabling continuous output.
- Treat registry export as an explicit reviewed summary step rather than a raw-log mirror.
- Preserve corrections and negative results instead of rewriting history.

## Safe harbor / degraded mode

When authority, connectivity, freshness, or policy is uncertain:

```text
FREEZE HIGH-IMPACT EFFECTS
KEEP READ-ONLY VERIFICATION IF SAFE
LABEL CACHE AGE / STALE STATE
PRESERVE USER EXIT
WRITE A RECONCILIATION RECEIPT
```

The system must never invent a current answer merely because the central backend is unavailable.

## Reporting

Do not include secrets, private telemetry, exploit payloads, or personal data in a public issue. Use GitHub private security reporting when available or contact the repository owner privately.

## Status

The current KETO reference analyzer is local and deterministic. Live source adapters, public platform automation and state-system integrations are not implemented. This policy is an admission boundary, not a security certification.
