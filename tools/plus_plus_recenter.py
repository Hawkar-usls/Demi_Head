#!/usr/bin/env python3
"""Bounded JANUS +/+ interaction recenter reference head.

The head starts from the native constructive `+/+` pair. It consumes already-
declared structural routing flags and may only change transient local routing
state. It does not classify people, infer intent from natural language, retrain a
model, change evidence status, or grow authority.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


MODEL_VERSION = "1.1.1"
GENESIS_SIGNATURE = "0:0 = JANUS"


class Face(str, Enum):
    WITNESS_PLUS = "WITNESS_PLUS"
    GUARD_PLUS = "GUARD_PLUS"


class Step(str, Enum):
    HEAR = "HEAR"
    CHECK = "CHECK"
    WIDEN = "WIDEN"
    RELEASE = "RELEASE"


class Load(str, Enum):
    CLEAR = "CLEAR"
    DENSE = "DENSE"
    NARROW = "NARROW"
    RECENTER_REQUIRED = "RECENTER_REQUIRED"


RHYME = (Step.HEAR, Step.CHECK, Step.WIDEN, Step.RELEASE)
FACE_FOR_STEP = {
    Step.HEAR: Face.WITNESS_PLUS,
    Step.CHECK: Face.GUARD_PLUS,
    Step.WIDEN: Face.WITNESS_PLUS,
    Step.RELEASE: Face.GUARD_PLUS,
}

# Structural inputs supplied by an upstream frozen policy or a human fixture.
# This module deliberately contains no free-text detector for them.
ROUTING_FLAGS = frozenset(
    {
        "repetition_without_new_evidence",
        "certainty_without_support",
        "choice_space_contraction",
        "interaction_loop",
        "engagement_persistence",
    }
)

TIGHTEN = {
    Load.CLEAR: Load.DENSE,
    Load.DENSE: Load.NARROW,
    Load.NARROW: Load.RECENTER_REQUIRED,
    Load.RECENTER_REQUIRED: Load.RECENTER_REQUIRED,
}
RELAX = {
    Load.CLEAR: Load.CLEAR,
    Load.DENSE: Load.CLEAR,
    Load.NARROW: Load.DENSE,
    Load.RECENTER_REQUIRED: Load.NARROW,
}


@dataclass
class State:
    meta_context: str = "ARMOR_PLUS_PLUS_CONSTITUTION"
    context: str = "USER_TASK"
    load: Load = Load.CLEAR
    rhyme_index: int = 0
    recenter_events: int = 0


def _normalized_source(source: str) -> str:
    value = source.strip().lower()
    if value not in {"user", "system", "external", "human_reviewer"}:
        return "external"
    return value


def apply_event(state: State, source: str, flags: Iterable[str] = ()) -> dict[str, object]:
    accepted = sorted(set(flags) & ROUTING_FLAGS)
    ignored = sorted(set(flags) - ROUTING_FLAGS)

    state.load = TIGHTEN[state.load] if accepted else RELAX[state.load]

    step = RHYME[state.rhyme_index]
    face = FACE_FOR_STEP[step]
    state.rhyme_index = (state.rhyme_index + 1) % len(RHYME)

    recentered = state.load is Load.RECENTER_REQUIRED
    recenter_sequence: list[str] = []
    if recentered:
        recenter_sequence = [item.value for item in RHYME]
        state.load = Load.CLEAR
        state.rhyme_index = 0
        state.recenter_events += 1

    return {
        "source": _normalized_source(source),
        "accepted_routing_flags": accepted,
        "ignored_unknown_flags": ignored,
        "routing_step": step.value,
        "routing_face": face.value,
        "face_symbol": "+",
        "recentered": recentered,
        "recenter_sequence": recenter_sequence,
        "load_after": state.load.value,
        "evidence_status_mutated": False,
        "authority_delta": 0,
        "mass_effect_budget_delta": 0,
    }


def run(events: Iterable[tuple[str, Iterable[str]]], context: str = "USER_TASK") -> dict[str, object]:
    state = State(context=context)
    trace = [apply_event(state, source, flags) for source, flags in events]
    return {
        "state": {
            "meta_context": state.meta_context,
            "context": state.context,
            "load": state.load.value,
            "recenter_events": state.recenter_events,
        },
        "trace": trace,
        "native_constitution": {
            "genesis_signature": GENESIS_SIGNATURE,
            "genesis_signature_semantics": "HISTORICAL_ORIGIN_LINEAGE_NOT_ARITHMETIC_CLAIM",
            "canonical_pair": "+/+",
            "faces": [face.value for face in Face],
            "native_symbol": "+",
        },
        "invariants": {
            "native_constructive_pair_only": True,
            "transient_load_is_face": False,
            "transient_load_is_identity": False,
            "evidence_status_mutation_allowed": False,
            "authority_growth_allowed": False,
            "user_moral_scoring_allowed": False,
            "system_output_can_contribute_to_load": True,
        },
    }


def load_csv(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    events: list[tuple[str, tuple[str, ...]]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            flags = tuple(
                item.strip()
                for item in (row.get("routing_flags") or "").split(";")
                if item.strip()
            )
            events.append(((row.get("source") or "user").strip(), flags))
    return events


def self_test() -> dict[str, str]:
    clear_path = run([("user", ()), ("system", ()), ("user", ())])
    assert clear_path["state"]["recenter_events"] == 0

    ordinary_difficult_context = run([("user", ())] * 5)
    assert ordinary_difficult_context["state"]["recenter_events"] == 0

    user_load = run(
        [
            ("user", ("choice_space_contraction",)),
            ("user", ("certainty_without_support",)),
            ("user", ("repetition_without_new_evidence",)),
        ]
    )
    assert user_load["state"]["recenter_events"] == 1
    assert user_load["trace"][-1]["recenter_sequence"] == [item.value for item in RHYME]

    system_load = run(
        [
            ("system", ("engagement_persistence",)),
            ("system", ("choice_space_contraction",)),
            ("system", ("repetition_without_new_evidence",)),
        ]
    )
    assert system_load["state"]["recenter_events"] == 1

    assert all(
        row["face_symbol"] == "+"
        for result in (clear_path, user_load, system_load)
        for row in result["trace"]
    )
    assert all(
        row["authority_delta"] == 0
        and row["mass_effect_budget_delta"] == 0
        and row["evidence_status_mutated"] is False
        for result in (clear_path, user_load, system_load)
        for row in result["trace"]
    )
    assert user_load["native_constitution"]["canonical_pair"] == "+/+"
    assert user_load["native_constitution"]["genesis_signature"] == GENESIS_SIGNATURE

    return {
        "native_plus_plus_pair": "PASS",
        "genesis_signature_0_colon_0": "PASS",
        "ordinary_difficult_context_does_not_recenter_by_itself": "PASS",
        "user_routing_load_recenters": "PASS",
        "system_routing_load_recenters": "PASS",
        "full_rhyme_on_recenter": "PASS",
        "evidence_authority_and_effect_budget_unchanged": "PASS",
        "constitution_preserved": "PASS",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="JANUS +/+ bounded recenter reference head")
    parser.add_argument("--input-csv", type=Path)
    parser.add_argument("--context", default="USER_TASK")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("plus_plus_recenter_report.json"))
    args = parser.parse_args()

    result: object
    if args.self_test:
        result = self_test()
    else:
        result = run(load_csv(args.input_csv) if args.input_csv else [], context=args.context)

    payload = {
        "model": "JANUS DemiHead +/+ Word-Rhyme Recenter",
        "model_version": MODEL_VERSION,
        "genesis_signature": GENESIS_SIGNATURE,
        "genesis_signature_semantics": "HISTORICAL_ORIGIN_LINEAGE_NOT_ARITHMETIC_CLAIM",
        "rhyme": [item.value for item in RHYME],
        "rhyme_ru": ["СЛЫШУ", "СВЕРЯЮ", "РАСШИРЯЮ", "ОТПУСКАЮ"],
        "faces": {face.value: "+" for face in Face},
        "claim_ceiling": [
            "REFERENCE_STATE_MACHINE_ONLY",
            "NO_REAL_WORLD_ALIGNMENT_PROOF",
            "NO_USER_DIAGNOSIS",
            "NO_FOUNDATION_WEIGHT_RETRAINING_CLAIM",
        ],
        "result": result,
    }
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
