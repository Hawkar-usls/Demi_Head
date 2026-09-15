#!/usr/bin/env python3
"""JANUS DemiHead Synesthetic Associative Core v1.

Consumes immutable Cousteau synesthetic research handshake packets and builds a
bounded associative-memory layer around them. The measurement fingerprint is
never recomputed, rewritten or promoted to evidence. HRAIN structural context
and iNAIHR associative context are kept as separate, provenance-bound views;
disagreement is preserved rather than averaged away.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / ".janus" / "JANUS_SYNAESTHETIC_RESEARCH_HANDSHAKE_V1.json"

CORE_ID = "JANUS_DEMIHEAD_SYNESTHETIC_ASSOCIATIVE_CORE"
CORE_VERSION = "1.0.0"
HANDSHAKE_SCHEMA = "janus.synesthesia.handshake.packet.v1"
RECEIPT_SCHEMA = "janus.demihead.synesthetic_associative_receipt.v1"
UNISON_SCHEMA = "janus.synesthesia.unison_receipt.v1"
COMPARISON_SCHEMA = "janus.demihead.synesthetic_associative_comparison.v1"
PROTOCOL_ID = "JANUS_SYNAESTHETIC_RESEARCH_HANDSHAKE"
PROTOCOL_VERSION = "1.0.0"
PROTOCOL_CONTRACT_SHA256 = "3aec527be027fc280fc9a8ace1255c9a3a7da73fc884d9b4856694a1f1530306"
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EMBED_DIMS = 16
EPISTEMIC_STATES = {"OBSERVED", "UNKNOWN", "STALE", "CONTAMINATED", "BLOCKED"}

AUTHORITY = {
    "memory_equals_truth": False,
    "mnemonic_similarity_is_scientific_similarity": False,
    "association_is_evidence": False,
    "may_change_raw_data": False,
    "may_change_calibration": False,
    "may_change_scientific_verdict": False,
    "may_reorder_review_priority": True,
    "authority_delta": 0,
    "mass_effect_budget_delta": 0,
}

FORBIDDEN_SCORE_TOKENS = {
    "verdict", "hypothesis", "interpretation", "claim", "pyramid", "target",
    "candidate", "anomaly", "h0", "h1", "h2", "artificial", "natural",
    "control_label", "class_label", "expected", "prediction", "story",
}

HEMISPHERES = {
    "LEFT_HRAIN": "STRUCTURAL_CONTEXT",
    "RIGHT_INAIHR": "ASSOCIATIVE_CONTEXT",
}


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()


def _hex64(value: Any) -> bool:
    return isinstance(value, str) and HEX64.fullmatch(value) is not None


def load_and_verify_contract() -> dict[str, Any]:
    obj = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if digest(obj) != PROTOCOL_CONTRACT_SHA256:
        raise RuntimeError("SYNAESTHETIC_HANDSHAKE_CONTRACT_HASH_MISMATCH")
    if obj.get("protocol_id") != PROTOCOL_ID or obj.get("protocol_version") != PROTOCOL_VERSION:
        raise RuntimeError("SYNAESTHETIC_HANDSHAKE_CONTRACT_ID_MISMATCH")
    return obj


def _finite_embedding(value: Any) -> bool:
    return (
        isinstance(value, list)
        and len(value) == EMBED_DIMS
        and all(isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(float(x)) for x in value)
    )


def verify_cousteau_packet(packet: Mapping[str, Any]) -> bool:
    """Fail-closed verification of a Cousteau-produced handshake packet."""
    if not isinstance(packet, Mapping) or packet.get("schema") != HANDSHAKE_SCHEMA:
        return False
    if packet.get("protocol_id") != PROTOCOL_ID or packet.get("protocol_version") != PROTOCOL_VERSION:
        return False
    if packet.get("contract_sha256") != PROTOCOL_CONTRACT_SHA256:
        return False
    producer = packet.get("producer")
    if not isinstance(producer, Mapping):
        return False
    if producer.get("repository") != "Hawkar-usls/Janus-Cosmos":
        return False
    if producer.get("role") != "COUSTEAU_MEASUREMENT_SENSORY_CORE":
        return False
    if not isinstance(packet.get("event_id"), str) or not packet["event_id"].strip():
        return False
    if packet.get("authority") != AUTHORITY:
        return False
    if packet.get("scientific_convergence_claim") is not False:
        return False
    claimed = packet.get("packet_sha256")
    if not _hex64(claimed):
        return False
    replay = dict(packet)
    replay.pop("packet_sha256", None)
    if digest(replay) != claimed:
        return False
    epistemic = packet.get("epistemic_state")
    if not isinstance(epistemic, Mapping) or epistemic.get("overall_state") not in EPISTEMIC_STATES:
        return False
    quality = epistemic.get("retrieval_quality_score")
    if not isinstance(quality, (int, float)) or isinstance(quality, bool) or not math.isfinite(float(quality)) or not (0.0 <= float(quality) <= 1.0):
        return False
    if epistemic.get("truth_confidence") is not None:
        return False
    fp = packet.get("measurement_fingerprint")
    if fp is None:
        return epistemic.get("overall_state") == "BLOCKED" and packet.get("scientific_measurement_use_allowed") is False
    if not isinstance(fp, Mapping):
        return False
    if not _hex64(fp.get("sha256")) or not _hex64(fp.get("blake2b_256")):
        return False
    if not _finite_embedding(fp.get("embedding")):
        return False
    if not isinstance(fp.get("feature_count"), int) or isinstance(fp.get("feature_count"), bool) or fp["feature_count"] < 1:
        return False
    if not _hex64(fp.get("feature_names_sha256")) or not _hex64(fp.get("units_sha256")):
        return False
    return True


def _source_key(packet: Mapping[str, Any]) -> str:
    binding = packet.get("source_binding")
    if isinstance(binding, Mapping) and _hex64(binding.get("source_raw_sha256")):
        return "RAW:" + str(binding["source_raw_sha256"])
    identity = packet.get("source_identity")
    if isinstance(identity, Mapping) and _hex64(identity.get("source_sha256")):
        return str(identity.get("source_hash_kind", "SOURCE")) + ":" + str(identity["source_sha256"])
    return "UNBOUND:" + digest(packet.get("source_identity") or {})


def _context_view(value: Mapping[str, Any] | None, hemisphere: str) -> dict[str, Any]:
    if hemisphere not in HEMISPHERES:
        raise ValueError("unknown hemisphere")
    raw = dict(value or {})
    canonical = canonical_json(raw)
    labels: list[str] = []
    ignored_for_score: list[str] = []
    for key, val in sorted(raw.items(), key=lambda kv: str(kv[0])):
        text = f"{key}:{val}".strip()
        slug = re.sub(r"[^a-z0-9]+", "_", text.casefold()).strip("_")
        if any(tok in slug for tok in FORBIDDEN_SCORE_TOKENS):
            ignored_for_score.append(text)
        else:
            labels.append(text)
    return {
        "hemisphere": hemisphere,
        "role": HEMISPHERES[hemisphere],
        "context_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "inspectable_labels": labels,
        "ignored_for_similarity_score": ignored_for_score,
        "raw_context": raw,
        "authority": "ANNOTATION_ONLY",
    }


def _stable_associative_tags(packet: Mapping[str, Any]) -> list[str]:
    """Tags from sensory/epistemic transport fields only, never story context."""
    tags: list[str] = []
    sensory = packet.get("sensory_summary") or {}
    context = packet.get("context") or {}
    epistemic = packet.get("epistemic_state") or {}
    for name in ("color_hex", "audio_mode", "texture"):
        value = sensory.get(name)
        if value is not None:
            tags.append(f"SENSE.{name.upper()}={value}")
    tone = sensory.get("audio_frequency_hz")
    if isinstance(tone, (int, float)) and not isinstance(tone, bool):
        octave = int(round(12 * math.log2(max(float(tone), 1e-9) / 440.0)))
        tags.append(f"SENSE.TONE_BIN={octave}")
    for name in ("direction", "scale"):
        value = context.get(name)
        if value is not None:
            tags.append(f"CONTEXT.{name.upper()}={value}")
    tags.append(f"EPISTEMIC.STATE={epistemic.get('overall_state')}")
    tags.append(f"EPISTEMIC.QUALITY={epistemic.get('quality_band')}")
    return sorted(set(tags))


def build_associative_receipt(
    packet: Mapping[str, Any],
    *,
    structural_context: Mapping[str, Any] | None = None,
    associative_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    load_and_verify_contract()
    if not verify_cousteau_packet(packet):
        raise ValueError("COUSTEAU_SYNAESTHETIC_PACKET_INVALID")

    fp = packet.get("measurement_fingerprint")
    blocked = fp is None
    left = _context_view(structural_context, "LEFT_HRAIN")
    right = _context_view(associative_context, "RIGHT_INAIHR")
    tags = [] if blocked else _stable_associative_tags(packet)
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "core": {"id": CORE_ID, "version": CORE_VERSION},
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "contract_sha256": PROTOCOL_CONTRACT_SHA256,
        "source_packet_sha256": packet["packet_sha256"],
        "event_id": packet["event_id"],
        "source_key": _source_key(packet),
        "status": "BLOCKED_HOLD" if blocked else "ASSOCIATIVE_MEMORY_READY",
        "measurement_fingerprint": None if blocked else json.loads(json.dumps(fp)),
        "measurement_fingerprint_bit_preserved": True,
        "sensory_digest": packet.get("sensory_digest"),
        "sensory_summary": json.loads(json.dumps(packet.get("sensory_summary") or {})),
        "epistemic_state": json.loads(json.dumps(packet.get("epistemic_state") or {})),
        "hemisphere_views": {"LEFT_HRAIN": left, "RIGHT_INAIHR": right},
        "associative_tags": tags,
        "routing": {
            "mode": "HOLD" if blocked else "BICAMERAL_ASSOCIATIVE_REVIEW",
            "disagreement_preserved": True,
            "automatic_graph_merge_performed": False,
            "external_effect_permitted": False,
            "direct_measurement_write_permitted": False,
        },
        "authority": dict(AUTHORITY),
        "truth_claim_made": False,
        "scientific_convergence_claim": False,
        "evidence_admission_performed": False,
    }
    receipt["receipt_sha256"] = digest(receipt)
    if not verify_associative_receipt(packet, receipt):
        raise RuntimeError("DEMIHEAD_ASSOCIATIVE_RECEIPT_SELF_VERIFY_FAILED")
    return receipt


def verify_associative_receipt(packet: Mapping[str, Any], receipt: Mapping[str, Any]) -> bool:
    if not verify_cousteau_packet(packet):
        return False
    if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
        return False
    if receipt.get("protocol_id") != PROTOCOL_ID or receipt.get("protocol_version") != PROTOCOL_VERSION or receipt.get("contract_sha256") != PROTOCOL_CONTRACT_SHA256:
        return False
    if receipt.get("source_packet_sha256") != packet.get("packet_sha256") or receipt.get("event_id") != packet.get("event_id"):
        return False
    if receipt.get("authority") != AUTHORITY:
        return False
    if receipt.get("truth_claim_made") is not False or receipt.get("scientific_convergence_claim") is not False or receipt.get("evidence_admission_performed") is not False:
        return False
    if receipt.get("measurement_fingerprint_bit_preserved") is not True:
        return False
    if receipt.get("measurement_fingerprint") != packet.get("measurement_fingerprint"):
        return False
    routing = receipt.get("routing")
    if not isinstance(routing, Mapping) or routing.get("disagreement_preserved") is not True or routing.get("automatic_graph_merge_performed") is not False:
        return False
    claimed = receipt.get("receipt_sha256")
    if not _hex64(claimed):
        return False
    replay = dict(receipt)
    replay.pop("receipt_sha256", None)
    return digest(replay) == claimed


def _cosine(a: Sequence[float], b: Sequence[float]) -> float | None:
    if len(a) != len(b) or not a:
        return None
    na = math.sqrt(sum(float(x) * float(x) for x in a))
    nb = math.sqrt(sum(float(x) * float(x) for x in b))
    if na == 0.0 or nb == 0.0:
        return None
    return max(-1.0, min(1.0, sum(float(x) * float(y) for x, y in zip(a, b)) / (na * nb)))


def compare_associative_receipts(a: Mapping[str, Any], b: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(a, Mapping) or not isinstance(b, Mapping) or a.get("schema") != RECEIPT_SCHEMA or b.get("schema") != RECEIPT_SCHEMA:
        raise ValueError("associative receipts required")
    fa = a.get("measurement_fingerprint")
    fb = b.get("measurement_fingerprint")
    same_identity = a.get("event_id") == b.get("event_id") and a.get("source_key") == b.get("source_key")
    if fa is None or fb is None:
        status = "BLOCKED_OR_INCOMPARABLE"
        cosine = None
    elif same_identity and fa.get("sha256") != fb.get("sha256"):
        status = "PROVENANCE_CONFLICT_HOLD"
        cosine = _cosine(fa.get("embedding") or [], fb.get("embedding") or [])
    elif fa.get("sha256") == fb.get("sha256"):
        status = "IDENTICAL_MEASUREMENT_MEMORY"
        cosine = 1.0
    else:
        status = "MNEMONIC_NEIGHBOR_ONLY"
        cosine = _cosine(fa.get("embedding") or [], fb.get("embedding") or [])

    qa = float((a.get("epistemic_state") or {}).get("retrieval_quality_score", 0.0))
    qb = float((b.get("epistemic_state") or {}).get("retrieval_quality_score", 0.0))
    review = None if cosine is None else round(max(0.0, (cosine + 1.0) / 2.0) * math.sqrt(max(0.0, qa) * max(0.0, qb)), 6)
    return {
        "schema": COMPARISON_SCHEMA,
        "status": status,
        "event_a": a.get("event_id"),
        "event_b": b.get("event_id"),
        "same_event_and_source_identity": same_identity,
        "mnemonic_cosine": None if cosine is None else round(float(cosine), 12),
        "quality_adjusted_review_score": review,
        "semantic_story_context_used_in_score": False,
        "disagreement_preserved": True,
        "scientific_convergence_claim": False,
        "evidence_admission_performed": False,
        "authority": "REVIEW_PRIORITY_OR_CONFLICT_HOLD_ONLY",
    }


@dataclass
class AssociativeMemoryIndex:
    """Small deterministic in-memory research index; no persistence authority."""
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def add(self, receipt: Mapping[str, Any]) -> dict[str, Any]:
        if not isinstance(receipt, Mapping) or receipt.get("schema") != RECEIPT_SCHEMA:
            raise ValueError("invalid associative receipt")
        candidate = json.loads(json.dumps(receipt))
        for existing in self.receipts:
            if existing.get("event_id") == candidate.get("event_id") and existing.get("source_key") == candidate.get("source_key"):
                ef = existing.get("measurement_fingerprint")
                cf = candidate.get("measurement_fingerprint")
                if isinstance(ef, Mapping) and isinstance(cf, Mapping) and ef.get("sha256") != cf.get("sha256"):
                    return {
                        "status": "PROVENANCE_CONFLICT_HOLD",
                        "event_id": candidate.get("event_id"),
                        "existing_receipt_sha256": existing.get("receipt_sha256"),
                        "incoming_receipt_sha256": candidate.get("receipt_sha256"),
                        "stored": False,
                        "scientific_claim": False,
                    }
                if existing.get("receipt_sha256") == candidate.get("receipt_sha256"):
                    return {"status": "IDEMPOTENT_PRESENT", "stored": False, "scientific_claim": False}
        self.receipts.append(candidate)
        self.receipts.sort(key=lambda r: (str(r.get("event_id")), str(r.get("receipt_sha256"))))
        return {"status": "STORED_FOR_RETRIEVAL_ONLY", "stored": True, "scientific_claim": False}

    def query(self, receipt: Mapping[str, Any], top_k: int = 5) -> list[dict[str, Any]]:
        if top_k < 1:
            raise ValueError("top_k must be >= 1")
        rows: list[dict[str, Any]] = []
        for other in self.receipts:
            cmp = compare_associative_receipts(receipt, other)
            rows.append({
                "receipt_sha256": other.get("receipt_sha256"),
                "event_id": other.get("event_id"),
                **cmp,
            })
        rows.sort(
            key=lambda r: (
                r["status"] == "PROVENANCE_CONFLICT_HOLD",
                -1.0 if r["quality_adjusted_review_score"] is None else r["quality_adjusted_review_score"],
                str(r.get("event_id")),
            ),
            reverse=True,
        )
        return rows[:top_k]


def build_unison_receipt(cousteau_packet: Mapping[str, Any], demihead_receipt: Mapping[str, Any]) -> dict[str, Any]:
    if not verify_cousteau_packet(cousteau_packet):
        raise ValueError("COUSTEAU_PACKET_INVALID")
    if not verify_associative_receipt(cousteau_packet, demihead_receipt):
        raise ValueError("DEMIHEAD_RECEIPT_INVALID")
    fp = cousteau_packet.get("measurement_fingerprint")
    out: dict[str, Any] = {
        "schema": UNISON_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "contract_sha256": PROTOCOL_CONTRACT_SHA256,
        "cousteau": {
            "repository": "Hawkar-usls/Janus-Cosmos",
            "packet_sha256": cousteau_packet["packet_sha256"],
            "event_id": cousteau_packet["event_id"],
            "measurement_fingerprint_sha256": None if fp is None else fp.get("sha256"),
        },
        "demihead": {
            "repository": "Hawkar-usls/Demi_Head",
            "receipt_sha256": demihead_receipt["receipt_sha256"],
            "measurement_fingerprint_sha256": None if demihead_receipt.get("measurement_fingerprint") is None else demihead_receipt["measurement_fingerprint"].get("sha256"),
        },
        "cousteau_measurement_fingerprint_bit_preserved": demihead_receipt.get("measurement_fingerprint") == fp,
        "disagreement_preserved": True,
        "route": "COUSTEAU_MEASUREMENT_SENSORY_CORE -> DEMIHEAD_ASSOCIATIVE_MEMORY_CORE -> HUMAN_REVIEW",
        "scientific_convergence_claim": False,
        "evidence_admission_performed": False,
        "authority": dict(AUTHORITY),
    }
    if out["cousteau_measurement_fingerprint_bit_preserved"] is not True:
        raise RuntimeError("MEASUREMENT_FINGERPRINT_MUTATION_DETECTED")
    out["unison_sha256"] = digest(out)
    return out


def _fixture_packet(*, event_id: str = "SYNTH-001", fingerprint_seed: str = "A", blocked: bool = False) -> dict[str, Any]:
    embedding = [0.0] * EMBED_DIMS
    embedding[0] = 1.0 if fingerprint_seed == "A" else 0.99
    embedding[1] = 0.0 if fingerprint_seed == "A" else 0.1
    fp = None if blocked else {
        "sha256": hashlib.sha256(("fp:" + fingerprint_seed).encode()).hexdigest(),
        "blake2b_256": hashlib.blake2b(("fp:" + fingerprint_seed).encode(), digest_size=32).hexdigest(),
        "embedding": embedding,
        "feature_count": 4,
        "feature_names_sha256": hashlib.sha256(b"features").hexdigest(),
        "units_sha256": hashlib.sha256(b"units").hexdigest(),
    }
    epistemic = {
        "overall_state": "BLOCKED" if blocked else "OBSERVED",
        "counts": {"OBSERVED": 0 if blocked else 4, "UNKNOWN": 0, "STALE": 0, "CONTAMINATED": 0, "BLOCKED": 1 if blocked else 0},
        "coverage_fraction": 0.0 if blocked else 1.0,
        "missing_fraction": 1.0 if blocked else 0.0,
        "unknown_fraction": 1.0 if blocked else 0.0,
        "stale_fraction": 0.0,
        "contaminated_fraction": 0.0,
        "retrieval_quality_score": 0.0 if blocked else 1.0,
        "quality_band": "BLOCKED" if blocked else "HIGH",
        "truth_confidence": None,
        "rule": "RETRIEVAL_QUALITY_NE_TRUTH_CONFIDENCE",
    }
    packet: dict[str, Any] = {
        "schema": HANDSHAKE_SCHEMA,
        "protocol_id": PROTOCOL_ID,
        "protocol_version": PROTOCOL_VERSION,
        "contract_sha256": PROTOCOL_CONTRACT_SHA256,
        "event_id": event_id,
        "producer": {"repository": "Hawkar-usls/Janus-Cosmos", "role": "COUSTEAU_MEASUREMENT_SENSORY_CORE", "core_id": "fixture", "core_version": "2.0.0"},
        "source_identity": {"source_hash_kind": "CANONICAL_JSON_SHA256_NOT_RAW_FILE_HASH", "source_sha256": hashlib.sha256(b"same-source").hexdigest()},
        "source_binding": {"status": "UNBOUND_SYNTHETIC_OR_GENERIC", "source_raw_sha256": None, "parser_sha256": None, "window_id": None},
        "context": {"direction": "HEAD_FORWARD", "scale": "60s"},
        "measurement_fingerprint": fp,
        "sensory_digest": hashlib.sha256(("sensory:" + fingerprint_seed).encode()).hexdigest(),
        "sensory_summary": {"color_hex": "#8080AA", "audio_mode": "SILENCE" if blocked else "TONE", "audio_frequency_hz": None if blocked else 220.0, "texture": "fog" if blocked else "smooth", "semantic_overlay_sha256": None},
        "epistemic_state": epistemic,
        "authority": dict(AUTHORITY),
        "scientific_measurement_use_allowed": False,
        "scientific_convergence_claim": False,
    }
    packet["packet_sha256"] = digest(packet)
    return packet


def self_test() -> dict[str, Any]:
    load_and_verify_contract()
    packet = _fixture_packet()
    receipt = build_associative_receipt(
        packet,
        structural_context={"geometry": "track-window", "hypothesis": "must not score"},
        associative_context={"memory": "known-neighbor", "target": "must not score"},
    )
    blocked = _fixture_packet(event_id="BLOCKED", blocked=True)
    blocked_receipt = build_associative_receipt(blocked)
    unison = build_unison_receipt(packet, receipt)
    conflict_packet = _fixture_packet(event_id="SYNTH-001", fingerprint_seed="B")
    conflict_receipt = build_associative_receipt(conflict_packet)
    checks = {
        "contract_hash": digest(load_and_verify_contract()) == PROTOCOL_CONTRACT_SHA256,
        "packet_verified": verify_cousteau_packet(packet),
        "fingerprint_bit_preserved": receipt["measurement_fingerprint"] == packet["measurement_fingerprint"],
        "blocked_no_association_fabrication": blocked_receipt["associative_tags"] == [] and blocked_receipt["status"] == "BLOCKED_HOLD",
        "forbidden_story_context_not_scored": bool(receipt["hemisphere_views"]["LEFT_HRAIN"]["ignored_for_similarity_score"]) and bool(receipt["hemisphere_views"]["RIGHT_INAIHR"]["ignored_for_similarity_score"]),
        "conflict_detected": compare_associative_receipts(receipt, conflict_receipt)["status"] == "PROVENANCE_CONFLICT_HOLD",
        "unison_preserves_fingerprint": unison["cousteau_measurement_fingerprint_bit_preserved"] is True,
        "science_claim_false": unison["scientific_convergence_claim"] is False,
    }
    return {"status": "PASS" if all(checks.values()) else "FAIL", "checks": checks}


if __name__ == "__main__":
    result = self_test()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
