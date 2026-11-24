# DemiHead Synesthetic Associative Core

The DemiHead synesthetic core is the associative half of a two-core research architecture:

```text
Cousteau
MEASUREMENT
  -> immutable measurement fingerprint
  -> sensory passport
  -> research handshake packet
                  |
                  v
DemiHead
  verify packet + provenance
  -> preserve measurement fingerprint bit-exact
  -> LEFT_HRAIN structural context
  -> RIGHT_INAIHR associative context
  -> disagreement-preserving associative memory
  -> review priority / HOLD
  -> human inspection
```

It is deliberately **not** a second measurement engine. Cousteau owns the measurement-derived fingerprint. DemiHead is allowed to remember, compare, bind context, preserve disagreement and surface neighbors. It is not allowed to recompute the fingerprint from story labels or convert mnemonic similarity into evidence.

## Shared handshake

Both repositories carry the same canonical contract:

`JANUS_SYNAESTHETIC_RESEARCH_HANDSHAKE v1`

Canonical SHA-256:

`3aec527be027fc280fc9a8ace1255c9a3a7da73fc884d9b4856694a1f1530306`

A packet is rejected if the contract id/version/hash, producer role, packet digest, epistemic state, fingerprint digests or 16-dimensional embedding do not replay exactly.

## Bicameral context

DemiHead keeps two contextual views separate:

- `LEFT_HRAIN` — structural context;
- `RIGHT_INAIHR` — associative context.

Both remain inspectable and provenance-bound. They do not write into the upstream measurement fingerprint. Story-bearing fields such as `hypothesis`, `verdict`, `H0/H1/H2`, `target`, `candidate`, `pyramid`, `prediction` and `interpretation` may be retained for audit but are excluded from similarity scoring.

## Comparison states

`IDENTICAL_MEASUREMENT_MEMORY` means two receipts carry the same measurement fingerprint. This is an identity/retrieval statement, not a scientific conclusion.

`MNEMONIC_NEIGHBOR_ONLY` means different measurement fingerprints are close in the sensory embedding. It may raise review priority only.

`PROVENANCE_CONFLICT_HOLD` is stronger operationally but weaker scientifically: the same event/source identity arrived with a different measurement fingerprint. DemiHead refuses to merge the records and preserves both sides for inspection.

`BLOCKED_OR_INCOMPARABLE` means a usable measurement comparison is unavailable. No missing association is synthesized.

## Epistemic firewall

The Cousteau packet carries `OBSERVED / UNKNOWN / STALE / CONTAMINATED / BLOCKED` state and a retrieval-quality score. DemiHead uses that score only to discount review priority. It does not infer truth confidence.

```text
RETRIEVAL_QUALITY != TRUTH_CONFIDENCE
ASSOCIATION != EVIDENCE
MEMORY != TRUTH
SENSORY_MATCH != SCIENTIFIC_CONVERGENCE
```

## Unison receipt

`build_unison_receipt()` binds the exact Cousteau packet SHA to the DemiHead receipt SHA and verifies:

- shared handshake contract;
- exact upstream packet replay;
- exact local receipt replay;
- bit-exact measurement fingerprint preservation;
- disagreement preservation;
- no evidence admission;
- no scientific convergence claim;
- `authority_delta = 0` and `mass_effect_budget_delta = 0`.

The unison receipt is therefore a **transport/integrity certificate**, not a scientific certificate.

## Memory index

`AssociativeMemoryIndex` is a deterministic reference index for research and testing. It supports idempotent insertion and top-k retrieval. A same-event/same-source fingerprint mutation creates `PROVENANCE_CONFLICT_HOLD` and is not stored as if it were a normal duplicate.

The reference index has no persistence, publication or evidence-admission authority.

## Validation

Local validation:

```bash
python tools/demihead_synesthetic_associative_core.py
python -m unittest -v tests.test_demihead_synesthetic_associative_core
```

CI additionally checks out the Cousteau research-core candidate from `Hawkar-usls/Janus-Cosmos`, verifies the same contract hash, generates a real cross-repository handshake packet, consumes it in DemiHead and requires a passing `UNISON_RECEIPT`.

The cross-repository negative control also sends a Hannah-profile payload without raw provenance. Cousteau must return `BLOCKED`; DemiHead must return `BLOCKED_HOLD`; no associative tags may be fabricated.
