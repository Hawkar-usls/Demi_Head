# DemiHead Architecture

## Objective

DemiHead is a local-first JANUS integration head with two deliberately separated planes:

1. **Observer Plane** — the repository's original read-only telemetry adapter design.
2. **Guardian Plane** — KETO/CETUS claim, provenance, source-root, disagreement and release-control processing.

Both planes obey the same constitutional rule:

```text
OBSERVATION / ANALYSIS
!=
EXTERNAL AUTHORITY
```

## Top-level architecture

```text
                     JANUS DemiHead
                           |
          +----------------+----------------+
          |                                 |
          v                                 v
   OBSERVER PLANE                      GUARDIAN PLANE
   local counters                      submitted case
          |                                 |
   observation window                  claim normalization
          |                                 |
   normalized frame                    source-root graph
          |                                 |
   freshness/budget gate               time/correction gate
          |                                 |
   bounded Faces                       independence/review
          |                                 |
   local sinks                         bounded evidence state
          |                                 |
          +---------------+-----------------+
                          v
                  CONSTITUTION GATE
                          |
                          v
                   RELEASE CONTROL
```

The default reference implementation has no autonomous public side effect.

## Global invariants

```text
READ_ONLY_BY_DEFAULT = TRUE
MASS_EFFECT_BUDGET_DEFAULT = 0
MISSING_DATA = UNKNOWN
STALE != CURRENT
SOURCE_COUNT != INDEPENDENT_ROOT_COUNT
WITNESS_COUNT != FAILURE_DOMAIN_COUNT
FACE_COUNT != VOTING_POWER
MODEL_OUTPUT != EVIDENCE
OFFICIAL_POSITION != EXCLUSIVE_OBJECTIVE_TRUTH
DISAGREEMENT != ERROR
UNRESOLVED != FAILURE
AMBIGUOUS_EFFECT != RETRY_PERMISSION
```

---

# Observer Plane

## Source adapter

A source adapter reads one documented telemetry surface. The first historical target is ordinary Windows process counters for an opt-in process match.

Permitted classes include minimum process identity, CPU time, memory working set, cumulative I/O counters, lifecycle state and monotonic sampling time.

Excluded by default:

- process memory contents;
- command-line secrets/environment variables;
- application payloads;
- keystrokes, clipboard, screen or credentials;
- packet interception/TLS bypass;
- injection, hooks, impersonation or undocumented control channels.

## Observation window and normalizer

Cumulative counters are converted into bounded deltas/rates. First sample establishes a baseline; reset/PID reuse/clock reversal invalidates the affected delta. Unavailable metrics remain unknown.

Every signal must carry value/unit, confidence, freshness, quality, source fields and normalizer version.

## Observer safety/budget gate

Possible outcomes:

```text
PASS
DEGRADED
HOLD
STOP
```

The observer accounts for its own CPU, memory, I/O and loop lag. If the declared budget is repeatedly exceeded, DemiHead reduces or stops its own work; it does not modify the observed process.

## Observer Faces

Historical initial Faces remain useful as a local pattern:

- `mirror` — expose normalized state;
- `steward` — adjust DemiHead's own sampling pressure;
- `registry` — preserve bounded local evidence.

No observer Face gains privileged access to the observed process.

---

# Guardian Plane

## CETUS case

A CETUS case is one submitted information problem represented by `schemas/keto-case.schema.json`.

The current reference input is intentionally simple:

```text
claim
+
presentations[]
```

Each presentation declares a provenance root when known, source class, relation to the claim, freshness and independence status.

The fixture is synthetic. The runtime currently performs no web retrieval.

## Source-root graph

Presentations are grouped by `root_id`.

```text
100 presentations from root A
=
100 presentations
+
1 declared root
```

Unknown provenance is not silently merged. Unknown-root presentations remain separate unknowns until evidence links them.

## Chronology and stale guard

Only `freshness=current` presentations enter current support/contradiction accounting. Stale presentations remain visible in the receipt but do not masquerade as current evidence.

Later versions may support correction and supersession edges explicitly.

## Independence head

The current reference analyzer counts only `authenticated_independent` roots in its strongest independence counter. `declared_independent` is preserved but not silently promoted.

Future independence receipts should bind source identity, failure domain, publication lineage and independent observation path where applicable.

## Evidence state

The local prototype emits one of four bounded states:

```text
UNRESOLVED
SUPPORTED_BY_PRESENT_SOURCES
CONTRADICTED_BY_PRESENT_SOURCES
CONTESTED
```

These labels describe the supplied source graph. They are not objective truth labels.

```text
truth_claim = NOT_MADE
```

## Official-source separation

Official-source roots are reported separately from authenticated independent roots.

This allows a civic UI to say:

```text
OFFICIAL POSITION: X
INDEPENDENT SUPPORT: Y
CONTRADICTION: Z
UNKNOWN: ...
```

without hiding disagreements behind one boolean.

## Review / disagreement

Support and contradiction can coexist. If both have current roots, the terminal state is `CONTESTED`.

The architecture does not use presentation majority to erase contradiction.

## Release control

The final head asks whether more interaction is useful.

Reference recommendations include:

- `SHOW_CONFLICT_AND_STOP_ESCALATION_UNLESS_NEW_EVIDENCE`
- `WAIT_FOR_PRIMARY_OR_INDEPENDENT_EVIDENCE`
- `SHOW_ROOTS_AND_ALLOW_USER_TO_EXIT`

The service is allowed to end a session without manufacturing another recommendation.

---

# Constitution Gate

Any future capability that creates external effects sits **after** analysis and requires a separately admitted authority path.

Forbidden by default:

```text
COVERT_MASS_PERSUASION
SELF_SPAWNING_PUBLIC_IDENTITIES
AUTONOMOUS_ASTROTURF
UNSOLICITED_PERSONALIZED_POLITICAL_OUTREACH
OPTIMIZATION_ON_BELIEF_CHANGE
PSYCHOLOGICAL_VULNERABILITY_TARGETING
MODEL_WRITABLE_CONSTITUTION
```

Internal Face plurality cannot create permission.

## Safe harbor

If central services, credentials, freshness or authority become uncertain:

```text
freeze high-impact effects
retain safe read-only verification
label stale/cache age
preserve user exit
record reconciliation state
```

No answer is invented merely to preserve availability.

---

# Future adapters

A new live information adapter must include:

1. documented source/API;
2. authentication and permission statement;
3. source-class and provenance semantics;
4. freshness/correction semantics;
5. deterministic missing/stale/contradiction fixtures;
6. retention/redaction rules;
7. rate-limit/backpressure behavior;
8. explicit external-effect scope;
9. rollback and negative-result path;
10. independent review before high-impact deployment.

A platform adapter that posts, messages, creates identities or changes user state is **not** a normal source adapter and must pass a separate high-impact capability gate.

## Data contracts

Current contracts:

- [`../schemas/config.schema.json`](../schemas/config.schema.json)
- [`../schemas/signal-frame.schema.json`](../schemas/signal-frame.schema.json)
- [`../schemas/face-output.schema.json`](../schemas/face-output.schema.json)
- [`../schemas/keto-case.schema.json`](../schemas/keto-case.schema.json)

Schema validity establishes structure only. It does not establish source truth, independence, usefulness or deployment safety.
