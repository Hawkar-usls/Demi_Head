from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from not_prediction_atomic_graph import analyze  # noqa: E402


FIXTURE = ROOT / "examples" / "not_prediction_atomic_baseline_minimal.json"


def load_fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_baseline_counts_are_frozen() -> None:
    result = analyze(load_fixture())
    counts = result["counting"]
    assert counts["semantic_case_family_count"] == 29
    assert counts["strict_phenomenon_session_root_count"] == 24
    assert counts["uncertain_phenomenology_root_count"] == 3
    assert counts["inclusive_phenomenology_root_count"] == 27


def test_holy_clock_is_twelve_event_sessions() -> None:
    result = analyze(load_fixture())
    row = next(item for item in result["per_case"] if item["case_id"] == "NP-003")
    assert row["strict_phenomenon_session_count"] == 12
    assert row["selection_process_root"] == "CLOCK_SALIENCE_AND_LOOKUP_PROCESS"


def test_session_subevents_do_not_become_independent_roots() -> None:
    result = analyze(load_fixture())
    np019 = next(item for item in result["per_case"] if item["case_id"] == "NP-019")
    np028 = next(item for item in result["per_case"] if item["case_id"] == "NP-028")
    assert np019["strict_phenomenon_session_count"] == 1
    assert np019["subevent_count"] == 23
    assert np028["strict_phenomenon_session_count"] == 0
    assert np028["subevent_count"] == 22


def test_direct_and_recursive_dependencies_are_hard_collapses() -> None:
    result = analyze(load_fixture())
    rows = {row["component_id"]: row for row in result["dependency_components"]}
    assert rows["DEP_GENESIS_013_014_PARENT"]["independence_effect"] == "HARD_INDEPENDENCE_COLLAPSE"
    assert rows["DEP_EYE_WEDJAT_RECURSION"]["independence_effect"] == "HARD_INDEPENDENCE_COLLAPSE"


def test_shared_selection_and_ontology_are_soft_dependencies() -> None:
    result = analyze(load_fixture())
    rows = {row["component_id"]: row for row in result["dependency_components"]}
    assert rows["DEP_CLOCK_SELECTION"]["independence_effect"] == "SOFT_NULL_MODEL_DEPENDENCY"
    assert rows["DEP_FUTURE_INFORMATION_STACK"]["independence_effect"] == "SOFT_NULL_MODEL_DEPENDENCY"


def test_no_extraordinary_claim_is_promoted() -> None:
    result = analyze(load_fixture())
    assert result["truth_claim"] == "NOT_MADE"
    assert result["prediction_claim"] == "NOT_PROMOTED"
    assert result["prophecy_claim"] == "NOT_PROMOTED"
    assert result["precognition_claim"] == "NOT_PROMOTED"
    assert result["physical_retrocausality_claim"] == "NOT_PROMOTED"


def test_missing_baseline_case_fails_closed() -> None:
    document = load_fixture()
    document["cases"] = document["cases"][:-1]
    try:
        analyze(document)
    except ValueError as exc:
        assert "NP-001..NP-029" in str(exc)
    else:
        raise AssertionError("missing baseline case should fail closed")
