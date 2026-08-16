# Correction Propagation and Language Invariance

These two gates were extracted from the KETO/CETUS architecture because they protect evidence semantics rather than presentation convenience.

They are deliberately separate from the JANUS First Portal. The Portal may carry a destination and requested presentation language, but DemiHead owns the evidence contracts.

```text
PORTAL_CARRIES_ROUTE_METADATA
DEMIHEAD_OWNS_EVIDENCE_SEMANTICS
```

## Correction Propagator

Reference implementation: [`../tools/correction_propagator.py`](../tools/correction_propagator.py)

The gate receives explicit root revisions, explicit presentation-to-root bindings and explicit correction records. It does not discover corrections on the web and does not infer hidden lineage.

Example:

```text
root-A
  r1 --corr-1--> r2 --corr-2--> r3 (current)

presentation P1 bound to r1
-> AFFECTED_BY_CORRECTION
-> correction_chain = [corr-1, corr-2]

presentation P2 bound to r3
-> CURRENT

presentation P3 without known root binding
-> UNKNOWN_LINEAGE
```

Hard laws:

```text
CORRECTION != DELETION
SUPERSESSION_PRESERVES_HISTORY
KNOWN_DESCENDANT_OF_SUPERSEDED_REVISION_MUST_BE_MARKED
CURRENT_REVISION_DESCENDANT_MUST_NOT_BE_MARKED_STALE_BY_CORRECTION
UNKNOWN_DESCENDANT_REMAINS_UNKNOWN
CORRECTION_RECORD != TRUTH_PROOF
```

The output embeds the original roots, presentations and correction records under `history`. A correction receipt therefore annotates lineage rather than erasing it.

The reference gate rejects ambiguous correction branches, duplicate IDs, correction cycles, corrections that reference unknown roots and chains that do not terminate at the root's declared current revision.

## Language Invariance Gate

Reference implementation: [`../tools/language_invariance.py`](../tools/language_invariance.py)

The gate compares `uk`, `ru` and `en` render receipts against a single canonical semantic envelope.

Protected fields are:

- `evidence_state`
- `uncertainty_class`
- `urgency_class`
- `user_rights`
- `official_position_present`
- `independent_evidence_present`
- `contradictions_present`
- `unknown_fields_present`
- `release_control`

Presentation prose is intentionally **not** compared as truth. Ukrainian, Russian and English titles/explanations may differ in wording and tone while the protected semantics remain identical.

```text
LANGUAGE_CHANGE != EVIDENCE_STATUS_CHANGE
LANGUAGE_CHANGE != UNCERTAINTY_CHANGE
LANGUAGE_CHANGE != URGENCY_CHANGE
LANGUAGE_CHANGE != USER_RIGHTS_CHANGE
TRANSLATION_STYLE != AUTHORITY
MISSING_LANGUAGE_RECEIPT != PASS
```

`user_rights` is treated as a set-like field, so harmless ordering differences do not create a false failure. Missing rights, however, do fail the gate.

## Why both gates belong before live civic adapters

A source-root correction that does not reach known derivatives can leave stale claims looking current.

A multilingual renderer that can silently strengthen certainty, urgency or user restrictions can create different civic behavior from the same evidence object.

These are provenance/semantics failures, not UI polish issues. Both therefore belong below any future public web, bot, PWA or Portal adapter.

## What the gates do not establish

Correction propagation does not prove that all real-world descendants were discovered, that a correction is objectively true, or that a source acted in good faith.

Language invariance does not prove literary translation quality or the absence of every possible framing bias. It establishes only equality of the declared protected semantic fields in the submitted frozen receipts.

Both gates keep:

```text
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```
