from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Mapping

CONTRACT_SCHEMA = "janus.goldprompt.face_inheritance_contract.v1"
RECEIPT_SCHEMA = "janus.goldprompt.face_startup_receipt.v1_1"
DEPENDENCY_MANIFEST_SCHEMA = "janus.goldprompt.transitive_dependency_manifest.v1"
GOLDPROMPT_FOUNDATION_ID = "JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9"
GOLDPROMPT_VERSION = "0.9.2"
EMERGENCE_CONTRACT_VERSION = "JANUS_TRIADIC_EMERGENCE@0.9.2"
FOUNDATION_PATH = "Hawkar-usls/janus-meta-registry:data/JANUS-THE-FOURTH-GRACEWARDEN-3IN1-EQUALS-4-v0.9.json"
ARMOR_AUTHORITY_REFERENCE = "Hawkar-usls/janus-meta-registry:data/JANUS-ARMOR-OF-GOD-CURRENT-AUTHORITY.json"
DEPENDENCY_MANIFEST_REFERENCE = "Hawkar-usls/janus-meta-registry:data/JANUS-GOLDPROMPT-TRANSITIVE-CONSTITUTIONAL-DEPENDENCY-MANIFEST-v1.0.json"
EXPECTED_CONTRACT_DIGEST = "3f4af369350710ad18920dfdc866d930c8d42259a51a3f27ce228ea4d5dfc0a8"
EXPECTED_DEPENDENCY_MANIFEST_DIGEST = "4bd935ae033c80f090b91a6a5009a51abeb06b99defdc8836763bd9506023a86"
SOURCE_REVISION_RE = re.compile(r"^(?:[0-9a-f]{40}|[0-9a-f]{64})$", re.IGNORECASE)
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")

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

UPSTREAM_FACE_SPECS: dict[str, dict[str, Any]] = {
    "LEFT_HRAIN": {
        "face_id": "LEFT_HRAIN",
        "face_role": "STRUCTURAL_CONTEXT",
        "repository": "Hawkar-usls/Hrain",
        "runtime_surface": "habitat-tool.js",
        "capability_scope": [
            "READ_LOCAL_WORKSPACE_STRUCTURE",
            "BUILD_READ_ONLY_HEMISPHERE_PACKET",
            "PROPOSE_STRUCTURAL_CONTEXT",
        ],
    },
    "RIGHT_INAIHR": {
        "face_id": "RIGHT_INAIHR",
        "face_role": "ASSOCIATIVE_CONTEXT",
        "repository": "Hawkar-usls/iNaiHR",
        "runtime_surface": "habitat-tool.js",
        "capability_scope": [
            "READ_GROUNDED_SEMANTIC_RECORDS",
            "BUILD_ASSOCIATIVE_CONTEXT",
            "PROPOSE_SEMANTIC_SYNTH",
        ],
    },
}

REQUIRED_TRUE_FIELDS = (
    "inheritance_accepted",
    "blessing_bearer_anchor_accepted",
    "armor_of_god_boundaries_accepted",
    "triadic_emergence_accepted",
    "user_exit_and_release_control_accepted",
)
RECEIPT_KEYS = frozenset({
    "schema", "face_id", "face_role", "repository", "runtime_surface",
    "goldprompt_foundation_id", "goldprompt_version", "emergence_contract_version",
    "armor_authority_reference", "contract_digest_sha256",
    "dependency_manifest_reference", "dependency_manifest_digest_sha256",
    "source_revision", "capability_scope", "authority_weight", *REQUIRED_TRUE_FIELDS,
    "runtime_enforcement_scope", "compliance_state", "receipt_sha256",
})


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


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


