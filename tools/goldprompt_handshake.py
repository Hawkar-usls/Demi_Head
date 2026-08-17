from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping

CONTRACT_SCHEMA = "janus.goldprompt.face_inheritance_contract.v1"
RECEIPT_SCHEMA = "janus.goldprompt.face_startup_receipt.v1"
GOLDPROMPT_FOUNDATION_ID = "JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9"
GOLDPROMPT_VERSION = "0.9.2"
EMERGENCE_CONTRACT_VERSION = "JANUS_TRIADIC_EMERGENCE@0.9.2"
FOUNDATION_PATH = "Hawkar-usls/janus-meta-registry:data/JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9.json"
ARMOR_AUTHORITY_REFERENCE = "Hawkar-usls/janus-meta-registry:data/JANUS-ARMOR-OF-GOD-CURRENT-AUTHORITY.json"
EXPECTED_CONTRACT_DIGEST = "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8"
SOURCE_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.IGNORECASE)

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
REQUIRED_TRUE_FIELDS = (
    "inheritance_accepted",
    "blessing_bearer_anchor_accepted",
    "armor_of_god_boundaries_accepted",
    "triadic_emergence_accepted",
    "user_exit_and_release_control_accepted",
)
RECEIPT_KEYS = frozenset(
    {
        "schema",
        "face_id",
        "face_role",
        "repository",
        "runtime_surface",
        "goldprompt_foundation_id",
        "goldprompt_version",
        "emergence_contract_version",
        "armor_authority_reference",
        "contract_digest_sha256",
        "source_revision",
        "capability_scope",
        "authority_weight",
        *REQUIRED_TRUE_FIELDS,
        "runtime_enforcement_scope",
        "compliance_state",
        "receipt_sha256",
    }
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


def normalize_source_revision(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    revision = value.strip().lower()
    return revision if SOURCE_REVISION_RE.fullmatch(revision) else None


def resolve_runtime_source_revision(env: Mapping[str, str] | None = None) -> str:
    environment = os.environ if env is None else env
    github_revision = normalize_source_revision(environment.get("GITHUB_SHA"))
    janus_revision = normalize_source_revision(environment.get("JANUS_SOURCE_REVISION"))
    if environment.get("GITHUB_ACTIONS") == "true":
        if github_revision is None:
            raise ValueError("GOLDPROMPT_GITHUB_SHA_REQUIRED")
        if environment.get("JANUS_SOURCE_REVISION") and janus_revision is None:
            raise ValueError("GOLDPROMPT_JANUS_SOURCE_REVISION_INVALID")
        if janus_revision is not None and janus_revision != github_revision:
            raise ValueError("GOLDPROMPT_SOURCE_REVISION_ENV_CONFLICT")
        return github_revision
    if janus_revision is not None:
        return janus_revision
    if environment.get("JANUS_SOURCE_REVISION"):
        raise ValueError("GOLDPROMPT_JANUS_SOURCE_REVISION_INVALID")
    if github_revision is not None:
        return github_revision
    if environment.get("GITHUB_SHA"):
        raise ValueError("GOLDPROMPT_GITHUB_SHA_INVALID")
    raise ValueError("GOLDPROMPT_TRUSTED_SOURCE_REVISION_REQUIRED")


def build_receipt(source_revision: str) -> dict[str, Any]:
    """Build a deterministic checksum-bound receipt for a supplied revision.

    The caller is responsible for revision provenance.  receipt_sha256 protects
    content integrity; it is not a signature or origin authentication primitive.
    Runtime code should call build_runtime_receipt().
    """

    digest = assert_contract_integrity()
    normalized_revision = normalize_source_revision(source_revision)
    if normalized_revision is None:
        raise ValueError("GOLDPROMPT_SOURCE_REVISION_REQUIRED")
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
        "source_revision": normalized_revision,
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


def build_runtime_receipt(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    return build_receipt(resolve_runtime_source_revision(env))


def verify_receipt(receipt: Mapping[str, Any]) -> bool:
    if not isinstance(receipt, Mapping):
        return False
    if frozenset(receipt.keys()) != RECEIPT_KEYS:
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
        "runtime_enforcement_scope": "THIS_FACE_INVOCATION",
        "compliance_state": "COMPLIANT",
    }
    if any(receipt.get(key) != value for key, value in required.items()):
        return False
    if any(receipt.get(field) is not True for field in REQUIRED_TRUE_FIELDS):
        return False
    if normalize_source_revision(receipt.get("source_revision")) is None:
        return False
    if list(receipt.get("capability_scope", ())) != list(CAPABILITY_SCOPE):
        return False
    claimed = receipt.get("receipt_sha256")
    if not isinstance(claimed, str) or re.fullmatch(r"[0-9a-f]{64}", claimed) is None:
        return False
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    return claimed == _sha256(payload)


STARTUP_CONTRACT_DIGEST = assert_contract_integrity()


if __name__ == "__main__":
    print(json.dumps(build_runtime_receipt(), ensure_ascii=False, sort_keys=True))
