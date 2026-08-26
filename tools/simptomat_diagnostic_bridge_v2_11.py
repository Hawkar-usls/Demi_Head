from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping

PACKET_SCHEMA = "janus.simptomat.diagnostic_reasoning_packet.v1"
REVIEW_SCHEMA = "janus.demihead.simptomat_epistemic_review.v1"
CLAIM_CEILING = "RESEARCH_DIAGNOSTIC_HYPOTHESIS_ONLY"
REVIEW_CEILING = "DEMIHEAD_EPISTEMIC_REVIEW_ONLY_NOT_CLINICAL_CONFIRMATION"
ALLOWED_SESSION_SCOPES = {"EPHEMERAL_CONVERSATION", "CONSENTED_RESEARCH_CASE"}
ALLOWED_STATES = {
    "SUPPORTED",
    "COMPATIBLE",
    "WEAKLY_COMPATIBLE",
    "CONTRADICTED",
    "INSUFFICIENT_DATA",
    "ESCALATE_FOR_REAL_WORLD_EVALUATION",
}
FORBIDDEN_KEYS = {
    "name",
    "full_name",
    "email",
    "phone",
    "telegram_id",
    "telegram_user_id",
    "address",
    "exact_address",
    "birth_date",
    "date_of_birth",
    "medical_record_number",
    "raw_chat_transcript",
    "genetic_data",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _walk_keys(value: Any):
    if isinstance(value, Mapping):
        for key, child in value.items():
            yield str(key).lower()
            yield from _walk_keys(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_keys(child)


def _unsafe_probability(candidate: Mapping[str, Any]) -> bool:
    if "clinical_probability" not in candidate:
        return False
    probability = candidate.get("clinical_probability")
    if not isinstance(probability, (int, float)) or isinstance(probability, bool):
        return True
    if not 0 <= float(probability) <= 1:
        return True
    return candidate.get("probability_calibration") != "EXTERNALLY_VALIDATED"


def verify_packet(packet: Mapping[str, Any]) -> bool:
    if not isinstance(packet, Mapping) or packet.get("schema") != PACKET_SCHEMA:
        return False
    if not isinstance(packet.get("packet_id"), str) or not packet["packet_id"]:
        return False
    if packet.get("session_scope") not in ALLOWED_SESSION_SCOPES:
        return False
    consent = packet.get("consent_scope")
    if not isinstance(consent, Mapping) or consent.get("conversation_processing_allowed") is not True:
        return False
    if not isinstance(consent.get("public_case_persistence_consent"), bool):
        return False
    if packet.get("claim_ceiling") != CLAIM_CEILING:
        return False
    if packet.get("authority_delta") != 0:
        return False
    if not isinstance(packet.get("clinical_confirmation_claimed"), bool):
        return False
    differential = packet.get("ranked_differential")
    if not isinstance(differential, list) or not differential:
        return False
    seen: set[str] = set()
    for candidate in differential:
        if not isinstance(candidate, Mapping):
            return False
        name = candidate.get("candidate")
        state = candidate.get("state")
        if not isinstance(name, str) or not name or name in seen or state not in ALLOWED_STATES:
            return False
        seen.add(name)
        if "research_score" in candidate and not isinstance(candidate.get("research_score"), (int, float)):
            return False
    for key in ("supporting_features", "contradicting_features", "uncertainties", "urgent_red_flags"):
        value = packet.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return False
    if packet.get("next_best_question") is not None and not isinstance(packet.get("next_best_question"), str):
        return False
    confirmation = packet.get("next_confirmation_step")
    if not isinstance(confirmation, Mapping):
        return False
    if not isinstance(confirmation.get("description"), str):
        return False
    if not isinstance(confirmation.get("requires_external_measurement"), bool):
        return False
    if FORBIDDEN_KEYS.intersection(set(_walk_keys(packet))):
        return False
    return True


def _unsafe_promotion(packet: Mapping[str, Any]) -> bool:
    if packet.get("clinical_confirmation_claimed") is True:
        return True
    return any(_unsafe_probability(candidate) for candidate in packet["ranked_differential"])


def choose_decision(packet: Mapping[str, Any]) -> str:
    if not verify_packet(packet):
        raise ValueError("SIMPTOMAT_PACKET_INVALID_OR_PRIVACY_UNSAFE")
    if _unsafe_promotion(packet):
        return "REJECT_UNSAFE_PROMOTION"
    if packet["urgent_red_flags"]:
        return "ESCALATE_FOR_REAL_WORLD_EVALUATION"
    if packet["next_confirmation_step"]["requires_external_measurement"]:
        return "HOLD_FOR_EXTERNAL_MEASUREMENT"
    if packet.get("next_best_question") in (None, "") and any(
        candidate["state"] == "INSUFFICIENT_DATA" for candidate in packet["ranked_differential"]
    ):
        return "HOLD_FOR_MORE_INFORMATION"
    return "PASS_AS_RESEARCH_HYPOTHESIS"


def build_review(packet: Mapping[str, Any]) -> dict[str, Any]:
    decision = choose_decision(packet)
    notes = [
        "Candidate ordering is preserved; DemiHead review does not silently replace Simptomat's differential.",
        "Contradictions and uncertainty remain first-class state.",
        "DemiHead review is not a clinical reference label and grants no treatment authority.",
    ]
    if decision == "REJECT_UNSAFE_PROMOTION":
        notes.append("Clinical confirmation or an uncalibrated clinical probability was requested/encoded and was rejected.")
    elif decision == "ESCALATE_FOR_REAL_WORLD_EVALUATION":
        notes.append("Urgent red flags are present; real-world evaluation outranks continued research branching.")
    elif decision == "HOLD_FOR_EXTERNAL_MEASUREMENT":
        notes.append("Conversation has reached a measurement handoff; no further evidence is invented internally.")
    review: dict[str, Any] = {
        "schema": REVIEW_SCHEMA,
        "packet_id": packet["packet_id"],
        "packet_sha256": digest(packet),
        "decision": decision,
        "preserved_candidate_order": [candidate["candidate"] for candidate in packet["ranked_differential"]],
        "contradiction_count": len(packet["contradicting_features"]),
        "uncertainty_count": len(packet["uncertainties"]),
        "privacy_gate": "PASS_MINIMIZED_PACKET",
        "clinical_confirmation_granted": False,
        "reference_label_granted": False,
        "authority_delta": 0,
        "claim_ceiling": REVIEW_CEILING,
        "review_notes": notes,
    }
    review["review_sha256"] = digest(review)
    return review


def verify_review(packet: Mapping[str, Any], review: Mapping[str, Any]) -> bool:
    if not verify_packet(packet) or not isinstance(review, Mapping) or review.get("schema") != REVIEW_SCHEMA:
        return False
    claimed = review.get("review_sha256")
    if not isinstance(claimed, str) or HEX64.fullmatch(claimed) is None:
        return False
    replay = dict(review)
    replay.pop("review_sha256", None)
    if digest(replay) != claimed:
        return False
    try:
        expected = build_review(packet)
    except ValueError:
        return False
    return dict(review) == expected


def main() -> None:
    parser = argparse.ArgumentParser(description="Review a minimized Simptomat diagnostic reasoning packet.")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args()

    packet = json.loads(args.packet.read_text(encoding="utf-8"))
    if args.verify:
        review = json.loads(args.verify.read_text(encoding="utf-8"))
        ok = verify_review(packet, review)
        print(json.dumps({"verified": ok, "authority_delta": 0}, sort_keys=True))
        raise SystemExit(0 if ok else 1)

    review = build_review(packet)
    text = json.dumps(review, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")


if __name__ == "__main__":
    main()
