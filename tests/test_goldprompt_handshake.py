from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from goldprompt_handshake import (  # noqa: E402
    DEPENDENCY_MANIFEST_REFERENCE,
    EXPECTED_CONTRACT_DIGEST,
    EXPECTED_DEPENDENCY_MANIFEST_DIGEST,
    FACE_ID,
    FACE_ROLE,
    STARTUP_CONTRACT_DIGEST,
    STARTUP_DEPENDENCY_MANIFEST_DIGEST,
    _sha256,
    build_receipt,
    build_upstream_fixture_receipt,
    contract_digest,
    dependency_manifest_digest,
    resolve_runtime_source_revision,
    verify_receipt,
    verify_upstream_receipt,
)
from hemisphere_bridge import self_test, verify_receipt_chain_result  # noqa: E402

TEST_SHA = "d" * 40


class GoldPromptHandshakeTests(unittest.TestCase):
    def setUp(self):
        self.previous_revision = os.environ.get("JANUS_SOURCE_REVISION")
        if not os.environ.get("GITHUB_SHA"):
            os.environ["JANUS_SOURCE_REVISION"] = TEST_SHA

    def tearDown(self):
        if self.previous_revision is None:
            os.environ.pop("JANUS_SOURCE_REVISION", None)
        else:
            os.environ["JANUS_SOURCE_REVISION"] = self.previous_revision

    def test_contract_and_dependency_manifest_are_frozen_at_startup(self):
        self.assertEqual(contract_digest(), EXPECTED_CONTRACT_DIGEST)
        self.assertEqual(STARTUP_CONTRACT_DIGEST, EXPECTED_CONTRACT_DIGEST)
        self.assertEqual(dependency_manifest_digest(), EXPECTED_DEPENDENCY_MANIFEST_DIGEST)
        self.assertEqual(STARTUP_DEPENDENCY_MANIFEST_DIGEST, EXPECTED_DEPENDENCY_MANIFEST_DIGEST)

    def test_demihead_receipt_replays(self):
        receipt = build_receipt(TEST_SHA)
        self.assertEqual(receipt["face_id"], FACE_ID)
        self.assertEqual(receipt["face_role"], FACE_ROLE)
        self.assertEqual(receipt["source_revision"], TEST_SHA)
        self.assertEqual(receipt["dependency_manifest_reference"], DEPENDENCY_MANIFEST_REFERENCE)
        self.assertEqual(receipt["dependency_manifest_digest_sha256"], EXPECTED_DEPENDENCY_MANIFEST_DIGEST)
        self.assertEqual(receipt["authority_weight"], 0)
        self.assertEqual(receipt["compliance_state"], "COMPLIANT")
        self.assertTrue(verify_receipt(receipt))

    def test_upstream_receipts_are_verified_by_face_identity(self):
        left = build_upstream_fixture_receipt("LEFT_HRAIN", "a" * 40)
        right = build_upstream_fixture_receipt("RIGHT_INAIHR", "b" * 40)
        self.assertTrue(verify_upstream_receipt(left, "LEFT_HRAIN"))
        self.assertTrue(verify_upstream_receipt(right, "RIGHT_INAIHR"))
        self.assertFalse(verify_upstream_receipt(left, "RIGHT_INAIHR"))
        self.assertFalse(verify_upstream_receipt(right, "LEFT_HRAIN"))

    def test_runtime_revision_requires_trusted_environment(self):
        with self.assertRaisesRegex(ValueError, "TRUSTED_SOURCE_REVISION_REQUIRED"):
            resolve_runtime_source_revision({})
        with self.assertRaisesRegex(ValueError, "JANUS_SOURCE_REVISION_INVALID"):
            resolve_runtime_source_revision({"JANUS_SOURCE_REVISION": "TEST-REV"})
        with self.assertRaisesRegex(ValueError, "SOURCE_REVISION_ENV_CONFLICT"):
            resolve_runtime_source_revision({"GITHUB_ACTIONS": "true", "GITHUB_SHA": "a" * 40, "JANUS_SOURCE_REVISION": "b" * 40})

    def test_receipt_tamper_fails_closed_even_after_rehash(self):
        receipt = build_receipt(TEST_SHA)
        for field, value in (
            ("authority_weight", 1),
            ("face_role", "TRUTH_ORACLE"),
            ("contract_digest_sha256", "0" * 64),
            ("dependency_manifest_digest_sha256", "0" * 64),
            ("goldprompt_version", "999"),
            ("runtime_enforcement_scope", "WHOLE_WORLD"),
            ("user_exit_and_release_control_accepted", False),
            ("capability_scope", ["PROPOSE_ARBITRATION_RESULT"]),
        ):
            tampered = copy.deepcopy(receipt)
            tampered[field] = value
            payload = dict(tampered)
            payload.pop("receipt_sha256", None)
            tampered["receipt_sha256"] = _sha256(payload)
            self.assertFalse(verify_receipt(tampered), field)

        extra = copy.deepcopy(receipt)
        extra["extra_authority_hint"] = True
        payload = dict(extra)
        payload.pop("receipt_sha256", None)
        extra["receipt_sha256"] = _sha256(payload)
        self.assertFalse(verify_receipt(extra))

    def test_malformed_source_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_REVISION_REQUIRED"):
            build_receipt("DEMIHEAD-TEST-SHA")

    def test_real_bicameral_result_contains_verified_receipt_chain(self):
        result = self_test()["result"]
        self.assertTrue(verify_receipt(result["goldprompt_receipt"]))
        self.assertTrue(verify_receipt_chain_result(result))
        self.assertEqual(set(result["upstream_goldprompt_receipts"]), {"LEFT_HRAIN", "RIGHT_INAIHR"})
        self.assertTrue(result["receipt_chain"]["end_to_end_receipt_binding_established"])
        self.assertFalse(result["receipt_chain"]["origin_authentication_established"])
        self.assertFalse(result["receipt_chain"]["live_process_identity_established"])
        self.assertFalse(result["claim_ceiling"]["agreement_is_truth"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)


if __name__ == "__main__":
    unittest.main()
