from __future__ import annotations

import hashlib
import json
from typing import Any, Iterable

SCHEMA = "janus.nohand.pair.message.v1"
CONTRACT = "JANUS_NOHAND_PAIR_V1"

NAS_HEAD = "NAS_NOHAND"
DEMIHEAD_HEAD = "DEMIHEAD_NOHAND"
ACTORS = frozenset({NAS_HEAD, DEMIHEAD_HEAD})

KINDS = frozenset({
    "OFFER",
    "REQUEST",
    "DECISION",
    "RECEIPT",
    "HOLD",
    "LEARNING_OBSERVATION",
})

GOLDPROMPT_VERSION = "0.9.2"
GOLDPROMPT_CONTRACT = "JANUS_TRIADIC_EMERGENCE@0.9.2"
GOLDPROMPT_CONTRACT_DIGEST = "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8"

CONTROL_TEMPLATE = {
    "authority_weight": 0,
    "authority_delta": 0,
    "mass_effect_budget_delta": 0,
    "delete_permitted": False,
    "move_permitted": False,
    "rename_permitted": False,
    "direct_cross_workspace_mutation": False,
    "automatic_external_effect_permitted": False,
    "message_is_command": False,
}

def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")

def sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()

def _hex64(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value.lower())

def _validate_object_ref(ref: dict[str, Any]) -> None:
    required = ("sha256", "size", "origin_kind")
    if any(key not in ref for key in required):
        raise ValueError("object_ref requires sha256, size and origin_kind")
    if not _hex64(ref["sha256"]):
        raise ValueError("object_ref.sha256 invalid")
    size = ref["size"]
    if isinstance(size, bool) or not isinstance(size, int) or size < 0:
        raise ValueError("object_ref.size invalid")
    if ref["origin_kind"] not in {"NAS_LOCAL", "GIT_REPOSITORY", "GIT_EXCHANGE"}:
        raise ValueError("object_ref.origin_kind invalid")
    locator = ref.get("locator")
    if locator is not None and not isinstance(locator, dict):
        raise ValueError("object_ref.locator must be an object")
    for key in ("path", "repository", "ref", "branch"):
        if locator and key in locator and not isinstance(locator[key], str):
            raise ValueError(f"object_ref.locator.{key} invalid")

def validate_prediction(prediction: dict[str, Any]) -> None:
    if not isinstance(prediction, dict):
        raise ValueError("prediction must be an object")
    if prediction.get("schema") != "janus.nohand.operational_forecast.v1":
        raise ValueError("prediction schema mismatch")
    p = prediction.get("p_success")
    if isinstance(p, bool) or not isinstance(p, (int, float)) or not 0.0 <= float(p) <= 1.0:
        raise ValueError("prediction.p_success invalid")
    if prediction.get("authority_weight") != 0:
        raise ValueError("prediction authority_weight must be zero")
    if prediction.get("claim_ceiling") != "OPERATIONAL_FORECAST_NOT_TRUTH":
        raise ValueError("prediction claim ceiling mismatch")
    if not isinstance(prediction.get("selection_process_root"), str) or not prediction["selection_process_root"]:
        raise ValueError("prediction.selection_process_root required")
    if not isinstance(prediction.get("action_event_root"), str) or not prediction["action_event_root"]:
        raise ValueError("prediction.action_event_root required")

def validate_guard(guard: dict[str, Any]) -> None:
    if not isinstance(guard, dict):
        raise ValueError("guard must be an object")
    if not _hex64(guard.get("safety_contract_sha256")):
        raise ValueError("guard safety contract digest invalid")
    if guard.get("guardian_of_guardian") != "PASS":
        raise ValueError("guardian-of-guardian must PASS")
    if guard.get("mutation_frozen") is not False:
        raise ValueError("mutation must not be frozen for actionable message")
    sentinel = guard.get("preservation_sentinel")
    if sentinel not in {"PASS", "NOT_APPLICABLE_APPEND_ONLY_GIT"}:
        raise ValueError("preservation sentinel status invalid")
    if guard.get("destructive_permissions") not in ([], ()):
        raise ValueError("destructive permissions must be empty")

def build_message(*, message_id: str, sender: str, target: str, kind: str, source_revision: str, object_ref: dict[str, Any] | None = None, decision: dict[str, Any] | None = None, prediction: dict[str, Any] | None = None, guard: dict[str, Any], references: dict[str, Any] | None = None) -> dict[str, Any]:
    msg = {
        "schema": SCHEMA,
        "contract": CONTRACT,
        "message_id": message_id,
        "sender": sender,
        "target": target,
        "kind": kind,
        "source_revision": source_revision,
        "goldprompt": {
            "version": GOLDPROMPT_VERSION,
            "emergence_contract": GOLDPROMPT_CONTRACT,
            "contract_digest_sha256": GOLDPROMPT_CONTRACT_DIGEST,
        },
        "object_ref": json.loads(json.dumps(object_ref)) if object_ref is not None else None,
        "decision": json.loads(json.dumps(decision)) if decision is not None else None,
        "prediction": json.loads(json.dumps(prediction)) if prediction is not None else None,
        "guard": json.loads(json.dumps(guard)),
        "references": json.loads(json.dumps(references or {})),
        "control": dict(CONTROL_TEMPLATE),
    }
    msg["message_sha256"] = sha256(msg)
    validate_message(msg)
    return msg

