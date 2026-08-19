from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from voice_language_bridge import (  # noqa: E402
    MAX_CANONICAL_JSON_BYTES,
    build_request,
    canonical_json_bytes,
    validate_request,
    verify_request,
)


class VoiceLanguageBridgeTests(unittest.TestCase):
    def request(self):
        return build_request(
            {"janus": "remembers", "value": [14, 14]},
            output_label="json_record_test",
            revision="a" * 40,
        )

    def test_builds_hash_bound_inline_json_request(self):
        request = self.request()
        self.assertTrue(verify_request(request))
        self.assertEqual(request["task"], "SONIFY_INLINE_JSON")
        self.assertEqual(request["control"]["microphone_start_permitted"], False)
        self.assertEqual(request["control"]["network_io_permitted"], False)
        self.assertEqual(request["canonical_json_bytes"], len(canonical_json_bytes(request["inline_json"])))

    def test_payload_tamper_fails_closed(self):
        request = self.request()
        tampered = copy.deepcopy(request)
        tampered["inline_json"]["value"] = [14, 15]
        with self.assertRaises(ValueError):
            validate_request(tampered)

    def test_microphone_start_cannot_be_dispatched(self):
        request = self.request()
        request["control"]["microphone_start_permitted"] = True
        with self.assertRaises(ValueError):
            validate_request(request)

    def test_extra_path_field_rejected(self):
        request = self.request()
        request["input_path"] = "../../secret.json"
        with self.assertRaises(ValueError):
            validate_request(request)

    def test_oversize_inline_json_rejected(self):
        with self.assertRaises(ValueError):
            build_request(
                {"payload": "x" * (MAX_CANONICAL_JSON_BYTES + 1)},
                revision="a" * 40,
            )


if __name__ == "__main__":
    unittest.main()
