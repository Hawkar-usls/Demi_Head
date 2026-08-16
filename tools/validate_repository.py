from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker

from constitution_optimizer import evaluate_trials, load_spec as load_optimizer_spec
from correction_propagator import load_graph as load_correction_graph, propagate_corrections
from flow_gate import load_trace as load_flow_trace, run_flow_gate
from human_appeal import evaluate_appeal, load_bundle as load_appeal_bundle
from keto_reference import load_case, summarize_case
from language_invariance import evaluate_invariance, load_bundle as load_language_bundle
from reviewer_disagreement import evaluate_collection, load_collection as load_reviewer_collection


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_json_documents() -> None:
    paths = [ROOT / "PROJECT_STATUS.json"]
    paths.extend(sorted((ROOT / "configs").glob("*.json")))
    paths.extend(sorted((ROOT / "schemas").glob("*.json")))
    paths.extend(sorted((ROOT / "examples").glob("*.json")))
    paths.extend(sorted((ROOT / "docs").glob("*.json")))
    for path in paths:
        load_json(path)


def validate_schemas() -> dict[str, object]:
    schemas = {path.name: load_json(path) for path in sorted((ROOT / "schemas").glob("*.json"))}
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    observer_config = load_json(ROOT / "configs" / "example.config.json")
    Draft202012Validator(schemas["config.schema.json"], format_checker=FormatChecker()).validate(observer_config)

    keto_config = load_json(ROOT / "configs" / "keto.example.json")
    Draft202012Validator(schemas["keto-config.schema.json"], format_checker=FormatChecker()).validate(keto_config)

    keto_case = load_case(ROOT / "examples" / "case_echo_collapse.json")
    Draft202012Validator(schemas["keto-case.schema.json"], format_checker=FormatChecker()).validate(keto_case)
    Draft202012Validator(schemas["keto-result.schema.json"], format_checker=FormatChecker()).validate(summarize_case(keto_case))

    flow_trace = load_flow_trace(ROOT / "examples" / "flow_gate_trace.json")
    Draft202012Validator(schemas["flow-gate-trace.schema.json"], format_checker=FormatChecker()).validate(flow_trace)

    optimizer_spec = load_optimizer_spec(ROOT / "examples" / "optimizer_trials.json")
    Draft202012Validator(schemas["optimizer-trials.schema.json"], format_checker=FormatChecker()).validate(optimizer_spec)

    correction_graph = load_correction_graph(ROOT / "examples" / "correction_graph.json")
    Draft202012Validator(schemas["correction-graph.schema.json"], format_checker=FormatChecker()).validate(correction_graph)

    language_bundle = load_language_bundle(ROOT / "examples" / "language_render_bundle.json")
    Draft202012Validator(schemas["language-render-bundle.schema.json"], format_checker=FormatChecker()).validate(language_bundle)

    reviewer_collection = load_reviewer_collection(ROOT / "examples" / "reviewer_collection.json")
    Draft202012Validator(schemas["reviewer-collection.schema.json"], format_checker=FormatChecker()).validate(reviewer_collection)

    appeal_bundle = load_appeal_bundle(ROOT / "examples" / "appeal_bundle.json")
    Draft202012Validator(schemas["appeal-bundle.schema.json"], format_checker=FormatChecker()).validate(appeal_bundle)
    return schemas


def validate_keto_invariants() -> None:
    case = load_case(ROOT / "examples" / "case_echo_collapse.json")
    presentations = case["presentations"]
    result = summarize_case(case)
    root_ids = {item["root_id"] for item in presentations}
    if len(presentations) <= len(root_ids):
        raise ValueError("Synthetic KETO fixture must contain derivative presentations to exercise root collapse")
    if result["accounting"]["presentation_count"] <= result["accounting"]["root_count"]:
        raise ValueError("KETO result failed to preserve presentation/root multiplicity distinction")
    if not any(item["freshness"] == "stale" for item in presentations):
        raise ValueError("Synthetic KETO fixture must exercise stale/current separation")
    if "root-D" in result["current_support_roots"]:
        raise ValueError("Stale source root was incorrectly promoted to current support")
    if result["evidence_state"] != "CONTESTED":
        raise ValueError("Support + contradiction fixture must remain CONTESTED")
    if result["truth_claim"] != "NOT_MADE" or result["mass_effect_budget"] != 0:
        raise ValueError("KETO reference boundary escaped")


def validate_performance_invariants() -> None:
    flow = run_flow_gate(load_flow_trace(ROOT / "examples" / "flow_gate_trace.json"))
    if not flow["invariants"]["quota_respected"] or flow["accounting"]["deferred_count"] < 1:
        raise ValueError("Flow fixture failed bounded/deferred accounting")
    if flow["accounting"]["unknown_observed_count"] < 1 or flow["invariants"]["evidence_state_mutated"]:
        raise ValueError("Flow fixture failed UNKNOWN/evidence boundary")
    if flow["invariants"]["authority_delta"] != 0 or flow["invariants"]["mass_effect_budget_delta"] != 0:
        raise ValueError("Flow scheduling created authority or mass effect")

    optimizer = evaluate_trials(load_optimizer_spec(ROOT / "examples" / "optimizer_trials.json"))
    if optimizer["accounting"]["rejected_count"] < 1 or optimizer["best_candidate"] is None:
        raise ValueError("Optimizer fixture did not exercise admission/rejection")
    if optimizer["best_candidate"]["candidate_id"] == "forbidden_authority_shortcut":
        raise ValueError("Constraint-violating optimizer candidate was selected")
    inv = optimizer["invariants"]
    if any(inv[key] for key in (
        "optimizer_can_mutate_evidence_state",
        "optimizer_can_mutate_source_roots",
        "optimizer_can_mutate_constitution",
        "optimizer_can_increase_authority",
        "optimizer_can_increase_mass_effect_budget",
    )):
        raise ValueError("Optimizer escaped its constitutional boundary")


