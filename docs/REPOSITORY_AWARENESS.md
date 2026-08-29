# Repository Awareness Head

`repository-awareness` gives JANUS DemiHead an inspectable map of the repository portfolio owned by the configured GitHub account.

It is a **context layer**, not an authority layer.

```text
REPOSITORY_DISCOVERY
        |
        v
PORTFOLIO INVENTORY
        |
        +--> KETO capability discovery
        +--> CONVERGENCE analogue/synthesis routing
        +--> source/provenance inspection
        +--> human-visible repository map
        |
        v
NO AUTOMATIC WRITE AUTHORITY
```

## Why it exists

DemiHead should not reason about one repository as if it were isolated when relevant mechanisms may already exist elsewhere in the same JANUS portfolio.

The head therefore maintains:

- a committed snapshot of the public portfolio;
- an optional authenticated runtime inventory that can include private repositories;
- repository visibility, archive/fork state and default branch;
- a local-only cache for authenticated inventory;
- search over the current inventory for routing other heads.

Repository presence does not prove relevance, novelty, correctness, authorship or permission.

## Privacy boundary

`Demi_Head` is public. Private repository names or metadata must not be copied into committed files merely to make the portfolio complete.

The committed file:

```text
configs/repository_portfolio.public.json
```

contains public repositories only.

Authenticated discovery uses `GITHUB_TOKEN` first and `GH_TOKEN` second. Tokens are read from the environment and are never written to the inventory.

The complete authenticated inventory is stored locally at:

```text
.janus/repository_portfolio.local.json
```

and that path is gitignored.

## Usage

Read the best available inventory:

```bash
python tools/repository_awareness.py
```

Refresh. With no token this rebuilds from the committed public snapshot:

```bash
python tools/repository_awareness.py --refresh
```

Require a complete authenticated owner inventory:

```bash
GITHUB_TOKEN=... python tools/repository_awareness.py --refresh --require-authenticated
```

Search the inventory:

```bash
python tools/repository_awareness.py --find cosmos
python tools/repository_awareness.py --find ESP32
```

Machine-readable output:

```bash
python tools/repository_awareness.py --json
```

## Consumers

The configuration declares these intended consumers:

```text
KETO
CONVERGENCE
SOURCE-GRAPH
INDEPENDENCE
REVIEW
GUARDIAN
```

This does not mean every consumer is fully wired to the inventory yet. It establishes one canonical portfolio-awareness surface so later heads do not invent separate repository lists.

## Invariants

```text
REPOSITORY_AWARENESS_IS_CONTEXT_NOT_AUTHORITY
DISCOVERY_DOES_NOT_GRANT_WRITE_PERMISSION
PRIVATE_METADATA_STAYS_LOCAL_BY_DEFAULT
MISSING_REPOSITORY_METADATA_IS_UNKNOWN_NOT_FALSE
ARCHIVED_REPOSITORY_IS_VISIBLE_BUT_NOT_ASSUMED_CURRENT
FORK_ORIGIN_IS_PROVENANCE_NOT_OWNERSHIP_OF_IDEA
```

The intended Convergence route is:

```text
IDEA
 -> PROVENANCE FREEZE
 -> TOPA/SPIDER external analogue discovery
 -> REPOSITORY-AWARENESS internal portfolio discovery
 -> CONVERGENCE HEAD structural alignment
 -> THIRD-THING candidates
 -> FUNDAMENTUM falsification
 -> META REGISTRY receipt
```
