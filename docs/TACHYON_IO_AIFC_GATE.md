# Tachyon × Ocean × Proof-of-Observation × AIFC

This is a read-only scientific evidence gate, not a production model change.

## Upstream placements
- Observation discipline: Hawkar-usls/janus-io-public, exact commit 41b1c9b6af6629a551d2814aa69c5dfcac042620, origin record docs/proof-of-observation-origin-record.json.
- Future-information evidence requirements: Hawkar-usls/AIFC, exact commit 86bf957815911658edad330d5948e1bea2ea59b1, docs/EVIDENCE_GRADES.md.
- Ocean producer: Hawkar-usls/Janus-Demiurge, frozen 009B GitHub run 42878578752, source artifact 13793425503, target date November 12, 2026.
- Tachyon consumer: Hawkar-usls/Demi_Head, tachyon/observation_aifc_gate.py.

## Automatic Actions
.github/workflows/tachyon-io-aifc-gate.yml runs on matching pull requests and after relevant main-branch pushes; workflow_dispatch is available for bounded manual verification. It does not introduce a second periodic search or modify the scheduled 009B future scoring jobs. The workflow validates exact external Git SHAs, runs fail-closed offline tests, fetches original GitHub run and artifact metadata again, verifies the source-bound timestamp and digest, then emits artifacts/tachyon-io-aifc/eligibility.json with a SHA-256 receipt.

## Claim ceilings
- Proof-of-Observation outcome: OBSERVATION_ONLY_PARTIAL_CHAIN. Integrity of a recorded GitHub artifact is not full proof of the underlying source truth or independent observer consensus.
- AIFC outcome: NOT_ADMITTED. This is an eligibility screen, not the full AIFC verifier. In the original Ocean trial, an independently certified pre-candidate trial slot, complete trial ledger, witness quorum, full conditioning view, evidenced historywise entropy bound, multiplicity audit and verified causal DAG were not established at the required AIFC level. This is not evidence that the future prediction failed; it means the strong scientific claim cannot yet be admitted.
- TOPA: HYPOTHESIS_ONLY. TOPA's earlier canonical-provider bridge remains separate.
- Direct training gradients, rewriting early predictions, changing source workflows, automatic merge/deployment, evidence promotion and retrocausality claims: all forbidden.

No direct integration with mining, hashing workloads, NAS containers, private receiver data, or source repositories was added. No proof-of-work claims or throughput advantages are inferred from the public IO record.

## Reproduction
Run the offline tests from Demi_Head repository root:

    python -m unittest discover -s tests -p test_tachyon_observation_aifc_gate.py -v

For the online check, GitHub Actions performs two read-only API requests against the exact Ocean 009B run and refuses mismatched metadata. The outcome is a new research receipt only; the existing Ocean delayed-scoring lane remains authoritative for future labels and does not consume this receipt as a learning signal.

## Activation boundary
Changes are part of draft PR #68 and are not yet merged into main. Successful CI is necessary but not sufficient for scientific admission.
