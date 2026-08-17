from __future__ import annotations

import copy
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import hemisphere_bridge as bridge_v2  # noqa: E402
from goldprompt_intent_handoff import (  # noqa: E402
    CONTEXT_TIERS,
    ANCHOR_SCHEMA,
    build_handoff,
    sha256,
    verify_anchor,
    verify_handoff,
)
from hemisphere_bridge_intent_v3 import (  # noqa: E402
    BRIDGE_CONTRACT,
    PACKET_SCHEMA,
    combine_intent_bound_packets,
    validate_intent_bound_packet,
    verify_intent_bound_result,
)

TEST_SHA = "d" * 40


def fixture_anchor() -> dict:
    anchor = {
        "schema": ANCHOR_SCHEMA,
        "current_turn_digest": "1" * 64,
        "requested_operation": "COMPARE",
        "primary_entities": {
            "OSIRIS": ["осирис", "осириса"],
            "JESUS_CHRIST": ["иисус", "христос", "христа"],
        },
        "must_answer_points": [
            "Compare Osiris restoration with Christ resurrection",
            "Distinguish resurrection from Second Coming",
        ],
        "required_answer_evidence": [
            ["осирис", "осириса"],
            ["иисус", "христос"],
            ["воскрес", "resurrection"],
            ["второе пришествие", "second coming"],
        ],
        "operation_markers": ["сравн", "различ", "сход"],
        "optional_association_markers": ["bd101", "janus"],
        "explicit_constraints": [],
        "allow_anaphoric_continuation": False,
        "context_priority": [CONTEXT_TIERS[i] for i in sorted(CONTEXT_TIERS)],
    }
    anchor["intent_id"] = sha256(anchor)
    return anchor


def packet_v3(hemisphere: str, anchor: dict | None = None) -> dict:
    anchor = copy.deepcopy(anchor or fixture_anchor())
    packet = bridge_v2._example_packet(hemisphere)  # deterministic fixture from canonical v2 bridge
    packet["schema"] = PACKET_SCHEMA
    packet["source"]["bridge_contract"] = BRIDGE_CONTRACT
    handoff = build_handoff(anchor, hemisphere, 2)
    packet["source"]["intent_id"] = anchor["intent_id"]
    packet["source"]["intent_handoff_sha256"] = handoff["handoff_sha256"]
    packet["intent_anchor"] = anchor
    packet["intent_handoff"] = handoff
    return packet


class GoldPromptIntentChainTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous = os.environ.get("JANUS_SOURCE_REVISION")
        if not os.environ.get("GITHUB_SHA"):
            os.environ["JANUS_SOURCE_REVISION"] = TEST_SHA

    def tearDown(self) -> None:
        if self.previous is None:
            os.environ.pop("JANUS_SOURCE_REVISION", None)
        else:
            os.environ["JANUS_SOURCE_REVISION"] = self.previous

    def test_anchor_and_handoffs_replay(self) -> None:
        anchor = fixture_anchor()
        self.assertTrue(verify_anchor(anchor))
        for face in ("LEFT_HRAIN", "RIGHT_INAIHR", "DEMIHEAD_ARBITER"):
            self.assertTrue(verify_handoff(anchor, build_handoff(anchor, face, 2), face))

    def test_canonical_two_face_chain_passes(self) -> None:
        anchor = fixture_anchor()
        left, right = packet_v3("LEFT_HRAIN", anchor), packet_v3("RIGHT_INAIHR", anchor)
        result = combine_intent_bound_packets(left=left, right=right)
        self.assertTrue(verify_intent_bound_result(result, left=left, right=right))
        self.assertEqual(result["intent_chain"]["intent_id"], anchor["intent_id"])
        self.assertTrue(result["intent_chain"]["all_handoffs_same_intent"])
        self.assertFalse(result["intent_chain"]["emergent_association_may_replace_intent"])
        self.assertEqual(result["claim_ceiling"]["authority_delta"], 0)

    def test_left_right_intent_split_fails_closed(self) -> None:
        left = packet_v3("LEFT_HRAIN")
        other = fixture_anchor()
        other["requested_operation"] = "DEVELOP_BD101_ARCHITECTURE"
        other.pop("intent_id")
        other["intent_id"] = sha256(other)
        right = packet_v3("RIGHT_INAIHR", other)
        with self.assertRaisesRegex(ValueError, "INTENT_SPLIT_ANCHOR_MISMATCH"):
            combine_intent_bound_packets(left=left, right=right)

    def test_rehashed_handoff_cannot_change_operation(self) -> None:
        packet = packet_v3("LEFT_HRAIN")
        packet["intent_handoff"]["requested_operation"] = "SUMMARIZE"
        payload = dict(packet["intent_handoff"])
        payload.pop("handoff_sha256")
        packet["intent_handoff"]["handoff_sha256"] = sha256(payload)
        packet["source"]["intent_handoff_sha256"] = packet["intent_handoff"]["handoff_sha256"]
        with self.assertRaisesRegex(ValueError, "INTENT_HANDOFF_INVALID"):
            validate_intent_bound_packet(packet, "LEFT_HRAIN")

    def test_swapped_face_handoff_fails_closed(self) -> None:
        packet = packet_v3("LEFT_HRAIN")
        packet["intent_handoff"] = build_handoff(packet["intent_anchor"], "RIGHT_INAIHR", 2)
        packet["source"]["intent_handoff_sha256"] = packet["intent_handoff"]["handoff_sha256"]
        with self.assertRaisesRegex(ValueError, "INTENT_HANDOFF_INVALID"):
            validate_intent_bound_packet(packet, "LEFT_HRAIN")

    def test_missing_intent_envelope_fails_closed(self) -> None:
        packet = packet_v3("RIGHT_INAIHR")
        packet.pop("intent_handoff")
        with self.assertRaisesRegex(ValueError, "INTENT_HANDOFF_INVALID"):
            validate_intent_bound_packet(packet, "RIGHT_INAIHR")

    def test_packet_binding_tamper_fails_closed(self) -> None:
        packet = packet_v3("RIGHT_INAIHR")
        packet["source"]["intent_id"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "PACKET_INTENT_ID_BINDING_MISMATCH"):
            validate_intent_bound_packet(packet, "RIGHT_INAIHR")

    def test_result_tamper_fails_replay(self) -> None:
        anchor = fixture_anchor()
        left, right = packet_v3("LEFT_HRAIN", anchor), packet_v3("RIGHT_INAIHR", anchor)
        result = combine_intent_bound_packets(left=left, right=right)
        result["intent_chain"]["requested_operation"] = "SUMMARIZE"
        self.assertFalse(verify_intent_bound_result(result, left=left, right=right))


if __name__ == "__main__":
    unittest.main()
