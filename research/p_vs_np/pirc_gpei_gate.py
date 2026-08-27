#!/usr/bin/env python3
"""Fail-closed finite-trace auditor for the JANUS PIRC/GPEI research contract.

This module checks a concrete trace against a frozen input-relative polynomial
budget. Passing a finite trace is NEVER a universal asymptotic theorem and
never changes P_VS_NP from OPEN.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Any

P_VS_NP = "OPEN"

REQUIRED_STAGE_FIELDS = (
    "state_bytes",
    "step_work",
    "certificate_bytes",
    "verifier_work",
    "normalization_microsteps",
    "exact_transition",
    "contextual_soundness",
    "tractable_interface",
    "hidden_oracle_free",
)


@dataclass(frozen=True)
class EnvelopeSpec:
    original_input_size: int
    state_exponent: int
    work_exponent: int
    certificate_exponent: int
    verifier_exponent: int
    microstep_exponent: int
    macrostep_exponent: int

    def validate(self) -> None:
        if self.original_input_size < 1:
            raise ValueError("original_input_size must be >= 1")
        for name, value in self.__dict__.items():
            if name == "original_input_size":
                continue
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")


def _cap(n: int, exponent: int) -> int:
    """Exact input-relative cap N^exponent; no floating-point comparison."""
    return pow(n, exponent)


def _nonnegative_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def audit_trace(spec: EnvelopeSpec, trace: Iterable[Mapping[str, Any]]) -> dict:
    """Audit one already-materialized finite trace.

    The result can falsify a proposed budget on the trace. It cannot prove
    universal preservation over all CNFs.
    """
    try:
        spec.validate()
    except (TypeError, ValueError) as exc:
        return {
            "kind": "PIRC_GPEI_FINITE_TRACE_AUDIT",
            "status": "SAFE_ERROR_INVALID_TRACE",
            "failures": ["INVALID_ENVELOPE_SPEC"],
            "detail": str(exc),
            "P_VS_NP": P_VS_NP,
        }

    stages = list(trace)
    failures: list[dict[str, Any]] = []
    n = spec.original_input_size

    caps = {
        "state_bytes": _cap(n, spec.state_exponent),
        "step_work": _cap(n, spec.work_exponent),
        "certificate_bytes": _cap(n, spec.certificate_exponent),
        "verifier_work": _cap(n, spec.verifier_exponent),
        "normalization_microsteps": _cap(n, spec.microstep_exponent),
        "macrosteps": _cap(n, spec.macrostep_exponent),
    }

    if len(stages) > caps["macrosteps"]:
        failures.append({
            "stage": None,
            "gate": "MACROSTEP_ENVELOPE",
            "observed": len(stages),
            "cap": caps["macrosteps"],
        })

    for index, stage in enumerate(stages):
        missing = [field for field in REQUIRED_STAGE_FIELDS if field not in stage]
        if missing:
            failures.append({
                "stage": index,
                "gate": "MISSING_STAGE_FIELDS",
                "missing": missing,
            })
            continue

        for field in (
            "state_bytes",
            "step_work",
            "certificate_bytes",
            "verifier_work",
            "normalization_microsteps",
        ):
            value = stage[field]
            if not _nonnegative_int(value):
                failures.append({
                    "stage": index,
                    "gate": "INVALID_LEDGER_VALUE",
                    "field": field,
                    "observed": value,
                })
                continue
            if value > caps[field]:
                failures.append({
                    "stage": index,
                    "gate": f"{field.upper()}_ENVELOPE",
                    "observed": value,
                    "cap": caps[field],
                })

        for field, gate in (
            ("exact_transition", "EXACTNESS_GATE"),
            ("contextual_soundness", "CONTEXTUAL_SOUNDNESS_GATE"),
            ("tractable_interface", "TRACTABLE_INTERFACE_GATE"),
            ("hidden_oracle_free", "HIDDEN_ORACLE_GATE"),
        ):
            if stage[field] is not True:
                failures.append({"stage": index, "gate": gate})

    status = (
        "OPEN_ENVELOPE_VIOLATION"
        if failures
        else "FINITE_TRACE_ENVELOPE_PASS_NOT_UNIVERSAL_THEOREM"
    )
    return {
        "kind": "PIRC_GPEI_FINITE_TRACE_AUDIT",
        "status": status,
        "input_size": n,
        "stages": len(stages),
        "caps": caps,
        "failures": failures,
        "universal_claim": False,
        "universal_GPEI_preservation": "OPEN",
        "P_VS_NP": P_VS_NP,
    }


def universal_obligations() -> tuple[str, ...]:
    return (
        "PROVE_INITIAL_ENVELOPE_FOR_ARBITRARY_CNF",
        "PROVE_REACHABLE_ENVELOPE_PRESERVATION_FOR_FROZEN_SCHEDULE",
        "PROVE_POLYNOMIAL_DISCOVERY_IN_ORIGINAL_N",
        "PROVE_POLYNOMIAL_NORMALIZATION_MICROSTEPS_IN_ORIGINAL_N",
        "PROVE_POLYNOMIAL_MACROSTEP_COUNT_IN_ORIGINAL_N",
        "PROVE_POLYNOMIAL_TERMINAL_QUERY_IN_ORIGINAL_N",
        "PROVE_FULL_RESOURCE_LEDGER_NO_HIDDEN_DEBT",
    )


def self_test() -> None:
    spec = EnvelopeSpec(
        original_input_size=4,
        state_exponent=2,
        work_exponent=3,
        certificate_exponent=2,
        verifier_exponent=2,
        microstep_exponent=2,
        macrostep_exponent=1,
    )
    good_stage = {
        "state_bytes": 16,
        "step_work": 64,
        "certificate_bytes": 8,
        "verifier_work": 12,
        "normalization_microsteps": 4,
        "exact_transition": True,
        "contextual_soundness": True,
        "tractable_interface": True,
        "hidden_oracle_free": True,
    }
    passed = audit_trace(spec, [good_stage, good_stage])
    assert passed["status"] == "FINITE_TRACE_ENVELOPE_PASS_NOT_UNIVERSAL_THEOREM"
    assert passed["P_VS_NP"] == "OPEN"

    bad_stage = dict(good_stage)
    bad_stage["state_bytes"] = 17
    failed = audit_trace(spec, [bad_stage])
    assert failed["status"] == "OPEN_ENVELOPE_VIOLATION"
    assert any(f["gate"] == "STATE_BYTES_ENVELOPE" for f in failed["failures"])

    locally_poly_but_globally_bad = []
    size = 4
    for _ in range(3):
        size = size * size
        locally_poly_but_globally_bad.append({**good_stage, "state_bytes": size})
    exploded = audit_trace(spec, locally_poly_but_globally_bad)
    assert exploded["status"] == "OPEN_ENVELOPE_VIOLATION"


if __name__ == "__main__":
    self_test()
    print("PIRC_GPEI_FINITE_TRACE_SELF_TEST=PASS")
    print("UNIVERSAL_GPEI_PRESERVATION=OPEN")
    print("P_VS_NP=OPEN")
