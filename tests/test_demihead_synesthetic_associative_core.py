from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import demihead_synesthetic_associative_core as core


class DemiHeadSynestheticAssociativeCoreTests(unittest.TestCase):
    def setUp(self):
        self.packet = core._fixture_packet(event_id="SYNTH-001", fingerprint_seed="A")

    def test_self_test(self):
        self.assertEqual(core.self_test()["status"], "PASS")

    def test_contract_hash_frozen(self):
        contract = core.load_and_verify_contract()
        self.assertEqual(core.digest(contract), core.PROTOCOL_CONTRACT_SHA256)

    def test_valid_cousteau_packet_accepted(self):
        self.assertTrue(core.verify_cousteau_packet(self.packet))

    def test_packet_tamper_rejected(self):
        tampered = copy.deepcopy(self.packet)
        tampered["measurement_fingerprint"]["embedding"][0] = 0.5
        self.assertFalse(core.verify_cousteau_packet(tampered))

    def test_associative_context_cannot_mutate_measurement_fingerprint(self):
        receipt = core.build_associative_receipt(
            self.packet,
            structural_context={"shape": "ridge", "hypothesis": "H1_REAL_MORPHOLOGY"},
            associative_context={"memory": "something", "target": "0012"},
        )
        self.assertEqual(receipt["measurement_fingerprint"], self.packet["measurement_fingerprint"])
        self.assertTrue(receipt["measurement_fingerprint_bit_preserved"])
        self.assertFalse(receipt["scientific_convergence_claim"])
        self.assertFalse(receipt["evidence_admission_performed"])

    def test_story_context_is_kept_inspectable_but_not_scored(self):
        a = core.build_associative_receipt(
            self.packet,
            structural_context={"hypothesis": "H1_REAL_MORPHOLOGY"},
            associative_context={"target": "0012"},
        )
        b = core.build_associative_receipt(
            self.packet,
            structural_context={"hypothesis": "H0_INSTRUMENT_ONLY"},
            associative_context={"target": "0037"},
        )
        self.assertEqual(a["measurement_fingerprint"], b["measurement_fingerprint"])
        cmp = core.compare_associative_receipts(a, b)
        self.assertEqual(cmp["status"], "IDENTICAL_MEASUREMENT_MEMORY")
        self.assertFalse(cmp["semantic_story_context_used_in_score"])
        self.assertTrue(a["hemisphere_views"]["LEFT_HRAIN"]["ignored_for_similarity_score"])
        self.assertTrue(a["hemisphere_views"]["RIGHT_INAIHR"]["ignored_for_similarity_score"])

    def test_blocked_packet_creates_hold_without_tags(self):
        packet = core._fixture_packet(event_id="BLOCKED", blocked=True)
        receipt = core.build_associative_receipt(packet)
        self.assertEqual(receipt["status"], "BLOCKED_HOLD")
        self.assertIsNone(receipt["measurement_fingerprint"])
        self.assertEqual(receipt["associative_tags"], [])
        self.assertEqual(receipt["routing"]["mode"], "HOLD")

    def test_same_identity_changed_fingerprint_is_conflict_hold(self):
        a = core.build_associative_receipt(self.packet)
        changed = core._fixture_packet(event_id="SYNTH-001", fingerprint_seed="B")
        b = core.build_associative_receipt(changed)
        cmp = core.compare_associative_receipts(a, b)
        self.assertEqual(cmp["status"], "PROVENANCE_CONFLICT_HOLD")
        self.assertTrue(cmp["disagreement_preserved"])
        self.assertFalse(cmp["scientific_convergence_claim"])

    def test_different_event_similar_fingerprint_is_neighbor_only(self):
        a = core.build_associative_receipt(self.packet)
        b = core.build_associative_receipt(core._fixture_packet(event_id="SYNTH-002", fingerprint_seed="B"))
        cmp = core.compare_associative_receipts(a, b)
        self.assertEqual(cmp["status"], "MNEMONIC_NEIGHBOR_ONLY")
        self.assertGreater(cmp["quality_adjusted_review_score"], 0.0)
        self.assertFalse(cmp["evidence_admission_performed"])

    def test_memory_index_is_idempotent_and_conflict_fail_closed(self):
        index = core.AssociativeMemoryIndex()
        a = core.build_associative_receipt(self.packet)
        self.assertEqual(index.add(a)["status"], "STORED_FOR_RETRIEVAL_ONLY")
        self.assertEqual(index.add(a)["status"], "IDEMPOTENT_PRESENT")
        conflicting = core.build_associative_receipt(core._fixture_packet(event_id="SYNTH-001", fingerprint_seed="B"))
        result = index.add(conflicting)
        self.assertEqual(result["status"], "PROVENANCE_CONFLICT_HOLD")
        self.assertFalse(result["stored"])

    def test_memory_query_is_review_only(self):
        index = core.AssociativeMemoryIndex()
        a = core.build_associative_receipt(self.packet)
        b = core.build_associative_receipt(core._fixture_packet(event_id="SYNTH-002", fingerprint_seed="B"))
        index.add(a)
        index.add(b)
        rows = index.query(a, top_k=2)
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(row["scientific_convergence_claim"] is False for row in rows))

    def test_unison_receipt_preserves_fingerprint_bit_exact(self):
        receipt = core.build_associative_receipt(self.packet)
        unison = core.build_unison_receipt(self.packet, receipt)
        self.assertTrue(unison["cousteau_measurement_fingerprint_bit_preserved"])
        self.assertEqual(
            unison["cousteau"]["measurement_fingerprint_sha256"],
            unison["demihead"]["measurement_fingerprint_sha256"],
        )
        self.assertEqual(unison["authority"]["authority_delta"], 0)
        self.assertFalse(unison["scientific_convergence_claim"])


if __name__ == "__main__":
    unittest.main()
