# DemiHead Architecture

## Objective

DemiHead converts low-cost, read-only observations of existing local processes into structured signals. The runtime must remain independently measurable, bounded, and removable without changing the observed application.

The architecture separates observation from interpretation and interpretation from action:

```text
source adapter
  -> raw sample
  -> observation window
  -> derived metrics
  -> normalized signals
  -> quality and budget gates
  -> face projections
  -> local sinks
```

## Design invariants

```text
OBSERVED_PROCESS_BEHAVIOR = UNCHANGED_BY_DEFAULT
READ_ONLY_SOURCE = REQUIRED
SOURCE_ALLOWLIST = REQUIRED
MISSING_DATA = UNKNOWN
STALE_DATA = NOT_ACTIONABLE
FACE_OUTPUT = DERIVED_FROM_SHARED_FRAME
OBSERVER_COST = MEASURED
BUDGET_EXCEEDED = DEGRADE_OR_STOP
EXTERNAL_SIDE_EFFECT = EXPLICITLY_OUT_OF_SCOPE_FOR_V0_1
```

An adapter that cannot satisfy these invariants does not enter the default runtime.

## Components

### 1. Source adapter

A source adapter reads one documented telemetry surface. The first planned adapter uses ordinary Windows process counters for an opt-in process match.

Permitted v0.1 classes:

- process identity needed for an allowlist match;
- CPU time counters;
- memory working-set counters;
- cumulative read/write operation and byte counters;
- process lifecycle state;
- monotonic sampling time.

Excluded v0.1 classes:

- process memory contents;
- command-line secrets or environment variables;
- application payloads;
- keystrokes, screen content, clipboard content, or credentials;
- packet interception or TLS bypass;
- code injection, hooks, impersonation, or undocumented control channels.

Each adapter reports capability and permission failures as data-quality states. It must not escalate privileges automatically.

### 2. Observation window

Most operating-system counters are cumulative. DemiHead therefore stores a small bounded window and derives rates from differences between monotonic samples.

Rules:

- the first sample establishes a baseline and emits no rate;
- counter reset, PID reuse, or clock reversal invalidates the affected delta;
- a gap larger than the configured freshness limit produces a stale frame;
- unavailable metrics remain `null` or absent, never synthetic zeroes;
- the window has an explicit memory limit.

### 3. Signal normalizer

The normalizer maps heterogeneous metrics into comparable, bounded signals. Candidate methods include exponentially weighted baselines, robust deviation scores, and clipped ratios. The exact method must be versioned in the emitted frame.

Every signal carries:

- value and unit;
- confidence in `[0, 1]`;
- freshness;
- quality status;
- source metric names;
- normalizer identifier and version.

The first implementation should prefer simple deterministic transforms over a learned model. A learned model can be evaluated later against the same frozen input/output contract.

### 4. Safety and budget gate

The gate decides whether a frame is usable and whether DemiHead itself may continue at the current sampling pressure.

Inputs include:

- signal freshness and quality;
- adapter error rate;
- observed host pressure;
- DemiHead CPU, memory, I/O, and loop-lag measurements;
- configured hard limits.

Possible outcomes:

```text
PASS       emit the frame normally
DEGRADED   emit with explicit quality flags
HOLD       pause expensive work and retain only a heartbeat
STOP       close the adapter and require a new start condition
```

No gate result may be represented as a successful zero-valued observation.

### 5. Faces

A face is a pure or side-effect-bounded projection from a shared signal frame. It does not get privileged access to the observed process.

Initial candidate faces:

| Face | Purpose | Allowed effect |
| --- | --- | --- |
| `mirror` | expose normalized state | local output only |
| `steward` | recommend or apply DemiHead pacing | DemiHead runtime only |
| `registry` | preserve bounded evidence records | configured local file only |

Face names and the final set remain open design decisions. All faces must declare their effect scope in the output envelope.

### 6. Sinks

The first sinks should be local and replaceable:

- JSON Lines for replay and inspection;
- console output for development;
- optional bounded summaries for the JANUS Meta Registry.

Network sinks, dashboards, and cross-device routing are later gates. They require explicit authentication, privacy, backpressure, and failure-domain design.

## Data contracts

The initial machine contracts are:

- [`../schemas/config.schema.json`](../schemas/config.schema.json)
- [`../schemas/signal-frame.schema.json`](../schemas/signal-frame.schema.json)
- [`../schemas/face-output.schema.json`](../schemas/face-output.schema.json)

Schema validity establishes structure only. It does not establish that a source was truthful, a signal was useful, or an efficiency claim is correct.

## Resource accounting

"No added load" is treated as a target budget, not a literal claim. The observer must account for its own cost using at least:

- process CPU time per wall-clock interval;
- resident memory;
- bytes written and read by DemiHead;
- sample-loop lag;
- dropped or delayed samples.

The benchmark must compare an idle baseline, observed-process-only baseline, and observed-process-plus-DemiHead run under a fixed protocol. Results may be positive, null, negative, or inconclusive.

## Failure behavior

DemiHead fails closed when:

- the target cannot be identified unambiguously;
- permission changes invalidate the adapter contract;
- timestamps or counters cannot produce a valid delta;
- the observer budget is exceeded repeatedly;
- output cannot be written without unbounded buffering;
- a face requests an undeclared effect scope.

Failing closed means reducing or stopping DemiHead's work. It does not mean terminating or modifying the observed process.

## Extension rule

A new adapter or face must include:

1. a documented public or OS-supported source surface;
2. a privacy and permission statement;
3. deterministic fixtures for counter resets, stale data, and missing data;
4. an overhead measurement path;
5. explicit effect scope;
6. schema-valid example output;
7. a negative-result and rollback path.