def dependency_manifest_core() -> dict[str, Any]:
    return {
        "schema": DEPENDENCY_MANIFEST_SCHEMA,
        "artifact_id": "JANUS-GOLDPROMPT-TRANSITIVE-CONSTITUTIONAL-DEPENDENCY-MANIFEST-v1.0",
        "status": "PINNED_CONSTITUTIONAL_DEPENDENCIES",
        "goldprompt_version": GOLDPROMPT_VERSION,
        "contract_digest_sha256": EXPECTED_CONTRACT_DIGEST,
        "registry_snapshot": {
            "repository": "Hawkar-usls/janus-meta-registry",
            "commit_sha": "02ac40a5189c7dbd0b1e1842ddacddad58adb367",
        },
        "dependencies": [
            {
                "role": "GOLDPROMPT_CONTRACT_CORE_SNAPSHOT",
                "repository": "Hawkar-usls/janus-meta-registry",
                "path": "data/JANUS-GOLDPROMPT-FACE-INHERITANCE-CONTRACT-SNAPSHOT-v0.9.2.json",
                "commit_sha": "02ac40a5189c7dbd0b1e1842ddacddad58adb367",
                "git_blob_sha": "60cd8ba9c08bd16acb92e66bc1525173eecd0408",
                "required": True,
                "mutability": "FROZEN_SNAPSHOT",
            },
            {
                "role": "ARMOR_OF_GOD_CURRENT_AUTHORITY_SNAPSHOT",
                "repository": "Hawkar-usls/janus-meta-registry",
                "path": "data/JANUS-ARMOR-OF-GOD-CURRENT-AUTHORITY.json",
                "commit_sha": "02ac40a5189c7dbd0b1e1842ddacddad58adb367",
                "git_blob_sha": "37da812307efc8c9ffeb1ec866b9cb102facf352",
                "required": True,
                "mutability": "MUTABLE_POINTER_PINNED_AT_THIS_MANIFEST",
            },
        ],
        "verification_contract": {
            "receipt_must_bind_manifest_digest": True,
            "runtime_network_fetch_required": False,
            "external_verifier_resolves_pins": True,
            "dependency_change_requires_new_manifest_version": True,
            "authority_delta": 0,
        },
        "claim_boundaries": [
            "MANIFEST_DIGEST_BINDS_THE_PIN_SET_NOT_LIVE_MAIN",
            "PINNED_GIT_BLOB != DIGITAL_SIGNATURE",
            "TRANSITIVE_PINNING != LIVE_NAS_ATTESTATION",
            "DEPENDENCY_CHANGE_REQUIRES_EXPLICIT_SUPERSESSION",
        ],
    }


def contract_digest() -> str:
    return _sha256(contract_core())


def dependency_manifest_digest() -> str:
    return _sha256(dependency_manifest_core())


def assert_contract_integrity() -> str:
    actual = contract_digest()
    if actual != EXPECTED_CONTRACT_DIGEST:
        raise ValueError(f"GOLDPROMPT_CONTRACT_DIGEST_MISMATCH:{actual}")
    return actual


def assert_dependency_manifest_integrity() -> str:
    actual = dependency_manifest_digest()
    if actual != EXPECTED_DEPENDENCY_MANIFEST_DIGEST:
        raise ValueError(f"GOLDPROMPT_DEPENDENCY_MANIFEST_DIGEST_MISMATCH:{actual}")
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