def validate_correction_and_language_invariants() -> None:
    correction = propagate_corrections(load_correction_graph(ROOT / "examples" / "correction_graph.json"))
    by_id = {row["presentation_id"]: row for row in correction["presentations"]}
    if by_id["post-old"]["status"] != "AFFECTED_BY_CORRECTION" or by_id["post-old"]["correction_chain"] != ["corr-A1", "corr-A2"]:
        raise ValueError("Known old descendant did not preserve correction chain")
    if by_id["post-current"]["status"] != "CURRENT" or by_id["unbound-copy"]["status"] != "UNKNOWN_LINEAGE":
        raise ValueError("Correction current/unknown classification failed")
    cinv = correction["invariants"]
    if cinv["history_deleted"] or cinv["source_text_rewritten"] or cinv["evidence_authority_delta"] != 0 or cinv["mass_effect_budget_delta"] != 0:
        raise ValueError("Correction propagator escaped boundary")

    language = evaluate_invariance(load_language_bundle(ROOT / "examples" / "language_render_bundle.json"))
    if language["status"] != "PASS" or language["violations"]:
        raise ValueError("Equivalent multilingual fixture must pass")
    linv = language["invariants"]
    if linv["presentation_prose_compared_as_truth"] or linv["language_identity_used_as_evidence_weight"]:
        raise ValueError("Language gate escaped semantic boundary")
    if linv["authority_delta"] != 0 or linv["mass_effect_budget_delta"] != 0:
        raise ValueError("Language gate created authority or mass effect")


def validate_reviewer_invariants() -> None:
    result = evaluate_collection(load_reviewer_collection(ROOT / "examples" / "reviewer_collection.json"))
    if result["collection_state"] != "READY_FOR_CONSENSUS" or result["consensus"] is None:
        raise ValueError("Reviewer fixture must be ready for consensus")
    if result["consensus"]["fields"]["evidence_state"] != "CONTESTED":
        raise ValueError("Unanimous reviewer field was not preserved")
    if result["consensus"]["fields"]["uncertainty_class"] != "DISAGREEMENT":
        raise ValueError("Non-unanimous reviewer field was not preserved")
    if result["consensus"]["majority_vote_used"] or result["consensus"]["model_fill_used"]:
        raise ValueError("Reviewer gate majority-voted or model-filled disagreement")
    if result["human_independence_proven_by_software"]:
        raise ValueError("Reviewer gate claimed software-proven human independence")
    rinv = result["invariants"]
    if rinv["reviewer_count_is_truth_weight"] or rinv["unanimity_is_objective_truth"]:
        raise ValueError("Reviewer gate escaped truth-weight boundary")
    if rinv["authority_delta"] != 0 or rinv["mass_effect_budget_delta"] != 0:
        raise ValueError("Reviewer processing created authority or mass effect")


def validate_appeal_invariants() -> None:
    result = evaluate_appeal(load_appeal_bundle(ROOT / "examples" / "appeal_bundle.json"))
    if result["status"] != "APPEAL_RECORDED_NEEDS_HUMAN_REVIEW":
        raise ValueError("Frozen appeal fixture must record a pending human-review request")
    if not result["decision_binding_verified"] or not result["needs_human_review"]:
        raise ValueError("Appeal decision binding or pending-review state failed")
    inv = result["invariants"]
    if inv["appeal_is_admission_of_error"] or inv["appeal_request_is_outcome_override"]:
        raise ValueError("Appeal was promoted into an error admission or outcome override")
    if inv["original_decision_rewritten"] or inv["history_deleted"]:
        raise ValueError("Appeal gate rewrote or deleted history")
    if inv["evidence_state_mutated_by_appeal_gate"] or inv["correction_applied_by_appeal_gate"]:
        raise ValueError("Appeal gate directly changed evidence/correction state")
    if inv["authority_delta"] != 0 or inv["mass_effect_budget_delta"] != 0:
        raise ValueError("Appeal gate created authority or mass effect")


def validate_markdown_links() -> None:
    missing: list[str] = []
    for markdown in sorted(ROOT.rglob("*.md")):
        if any(part.startswith(".") for part in markdown.relative_to(ROOT).parts):
            continue
        text = markdown.read_text(encoding="utf-8")
        for match in LOCAL_LINK.finditer(text):
            raw_link = match.group(1).strip("<>")
            if raw_link.startswith(("http://", "https://", "mailto:", "#")):
                continue
            path_part = unquote(raw_link.split("#", 1)[0])
            if not path_part:
                continue
            target = (markdown.parent / path_part).resolve()
            if not target.exists():
                missing.append(f"{markdown.relative_to(ROOT)} -> {raw_link}")
    if missing:
        details = "\n".join(f"- {item}" for item in missing)
        raise ValueError(f"Missing local Markdown targets:\n{details}")


def main() -> None:
    validate_json_documents()
    validate_schemas()
    validate_keto_invariants()
    validate_performance_invariants()
    validate_correction_and_language_invariants()
    validate_reviewer_invariants()
    validate_appeal_invariants()
    validate_markdown_links()
    print(
        "Repository contracts, JSON documents, KETO/flow/optimizer/correction/language/reviewer/appeal results, "
        "constitutional invariants, and local documentation links are valid."
    )


if __name__ == "__main__":
    main()
