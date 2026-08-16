import unittest

from tools.source_bound_witness import analyze_packet


class SourceBoundWitnessTests(unittest.TestCase):
    def packet(self):
        return {
            "schema": "janus.demihead.source_bound_witness.v1",
            "case_id": "fixture",
            "witness_id": "WITNESS",
            "evidence": [
                {"evidence_id": "support", "relation": "supports"},
                {"evidence_id": "contra", "relation": "contradicts"},
                {"evidence_id": "context", "relation": "context_only"},
            ],
            "questions": [
                {
                    "question_id": "supported",
                    "text": "supported?",
                    "evidence_ids": ["support"],
                },
                {
                    "question_id": "open",
                    "text": "open?",
                    "evidence_ids": ["context"],
                },
                {
                    "question_id": "contested",
                    "text": "contested?",
                    "evidence_ids": ["support", "contra"],
                },
            ],
        }

    def test_bound_states(self):
        result = analyze_packet(self.packet())
        states = {row["question_id"]: row["state"] for row in result["answers"]}
        self.assertEqual(states["supported"], "SUPPORTED_BY_BOUND_SOURCES")
        self.assertEqual(states["open"], "UNRESOLVED")
        self.assertEqual(states["contested"], "CONTESTED")

    def test_no_supernatural_testimony_is_claimed(self):
        result = analyze_packet(self.packet())
        self.assertFalse(result["model_output_is_evidence"])
        self.assertFalse(result["supernatural_contact_claimed"])


if __name__ == "__main__":
    unittest.main()
