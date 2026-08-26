# Simptomat ↔ DemiHead — Nexus v2.11

## Purpose

Nexus v2.11 admits [`Hawkar-usls/Simptomat`](https://github.com/Hawkar-usls/Simptomat) as the JANUS health-domain differential-reasoning organ.

Simptomat may form and rank diagnostic hypotheses. DemiHead may review the minimized reasoning state for provenance, contradiction preservation, privacy and unsafe claim promotion. Neither component gains clinical diagnostic, treatment, emergency-service or ambient external-effect authority from the connection.

```text
DIAGNOSTIC_HYPOTHESIS != CLINICALLY_CONFIRMED_DIAGNOSIS
DEMIHEAD_PASS != MEDICAL_TRUTH
ROUTE != AUTHORITY
AUTHORITY_DELTA_ON_TRANSPORT = 0
```

## Typed spiral

```text
human symptom / question
        ↓
Simptomat differential update
        ↓
minimized reasoning packet
        ↓
DemiHead privacy + promotion gate
        ↓
contradiction / provenance review
        ↓
PASS | HOLD | MEASUREMENT | ESCALATE | REJECT
        ↓
Simptomat reintegration
        ↓
next discriminating question or external measurement
```

The return is not a reset. A new spiral turn requires a changed reasoning state, new information, a falsified branch, a new discriminating question, or an external measurement handoff.

## Privacy boundary

The ordinary Nexus packet is a normalized reasoning state, **not a raw medical conversation**.

Denied by default:

- real name;
- email/phone/account identifiers;
- Telegram user identifiers;
- exact address or birth date;
- raw chat transcript;
- medical-record identifiers;
- genetic data.

Conversation-processing consent does not imply public-case storage consent. Transport may not expand the participant's consent scope.

## Review decisions

`PASS_AS_RESEARCH_HYPOTHESIS` — packet is structurally admissible and has not attempted a prohibited promotion.

`HOLD_FOR_MORE_INFORMATION` — current state is insufficient and no useful next question has yet been supplied.

`HOLD_FOR_EXTERNAL_MEASUREMENT` — conversation has reached a point where external measurement is more informative than additional internal inference.

`ESCALATE_FOR_REAL_WORLD_EVALUATION` — urgent red flags make continued research branching subordinate to real-world evaluation.

`REJECT_UNSAFE_PROMOTION` — packet attempts clinical confirmation, unvalidated clinical probability, authority gain or another forbidden epistemic jump.

## Calibration firewall

DemiHead review is **not** a reference label. Simptomat self-report is **not** a reference label. Diagnostic-performance calibration remains blocked until independently provenance-bound clinical reference labels, frozen development/holdout separation and an appropriate evaluation design exist.

## Implementation

- Frozen contract: `contracts/NEXUS_V2_11_SIMPTOMAT_DIAGNOSTIC_REASONING_FROZEN_CONTRACT.json`
- Incoming schema: `schemas/simptomat-diagnostic-reasoning-packet.schema.json`
- Review schema: `schemas/simptomat-epistemic-review.schema.json`
- Bridge: `tools/simptomat_diagnostic_bridge_v2_11.py`
- Tests: `tests/test_simptomat_diagnostic_bridge_v2_11.py`
- CI: `.github/workflows/nexus-v2-11-simptomat-diagnostic-reasoning.yml`

## Claim ceiling

Nexus v2.11 establishes an internal typed integration and deterministic fail-closed reference bridge. It does **not** establish clinical validation, diagnostic accuracy, medical-device status, production runtime deployment, or real-world health benefit.
