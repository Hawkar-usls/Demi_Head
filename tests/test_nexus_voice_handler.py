from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import nexus_voice_handler as voice  # noqa: E402


class NexusVoiceHandlerTests(unittest.TestCase):
    def intent(self, **overrides):
        value = {
            "schema": voice.INTENT_SCHEMA,
            "contract": voice.CONTRACT,
            "task": voice.TASK,
            "speaker": "aidar",
            "output_label": "OSIRIS_ORIGIN_PRIME_NEURAL_AIDAR",
            "control": {"prepare_only": True},
        }
        value.update(overrides)
        return value

    def test_deterministic_content_addressed_request(self):
        first = voice.prepare_voice_render_request(self.intent())
        second = voice.prepare_voice_render_request(self.intent())
        self.assertEqual(first, second)
        core = {k: v for k, v in first.items() if k != "request_sha256"}
        self.assertEqual(first["request_sha256"], voice.sha256(core))
        self.assertFalse(first["control"]["audio_rendered"])
        self.assertTrue(first["control"]["explicit_voice_execute_required"])

    def test_local_handler_keeps_certified_pure_boundary(self):
        handler = voice.local_handler()
        self.assertEqual(handler.target_head, "VOICE_RUNTIME")
        self.assertFalse(handler.network_io_permitted)
        self.assertFalse(handler.filesystem_io_permitted)
        self.assertFalse(handler.external_effect_permitted)
        self.assertEqual(handler.authority_delta, 0)
        self.assertEqual(handler.mass_effect_budget_delta, 0)

    def test_rejects_unknown_speaker(self):
        with self.assertRaises(ValueError):
            voice.prepare_voice_render_request(self.intent(speaker="not-a-speaker"))

    def test_rejects_path_injection_label(self):
        with self.assertRaises(ValueError):
            voice.prepare_voice_render_request(self.intent(output_label="../../escape"))

    def test_rejects_external_effect_requests(self):
        bad = self.intent()
        bad["control"] = {"prepare_only": True, "automatic_playback": True}
        with self.assertRaises(ValueError):
            voice.prepare_voice_render_request(bad)

    def test_rejects_arbitrary_source_path_field(self):
        bad = self.intent(source_path="/tmp/anything")
        with self.assertRaises(ValueError):
            voice.prepare_voice_render_request(bad)


if __name__ == "__main__":
    unittest.main()
