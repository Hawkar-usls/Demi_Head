# JANUS NOHAND Pair Protocol v1

Status: **feature candidate / not deployed**

This binds a NAS-side NOHAND reconciler to an analogous DemiHead-side advisor without turning Git messages into commands.

```text
NAS_NOHAND
  observe -> operational forecast -> OFFER
     |
     v
Git/Nexus append-only channel
     |
     v
DEMIHEAD_NOHAND
  validate -> predict usefulness/risk -> REQUEST/HOLD
     |
     v
NAS guard-of-guard -> copy -> verify -> RECEIPT
     |
     v
both sides calibrate on the observed action event
```

The reverse direction is symmetric: DemiHead offers a source-revision-bound Git object; NAS independently accepts or holds it.

## Existing JANUS lineage reused

The pair is an extension of existing DemiHead mechanisms:

- `tools/hemisphere_bridge.py` / `goldprompt_handshake.py`: parent Face and GoldPrompt constitution.
- `tools/nexus_habitat.py`: read-only routing, no direct cross-head mutation.
- `tools/nexus_local_transport.py`: authenticated bounded transport/replay semantics.
- `tools/nexus_replay_ledger.py`: restart-persistent replay control.
- `tools/nexus_guardian_ingress.py`: HOLD is preserved; no automatic escalation.
- `NOT_PREDICTION_*`: observation/selection/event-root discipline.

## Laws

```text
MESSAGE != COMMAND
OFFER != COPY
REQUEST != AUTHORITY
PREDICTION != TRUTH
PRESENTATION_COUNT != ACTION_EVENT_ROOT_COUNT
LEARNER_CALIBRATION != AUTHORITY_WEIGHT
LEARNER_CANNOT_BYPASS_GUARD
NO_DELETE
NO_MOVE
NO_RENAME
COPY_IS_NOT_CONSUMPTION
DIFFERENT_HASH -> LOCAL_POLICY + PREIMAGE_BACKUP OR HOLD
```

The learner uses operational forecasts only. It is calibrated against completed action-event roots, deduplicates repeated presentations of the same event, records selection-process roots, and exposes descriptive selection concentration. It never promotes a prediction into evidence or runtime permission.

## Pair handshake

1. `OFFER`: one side advertises `sha256 + size + immutable locator/provenance`; no bytes are consumed by the receiver merely because an offer exists.
2. Receiver independently predicts operational success/usefulness and returns `REQUEST_COPY`, `HOLD`, or `REJECT`.
3. Sender re-runs its local guard-of-guard before any copy.
4. File bytes move by copying only. Existing source stays in place.
5. Receiver verifies the exact SHA-256 and returns a bound `RECEIPT`.
6. Both sides may append one calibration observation for the unique `action_event_root`.

Repeated presentations of one action-event root must not become multiple calibration samples.

## Payload movement

Control messages are small append-only JSON. File bytes are not commands.

- DemiHead -> NAS: offer points at `repository + immutable source revision + path + SHA-256`.
- NAS -> DemiHead: NAS first offers metadata; only after DemiHead requests the object does NAS copy it to the dedicated exchange/Transfer Node and emit a receipt locator.
- Large objects route through Habitat Transfer Node rather than Git Contents API.

## Authority

`DEMIHEAD_NOHAND` is a bounded capability under parent `DEMIHEAD_ARBITER`, not an additional voting Face. `authority_weight=0`. The GoldPrompt 0.9.2 contract digest remains `3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8`.

`GITHUB_MAIN_CI_RUNTIME_HANDSHAKE != LIVE_NAS_RUNTIME_HANDSHAKE` remains in force. No merge, deployment, NAS write, or live-runtime proof is implied by this feature branch.
