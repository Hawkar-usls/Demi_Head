from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "janus.demihead.source_bound_witness.v1"
VALID_RELATIONS = {"supports", "contradicts", "context_only"}


def load_packet(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        packet = json.load(handle)
    if packet.get("schema") != SCHEMA:
        raise ValueError(f"Unsupported schema: {packet.get('schema')!r}")
    if not packet.get("witness_id"):
        raise ValueError("witness_id is required")
    if not packet.get("questions"):
        raise ValueError("At least one question is required")
    evidence = packet.get("evidence", [])
    ids: set[str] = set()
    for item in evidence:
        evidence_id = item.get("evidence_id")
        if not evidence_id or evidence_id in ids:
            raise ValueError("Evidence IDs must be unique and non-empty")
        ids.add(evidence_id)
        if item.get("relation") not in VALID_RELATIONS:
            raise ValueError(f"Invalid evidence relation for {evidence_id}")
    return packet


def evaluate_question(question: dict[str, Any], evidence_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    refs = list(question.get("evidence_ids", []))
    missing = [ref for ref in refs if ref not in evidence_by_id]
    if missing:
        raise ValueError(f"Unknown evidence IDs: {missing}")

    selected = [evidence_by_id[ref] for ref in refs]
    supports = sorted(item["evidence_id"] for item in selected if item["relation"] == "supports")
    contradicts = sorted(item["evidence_id"] for item in selected if item["relation"] == "contradicts")
    context_only = sorted(item["evidence_id"] for item in selected if item["relation"] == "context_only")

    if supports and contradicts:
        state = "CONTESTED"
    elif supports:
        state = "SUPPORTED_BY_BOUND_SOURCES"
    elif contradicts:
        state = "CONTRADICTED_BY_BOUND_SOURCES"
    else:
        state = "UNRESOLVED"

    return {
        "question_id": question["question_id"],
        "question": question["text"],
        "target_claim": question.get("target_claim"),
        "state": state,
        "support_ids": supports,
        "contradiction_ids": contradicts,
        "context_only_ids": context_only,
        "answer_contract": (
            "No first-person supernatural testimony is created. The witness name is a source-bound "
            "query interface; only the bound evidence may determine the state."
        ),
    }


def analyze_packet(packet: dict[str, Any]) -> dict[str, Any]:
    evidence = packet.get("evidence", [])
    evidence_by_id = {item["evidence_id"]: item for item in evidence}
    answers = [evaluate_question(question, evidence_by_id) for question in packet["questions"]]

    return {
        "schema": "janus.demihead.source_bound_witness.result.v1",
        "case_id": packet.get("case_id"),
        "witness_id": packet["witness_id"],
        "mode": "SOURCE_BOUND_QUERY_INTERFACE",
        "answers": answers,
        "model_output_is_evidence": False,
        "supernatural_contact_claimed": False,
        "release_control": "RETURN_BOUND_STATES_AND_REQUEST_NEW_PRIMARY_EVIDENCE_FOR_OPEN_QUESTIONS",
        "invariants": [
            "MODEL_OUTPUT != EVIDENCE",
            "ROLEPLAY != TESTIMONY",
            "NO_SOURCE != FALSE",
            "CONTEXT_ONLY != SUPPORT",
            "UNRESOLVED != NEGATIVE",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate direct witness questions against bound source roots.")
    parser.add_argument("packet", type=Path)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    result = analyze_packet(load_packet(args.packet))
    rendered = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


if __name__ == "__main__":
    main()
