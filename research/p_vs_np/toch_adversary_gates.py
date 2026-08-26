#!/usr/bin/env python3
"""Named adversary gates harvested from TOCH.

These checks are intentionally conservative. They classify a candidate
representation theorem contract; they do not prove P vs NP.
"""
from __future__ import annotations

P_VS_NP = "OPEN"

REQUIRED_FIELDS = {
    "source_fingerprint",
    "representation_kind",
    "exact_equivalence",
    "witness_map",
    "discovery_bound",
    "representation_bound",
    "verification_bound",
    "transition_closure_bound",
    "hidden_oracle_free",
}


def audit(candidate: dict) -> dict:
    missing = sorted(REQUIRED_FIELDS - set(candidate))
    failures = []
    if missing:
        failures.append("MISSING_CONTRACT_FIELDS")
    if candidate.get("hidden_oracle_free") is not True:
        failures.append("HIDDEN_ORACLE_GATE")
    if candidate.get("exact_equivalence") is not True:
        failures.append("EXACTNESS_GATE")
    if not candidate.get("witness_map"):
        failures.append("REDUCTION_SIZE_WITNESS_GATE")

    # We accept symbolic polynomial-bound declarations only as research-contract
    # fields here. A later theorem verifier must prove them; this layer must never
    # silently treat a string such as O(N^2) as a theorem.
    for key, gate in (
        ("discovery_bound", "CERTIFICATE_DISCOVERY_GATE"),
        ("representation_bound", "EXTENDED_FORMULATION_SIZE_GATE"),
        ("verification_bound", "VERIFICATION_COST_GATE"),
        ("transition_closure_bound", "NESTED_OPERATIONAL_CLOSURE_GATE"),
    ):
        if not candidate.get(key):
            failures.append(gate)

    return {
        "kind": "TOCH_ADVERSARY_AUDIT",
        "status": "OPEN" if failures else "CONTRACT_COMPLETE_NOT_THEOREM",
        "failures": sorted(set(failures)),
        "missing": missing,
        "P_VS_NP": P_VS_NP,
    }


def self_test() -> None:
    assert audit({})["status"] == "OPEN"
    complete = {
        "source_fingerprint": "deadbeef",
        "representation_kind": "EXACT_QUOTIENT",
        "exact_equivalence": True,
        "witness_map": "replayable",
        "discovery_bound": "UNPROVED_SYMBOLIC_BOUND",
        "representation_bound": "UNPROVED_SYMBOLIC_BOUND",
        "verification_bound": "UNPROVED_SYMBOLIC_BOUND",
        "transition_closure_bound": "UNPROVED_SYMBOLIC_BOUND",
        "hidden_oracle_free": True,
    }
    out = audit(complete)
    assert out["status"] == "CONTRACT_COMPLETE_NOT_THEOREM"
    assert out["P_VS_NP"] == "OPEN"


if __name__ == "__main__":
    self_test()
    print("TOCH_ADVERSARY_GATES_SELF_TEST=PASS")
    print("P_VS_NP=OPEN")
