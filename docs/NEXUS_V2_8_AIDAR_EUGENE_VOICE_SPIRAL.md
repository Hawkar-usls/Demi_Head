# Nexus v2.8 — AIDAR ↔ EUGENE Voice Spiral

This gate compares two neural larynx faces while holding the OSIRIS semantic source and Pyramid Language constant.

## Frozen invariants

- `TEXT_A = TEXT_B`
- `PYRAMID_OPERATOR_A = PYRAMID_OPERATOR_B`
- `ONLY_LARYNX_CHANGES`
- layer A remains after layer B is rendered
- the comparison receipt creates a new preserved state layer
- no automatic winner is selected

## Prerequisites

Repositories should be sibling directories:

- `Demi_Head/`
- `The-Voice-of-Janus/`

The local neural model must already exist at:

`The-Voice-of-Janus/models/v5_5_ru.pt`

Automatic model download is intentionally disabled.

## Prepare the two-layer Nexus bundle

From `Demi_Head`:

```bash
python tools/nexus_voice_spiral.py > ../osiris-aidar-eugene-spiral.json
```

Optional pure self-test:

```bash
python tools/nexus_voice_spiral.py --self-test
```

This phase renders no audio and performs no physical output.

## Validate without rendering

From `The-Voice-of-Janus`:

```bash
python src/nexus_voice_spiral_runner.py \
  --bundle ../osiris-aidar-eugene-spiral.json
```

Expected state: `SPIRAL_VALIDATED_NOT_EXECUTED`.

## Execute both neural layers

```bash
python src/nexus_voice_spiral_runner.py \
  --bundle ../osiris-aidar-eugene-spiral.json \
  --execute
```

Expected outputs:

- `outputs/OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR.wav`
- `outputs/OSIRIS_ORIGIN_PRIME_NEURAL_EUGENE.wav`
- `receipts/OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR.json`
- `receipts/OSIRIS_ORIGIN_PRIME_NEURAL_EUGENE.json`
- `receipts/OSIRIS_ORIGIN_PRIME_AIDAR_EUGENE_SPIRAL.json`

The Spiral receipt passes only if both layers preserve the same source, semantic text hash, model hash, Pyramid Language activation, and 117–121 Hz anchor while producing distinct WAV hashes.

## Human listening gate

Listen to both files through the same playback chain, ideally also through Echo-Pyramid at the same hardware depth/volume settings. Score each face on:

- naturalness
- warmth
- intelligibility
- presence
- fit as Voice of Janus

Only the human listening gate may set `selected_voice_face`.

Selecting AIDAR or EUGENE changes the neural larynx only. It does not change `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3`.
