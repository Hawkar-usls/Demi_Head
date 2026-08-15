# Guardian Mesh in DemiHead

## Purpose

DemiHead is the integration head for the defensive/civic branch of JANUS. It composes bounded mechanisms from sibling projects into one inspectable flow without importing their domain-specific authority.

The primary object is a **CETUS case**: a claim, incident, post, message, screenshot description, banner, or source cluster submitted for inspection.

`KETO` is the composition/audit layer that decides which bounded mechanisms are needed for the case.

```text
CETUS CASE
   |
   v
CLAIM HEAD
   |
   v
SOURCE GRAPH HEAD ------> CORRECTION / TIME HEAD
   |                            |
   v                            v
INDEPENDENCE HEAD ------> DISAGREEMENT HEAD
   |                            |
   +-------------+--------------+
                 v
          GUARDIAN RESULT
                 |
                 v
          RELEASE CONTROL
```

## Constitutional boundary

The architecture is intentionally asymmetric:

```text
CAPABILITY MAY GROW
AUTHORITY DOES NOT GROW AUTOMATICALLY
```

Permanent laws:

```text
PROPOSAL != WORLD_EFFECT
FACE_COUNT != VOTING_POWER
SOURCE_COUNT != INDEPENDENT_ROOT_COUNT
WITNESS_COUNT != FAILURE_DOMAIN_COUNT
MODEL_OUTPUT != EVIDENCE
OFFICIAL_POSITION != EXCLUSIVE_OBJECTIVE_TRUTH
DISAGREEMENT != ERROR
UNRESOLVED != FAILURE
MORE_FACES != MORE_RIGHTS
```

The default external mass-effect budget is zero.

## Heads

### Observer Head

Inherited from the original DemiHead architecture. It observes allowlisted local telemetry, keeps stale/missing state explicit, and measures its own overhead.

Useful Guardian translation:

```text
CENTRAL_BACKEND_DOWN != INVENT_AN_ANSWER
STALE_SOURCE != CURRENT_SOURCE
NO_SOURCE != FALSE
OFFLINE != BLIND
```

### Claim Head

Normalizes the submitted statement without deciding truth. A complex message may later be decomposed into several claim objects, each preserving the original presentation lineage.

### Source Graph Head

Maintains two counts:

```text
presentation_count
independent_root_count
```

Ten reposts that declare the same root remain ten presentations and one root.

Root collapse is a provenance operation, not a semantic guess. When provenance is unknown, the root must remain unknown rather than being silently merged.

### Independence Head

A root becomes an independent witness only when the declared independence criteria are met. Merely being hosted on a different domain or account is not enough.

Future authenticated independence receipts may include:

- distinct source identity;
- distinct publication chain;
- distinct failure domain;
- independent observation path;
- temporal precedence;
- no known derivative edge.

If those facts are unavailable, the result is `UNKNOWN_INDEPENDENCE`.

### Chronology / Correction Head

Tracks:

- observed/published time;
- freshness state;
- superseded-by relation;
- correction descendants;
- stale cache status.

A true historical statement can become stale for a current operational question.

### Review / Disagreement Head

Preserves conflicting reviewers or evidence roots. It does not average away disagreement merely to produce a confident answer.

Possible terminal state:

```text
HOLD / CONTESTED / UNRESOLVED
```

This is a valid success state for the safety architecture.

### Guardian Result Head

Produces a bounded evidence-state summary. The reference prototype deliberately uses labels that describe **present source state**, not objective truth:

- `UNRESOLVED`
- `SUPPORTED_BY_PRESENT_SOURCES`
- `CONTRADICTED_BY_PRESENT_SOURCES`
- `CONTESTED`

A future verified domain-specific adapter may add more precise classes only through a versioned policy.

### Release Control Head

The end goal is not engagement. Once the case is sufficiently summarized, DemiHead should prefer a finite result and an exit path.

```text
VERIFY -> EXPLAIN -> ACT_IF_NEEDED -> RELEASE_CONTROL
```

Release control may recommend:

- stop rechecking unchanged derivative presentations;
- subscribe to a primary update source instead of many echoes;
- wait for a missing primary document;
- hand off a high-stakes unresolved case to a human reviewer;
- end the session when no new evidence is present.

## Face orchestration

DemiHead may later ask Janus_Genesis to select several internal Faces, for example:

```text
PROVENANCE
CHRONOS
OFFICIAL_SOURCE_CHECK
INDEPENDENT_CORROBORATION
RED_TEAM
UNCERTAINTY_KEEPER
ARMOR_RECOVERY
```

But internal plurality does not count as external corroboration.

```text
100 FACES AGREEING
!=
100 INDEPENDENT SOURCES
```

Face output remains a proposal until authority and effect gates are satisfied.

## Civic-service mode

A future civic deployment can provide one trusted entry point while keeping evidence plurality visible.

Required output separation:

```text
OFFICIAL_POSITION
INDEPENDENT_EVIDENCE
CONTRADICTIONS
UNKNOWN
ACTION_IF_NEEDED
```

Forbidden shortcuts:

- official source automatically becomes universal truth;
- model confidence becomes legal or political authority;
- disagreement becomes disloyalty;
- user vulnerability becomes a targeting variable;
- personalization changes factual status;
- many Faces satisfy a two-key human authorization rule.

## Wartime information mode

Guardian Mesh can support a manual `WAR_FEED_AUDIT` workflow without trying to control a person's politics.

The useful sequence is:

```text
SUBSCRIPTION AUDIT
-> REMOVE DEGRADED / DOOM / GRAPHIC / SCAM / BAIT SOURCES
-> PRESERVE ESSENTIAL OFFICIAL ALERTS
-> COLLAPSE ECHO ROOTS
-> RESTORE HUMAN SOURCE SELECTION
-> OPTIONAL NEUTRAL RECOVERY BRIDGE
-> RETURN TO SIGNAL HYGIENE
```

An anxiety-provoking safety alert is not removed merely because it is negative. Safety relevance and emotional valence are separate fields.

## Children and work profiles

Two account-separation rules are inherited from the Armor branch:

```text
WORK_EXPOSURE != PERSONAL_IDEOLOGY
CHILD_PROFILE != ADULT_DESTINY
```

Future youth-facing interfaces require stricter privacy, no covert persuasion, no political microtargeting, bounded retention, and a fresh-start/selective-inheritance transition when the user reaches adulthood.

## Doomsday firewall

The reference head cannot grow external authority merely by discovering more adapters or Faces.

```text
NO_COVERT_MASS_PERSUASION
NO_SELF_SPAWNING_PUBLIC_IDENTITIES
NO_AUTONOMOUS_ASTROTURF
NO_UNSOLICITED_PERSONALIZED_POLITICAL_OUTREACH
NO_OPTIMIZATION_ON_BELIEF_CHANGE
NO_PSYCHOLOGICAL_VULNERABILITY_TARGETING
NO_MODEL_WRITABLE_CONSTITUTION
AMBIGUOUS_EFFECT != RETRY_PERMISSION
```

If authority becomes uncertain, high-impact actions freeze while read-only verification and local exit controls remain available.

## Next validation gates

1. synthetic root-collapse tests;
2. stale/current tests;
3. support/contradiction disagreement tests;
4. language-invariance tests;
5. authenticated independence fixture;
6. read-only public-source adapter with frozen expected output;
7. human review and correction ledger;
8. external governance/security/privacy audit before any high-impact pilot.
