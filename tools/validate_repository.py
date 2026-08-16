from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker

from hemisphere_bridge import combine_packets, validate_packet
from keto_reference import load_case, summarize_case


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
    schemas = {
        path.name: load_json(path) for path in sorted((ROOT / "schemas").glob("*.json"))
    }
    for schema in schemas.values():
        Draft202012Validator.check_schema(schema)

    observer_config = load_json(ROOT / "configs" / "example.config.json")
    Draft202012Validator(
        schemas["config.schema.json"], format_checker=FormatChecker()
    ).validate(observer_config)

    keto_config = load_json(ROOT / "configs" / "keto.example.json")
    Draft202012Validator(
        schemas["keto-config.schema.json"], format_checker=FormatChecker()
    ).validate(keto_config)

    keto_case = load_case(ROOT / "examples" / "case_echo_collapse.json")
    Draft202012Validator(
        schemas["keto-case.schema.json"], format_checker=FormatChecker()
    ).validate(keto_case)

    keto_result = summarize_case(keto_case)
    Draft202012Validator(
        schemas["keto-result.schema.json"], format_checker=FormatChecker()
    ).validate(keto_result)

    left_packet = load_json(ROOT / "examples" / "hemisphere_left_hrain.json")
    right_packet = load_json(ROOT / "examples" / "hemisphere_right_inaihr.json")
    packet_validator = Draft202012Validator(
        schemas["hemisphere-packet.schema.json"], format_checker=FormatChecker()
    )
    packet_validator.validate(left_packet)
    packet_validator.validate(right_packet)
    validate_packet(left_packet, "LEFT_HRAIN")
    validate_packet(right_packet, "RIGHT_INAIHR")

    bicameral_result = combine_packets(left=left_packet, right=right_packet)
    Draft202012Validator(
        schemas["bicameral-result.schema.json"], format_checker=FormatChecker()
    ).validate(bicameral_result)

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

    if result["truth_claim"] != "NOT_MADE":
        raise ValueError("Reference analyzer must not emit an objective truth claim")

    if result["mass_effect_budget"] != 0:
        raise ValueError("Reference analyzer mass-effect budget must remain zero")


def validate_hemisphere_invariants() -> None:
    left = load_json(ROOT / "examples" / "hemisphere_left_hrain.json")
    right = load_json(ROOT / "examples" / "hemisphere_right_inaihr.json")
    result = combine_packets(left=left, right=right)

    if result["status"] != "BICAMERAL_OVERLAP_PRESENT":
        raise ValueError("Reference hemisphere fixture must exercise overlap")
    if result["comparison"]["shared_semantic_keys"] != ["context", "evidence"]:
        raise ValueError("Reference hemisphere overlap changed unexpectedly")
    if result["comparison"]["automatic_graph_merge_performed"] is not False:
        raise ValueError("Bicameral bridge must not automatically merge workspaces")
    if result["routing"]["external_effect_permitted"] is not False:
        raise ValueError("Bicameral comparison must not authorize external effects")
    if result["routing"]["direct_cross_hemisphere_write_permitted"] is not False:
        raise ValueError("Direct cross-hemisphere writes must remain disabled")
    if result["claim_ceiling"]["truth_claim_made"] is not False:
        raise ValueError("Bicameral overlap must not become a truth claim")
    if result["claim_ceiling"]["agreement_is_truth"] is not False:
        raise ValueError("Agreement must not be promoted to truth")
    if result["claim_ceiling"]["hemisphere_count_is_authority"] is not False:
        raise ValueError("Hemisphere count must not create authority")
    if result["claim_ceiling"]["authority_delta"] != 0:
        raise ValueError("Hemisphere bridge authority delta must remain zero")
    if result["claim_ceiling"]["mass_effect_budget_delta"] != 0:
        raise ValueError("Hemisphere bridge mass-effect budget delta must remain zero")

    degraded = combine_packets(left=left)
    if degraded["routing"]["mode"] != "DEGRADED_SINGLE_HEMISPHERE_HOLD":
        raise ValueError("Single-hemisphere operation must degrade to HOLD")


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
    validate_hemisphere_invariants()
    validate_markdown_links()
    print("Repository contracts, JSON mirrors, KETO/bicameral invariants, and local documentation links are valid.")


if __name__ == "__main__":
    main()
