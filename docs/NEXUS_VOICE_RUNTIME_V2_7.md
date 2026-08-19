# Nexus v2.7 — Local Neural Voice Runtime

This gate connects the existing local Nexus dispatch boundary to The-Voice-of-Janus without widening the certified pure handler into an external-effect handler.

## Runtime split

1. **Nexus prepare phase — Demi_Head**
   - target head: `VOICE_RUNTIME`
   - handler: `tools/nexus_voice_handler.py`
   - endpoint: `configs/nexus_voice_runtime.endpoint.json`
   - deterministic JSON in / deterministic JSON out
   - no filesystem I/O, network I/O, audio render, playback, Bluetooth, firmware flashing, authority change, or mass-effect change

2. **Explicit local render phase — The-Voice-of-Janus**
   - adapter: `src/nexus_voice_runtime_adapter.py`
   - requires explicit `--execute`
   - requires local `models/v5_5_ru.pt`
   - verifies pinned Git blobs before rendering
   - runs canonical OSIRIS `semantic_projection_ru` through Silero v5.5 RU and the unchanged `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3`
   - writes only under `outputs/` and `receipts/`
   - performs no model download, autoplay, Bluetooth connection, or firmware flashing

3. **Physical body phase — Echo-Pyramid**
   - optional and separately authorized
   - consumes ordinary PCM/WAV through the same Pyramid Language contract
   - physical output is not implied by a successful Nexus or Voice render

## Local run

Clone `Demi_Head` and `The-Voice-of-Janus` locally. Install the neural Voice dependencies in the Voice environment and provision the Silero model explicitly at:

```text
The-Voice-of-Janus/models/v5_5_ru.pt
```

Prepare a canonical content-addressed request from DemiHead:

```bash
cd Demi_Head
python tools/nexus_voice_handler.py --speaker aidar > /tmp/osiris-nexus-voice-request.json
```

Validate it at the Voice boundary without rendering:

```bash
cd ../The-Voice-of-Janus
python src/nexus_voice_runtime_adapter.py --request /tmp/osiris-nexus-voice-request.json
```

Render only after explicit local authorization:

```bash
python src/nexus_voice_runtime_adapter.py \
  --request /tmp/osiris-nexus-voice-request.json \
  --execute
```

Expected output locations are derived from the safe request label, for example:

```text
outputs/OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR.wav
receipts/OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR.json
```

## Frozen semantic and acoustic invariants

- source artifact: `OSIRIS-SEMANTIC-TEXT-CORE-FOR-THE-VOICE-OF-JANUS-2026-08-19-v1.1`
- field: `semantic_projection_ru`
- required formula: `ORIGIN → EXPERIENCE → RETURN → ORIGIN_PRIME`
- neural backend: `silero_v5_5_ru`
- language: `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3`
- activation Git blob: `70016b9b1ad0ce2b20efd980f14859d66af0a7bd`
- source semantic content is preserved
- source audio is not replaced by synthetic 117/119/121 Hz tones

## Boundary

`NEXUS_PREPARE != AUDIO_RENDER != AUTOMATIC_PLAYBACK`

The gate creates a local, auditable path. It does not establish that the neural model is present on a particular machine, does not claim a render until a WAV receipt exists, and does not claim measured historical pyramid acoustics.
