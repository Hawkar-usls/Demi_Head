from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote

from jsonschema import Draft202012Validator, FormatChecker

from hemisphere_bridge import combine_packets, validate_packet
from keto_reference import load_case, summarize_case


ROOT = Path(__file__).resolve().parents[1]
LOCAL_LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BICAMERAL_TRANSPORT_FREEZE = "d33077fbd0d244bf0ae6d678894bdc9a8eddcf0d779ce11b85e39eeff6143883"
LOCAL_ACCEPT_BROWSER_FREEZE = "f44263abaf0fa23c0344f4c68719e1a695d122c251fc373e732724d7958f2c49"


def load_json(path: Path) -> object:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def canonical_sha256(value: object) -> str:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def validate_json_documents() -> None:
    paths = [ROOT / "PROJECT_STATUS.json"]
    paths.extend(sorted((ROOT / "configs").glob("*.json")))
    paths.extend(sorted((ROOT / "schemas").glob("*.json")))
    paths.extend(sorted((ROOT / "examples").glob("*.json")))
    paths.extend(sorted((ROOT / "docs").glob("*.json")))
    paths.extend(sorted((ROOT / "holdout").rglob("*.json")))
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


def validate_bicameral_transport_freeze() -> None:
    path = ROOT / "holdout" / "bicameral_transport_v1" / "frozen_corpus.json"
    corpus = load_json(path)
    if not isinstance(corpus, dict):
        raise ValueError("Bicameral transport corpus must be an object")
    if corpus.get("schema") != "janus.demihead.bicameral_transport_holdout.v1":
        raise ValueError("Unexpected bicameral transport holdout schema")
    if corpus.get("freeze_sha256") != BICAMERAL_TRANSPORT_FREEZE:
        raise ValueError("Bicameral transport declared freeze SHA drifted")
    payload = corpus.get("freeze_payload")
    if canonical_sha256(payload) != BICAMERAL_TRANSPORT_FREEZE:
        raise ValueError("Bicameral transport canonical freeze payload hash mismatch")
    if not isinstance(payload, dict) or payload.get("frozen_before_first_execution") is not True:
        raise ValueError("Bicameral transport corpus must be frozen before first execution")
    if len(payload.get("cases", [])) != 18:
        raise ValueError("Bicameral transport holdout must keep exactly 18 preregistered cases")
    if payload.get("timeout_ms") != 2000:
        raise ValueError("Bicameral transport timeout preregistration drifted")
    if payload.get("latency_quantile_method") != "nearest_rank":
        raise ValueError("Bicameral transport quantile method drifted")
    if payload.get("latency_semantics") != "frozen_synthetic_event_trace_not_wall_clock":
        raise ValueError("Synthetic latency claim ceiling drifted")
    ceiling = payload.get("claim_ceiling", {})
    if ceiling.get("real_browser_network_latency_measured") is not False:
        raise ValueError("Synthetic holdout cannot claim real browser/network latency")
    if ceiling.get("production_readiness_established") is not False:
        raise ValueError("Synthetic holdout cannot establish production readiness")
    if ceiling.get("request_id_is_authentication") is not False:
        raise ValueError("Request-id freshness binding cannot become authentication")
    if ceiling.get("authority_delta") != 0 or ceiling.get("mass_effect_budget_delta") != 0:
        raise ValueError("Transport holdout cannot change authority or mass-effect budget")


def validate_local_accept_browser_freeze() -> None:
    path = ROOT / "holdout" / "local_accept_browser_v1" / "frozen_corpus.json"
    corpus = load_json(path)
    if not isinstance(corpus, dict):
        raise ValueError("Local-accept browser corpus must be an object")
    if corpus.get("schema") != "janus.demihead.local_accept_browser_holdout.v1":
        raise ValueError("Unexpected local-accept browser holdout schema")
    if corpus.get("freeze_sha256") != LOCAL_ACCEPT_BROWSER_FREEZE:
        raise ValueError("Local-accept browser declared freeze SHA drifted")
    payload = corpus.get("freeze_payload")
    if canonical_sha256(payload) != LOCAL_ACCEPT_BROWSER_FREEZE:
        raise ValueError("Local-accept browser canonical freeze payload hash mismatch")
    if not isinstance(payload, dict) or payload.get("frozen_before_first_execution") is not True:
        raise ValueError("Local-accept browser corpus must be frozen before first execution")
    if len(payload.get("cases", [])) != 17:
        raise ValueError("Local-accept browser holdout must keep exactly 17 preregistered cases")
    if payload.get("admission", {}).get("required_pass_count") != 17:
        raise ValueError("Local-accept browser admission count drifted")
    browser = payload.get("browser", {})
    if browser.get("engine") != "chromium":
        raise ValueError("Local-accept browser engine preregistration drifted")
    if browser.get("server") != "http://127.0.0.1:8765":
        raise ValueError("Local-accept browser isolated server preregistration drifted")
    if browser.get("live_user_data") is not False:
        raise ValueError("Browser holdout may not use live user data")
    if browser.get("network_external_effects") is not False:
        raise ValueError("Browser holdout may not permit external network effects")
    ceiling = payload.get("claim_ceiling", {})
    if ceiling.get("production_network_latency_measured") is not False:
        raise ValueError("Localhost functional holdout cannot claim production network latency")
    if ceiling.get("authenticated_human_identity_established") is not False:
        raise ValueError("Browser click cannot become authenticated human identity")
    if ceiling.get("sha256_binding_is_signature") is not False:
        raise ValueError("SHA-256 content binding cannot become a digital signature")
    if ceiling.get("real_user_workspace_touched") is not False:
        raise ValueError("Browser holdout must not touch real user workspaces")
    if ceiling.get("production_readiness_established") is not False:
        raise ValueError("Browser holdout cannot establish production readiness")
    if ceiling.get("authority_delta") != 0 or ceiling.get("mass_effect_budget_delta") != 0:
        raise ValueError("Browser holdout cannot change authority or mass-effect budget")


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
    validate_bicameral_transport_freeze()
    validate_local_accept_browser_freeze()
    validate_markdown_links()
    print("Repository contracts, JSON mirrors, KETO/bicameral invariants, frozen transport/browser corpora, and local documentation links are valid.")


if __name__ == "__main__":
    main()
