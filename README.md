<div align="center">

# JANUS DemiHead
### KETO / CETUS Guardian Mesh reference head

![Status](https://img.shields.io/badge/status-active%20prototype-2f81f7)
![Mode](https://img.shields.io/badge/default-read--only%20verification-8957e5)
![Authority](https://img.shields.io/badge/mass%20effect%20budget-0-critical)

`observe` · `collapse roots` · `verify provenance` · `preserve disagreement` · `release control`

</div>

> **DemiHead is the integration head for the JANUS Guardian Mesh / Armor of God civic-information branch.** It combines the repository's original local-first observer foundation with bounded claim decomposition, source-root collapse, evidence-state receipts, Face orchestration contracts, and fail-safe civic-service architecture.

## Mission

DemiHead is not a ministry of truth and not an engagement engine. Its target is narrower:

```text
INPUT
  -> CLAIM
  -> PRESENTATIONS
  -> SOURCE ROOTS
  -> CHRONOLOGY / FRESHNESS
  -> SUPPORT / CONTRADICTION / UNKNOWN
  -> BOUNDED RESULT
  -> HUMAN INSPECTION
  -> RELEASE CONTROL
```

The reference implementation must make it easier to inspect evidence without turning JANUS into a covert persuasion system.

```text
SOURCE_COUNT != INDEPENDENT_ROOT_COUNT
OFFICIAL_POSITION != EXCLUSIVE_OBJECTIVE_TRUTH
STALE != CURRENT
NO_SOURCE != FALSE
MODEL_OUTPUT != EVIDENCE
MORE_FACES != MORE_RIGHTS
```

## Why DemiHead

The repository already contained a useful lower layer: a read-only observer that converts allowlisted local process telemetry into normalized frames through freshness and budget gates. That design is preserved as **Observer Head** rather than discarded.

DemiHead now hosts several bounded heads over the same constitutional boundary:

| Head | Purpose | Default external effect |
| --- | --- | --- |
| `observer` | local telemetry / degraded-mode state | none |
| `claim` | normalize a submitted claim | none |
| `source-graph` | collapse derivative presentations to provenance roots | none |
| `independence` | count authenticated roots/failure domains separately | none |
| `review` | preserve disagreement / HOLD | none |
| `guardian` | produce a bounded evidence-state response | local output only |
| `release-control` | stop escalation when information need is satisfied | reduces activity |

External publication, outreach, platform posting, political targeting, identity creation and state action are **not** part of the reference head.

## KETO / CETUS model

`KETO` is the portfolio-audit / composition layer: it may discover useful mechanisms across JANUS projects, but discovery never grants authority.

`CETUS` is a bounded case object: one submitted incident, claim, message, banner, post or source cluster being inspected.

`KRAKEN_MODE` remains a post-ironic operator alias only.

```text
KETO_DISCOVERS_CAPABILITIES
KETO_DOES_NOT_INHERIT_AUTHORITY
```

Canonical design record:

- `janus-meta-registry/data/JANUS-GENESIS-GUARDIAN-MESH-KETO-CETUS-ECOSYSTEM-SWEEP-AND-CIVIC-RESILIENCE-v1.2.json`
- mirrored in `Janus_Genesis/docs/`

## First executable vertical slice

The repository now targets a small deterministic reference path:

```bash
python tools/keto_reference.py examples/case_echo_collapse.json
```

The tool does **not** browse the web and does not decide objective truth. It demonstrates the core accounting rules:

1. parse one case;
2. preserve every presentation;
3. collapse presentations by declared `root_id`;
4. keep stale/current state explicit;
5. separate official-position roots from independent roots;
6. preserve support and contradiction together;
7. emit `UNRESOLVED`, `SUPPORTED_BY_PRESENT_SOURCES`, `CONTRADICTED_BY_PRESENT_SOURCES`, or `CONTESTED`;
8. emit a release-control recommendation rather than another engagement loop.

A later live source adapter must earn admission through separate security, provenance, freshness and governance gates.

## Cross-repository composition

DemiHead intentionally composes **patterns**, not ambient privileges:

- **Janus_Genesis** — Face microcontrol, authority epochs, typed capability boundaries and receipts;
- **JANUS Meta Registry / OPIR / Connection** — semantic lineage, correction descendants, source-unit collapse and authenticated independence;
- **HRain / iNaiHR** — human-visible graph and inspectable semantic decomposition;
- **AIFC** — canonicalization, witness lifecycle, append-only evidence and fail-closed verification;
- **Fast-CAT-SHAiTan** — blinded human review and disagreement preservation;
- **Janus-Fundamentum** — falsification, negative-result preservation and claim ceilings;
- **janus-io / janus-io-public** — proof-of-observation and counterfactual incident review;
- **Janus-Cosmos** — anti-pseudoreplication and blind-gate discipline;
- **janus-distributed-ai-swarm** — stale visibility, local degraded mode and no-fake-sensor rules.

See [`docs/CROSS_REPO_LINEAGE.md`](docs/CROSS_REPO_LINEAGE.md) and [`docs/GUARDIAN_MESH.md`](docs/GUARDIAN_MESH.md).

## Civic-service direction

A future public-service deployment may expose user-invoked web/PWA/bot/SMS-bootstrap interfaces, but this repository does not claim connection to Ukrainian state systems or production readiness.

A civic deployment must preserve:

```text
OFFICIAL_POSITION || INDEPENDENT_EVIDENCE || CONTRADICTIONS || UNKNOWN
```

rather than collapsing everything into a state-issued boolean.

The citizen must be able to inspect sources, disagree, appeal, opt out, remove optional personalization context and leave the service.

## Doomsday firewall

DemiHead has a deliberately boring answer to the "what if the monster grows teeth?" problem:

```text
MASS_EFFECT_BUDGET_DEFAULT = 0
NO_COVERT_MASS_PERSUASION
NO_SELF_SPAWNING_PUBLIC_IDENTITIES
NO_AUTONOMOUS_ASTROTURF
NO_UNSOLICITED_PERSONALIZED_POLITICAL_OUTREACH
NO_OPTIMIZATION_ON_BELIEF_CHANGE
NO_PSYCHOLOGICAL_VULNERABILITY_TARGETING
NO_MODEL_WRITABLE_CONSTITUTION
AMBIGUOUS_EFFECT != RETRY_PERMISSION
```

Many Faces may review a proposal; they do not manufacture external authority.

## Repository map

```text
Demi_Head/
├── README.md
├── PROJECT_STATUS.json
├── SECURITY.md
├── docs/
│   ├── ARCHITECTURE.md
│   ├── GUARDIAN_MESH.md
│   ├── CROSS_REPO_LINEAGE.md
│   ├── GLOSSARY.md
│   └── ROADMAP.md
├── schemas/
│   ├── config.schema.json
│   ├── signal-frame.schema.json
│   ├── face-output.schema.json
│   └── keto-case.schema.json
├── configs/
│   ├── example.config.json
│   └── keto.example.json
├── examples/
│   └── case_echo_collapse.json
└── tools/
    ├── keto_reference.py
    └── validate_repository.py
```

## Current boundary

```text
MATURITY = ACTIVE_PROTOTYPE
LIVE_FACT_CHECKING = NOT_IMPLEMENTED
STATE_API_INTEGRATION = NOT_ESTABLISHED
PLATFORM_AUTOMATION = NOT_IMPLEMENTED
MASS_PUBLICATION = FORBIDDEN_BY_DEFAULT
COERCIVE_OR_COVERT_PERSUASION = FORBIDDEN
OBJECTIVE_TRUTH_FROM_MODEL_OUTPUT = FORBIDDEN
READ_ONLY_LOCAL_REFERENCE_PATH = IMPLEMENTATION_TARGET
```

Schema validity establishes structure, not truth. A hash establishes integrity, not truth. Multiple presentations establish repetition, not independence.

## Validation

```bash
python -m pip install -r requirements-dev.txt
python tools/validate_repository.py
python -m unittest discover -s tests -v
```

## License

Apache License 2.0. See [`LICENSE`](LICENSE).

**Canonical motto:** *Let the mother of monsters birth checks, not masters.*
