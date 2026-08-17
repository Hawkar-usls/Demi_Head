from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from goldprompt_handshake import (  # noqa: E402
    EXPECTED_CONTRACT_DIGEST,
    FACE_ID,
    FACE_ROLE,
    STARTUP_CONTRACT_DIGEST,
    build_receipt,
    contract_digest,
    resolve_runtime_source_revision,
    verify_receipt,
)
from hemisphere_bridge import self_test  # noqa: E402

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

    def test_contract_digest_is_frozen_at_startup(self):
        self.assertEqual(contract_digest(), EXPECTED_CONTRACT_DIGEST)
        self.assertEqual(STARTUP_CONTRACT_DIGEST, EXPECTED_CONTRACT_DIGEST)

    def test_demihead_receipt_replays(self):
        receipt = build_receipt(TEST_SHA)
        self.assertEqual(receipt["face_id"], FACE_ID)
        self.assertEqual(receipt["face_role"], FACE_ROLE)
        self.assertEqual(receipt["source_revision"], TEST_SHA)
        self.assertEqual(receipt["authority_weight"], 0)
        self.assertEqual(receipt["compliance_state"], "COMPLIANT")
        self.assertEqual(receipt["runtime_enforcement_scope"], "THIS_FACE_INVOCATION")
        self.assertTrue(receipt["inheritance_accepted"])
        self.assertTrue(receipt["blessing_bearer_anchor_accepted"])
        self.assertTrue(receipt["armor_of_god_boundaries_accepted"])
        self.assertTrue(receipt["triadic_emergence_accepted"])
        self.assertTrue(receipt["user_exit_and_release_control_accepted"])
        self.assertTrue(verify_receipt(receipt))

    def test_runtime_revision_requires_trusted_environment(self):
        with self.assertRaisesRegex(ValueError, "TRUSTED_SOURCE_REVISION_REQUIRED"):
            resolve_runtime_source_revision({})
        with self.assertRaisesRegex(ValueError, "JANUS_SOURCE_REVISION_INVALID"):
            resolve_runtime_source_revision({"JANUS_SOURCE_REVISION": "TEST-REV"})
        with self.assertRaisesRegex(ValueError, "SOURCE_REVISION_ENV_CONFLICT"):
            resolve_runtime_source_revision({
                "GITHUB_ACTIONS": "true",
                "GITHUB_SHA": "a" * 40,
                "JANUS_SOURCE_REVISION": "b" * 40,
            })

    def test_receipt_tamper_fails_closed_even_after_rehash(self):
        receipt = build_receipt(TEST_SHA)
        for field, value in (
            ("authority_weight", 1),
            ("face_role", "TRUTH_ORACLE"),
            ("contract_digest_sha256", "0" * 64),
            ("goldprompt_version", "999"),
            ("runtime_enforcement_scope", "WHOLE_WORLD"),
            ("user_exit_and_release_control_accepted", False),
            ("capability_scope", ["PROPOSE_ARBITRATION_RESULT"]),
        ):
            tampered = copy.deepcopy(receipt)
            tampered[field] = value
            payload = dict(tampered)
            payload.pop("receipt_sha256", None)
            from goldprompt_handshake import _sha256  # noqa: PLC0415
            tampered["receipt_sha256"] = _sha256(payload)
            self.assertFalse(verify_receipt(tampered), field)

        extra = copy.deepcopy(receipt)
        extra["extra_authority_hint"] = True
        payload = dict(extra)
        payload.pop("receipt_sha256", None)
        from goldprompt_handshake import _sha256  # noqa: PLC0415
        extra["receipt_sha256"] = _sha256(payload)
        self.assertFalse(verify_receipt(extra))

    def test_malformed_source_revision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "SOURCE_REVISION_REQUIRED"):
            build_receipt("DEMIHEAD-TEST-SHA")

    def test_real_bicameral_result_contains_receipt(self):
        result = self_test()["result"]
        self.assertIn("goldprompt_receipt", result)
        receipt = result["goldprompt_receipt"]
        self.assertTrue(verify_receipt(receipt))
        self.assertEqual(receipt["runtime_enforcement_scope"], "THIS_FACE_INVOCATION")
        self.assertEqual(receipt["authority_weight"], 0)
        self.assertFalse(result["claim_ceiling"]["agreement_is_truth"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)


if __name__ == "__main__":
    unittest.main()
