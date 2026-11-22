"""TACHYON R5D: independent public-corpus qualification, not a false blind score.

This is a DATA CONTRACT audit for two independently authored academic temporal
relation corpora. They contain text/event annotations, not two authenticated
sensor witnesses or physical episode identities. The frozen R5C network cannot
legitimately ingest them. No gold labels are mapped into synthetic sensor slots.

The assay intentionally returns NO_VALID_MODEL_COMPARISON, never neural gain.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from tools.tachyon_r5c_observation_native_train import extract_observation_features

SOURCES = {
    "TDT_EXPERT": {
        "repo": "yuchenz/crowdsourced_EN_TDT_corpus",
        "ref": "da2a91e7d7edded1b4cf2369e2496cffeb4dfa35",
        "file": "data/timebank-dense.expert.tdt",
        "blob": "6b6d76a270e2ffcfc4a2324ca68c74c9834003c5",
        "license": "BSD-2-Clause",
    },
    "TDT_CROWD": {
        "repo": "yuchenz/crowdsourced_EN_TDT_corpus",
        "ref": "da2a91e7d7edded1b4cf2369e2496cffeb4dfa35",
        "file": "data/timebank.crowd.tdt",
        "blob": "d0410382f7ef2da368159977198319419163fc9d",
        "license": "BSD-2-Clause",
    },
    "TORQUE_DEV": {
        "repo": "qiangning/TORQUE-dataset",
        "ref": "ab27019cc6a317fde3c879900499f02acce8b16d",
        "file": "data/dev.json",
        "blob": "d7ac85423dd40df7c5bfeb637f801a275746858b",
        "license": "Apache-2.0",
    },
    "TORQUE_TEST": {
        "repo": "qiangning/TORQUE-dataset",
        "ref": "ab27019cc6a317fde3c879900499f02acce8b16d",
        "file": "data/test.json",
        "blob": "acbf618c824753fce67c6fb6f10826141ab0829a",
        "license": "Apache-2.0",
    },
}
LABEL_FIELDS = {"answer", "answers", "gold", "gold_label", "correct_answer", "correct_answers"}
HOLD = "HOLD_EXTERNAL_CUSTODIAN_AND_COMPATIBLE_REAL_WITNESS_INPUTS"


def git_blob_sha(content: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(content)).encode("ascii") + b"\x00" + content
    ).hexdigest()


def verify_source(path: Path, name: str) -> dict:
    expected = SOURCES[name]
    raw = path.read_bytes()
    blob = git_blob_sha(raw)
    if blob != expected["blob"]:
        raise ValueError(f"{name}: source has changed, refuse unpinned dataset")
    return {"source_id": name, "repo": expected["repo"], "ref": expected["ref"],
            "blob_sha1": blob, "sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw), "license": expected["license"]}


def parse_tdt(text: str, *, source_name: str) -> dict:
    documents = set()
    relations = Counter()
    records = {}
    lines = [x for x in text.splitlines() if x.strip()]
    for line_number, line in enumerate(lines, 1):
        cells = line.split("\t")
        if len(cells) != 9:
            raise ValueError(f"{source_name}:{line_number} expected 9 fields, got {len(cells)}")
        document, sentence, start, end, child, psentence, pstart, pend, label = cells
        if not document or not label:
            raise ValueError("missing temporal relation provenance")
        for value in (sentence, start, end, psentence, pstart, pend):
            try:
                int(value)
            except ValueError as exc:
                raise ValueError(f"bad position in {source_name}:{line_number}") from exc
        documents.add(document)
        relations[label] += 1
        # Only exact row-address pairs are comparable; no event text inferred.
        key = tuple(cells[:8])
        records.setdefault(key, []).append(label)
    return {
        "documents": len(documents),
        "rows": len(lines),
        "relation_distribution": dict(sorted(relations.items())),
        "duplicate_row_keys": sum(len(vals)-1 for vals in records.values()),
        "records": records,
    }


def _textual_dataset_stats(obj: object, *, split: str) -> dict:
    if not isinstance(obj, dict) or not obj:
        raise ValueError(f"TORQUE {split}: expected nonempty document map")
    question_count = 0
    answer_field_count = 0
    for doc, value in obj.items():
        if not isinstance(doc, str) or not isinstance(value, dict):
            raise ValueError(f"TORQUE {split}: invalid passage key")
        passage = value.get("passage")
        questions = value.get("question_answer_pairs")
        if not isinstance(passage, str) or not isinstance(questions, dict):
            raise ValueError(f"TORQUE {split}: expected passage/questions, not witness format")
        question_count += len(questions)
        for _, annotation in questions.items():
            if not isinstance(annotation, dict):
                raise ValueError(f"TORQUE {split}: invalid question annotation")
            answer_field_count += sum(name.lower() in LABEL_FIELDS for name in annotation)
    return {
        "passages": len(obj),
        "questions": question_count,
        "answer_field_occurrences": answer_field_count,
    }


def check_frozen_r5c_rejects_real_text() -> bool:
    """Hard admission check, not model scoring or a prediction."""
    external = {
        "schema": "external.tdt.temporal_relation.v1",
        "synthetic_only": False,
        "witnesses": [],
        "reference_time_utc": "2026-11-22T12:00:00+00:00",
    }
    try:
        extract_observation_features(external)
    except ValueError:
        return True
    return False


def qualify(tdt_root: Path, torque_root: Path) -> dict:
    paths = {
        name: ((tdt_root if name.startswith("TDT") else torque_root) / info["file"])
        for name, info in SOURCES.items()
    }
    files = {name: verify_source(path, name) for name, path in paths.items()}
    expert = parse_tdt(paths["TDT_EXPERT"].read_text(), source_name="TDT_EXPERT")
    crowd = parse_tdt(paths["TDT_CROWD"].read_text(), source_name="TDT_CROWD")
    overlap = set(expert["records"]) & set(crowd["records"])
    comparable = [key for key in overlap if len(expert["records"][key]) == 1
                  and len(crowd["records"][key]) == 1]
    agreements = sum(expert["records"][key][0] == crowd["records"][key][0]
                     for key in comparable)
    torque_dev = _textual_dataset_stats(
        json.loads(paths["TORQUE_DEV"].read_text()), split="dev"
    )
    torque_test = _textual_dataset_stats(
        json.loads(paths["TORQUE_TEST"].read_text()), split="test"
    )
    if torque_test["answer_field_occurrences"]:
        raise ValueError("Test gold unexpectedly exposed; quarantine source")
    admitted = check_frozen_r5c_rejects_real_text()
    if not admitted:
        raise RuntimeError("R5C unexpectedly attempted inference on real external data")
    return {
        "schema": "janus.demihead.tachyon.r5d.external_source_qualification.v1",
        "status": "EXTERNAL_PUBLIC_CORPORA_VERIFIED__BLIND_MODEL_EVALUATION_HOLD",
        "datasets": files,
        "tdt": {
            "expert": {k: v for k, v in expert.items() if k != "records"},
            "crowd": {k: v for k, v in crowd.items() if k != "records"},
            "exact_row_key_overlap": len(overlap),
            "unique_matched_keys": len(comparable),
            "matched_annotation_agreements": agreements,
            "matched_annotation_disagreements": len(comparable)-agreements,
            "annotation_context": "Textual event relation annotations, not physical independently timestamped observations",
        },
        "torque": {
            "dev": torque_dev, "test": torque_test,
            "test_gold_available": False,
            "test_evaluation_policy": "Only original dataset custodians/leaderboard can score unreleased gold",
        },
        "r5c_frozen_model": {
            "source": "Hawkar-usls/Demi_Head",
            "input_schema": "janus.demihead.tachyon.r5b.synthetic_witness_input.v1",
            "r5c_safe_real_text_rejection": admitted,
            "eligible_instances": 0,
            "predictions_executed": 0,
            "accuracy": None,
            "learned_gain_percentage_points": None,
            "generalization_outcome": "NOT_EVALUABLE_SCHEMA_AND_PROVENANCE_MISMATCH",
        },
        "outside_author_data_verified": True,
        "external_blind_model_exam_completed": False,
        "independent_custodian": False,
        "physical_sensor_witnesses_authenticated": False,
        "future_target_externally_hidden": False,
        "model_weights_updated": False,
        "clinical_data_ingested": False,
        "physical_retrocausality_proven": False,
        "scientific_gate": HOLD,
        "source_admission": "Data authors/annotations are external, but labels and domain differ from authenticated physical sensor witnesses. A genuine hidden external witness exam still needs an independent custodian, a new compatible frozen evaluation contract and no leakage of target labels.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--qualify", action="store_true")
    parser.add_argument("--tdt-root", type=Path)
    parser.add_argument("--torque-root", type=Path)
    args = parser.parse_args()
    if not args.qualify or not args.tdt_root or not args.torque_root:
        parser.error("--qualify --tdt-root <path> --torque-root <path> required")
    result = qualify(args.tdt_root, args.torque_root)
    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    if result["r5c_frozen_model"]["predictions_executed"]:
        raise SystemExit("External data unexpectedly scored by old model")


if __name__ == "__main__":
    main()
