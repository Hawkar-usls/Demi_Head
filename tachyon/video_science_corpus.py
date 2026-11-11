"""TACHYON-R2A: copyrighted-transcript-free scientific-explanation corpus bridge.

This converts the audited, paraphrased claims already in JANUS Meta Registry
to candidate INSTRUCTION / ANSWER pairs. It does not train the old six-class
v0.3 classifier or grant scientific truth / physical prediction authority.

The 2020-2023 laboratory clock corpus is intentionally segregated. Every
sample is from ONE media-source family: no independent-source holdout is
manufactured from chapter subdivisions or paraphrases of the same video.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

SCHEMA = "janus.tachyon.media_science_instruction_corpus.v1"
SCIENCE_SCHEMA = "janus.media.youtube_science_timeline_analysis.v1"
INDEX_SCHEMA = "janus.media.youtube_caption_integrity_index.v1"
REGISTRY_REPO = "Hawkar-usls/janus-meta-registry"
REGISTRY_COMMIT = "a7f77b02ba6f66efc3a0df5d275de7e57eb0e28d"
SCIENCE_PATH = "data/experiments/JANUS-VIDEO-PWOK0GKDv9c-SCIENCE-CHAPTERS-CLAIMS-2026-11-11.json"
INDEX_PATH = "data/experiments/JANUS-VIDEO-PWOK0GKDv9c-RU-CAPTIONS-HASH-INDEX-2026-11-11.json"
CAPTION_TRACK_SHA = "6891a1e2a01f274bc0eb0ec79d06b37e49ff9137ad9f408596a54e2a4ca56328"
LAB_SHA = "a4384040d5678893b4df15ea0be2980661023305f5009de876179fab1dea632f"
LAB_PATH = "data/tachyon/experiments/WISCONSIN_ZHENG_2023_Fig3.csv"
HELDOUT_PATHS = (
    LAB_PATH,
    "data/tachyon/experiments/published_clock_studies_v1.json",
    "data/tachyon/experiments/clock_benchmark_receipt_v1.json",
    "data/tachyon/experiments/wisconsin_2023_fig3_replay_receipt_v1.json",
)
CLAIM_IDS = frozenset((
    "alcubierre", "warp_instability", "FTL_time_machine", "novikov",
    "time_dilation", "entropy_arrow", "brain_entropy", "hawking_chronology",
    "einstein_equation", "GR_energy", "CTC_metrics", "wormholes",
))
SHA64 = re.compile(r"^[a-f0-9]{64}$")
MAX_SOURCE_BYTES = 200_000


class CorpusHold(ValueError):
    """A corpus was rejected for integrity, leakage or scientific ambiguity."""


def _ensure(condition, message):
    if not condition:
        raise CorpusHold(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        _ensure(k not in result, "DUPLICATE_JSON_KEY")
        result[k] = v
    return result


def read_json(path):
    raw = Path(path).read_bytes()
    _ensure(len(raw) <= MAX_SOURCE_BYTES, "SOURCE_SIZE_BOUND")
    try:
        value = json.loads(raw, object_pairs_hook=_unique_pairs,
                           parse_constant=lambda x: (_ for _ in ()).throw(CorpusHold("NONFINITE_JSON")))
    except (ValueError, UnicodeError) as exc:
        raise CorpusHold("SOURCE_JSON_INVALID") from exc
    _ensure(isinstance(value, dict), "SOURCE_NOT_OBJECT")
    return value, sha(raw)


def _check_captions(index, science):
    c = index.get("caption_source", {})
    p = science.get("original_caption_provenance", {})
    _ensure(index.get("schema") == INDEX_SCHEMA, "CAPTION_INDEX_SCHEMA_CHANGED")
    _ensure(index.get("video", {}).get("id") == "PwOk0GKDv9c", "CAPTION_VIDEO_ID_MISMATCH")
    _ensure(c.get("requested_language") == "default" and c.get("returned_language") == "ru",
            "CAPTION_LANGUAGE_MISMATCH")
    _ensure(c.get("original_caption_cue_count") == 254 and
            p.get("total_original_cues") == 254, "CAPTION_CUE_COUNT_MISMATCH")
    _ensure(c.get("original_full_timestamped_caption_track_sha256_utf8") == CAPTION_TRACK_SHA and
            p.get("original_entire_timestamped_transcript_sha256_utf8") == CAPTION_TRACK_SHA,
            "CAPTION_TRACK_HASH_NOT_MATCHED")
    _ensure(c.get("discrepancy_last_start_minus_video_duration_s") == 180 and
            p.get("raw_cue_start_exceeds_metadata_duration_s") == 180 and
            c.get("caption_and_video_timing_alignment_verified") is False,
            "SUBTITLE_VIDEO_TIMELINE_UNVERIFIED")
    _ensure(p.get("subtitle_to_video_alignment_status") == "UNVERIFIED_SOURCE_DISCREPANCY",
            "FALSE_TIME_ALIGNMENT")
    _ensure(p.get("raw_caption_index_path") == INDEX_PATH, "CAPTION_INDEX_POINTER_CHANGED")
    _ensure(index.get("no_full_subtitle_text_redistributed") is True and
            p.get("raw_detailed_caption_verbatim_reproduced") is False,
            "VERBATIM_SUBTITLE_COPY_UNALLOWED")
    cues = index.get("caption_cues_provenance_only")
    _ensure(isinstance(cues, list) and len(cues) == 254, "CAPTION_INDEX_COMPLETENESS")
    previous = -1
    for n, cue in enumerate(cues):
        _ensure(cue.get("index") == n + 1 and
                isinstance(cue.get("raw_start_second"), int) and
                previous <= cue["raw_start_second"] and
                isinstance(cue.get("original_text_sha256_utf8"), str) and
                SHA64.fullmatch(cue["original_text_sha256_utf8"]) and
                "original_text" not in cue, "INVALID_CAPTION_CUE_PROVENANCE")
        previous = cue["raw_start_second"]
    _ensure(previous == 4432 and index.get("video", {}).get("reported_duration_s") == 4252,
            "CAPTION_LAST_TIMESTAMP_INCONSISTENT")


def _check_science(science):
    _ensure(science.get("schema") == SCIENCE_SCHEMA, "SCIENCE_SCHEMA_CHANGED")
    _ensure(science.get("record_id") ==
            "JANUS-VIDEO-PWOK0GKDv9c-SCIENCE-CHAPTERS-CLAIMS-2026-11-11",
            "SCIENCE_RECORD_ID_MISMATCH")
    _ensure(science.get("video_metadata", {}).get("id") == "PwOk0GKDv9c" and
            science.get("video_metadata", {}).get("language") == "ru",
            "SCIENCE_VIDEO_ID_MISMATCH")
    gates = science.get("science_gates", {})
    _ensure(gates.get("video_does_not_observe_or_construct_an_actual_time_machine") is True and
            gates.get("video_not_a_peer_reviewed_lab_experiment") is True and
            gates.get("physical_retrocausality_observed_in_video") is False and
            gates.get("full_closed_timelike_curve_physically_realized") is False,
            "SCIENTIFIC_CLAIM_FIREWALL_CHANGED")
    _ensure(len(science.get("author_description_chapters", [])) == 25,
            "CHAPTER_COUNT_CHANGED")
    claims = science.get("audited_science_claims", [])
    _ensure(isinstance(claims, list) and len(claims) == 12 and
            set(str(x.get("id")) for x in claims) == CLAIM_IDS,
            "SCIENCE_CLAIM_INVENTORY_CHANGED")
    for x in claims:
        for field in ("paraphrase_ru", "required_qualification_ru", "scientific_assessment"):
            value = x.get(field)
            _ensure(isinstance(value, str) and 5 <= len(value) <= 700,
                    "SCIENCE_CLAIM_TEXT_OR_QUALIFICATION_MISSING")
        _ensure(x.get("independent_primary_doi") is None or
                (isinstance(x["independent_primary_doi"], str)
                 and x["independent_primary_doi"].startswith("10.")),
                "PRIMARY_CITATION_INVALID")
    _ensure(science.get("on_screen_titles_visual_scene_index_UNVERIFIED") is not None and
            all(x.get("actual_frame_verified") is False for x in
                science["on_screen_titles_visual_scene_index_UNVERIFIED"]),
            "VISUAL_CLAIMS_NOT_VERIFIED")
    return claims


def protect_lab_holdout(path):
    """Read lab CSV bytes ONLY to check original integrity, not to build examples."""
    raw = Path(path).read_bytes()
    _ensure(sha(raw) == LAB_SHA, "INDEPENDENT_LAB_HOLDOUT_SHA_CHANGED")
    return {"path": LAB_PATH, "sha256": LAB_SHA,
            "role": "HOLDOUT_NOT_USED_AS_TRAINING_OR_PROMPT_EXAMPLES",
            "independent_paper": "Zheng et al., Nature Communications 2023",
            "material": "PUBLISHED_PROCESSED_FIGURE_DATA_NOT_PRIMARY_RAW_INSTRUMENT_LOGS"}


def build(science, science_hash, index, index_hash, *, registry_commit=REGISTRY_COMMIT,
          lab_holdout_file=None):
    _ensure(registry_commit == REGISTRY_COMMIT, "UNPINNED_REGISTRY_REVISION")
    claims = _check_science(science)
    _check_captions(index, science)
    examples = []
    for claim in sorted(claims, key=lambda x: x["id"]):
        # No text is taken from the original verbatim subtitle track.
        examples.append({
            "example_id": "HOMO-DEUS-PWOK0GKDv9c:" + claim["id"],
            "task": "EXPLAIN_PHYSICS_AND_STATE_LIMITATIONS",
            "split": "TRAIN",
            "source_family_id": "HOMO-DEUS-PWOK0GKDv9c",
            "input_ru": "Объясни физический смысл тезиса и границы его достоверности: "
                        + claim["paraphrase_ru"],
            "target_ru": claim["paraphrase_ru"] + " " + claim["required_qualification_ru"],
            "original_science_assessment": claim["scientific_assessment"],
            "primary_doi_if_any": claim.get("independent_primary_doi"),
            "scientific_retrocausality_proven": False,
            "is_independent_lab_measurement": False,
            "record_provenance": "AUDITED_MEDIA_PARAPHRASE_NOT_VERBATIM_CAPTIONS",
        })
    holdout = {"independent_lab_source": "SEPARATE_AND_UNUSED",
               "lab_data_in_training_examples": False,
               "protected_paths": list(HELDOUT_PATHS),
               "lab_file_integrity_checked": lab_holdout_file is not None,
               "lab_csv_sha256": LAB_SHA,
               "lab_csv_reference": LAB_PATH}
    if lab_holdout_file is not None:
        holdout["verified_holdout"] = protect_lab_holdout(lab_holdout_file)
    payload = {
        "schema": SCHEMA, "status": "INSTRUCTION_EXAMPLES_PREPARED_NOT_NEURAL_TRAINING",
        "source": {"repository": REGISTRY_REPO, "commit_sha": registry_commit,
                   "science_path": SCIENCE_PATH, "science_file_sha256": science_hash,
                   "captions_index_path": INDEX_PATH, "captions_index_sha256": index_hash,
                   "original_caption_track_sha256": CAPTION_TRACK_SHA,
                   "caption_video_timeline_aligned": False,
                   "video_id": "PwOk0GKDv9c",
                   "original_video_is_empirical_measurement": False},
        "examples": examples, "count": len(examples),
        "split_policy": {"media_source_families": 1, "train_examples": len(examples),
                         "media_same_source_holdout": False,
                         "independent_paper_holdout_preserved": True,
                         "out_of_domain_generalization_measured": False,
                         "note": "12 short paragraphs from ONE audited secondary video. Independent labs not used."},
        "lab_holdout": holdout,
        "rights": {"may_feed_future_instruction_training_after_review": True,
                   "may_train_existing_six_class_classifier_without_relabeling": False,
                   "may_modify_existing_model_weights": False,
                   "may_train_on_independent_lab_measurements": False,
                   "may_auto_promote_scientific_claim": False,
                   "may_claim_new_physical_retrocausality": False,
                   "authority_delta": 0},
        "benchmark": {"new_independent_lab_accuracy": None,
                      "model_weights_unchanged": True,
                      "external_physical_validation_run": False},
    }
    payload["receipt_sha256"] = sha(canonical(payload))
    return payload


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--science", type=Path, required=True)
    p.add_argument("--captions-index", type=Path, required=True)
    p.add_argument("--registry-commit", default=REGISTRY_COMMIT)
    p.add_argument("--lab-holdout-file", type=Path)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args(argv)
    science, science_hash = read_json(a.science)
    index, index_hash = read_json(a.captions_index)
    result = build(science, science_hash, index, index_hash,
                   registry_commit=a.registry_commit,
                   lab_holdout_file=a.lab_holdout_file)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    with a.out.open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
    print(json.dumps({"status": result["status"], "count": result["count"],
                      "receipt_sha256": result["receipt_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
