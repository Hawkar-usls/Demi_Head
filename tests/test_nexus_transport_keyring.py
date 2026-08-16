from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from nexus_transport_keyring import load_principal_lookup, public_summary, self_test, validate_config  # noqa: E402


class NexusTransportKeyringTests(unittest.TestCase):
    def config(self):
        return json.loads((ROOT / "configs" / "nexus_transport.principals.example.json").read_text(encoding="utf-8"))

    def test_public_config_contains_no_inline_secret_material(self):
        config = self.config()
        validate_config(config)
        raw = json.dumps(config).lower()
        self.assertNotIn('"key":', raw)
        self.assertNotIn('"secret":', raw)
        self.assertNotIn('"token":', raw)
        summary = public_summary(config)
        self.assertFalse(summary["inline_secret_material_present"])

    def test_enabled_principal_loads_secret_from_environment_only(self):
        lookup = load_principal_lookup(
            self.config(),
            environ={"JANUS_NEXUS_GUARDIAN_KEY": "base64:MTIzNDU2Nzg5MGFiY2RlZg=="},
        )
        self.assertEqual(lookup["DEMIHEAD_GUARDIAN_V1"]["key"], b"1234567890abcdef")
        self.assertEqual(lookup["DEMIHEAD_GUARDIAN_V1"]["sender_id"], "DEMIHEAD.GUARDIAN")
        self.assertEqual(lookup["DEMIHEAD_GUARDIAN_V1"]["allowed_source_heads"], ["GUARDIAN"])
        self.assertFalse(lookup["DEMIHEAD_OBSERVER_V1"]["enabled"])

    def test_missing_enabled_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            load_principal_lookup(self.config(), environ={})

    def test_inline_secret_field_fails_closed(self):
        config = self.config()
        config["principals"][0]["key_material"] = "forbidden"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_duplicate_key_id_fails_closed(self):
        config = self.config()
        config["principals"].append(dict(config["principals"][0]))
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_short_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            load_principal_lookup(
                self.config(),
                environ={"JANUS_NEXUS_GUARDIAN_KEY": "too-short"},
            )

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
