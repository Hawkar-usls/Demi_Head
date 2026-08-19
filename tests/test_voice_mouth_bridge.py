from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from voice_mouth_bridge import (  # noqa: E402
    build_request,
    self_test,
    validate_request,
    verify_request,
)


class VoiceMouthBridgeTests(unittest.TestCase):
    def request(self):
        return build_request(
            "GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE",
            output_label="test_voice",
            revision="a" * 40,
        )

    def test_valid_request_roundtrip(self):
        request = self.request()
        validate_request(request)
        self.assertTrue(verify_request(request))
        self.assertEqual(request["task"], "RENDER_PRESET")
        self.assertEqual(request["control"]["authority_delta"], 0)
        self.assertEqual(request["control"]["mass_effect_budget_delta"], 0)
        self.assertFalse(request["control"]["network_io_permitted"])
        self.assertFalse(request["control"]["automatic_playback_permitted"])

    def test_unknown_preset_fails_closed(self):
        with self.assertRaises(ValueError):
            build_request("../../etc/passwd", revision="a" * 40)

    def test_unsafe_output_label_fails_closed(self):
        with self.assertRaises(ValueError):
            build_request(
                "GREAT_PYRAMID_KINGS_CHAMBER_EXAMPLE",
                output_label="../escape",
                revision="a" * 40,
            )

    def test_network_or_autoplay_escalation_fails_closed(self):
        for key in ("network_io_permitted", "automatic_playback_permitted"):
            request = self.request()
            request["control"][key] = True
            self.assertFalse(verify_request(request))

    def test_authority_escalation_fails_closed(self):
        request = self.request()
        request["control"]["authority_delta"] = 1
        self.assertFalse(verify_request(request))

    def test_extra_field_fails_closed(self):
        request = self.request()
        request["command"] = "rm -rf /"
        self.assertFalse(verify_request(request))

    def test_hash_tamper_fails_closed(self):
        request = self.request()
        request["output_label"] = "tampered"
        self.assertFalse(verify_request(request))

    def test_destination_tamper_fails_closed(self):
        request = self.request()
        request["destination"]["repository"] = "example/other"
        self.assertFalse(verify_request(request))

    def test_copy_is_not_accidentally_mutating_baseline(self):
        request = self.request()
        other = copy.deepcopy(request)
        other["control"]["shell_execution_permitted"] = True
        self.assertTrue(verify_request(request))
        self.assertFalse(verify_request(other))

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