def validate_message(message: dict[str, Any]) -> None:
    if not isinstance(message, dict) or message.get("schema") != SCHEMA:
        raise ValueError("NOHAND message schema mismatch")
    if message.get("contract") != CONTRACT:
        raise ValueError("NOHAND contract mismatch")
    if message.get("sender") not in ACTORS or message.get("target") not in ACTORS:
        raise ValueError("unknown NOHAND actor")
    if message["sender"] == message["target"]:
        raise ValueError("NOHAND sender and target must differ")
    if message.get("kind") not in KINDS:
        raise ValueError("NOHAND kind invalid")
    if not isinstance(message.get("message_id"), str) or not message["message_id"].strip():
        raise ValueError("message_id required")
    if not isinstance(message.get("source_revision"), str) or not message["source_revision"].strip():
        raise ValueError("source_revision required")

    gold = message.get("goldprompt")
    if not isinstance(gold, dict):
        raise ValueError("goldprompt binding required")
    if gold.get("version") != GOLDPROMPT_VERSION or gold.get("emergence_contract") != GOLDPROMPT_CONTRACT or gold.get("contract_digest_sha256") != GOLDPROMPT_CONTRACT_DIGEST:
        raise ValueError("goldprompt binding mismatch")
    if message.get("control") != CONTROL_TEMPLATE:
        raise ValueError("NOHAND control boundary mismatch")
    validate_guard(message.get("guard"))

    kind = message["kind"]
    obj = message.get("object_ref")
    if kind in {"OFFER", "REQUEST", "RECEIPT"}:
        if not isinstance(obj, dict):
            raise ValueError(f"{kind} requires object_ref")
        _validate_object_ref(obj)
    elif obj is not None:
        _validate_object_ref(obj)
    pred = message.get("prediction")
    if pred is not None:
        validate_prediction(pred)
    decision = message.get("decision")
    if kind in {"DECISION", "HOLD"}:
        if not isinstance(decision, dict):
            raise ValueError(f"{kind} requires decision")
        state = decision.get("state")
        if state not in {"REQUEST_COPY", "ACCEPT", "HOLD", "REJECT", "VERIFY_ONLY"}:
            raise ValueError("decision state invalid")
        if state in {"HOLD", "REJECT"} and not isinstance(decision.get("reason"), str):
            raise ValueError("HOLD/REJECT reason required")
    claimed = message.get("message_sha256")
    if not _hex64(claimed):
        raise ValueError("message_sha256 invalid")
    unsigned = dict(message)
    unsigned.pop("message_sha256", None)
    if claimed != sha256(unsigned):
        raise ValueError("message hash binding mismatch")

def make_nexus_envelope(message: dict[str, Any]) -> dict[str, Any]:
    validate_message(message)
    return {
        "schema": "janus.demihead.nexus_envelope.v1",
        "contract": "JANUS_NEXUS_HABITAT_V1",
        "envelope_id": f"nohand:{message['message_id']}",
        "source_head": message["sender"],
        "target_head": message["target"],
        "payload_kind": f"NOHAND_{message['kind']}",
        "payload_ref": {
            "sha256": message["message_sha256"],
            "locator": "git://janus-io/gate/terminal-copy-v1/habitat/terminal/nohand/channel",
        },
        "trace": [],
        "control": {
            "read_only_transfer": True,
            "direct_workspace_mutation": False,
            "external_effect_permitted": False,
            "authority_delta": 0,
            "mass_effect_budget_delta": 0,
            "ttl_hops": 4,
        },
    }

def descriptive_selection_concentration(selection_roots: Iterable[str]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    total = 0
    for root in selection_roots:
        if not isinstance(root, str) or not root:
            continue
        counts[root] = counts.get(root, 0) + 1
        total += 1
    if total == 0:
        return {"observation_count": 0, "selection_family_count": 0, "herfindahl_descriptive_only": None, "claim_ceiling": "DESCRIPTIVE_SELECTION_CONCENTRATION_ONLY"}
    hhi = sum((count / total) ** 2 for count in counts.values())
    return {
        "observation_count": total,
        "selection_family_count": len(counts),
        "families": dict(sorted(counts.items())),
        "herfindahl_descriptive_only": hhi,
        "claim_ceiling": "DESCRIPTIVE_SELECTION_CONCENTRATION_ONLY",
        "laws": ["PRESENTATION_COUNT != ACTION_EVENT_ROOT_COUNT", "SELECTION_FAMILY_COUNT != EFFECTIVE_SAMPLE_SIZE", "OPERATIONAL_FORECAST != TRUTH"],
    }
