# JANUS Nexus v2.1 — SkinGPT observation edge

Status: **candidate under frozen contract**.

This layer inherits promoted Nexus v2 and adds one physical-sensory source:

```text
SKINGPT -> OBSERVER : TELEMETRY_SAMPLE
```

It does **not** route raw sensor frames directly to Guardian, Release Control or Registry.

## Source baseline

- repository: `Hawkar-usls/SkinGPT`
- source baseline SHA: `1efd61a17bb24f63b8d92788acec9909bdda76c8`
- frame schema: `skingpt.frame.v0.3`
- schema blob SHA: `d1e36072e917ba32ffdeba8552064d3a526d00b4`

The source repository is private. This design does not assume that a DemiHead GitHub Actions token has ambient read authority over another private repository. Source identity/schema are frozen from authenticated source reads; the consumer CI validates the frozen normalization and routing layer without embedding cross-repository credentials.

## Normalization boundary

A valid SkinGPT v0.3 frame is converted to `janus.demihead.skingpt_telemetry_sample.v1`.

The normalized sample:

- binds the canonical frame SHA-256;
- binds the exact source repository/SHA/schema blob;
- hashes `device_id + boot_id` into a provenance identity instead of forwarding them raw;
- never forwards `source_ip`;
- preserves `system_operational` and `experiment_baseline_valid` as distinct states;
- preserves rule-based event output as heuristic semantics;
- labels `confidence` as internal rule confidence, not a calibrated posterior;
- labels `severity_score` as relative heuristic severity, not damage/injury/failure/safety probability;
- preserves missing measurements as missing/unknown;
- does not claim traceable physical calibration.

## Permanent laws

```text
RAW_SENSOR_FRAME != OBSERVATION_SIGNAL
TELEMETRY_SAMPLE != TRUTH
HEURISTIC_SCORE != PROBABILITY
SYSTEM_OPERATIONAL != EXPERIMENT_BASELINE_VALID
HASH_INTEGRITY != SENSOR_TRUTH
ROUTE_RECEIPT != DELIVERY
AUTHORITY_DELTA = 0
MASS_EFFECT_BUDGET_DELTA = 0
```

A later Observer stage may transform an admitted telemetry sample into an `OBSERVATION_SIGNAL` under its own contract. This route alone does not do that transformation.
