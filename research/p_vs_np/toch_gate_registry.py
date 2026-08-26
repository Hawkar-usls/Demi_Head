#!/usr/bin/env python3
"""Fail-closed registry for predecessor-derived JANUS research gates.

This module does not solve SAT or P vs NP. It only validates that a proposed
historical seed has been translated into an exact, auditable gate contract
before DemiHead is allowed to experiment with it.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable

P_VS_NP = "OPEN"

REQUIRED_OBLIGATIONS = (
    "exact_semantics",
    "explicit_model",
    "polynomial_discovery_ledger",
    "polynomial_state_ledger",
    "polynomial_certificate_ledger",
    "polynomial_verification_ledger",
    "independent_replay",
    "no_hidden_oracle",
    "fail_closed",
)

KNOWN_GATES = {
    "NASH_SHORTCUT_COMPLETENESS_GATE",
    "CERTIFICATE_DISCOVERY_GATE",
    "EXACT_CONTRACTION_CONGRUENCE_GATE",
    "REDUCTION_SIZE_WITNESS_GATE",
    "RELATIVIZATION_GATE",
    "SCHAEFER_MIXED_LANGUAGE_GATE",
    "EXTENDED_FORMULATION_SIZE_GATE",
}

@dataclass(frozen=True)
class GateContract:
    gate_id: str
    source_id: str
    obligations: tuple[str, ...]
    theorem_scope: str = "LOCAL_RESEARCH_GATE"


def validate_contract(contract: GateContract) -> dict:
    missing = sorted(set(REQUIRED_OBLIGATIONS) - set(contract.obligations))
    unknown = contract.gate_id not in KNOWN_GATES
    admitted = not missing and not unknown and contract.theorem_scope != "P_VS_NP_RESOLUTION"
    return {
        "kind": "TOCH_GATE_CONTRACT_VALIDATION",
        "gate_id": contract.gate_id,
        "source_id": contract.source_id,
        "admitted_for_experiment": admitted,
        "missing_obligations": missing,
        "unknown_gate": unknown,
        "P_VS_NP": P_VS_NP,
    }


def self_test() -> None:
    good = GateContract(
        gate_id="NASH_SHORTCUT_COMPLETENESS_GATE",
        source_id="TOCH-NASH-1955",
        obligations=REQUIRED_OBLIGATIONS,
    )
    assert validate_contract(good)["admitted_for_experiment"] is True

    bad = GateContract(
        gate_id="NASH_SHORTCUT_COMPLETENESS_GATE",
        source_id="TOCH-NASH-1955",
        obligations=("exact_semantics",),
    )
    result = validate_contract(bad)
    assert result["admitted_for_experiment"] is False
    assert result["P_VS_NP"] == "OPEN"


if __name__ == "__main__":
    self_test()
    print("TOCH_GATE_REGISTRY_SELF_TEST=PASS")
    print("P_VS_NP=OPEN")