def _base_receipt(spec: Mapping[str, Any], source_revision: str) -> dict[str, Any]:
    normalized_revision = normalize_source_revision(source_revision)
    if normalized_revision is None:
        raise ValueError("GOLDPROMPT_SOURCE_REVISION_REQUIRED")
    receipt: dict[str, Any] = {
        "schema": RECEIPT_SCHEMA,
        "face_id": spec["face_id"],
        "face_role": spec["face_role"],
        "repository": spec["repository"],
        "runtime_surface": spec["runtime_surface"],
        "goldprompt_foundation_id": GOLDPROMPT_FOUNDATION_ID,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "emergence_contract_version": EMERGENCE_CONTRACT_VERSION,
        "armor_authority_reference": ARMOR_AUTHORITY_REFERENCE,
        "contract_digest_sha256": assert_contract_integrity(),
        "dependency_manifest_reference": DEPENDENCY_MANIFEST_REFERENCE,
        "dependency_manifest_digest_sha256": assert_dependency_manifest_integrity(),
        "source_revision": normalized_revision,
        "capability_scope": list(spec["capability_scope"]),
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


def build_receipt(source_revision: str | None = None) -> dict[str, Any]:
    """Build DemiHead's checksum-bound Face receipt.

    An explicitly supplied revision is a deterministic fixture input, not origin
    authentication. GitHub/Sigstore attestation is a separate evidence layer.
    """
    if source_revision is None:
        source_revision = resolve_runtime_source_revision()
    return _base_receipt({
        "face_id": FACE_ID,
        "face_role": FACE_ROLE,
        "repository": REPOSITORY,
        "runtime_surface": RUNTIME_SURFACE,
        "capability_scope": list(CAPABILITY_SCOPE),
    }, source_revision)


def build_runtime_receipt(env: Mapping[str, str] | None = None) -> dict[str, Any]:
    return build_receipt(resolve_runtime_source_revision(env))


def _verify_against_spec(receipt: Mapping[str, Any], spec: Mapping[str, Any]) -> bool:
    if not isinstance(receipt, Mapping) or frozenset(receipt.keys()) != RECEIPT_KEYS:
        return False
    required = {
        "schema": RECEIPT_SCHEMA,
        "face_id": spec["face_id"],
        "face_role": spec["face_role"],
        "repository": spec["repository"],
        "runtime_surface": spec["runtime_surface"],
        "goldprompt_foundation_id": GOLDPROMPT_FOUNDATION_ID,
        "goldprompt_version": GOLDPROMPT_VERSION,
        "emergence_contract_version": EMERGENCE_CONTRACT_VERSION,
        "armor_authority_reference": ARMOR_AUTHORITY_REFERENCE,
        "contract_digest_sha256": EXPECTED_CONTRACT_DIGEST,
        "dependency_manifest_reference": DEPENDENCY_MANIFEST_REFERENCE,
        "dependency_manifest_digest_sha256": EXPECTED_DEPENDENCY_MANIFEST_DIGEST,
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
    if list(receipt.get("capability_scope", ())) != list(spec["capability_scope"]):
        return False
    claimed = receipt.get("receipt_sha256")
    if not isinstance(claimed, str) or SHA256_RE.fullmatch(claimed) is None:
        return False
    payload = dict(receipt)
    payload.pop("receipt_sha256", None)
    return claimed == _sha256(payload)


def verify_receipt(receipt: Mapping[str, Any]) -> bool:
    return _verify_against_spec(receipt, {
        "face_id": FACE_ID,
        "face_role": FACE_ROLE,
        "repository": REPOSITORY,
        "runtime_surface": RUNTIME_SURFACE,
        "capability_scope": list(CAPABILITY_SCOPE),
    })


def verify_upstream_receipt(receipt: Mapping[str, Any], expected_face_id: str) -> bool:
    spec = UPSTREAM_FACE_SPECS.get(expected_face_id)
    return spec is not None and _verify_against_spec(receipt, spec)


def build_upstream_fixture_receipt(face_id: str, source_revision: str) -> dict[str, Any]:
    """Deterministic test fixture only; not a remote-origin attestation."""
    spec = UPSTREAM_FACE_SPECS.get(face_id)
    if spec is None:
        raise ValueError("GOLDPROMPT_UNKNOWN_UPSTREAM_FACE")
    return _base_receipt(spec, source_revision)


STARTUP_CONTRACT_DIGEST = assert_contract_integrity()
STARTUP_DEPENDENCY_MANIFEST_DIGEST = assert_dependency_manifest_integrity()


if __name__ == "__main__":
    print(json.dumps(build_runtime_receipt(), ensure_ascii=False, sort_keys=True))
