# JANUS DemiHead — Event Unit and Selection Gate

## Why source-root collapse is not enough

A source artifact can contain several underlying observations, while several source artifacts can describe the same underlying event.

```text
PRESENTATION_COUNT != SOURCE_ROOT_COUNT
SOURCE_ROOT_COUNT != EVENT_ROOT_COUNT
```

Therefore Not-Prediction counting must keep at least three layers separate:

```text
presentation -> source/lineage root -> event root
```

A file lineage is not automatically one event, and a repeated coordinate across files is not automatically multiple events.

## Clock-selection problem

Clock observations are especially vulnerable to selection effects. If a person notices and records salient times such as repeated digits, mirrored digits or personally meaningful coordinates while ordinary clock views are not logged, then the recorded sample is not a random sample of minutes.

```text
RECORDED_CLOCKS != ALL_CLOCK_VIEW_OPPORTUNITIES
SALIENCE_TRIGGERED_SAMPLE != RANDOM_SAMPLE
```

Consequently, a naive probability calculation against all 1,440 minutes of a day is not admissible unless the opportunity set and logging rule were frozen in advance and all observations were captured.

## Lookup conditioning

Once a coordinate such as `21:27` is observed, looking up many sources with chapter/verse or other coordinates `21:27` creates dependent presentations selected by the observation itself.

```text
ONE OBSERVED KEY
  -> MANY SAME-KEY LOOKUPS
!=
MANY INDEPENDENT CONFIRMATIONS
```

These lookups may still carry personal or interpretive meaning, but they must not be counted as independent evidence for the original observation.

## Selection modes

The reference tool distinguishes:

- `UNCONDITIONED_OR_PREREGISTERED` — a frozen opportunity set with all observations logged;
- `UNKNOWN` — selection process not sufficiently documented;
- `POST_HOC_DISCOVERY` — candidate selected after looking through existing material;
- `SALIENCE_TRIGGERED` — observation recorded because it looked notable;
- `LOOKUP_CONDITIONED` — later material selected using a key discovered in the observation.

Higher selection risk does not make an observation false. It changes the admissible null model.

## Reference tool

```bash
python tools/not_prediction_event_unit.py examples/not_prediction_event_unit_manifest.json
```

The tool reports:

- event-root count;
- cases where source roots are only a fallback because event identity is unresolved;
- selection mode counts;
- whether a selection-matched null is required;
- whether naive uniform-frequency inference is forbidden.

## Claim ceiling

This gate does not decide whether an observation is meaningful, supernatural, prophetic, precognitive or causal. It only prevents file counts, source counts and selection-conditioned observations from being silently converted into event counts or probability claims.
