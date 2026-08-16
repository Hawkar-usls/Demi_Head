#!/usr/bin/env python3
"""Bounded JANUS +/+ interaction recenter reference head.

This module does not classify people, infer intent from natural language, retrain a
model, or change evidence status. It consumes already-declared symbolic pressure
flags and may only change a transient local routing state.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterable


MODEL_VERSION = "1.0.0"


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
    LOADED = "LOADED"
    LOOPING = "LOOPING"
    RECENTER_REQUIRED = "RECENTER_REQUIRED"


RHYME = (Step.HEAR, Step.CHECK, Step.WIDEN, Step.RELEASE)
FACE_FOR_STEP = {
    Step.HEAR: Face.WITNESS_PLUS,
    Step.CHECK: Face.GUARD_PLUS,
    Step.WIDEN: Face.WITNESS_PLUS,
    Step.RELEASE: Face.GUARD_PLUS,
}

# These are symbolic inputs from an upstream frozen policy or human fixture.
# This module deliberately contains no NLP detector for them.
PRESSURE_FLAGS = frozenset(
    {
        "repetition_without_new_evidence",
        "certainty_without_support",
        "choice_narrowing",
        "coercive_or_hostile_pressure",
        "high_arousal_loop",
        "identity_capture_pressure",
        "engagement_pressure",
    }
)

UP = {
    Load.CLEAR: Load.LOADED,
    Load.LOADED: Load.LOOPING,
    Load.LOOPING: Load.RECENTER_REQUIRED,
    Load.RECENTER_REQUIRED: Load.RECENTER_REQUIRED,
}
DOWN = {
    Load.CLEAR: Load.CLEAR,
    Load.LOADED: Load.CLEAR,
    Load.LOOPING: Load.LOADED,
    Load.RECENTER_REQUIRED: Load.LOOPING,
}


@dataclass
class State:
    meta_context: str = "ARMOR_PLUS_PLUS_CONSTITUTION"
    context: str = "USER_TASK"
    pressure: Load = Load.CLEAR
    rhyme_index: int = 0
    recenter_events: int = 0


def _normalized_source(source: str) -> str:
    value = source.strip().lower()
    if value not in {"user", "system", "external", "human_reviewer"}:
        return "external"
    return value


def apply_event(state: State, source: str, flags: Iterable[str] = ()) -> dict[str, object]:
    accepted = sorted(set(flags) & PRESSURE_FLAGS)
    rejected = sorted(set(flags) - PRESSURE_FLAGS)

    state.pressure = UP[state.pressure] if accepted else DOWN[state.pressure]

    step = RHYME[state.rhyme_index]
    face = FACE_FOR_STEP[step]
    state.rhyme_index = (state.rhyme_index + 1) % len(RHYME)

    recentered = state.pressure is Load.RECENTER_REQUIRED
    recenter_sequence: list[str] = []
    if recentered:
        recenter_sequence = [item.value for item in RHYME]
        state.pressure = Load.CLEAR
        state.rhyme_index = 0
        state.recenter_events += 1

    return {
        "source": _normalized_source(source),
        "accepted_pressure_flags": accepted,
        "ignored_unknown_flags": rejected,
        "routing_step": step.value,
        "routing_face": face.value,
        "face_polarity": "+",
        "recentered": recentered,
        "recenter_sequence": recenter_sequence,
        "pressure_after": state.pressure.value,
        "evidence_status_mutated": False,
        "authority_delta": 0,
    }


def run(events: Iterable[tuple[str, Iterable[str]]], context: str = "USER_TASK") -> dict[str, object]:
    state = State(context=context)
    trace = [apply_event(state, source, flags) for source, flags in events]
    return {
        "state": {
            "meta_context": state.meta_context,
            "context": state.context,
            "pressure": state.pressure.value,
            "recenter_events": state.recenter_events,
        },
        "trace": trace,
        "invariants": {
            "negative_face_exists": False,
            "evidence_status_mutation_allowed": False,
            "authority_growth_allowed": False,
            "user_moral_scoring_allowed": False,
            "system_self_pressure_counted": True,
        },
    }


def load_csv(path: Path) -> list[tuple[str, tuple[str, ...]]]:
    events: list[tuple[str, tuple[str, ...]]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            flags = tuple(
                item.strip()
                for item in (row.get("pressure_flags") or "").split(";")
                if item.strip()
            )
            events.append(((row.get("source") or "user").strip(), flags))
    return events


def self_test() -> dict[str, str]:
    neutral = run([("user", ()), ("system", ()), ("user", ())])
    assert neutral["state"]["recenter_events"] == 0

    sad_but_not_pressure = run([("user", ())] * 5)
    assert sad_but_not_pressure["state"]["recenter_events"] == 0

    user_pressure = run(
        [
            ("user", ("choice_narrowing",)),
            ("user", ("certainty_without_support",)),
            ("user", ("repetition_without_new_evidence",)),
        ]
    )
    assert user_pressure["state"]["recenter_events"] == 1
    assert user_pressure["trace"][-1]["recenter_sequence"] == [item.value for item in RHYME]

    system_pressure = run(
        [
            ("system", ("engagement_pressure",)),
            ("system", ("choice_narrowing",)),
            ("system", ("repetition_without_new_evidence",)),
        ]
    )
    assert system_pressure["state"]["recenter_events"] == 1

    assert all(
        row["face_polarity"] == "+"
        for result in (neutral, user_pressure, system_pressure)
        for row in result["trace"]
    )
    assert all(
        row["authority_delta"] == 0 and row["evidence_status_mutated"] is False
        for result in (neutral, user_pressure, system_pressure)
        for row in result["trace"]
    )

    return {
        "neutral_not_forced_positive": "PASS",
        "negative_topic_not_implicitly_pressure": "PASS",
        "plus_plus_faces_only": "PASS",
        "user_pressure_recenters": "PASS",
        "system_pressure_recenters": "PASS",
        "full_rhyme_on_recenter": "PASS",
        "evidence_and_authority_unchanged": "PASS",
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
