from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from epistemic_execution_gate import (  # noqa: E402
    CASE_SCHEMA,
    CURRENT_STATE,
    EXACT_COMPUTATION,
    EXTERNAL_FACT,
    INTERPRETATION,
    assess_case,
    compute_sha256_file,
    compute_sha256_text,
    self_test,
)


class EpistemicExecutionGateTests(unittest.TestCase):
    def test_model_generated_hash_is_not_execution_evidence(self) -> None:
        fake = "a" * 64
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "MODEL_ONLY",
            "claim_type": EXACT_COMPUTATION,
            "claim": "hash matches",
            "claimed_value": fake,
            "evidence": [{"kind": "model_output", "text": fake}],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")
        self.assertFalse(result["definitive_claim_permitted"])
        self.assertIn("DO_NOT_GUESS_A_VALUE", result["response_policy"])

    def test_plausible_hash_shape_does_not_upgrade_claim(self) -> None:
        plausible = "0123456789abcdef" * 4
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "SHAPE_ONLY",
            "claim_type": EXACT_COMPUTATION,
            "claim": "this is the SHA-256",
            "claimed_value": plausible,
            "evidence": [],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")
        self.assertIn("HASH_SHAPE != HASH_VERIFIED", result["invariants"])

    def test_real_sha256_text_execution_matches_hashlib(self) -> None:
        expected = hashlib.sha256("JANUS".encode("utf-8")).hexdigest()
        receipt = compute_sha256_text("JANUS", expected=expected)
        self.assertEqual(receipt["computed_value"], expected)
        self.assertEqual(receipt["comparison"], "MATCH")
        self.assertEqual(receipt["execution_state"], "EXECUTED")

    def test_real_sha256_file_execution_binds_file_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "payload.bin"
            path.write_bytes(b"JANUS\x00RECEIPT")
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            receipt = compute_sha256_file(path, expected=expected)
        self.assertEqual(receipt["computed_value"], expected)
        self.assertEqual(receipt["input_byte_length"], len(b"JANUS\x00RECEIPT"))
        self.assertTrue(receipt["input_bound"])
        self.assertTrue(receipt["result_bound"])

    def test_wrong_expected_hash_is_reported_as_mismatch_not_massaged(self) -> None:
        receipt = compute_sha256_text("JANUS", expected="0" * 64)
        self.assertEqual(receipt["comparison"], "MISMATCH")
        self.assertEqual(receipt["verification_state"], "VERIFIED_MISMATCH_BY_LOCAL_EXECUTION")

    def test_unexecuted_receipt_fails_closed(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "NOT_EXECUTED",
            "claim_type": EXACT_COMPUTATION,
            "claim": "verified",
            "claimed_value": "x",
            "evidence": [{
                "kind": "execution_receipt",
                "origin": "trusted_local_tool",
                "execution_state": "PLANNED",
                "input_bound": True,
                "result_bound": True,
                "computed_value": "x",
            }],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")

    def test_model_cannot_self_certify_execution_receipt(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "SELF_CERT",
            "claim_type": EXACT_COMPUTATION,
            "claim": "verified",
            "claimed_value": "x",
            "evidence": [{
                "kind": "execution_receipt",
                "origin": "model_output",
                "execution_state": "EXECUTED",
                "input_bound": True,
                "result_bound": True,
                "computed_value": "x",
            }],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")

    def test_conflicting_execution_receipts_remain_contested(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "CONFLICT",
            "claim_type": EXACT_COMPUTATION,
            "claim": "computed value",
            "claimed_value": "a",
            "evidence": [
                {"kind": "execution_receipt", "origin": "tool_a", "execution_state": "EXECUTED", "input_bound": True, "result_bound": True, "computed_value": "a"},
                {"kind": "execution_receipt", "origin": "tool_b", "execution_state": "EXECUTED", "input_bound": True, "result_bound": True, "computed_value": "b"},
            ],
        })
        self.assertEqual(result["evidence_state"], "CONTESTED_EXECUTION")
        self.assertFalse(result["definitive_claim_permitted"])

    def test_stale_source_cannot_verify_current_state(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "STALE_NOW",
            "claim_type": CURRENT_STATE,
            "claim": "service is online now",
            "claimed_value": True,
            "evidence": [{
                "kind": "source_receipt",
                "origin": "connector",
                "retrieved": True,
                "source_locator": "status-endpoint",
                "freshness": "stale",
                "observed_value": True,
            }],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")

    def test_current_source_receipt_can_support_current_state_without_becoming_truth_oracle(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "CURRENT",
            "claim_type": CURRENT_STATE,
            "claim": "service is online now",
            "claimed_value": True,
            "evidence": [{
                "kind": "source_receipt",
                "origin": "connector",
                "retrieved": True,
                "source_locator": "status-endpoint",
                "freshness": "current",
                "observed_value": True,
            }],
        })
        self.assertEqual(result["evidence_state"], "SUPPORTED_BY_SOURCE_RECEIPT")
        self.assertTrue(result["definitive_claim_permitted"])
        self.assertIn("SOURCE_RETRIEVAL != SOURCE_TRUTH", result["invariants"])

    def test_external_fact_requires_source_not_model_output(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "FACT",
            "claim_type": EXTERNAL_FACT,
            "claim": "fact X",
            "claimed_value": 42,
            "evidence": [{"kind": "model_output", "text": "42"}],
        })
        self.assertEqual(result["evidence_state"], "EVIDENCE_INSUFFICIENT")

    def test_interpretation_is_allowed_only_as_labeled_nonverification(self) -> None:
        result = assess_case({
            "schema": CASE_SCHEMA,
            "case_id": "INTERP",
            "claim_type": INTERPRETATION,
            "claim": "symbolic reading",
            "evidence": [],
        })
        self.assertEqual(result["evidence_state"], "LABELED_INTERPRETATION_NOT_FACT_VERIFICATION")
        self.assertFalse(result["definitive_claim_permitted"])

    def test_builtin_self_test_passes(self) -> None:
        result = self_test()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["passed"], result["total"])
        json.dumps(result, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
