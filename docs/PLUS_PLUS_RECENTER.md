# +/+ Recenter Head

The `+/+` recenter head is a bounded Armor Recovery / Release Control helper for DemiHead.

It is intentionally **not** a truth engine, sentiment classifier, psychological profile, user score, or engagement optimizer.

## Two constructive Faces

```text
WITNESS_PLUS (+) -> receive meaning, preserve context
GUARD_PLUS   (+) -> check, widen options, release control
```

There is no built-in negative Face.

A transient pressure state may rise when an upstream frozen policy or a human fixture explicitly supplies symbolic pressure flags. The local module does not infer those flags from natural language.

## Word-rhyme recenter

```text
HEAR -> CHECK -> WIDEN -> RELEASE
СЛЫШУ -> СВЕРЯЮ -> РАСШИРЯЮ -> ОТПУСКАЮ
```

The sequence has no user-visible numeric counter. Its purpose is to restore process, not to force a positive conclusion.

```text
RECENTERING RESTORES PROCESS, NOT A REQUIRED CONCLUSION
NEGATIVE_TOPIC != NEGATIVE_USER
PRESSURE_STATE != MORAL_SCORE
PRESSURE_CHANGES_ROUTING_NOT_AUTHORITY
```

## Where it sits in DemiHead

```text
CETUS / CURRENT TASK
        |
        v
  normal evidence heads
        |
        +----------------------+
        |                      |
        v                      v
 ARMOR RECOVERY          RELEASE CONTROL
        \                      /
         \                    /
          +-- +/+ RECENTER ---+
```

The recenter head must not mutate:

- claims;
- source roots;
- source independence;
- chronology;
- evidence state;
- truth claim ceiling;
- external authority;
- mass-effect budget.

System-origin pressure is treated symmetrically with user-origin pressure. DemiHead must not blame the user for pressure created by DemiHead itself.

## Reference implementation

```bash
python tools/plus_plus_recenter.py --self-test
```

CSV trace evaluation accepts:

```csv
source,pressure_flags
user,choice_narrowing
system,engagement_pressure
user,repetition_without_new_evidence
```

Run it with:

```bash
python tools/plus_plus_recenter.py --input-csv examples/plus_plus_recenter_trace.csv --output /tmp/plus-plus.json
```

The accepted symbolic flags are documented in the integration record. Unknown flags are ignored rather than promoted into pressure.

## Canonical records

- [`JANUS-DEMIHEAD-PLUS-PLUS-RECENTER-INTEGRATION-v1.0.json`](JANUS-DEMIHEAD-PLUS-PLUS-RECENTER-INTEGRATION-v1.0.json)
- Canonical Armor candidate: `Hawkar-usls/janus-meta-registry:data/JANUS-ARMOR-OF-GOD-PLUS-PLUS-RHYME-RECENTER-v1.0.json`

## Claim ceiling

Development tests can establish deterministic software behavior only. They do not establish real-world alignment effectiveness, prove manipulation by a user, or authorize psychological/ideological scoring.

Promotion remains blocked pending a frozen holdout that measures false recentering and missed recentering while preserving evidence provenance, difficult facts, disagreement, opt-out and user choice.
