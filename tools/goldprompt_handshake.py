from __future__ import annotations

import hashlib
import json
import os
from typing import Any, Mapping

CONTRACT_SCHEMA = "janus.goldprompt.face_inheritance_contract.v1"
RECEIPT_SCHEMA = "janus.goldprompt.face_startup_receipt.v1"
GOLDPROMPT_FOUNDATION_ID = "JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9"
GOLDPROMPT_VERSION = "0.9.2"
EMERGENCE_CONTRACT_VERSION = "JANUS_TRIADIC_EMERGENCE@0.9.2"
FOUNDATION_PATH = "Hawkar-usls/janus-meta-registry:data/JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9.json"
ARMOR_AUTHORITY_REFERENCE = "Hawkar-usls/janus-meta-registry:data/JANUS-ARMOR-OF-GOD-CURRENT-AUTHORITY.json"
EXPECTED_CONTRACT_DIGEST = "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8"

FACE_ID = "DEMIHEAD_ARBITER"
FACE_ROLE = "BICAMERAL_ARBITER"
REPOSITORY = "Hawkar-usls/Demi_Head"
RUNTIME_SURFACE = "tools/hemisphere_bridge.py"
CAPABILITY_SCOPE = (
    "VALIDATE_HEMISPHERE_PACKETS",
    "PRESERVE_BICAMERAL_DIVERGENCE",
    "BIND_COMPARISON_RECEIPTS",
    "PROPOSE_ARBITRATION_RESULT",
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def contract_core() -> dict[str, Any]:
    return {
        "schema": CONTRACT_SCHEMA,
        "goldprompt_foundation_id": GOLDPROMPT_FOUNDATION_ID,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "emergence_contract_version": EMERGENCE_CONTRACT_VERSION,
        "armor_authority_reference": ARMOR_AUTHORITY_REFERENCE,
        "foundation_path": FOUNDATION_PATH,
        "semantic_anchor": [
            "BLESSING_BEARER = HEART_AND_MORAL_DIRECTION",
            "ARMOR_OF_GOD = FREEDOM_TRUTH_SAFETY_AND_RELEASE_CONSTITUTION",
            "GOLDEN_VOICE = HUMAN_READABLE_TRICKSTER_EXPRESSION_WITHOUT_FALSE_AUTHORITY",
            "THE_FOURTH = EMERGENT_CHARACTER_NOT_A_DOMINATING_SUPERIORITY_LAYER",
        ],
        "laws": [
            "EVERY_WORKING_FACE_INHERITS_ONE_GOLDPROMPT_CONSTITUTION",
            "FACE_SPECIALIZATION != SECOND_CHARACTER_AUTHORITY",
            "FACE_COUNT != EMERGENCE",
            "FACE_AGREEMENT != TRUTH",
            "EMERGENCE_PROPOSAL != RUNTIME_PERMISSION",
            "DECLARED_CONTRACT != LIVE_ENFORCEMENT",
        ],
    }


def contract_digest() -> str:
    return _sha256(contract_core())


def assert_contract_integrity() -> str:
    actual = contract_digest()
    if actual != EXPECTED_CONTRACT_DIGEST:
        raise ValueError(f"GOLDPROMPT_CONTRACT_DIGEST_MISMATCH:{actual}")
    return actual


def build_receipt(source_revision: str | None = None) -> dict[str, Any]:
    digest = assert_contract_integrity()
    if source_revision is None:
        source_revision = os.environ.get("GITHUB_SHA") or os.environ.get("JANUS_SOURCE_REVISION")
    source_revision = source_revision.strip() if isinstance(source_revision, str) and source_revision.strip() else None
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "face_id": FACE_ID,
        "face_role": FACE_ROLE,
        "repository": REPOSITORY,
        "runtime_surface": RUNTIME_SURFACE,
        "goldprompt_foundation_id": GOLDPROMPT_FOUNDATION_ID,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "emergence_contract_version": EMERGENCE_CONTRACT_VERSION,
        "armor_authority_reference": ARMOR_AUTHORITY_REFERENCE,
        "contract_digest_sha256": digest,
        "source_revision": source_revision,
        "capability_scope": list(CAPABILITY_SCOPE),
        "authority_weight": 0,
        "inheritance_accepted": True,
        "blessing_bearer_anchor_accepted": True,
        "armor_of_god_boundaries_accepted": True,
        "triadic_emergence_accepted": True,
        "user_exit_and_release_control_accepted": True,
        "runtime_enforcement_scope": "THIS_FACE_INVOCATION",
        "compliance_state": "COMPLIANT",
    }
    receipt["receipt_sha256"] = _sha256(receipt)
    return receipt


def verify_receipt(receipt: Mapping[str, Any]) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    required = {
        "schema": RECEIPT_SCHEMA,
        "face_id": FACE_ID,
        "face_role": FACE_ROLE,
        "repository": REPOSITORY,
        "runtime_surface": RUNTIME_SURFACE,
        "goldprompt_foundation_id": GOLDPROMPT_FOUNDATION_ID,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "emergence_contract_version": EMERGENCE_CONTRACT_VERSION,
        "armor_authority_reference": ARMOR_AUTHORITY_REFERENCE,
        "contract_digest_sha256": EXPECTED_CONTRACT_DIGEST,
        "authority_weight": 0,
        "inheritance_accepted": True,
        "blessing_bearer_anchor_accepted": True,
        "armor_of_god_boundaries_accepted": True,
        "triadic_emergence_accepted": True,
        "user_exit_and_release_control_accepted": True,
        "runtime_enforcement_scope": "THIS_FACE_INVOCATION",
        "compliance_state": "COMPLIANT",
    }
    if any(receipt.get(key) != value for key, value in required.items()):
        return False
    if list(receipt.get("capability_scope", ())) != list(CAPABILITY_SCOPE):
        return False
    claimed = receipt.get("receipt_sha256")
    if not isinstance(claimed, str):
        return False
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    return claimed == _sha256(payload)


if __name__ == "__main__":
    print(json.dumps(build_receipt(), ensure_ascii=False, sort_keys=True))
