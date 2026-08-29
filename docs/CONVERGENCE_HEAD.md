# CONVERGENCE HEAD

`convergence` is the JANUS DemiHead head for independent-idea comparison, analogue decomposition and third-thing synthesis.

It does not assume that novelty means isolation from prior work. Its job is to distinguish provenance, overlap, independent convergence, borrowing, recombination and emergent synthesis without collapsing them into one label.

## Principle

```text
IDEAS_DO_NOT_NEED_TO_BE_CREATED_FROM_VACUUM
PROVENANCE != SHAME
OVERLAP != PLAGIARISM
INDEPENDENT_CONVERGENCE != COPYING
RECOMBINATION_CAN_CREATE_NEW_STRUCTURE
SYNTHESIS_CLAIM_REQUIRES_EXPLICIT_DELTA
```

The philosophical inspiration includes Mark Twain's well-known reflections on unconscious literary borrowing and the scarcity of wholly original thoughts. The implementation deliberately avoids treating literary rhetoric as an empirical law: provenance and independence are evaluated from evidence, not from aphorisms.

## Internal route

```text
IDEA
 -> PROVENANCE FREEZE
 -> REPOSITORY AWARENESS (internal portfolio analogues)
 -> KETO capability candidates
 -> TOPA/SPIDER (external analogues)
 -> STRUCTURAL ALIGNMENT
 -> CLASSIFY RELATION
 -> THIRD-THING CANDIDATES
 -> FUNDAMENTUM FALSIFICATION
 -> META REGISTRY RECEIPT
```

## Relation classes

```text
PRIOR_ART
INDEPENDENT_CONVERGENCE
PARTIAL_CONVERGENCE
ORTHOGONAL_COMPLEMENT
DERIVATIVE_WITH_PROVENANCE
THIRD_THING
UNKNOWN
```

`THIRD_THING` is reserved for a candidate whose proposed properties are not merely the union of the two input feature lists. It is a synthesis hypothesis, not an automatic novelty claim.

## Internal portfolio first

Before searching externally, DemiHead should inspect the best available Repository Awareness inventory and ask whether another repository already contains a mechanism, representation, constraint, test discipline, interface or algorithm useful to the current idea.

This is not ownership transfer and not write authority. It is cognitive reuse across the portfolio.

```text
REPOSITORY_PRESENT != RELEVANT
REPOSITORY_RELEVANT != NOVEL
REPOSITORY_KNOWN != WRITE_ALLOWED
SAME_OWNER != SAME_PROVENANCE
```

## KETO handoff

KETO receives repository-awareness candidates as a bounded capability-discovery surface. It may rank or group mechanisms for inspection, but discovery does not authorize mutation of source repositories.

The canonical output of this stage is a proposal set:

```text
candidate_repository
candidate_mechanism
why_relevant
provenance_state
confidence
read_only_reference
```

## Third-thing rule

For candidate systems `A` and `B`:

```text
shared_core = intersection(A, B)
unique_A = A - shared_core
unique_B = B - shared_core
interaction_delta = properties(synthesis(A,B)) - union(properties(A), properties(B))
```

A `THIRD_THING` proposal requires a non-empty, inspectable `interaction_delta`.

```text
A + B IS NOT AUTOMATICALLY X
X REQUIRES EXPLICIT INTERACTION DELTA
```

## Claim ceiling

Convergence output may say:

```text
independent convergence appears plausible
structural overlap is present
an internal analogue exists
this synthesis introduces the following explicit delta
```

It may not say, without evidence:

```text
this idea is absolutely original
this proves no prior art exists
this proves plagiarism
this proves legal ownership
```

The head is therefore a synthesis engine with provenance discipline, not a novelty oracle.
