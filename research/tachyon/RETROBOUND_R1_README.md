# TACHYON / RETROBOUND R1 — opt-in integration

**Status:** R1 PORT VALIDATED IN GITHUB ACTIONS; 16/16 UNIT TESTS, GOLDEN REPLAY AND TWO PAIRED SYNTHETIC CONTROLS PASS; PHYSICAL SCIENCE HOLD; DRAFT PR NOT MERGED.

This repository is the active JANUS DemiHead TACHYON research home.
RETROBOUND is a **separate classical mathematical lane**, not an upgrade to
existing R5F causal-memory results, not a TACHYON neural model retraining,
and not a physical time machine.

## Entry points

- Original frozen R5F source: tools/tachyon_r5f_causal_memory_audit.py
- New offline RETROBOUND implementation: tools/tachyon_retrobound_r1.py
- Opt-in experiment routing: tools/tachyon_experiment_router.py
- Frozen protocol for future testing: research/tachyon/retrobound_r1_integration_protocol_20261123.json
- Prepared but unexecuted tests: tests/test_tachyon_retrobound_r1.py

The router does not activate experiments unless explicitly instructed:

    python -m tools.tachyon_experiment_router describe

**For the NEXT testing stage only:**

    python -m unittest discover -s tests -p 'test_tachyon_retrobound_r1.py' -v
    python -m tools.tachyon_experiment_router run --lane retrobound-r1 --steps 8 --rho 0.85 --eta 0.9 --trials 40000 --seed 20261123

The prior R5F procedure remains available, independently:

    python -m tools.tachyon_experiment_router run --lane r5f-causal-replay

**Validation was executed only after the pre-test protocol was committed.**
CI checks are engineering and mathematical, not an independent physical test. 

## Three non-interchangeable evidence layers

| Layer | What can be calculated | Physical authority |
|---|---|---|
| Mathematical two-boundary conditioning | P(x[0:T] \| b), alpha/beta messages and E[b*x[0]]=eta*rho^T | None |
| Operational observable | Distribution of an explicitly allowed *early* record under future settings | Does not validate retrocausality on its own; requires independent time order |
| Independently validated physical influence | Pre-frozen early record predicts a genuinely independently generated later target beyond controlled forward alternatives | Not available in R1; requires prospective external trial |

R1 early public observable is **ONLY** the transition parity sequence
y[t]=x[t]*x[t+1]. It is invariant under global spin sign reversal. This
makes no-signalling for that readout an *exact consequence of choosing
that readout*, not evidence that a real instrument has this property.

The hidden spin x[0] does correlate with b in the postconditioned model.
But R1's offline solver already knows b before creating the path; x[0]
cannot be promoted to a pre-existing physical reading. Its tempting
guess-accuracy is not a usable future predictor.

## Required alternative models

1. Two-boundary global solver: samples after b is known.
2. Forward causal null: draws the path first and b only afterward.
3. Forward postselection: accepts/rejects paths based on terminal b.

The third alternative is exactly distribution-equivalent to the first.
Therefore **any R1 statistic compatible with both provides no
discriminatory evidence between retrocausal interpretation and ordinary
conditioning**. This negative result is an important part of the design.

## Prospective science gate, later

The next experiment must preregister its target physical prediction before
looking at outcomes, hash every early record and timestamp it with an
independent witness, generate late entropy **only after the freeze**,
record every trial including misses/aborts, and compare against honest
forward-causal, leakage and postselection controls. Observers must be
physically independent of any later choice, not just assigned different
software seeds. A difference needs replication and an explicit
identified mechanism before any retrocausality claim.

Rule #1 about **subjective time and memory** remains separate from
physical chronology; no psychological report can validate this lane.
The Janus-Cosmos/SETI and R5F scientific HOLD states are unchanged.

## Source lineage and preservation

Original RETROBOUND R1 Python SHA256:
690e6d8fd4ca21f0b2a3cc1784ae1d265ce08c6817624efc9cbbab1a7157c3b8

Original R1 package SHA256:
5dd340abe60a7ed05fb24078598684869e6a7392053584498301d2db5e83f9ba

Existing R5F code Git blob (kept unchanged):
ea3ebbbd14594291adcde4f403a7e040d65f76a3

These identities bind methodology; they do NOT authenticate the original
simulated conclusions as physically verified. No production weights,
sensors, human data, GitHub Actions schedules, quantum hardware, or
autonomous external actions are modified.

## R1 validation receipt (2026-11-23)

The source-preserving port was compared against an independently rerun
standalone original R1 frozen numeric fixture, with no parameter retuning.

- [Push Actions run](https://github.com/Hawkar-usls/Demi_Head/actions/runs/45081949821) **SUCCESS**, 16/16 unit tests
- [Pull-request Actions run](https://github.com/Hawkar-usls/Demi_Head/actions/runs/45081955109) **SUCCESS**
- Nine original-port self checks: **9/9 PASS**
- Common-choice paired default: **11/11 checks PASS**, T=8, rho=.85, eta=.9, 40,000 accepted histories per arm
- Common-choice paired alternative: **11/11 checks PASS**, T=5, rho=.65, eta=.7, 10,000 per arm
- Paired default expected hidden/boundary correlation **0.24524147**:
  conditional **0.2402**, forward-null **-0.00615**, postselected **0.2430**
- Default early public parity deltas: **+0.000307**, **-0.004462** and **+0.001770**
- Paired conditional minus postselection hidden correlation difference **-0.0028**,
  standard error **0.00686**; the conventional control was not rejected
- Postselection cost: **1.891875 forward draws per accepted trajectory**,
  analytic expectation **1.9**
- The chosen early parity record has **exact TV distance 0 by model symmetry**,
  which is not a universal prohibition of signalling for other observables.

Full machine-readable result and immutable source/run/artifact identities:
[retrobound_r1_validation_result_20261123.json](retrobound_r1_validation_result_20261123.json).

**Do not treat passing R1 as physical retrocausality, a future-information
channel, proof of two-boundary ontology, or authorization to alter production
models or the frozen R5F track.** The next research gate is prospective,
independent late physical entropy after externally frozen early observations.
