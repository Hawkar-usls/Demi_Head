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

    def env(self):
        return {"JANUS_NEXUS_GUARDIAN_KEY_E1": "base64:MTIzNDU2Nzg5MGFiY2RlZg=="}

    def test_public_config_contains_no_inline_secret_material(self):
        config = self.config()
        validate_config(config)
        raw = json.dumps(config).lower()
        self.assertNotIn('"key":', raw)
        self.assertNotIn('"secret":', raw)
        self.assertNotIn('"token":', raw)
        summary = public_summary(config)
        self.assertFalse(summary["inline_secret_material_present"])
        self.assertEqual(summary["principals"][0]["epoch"], 1)
        self.assertFalse(summary["principals"][0]["revoked"])

    def test_enabled_principal_loads_secret_and_epoch_policy(self):
        lookup = load_principal_lookup(self.config(), environ=self.env())
        guardian = lookup["DEMIHEAD_GUARDIAN_E1"]
        self.assertEqual(guardian["key"], b"1234567890abcdef")
        self.assertEqual(guardian["sender_id"], "DEMIHEAD.GUARDIAN")
        self.assertEqual(guardian["allowed_source_heads"], ["GUARDIAN"])
        self.assertEqual(guardian["epoch"], 1)
        self.assertEqual(guardian["not_before_ms"], 1700000000000)
        self.assertEqual(guardian["not_after_ms"], 1900000000000)
        self.assertFalse(guardian["revoked"])
        self.assertFalse(lookup["DEMIHEAD_OBSERVER_E1"]["enabled"])

    def test_missing_enabled_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            load_principal_lookup(self.config(), environ={})

    def test_revoked_principal_does_not_load_secret(self):
        config = self.config()
        config["principals"][0]["revoked"] = True
        lookup = load_principal_lookup(config, environ={})
        self.assertTrue(lookup["DEMIHEAD_GUARDIAN_E1"]["revoked"])

    def test_invalid_epoch_and_window_fail_closed(self):
        for mutate in (
            lambda config: config["principals"][0].__setitem__("epoch", 0),
            lambda config: config["principals"][0].__setitem__("not_after_ms", config["principals"][0]["not_before_ms"]),
            lambda config: config["principals"][0].__setitem__("revoked", "no"),
        ):
            config = self.config()
            mutate(config)
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_inline_secret_field_fails_closed(self):
        config = self.config()
        config["principals"][0]["key_material"] = "forbidden"
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_duplicate_key_id_and_sender_epoch_fail_closed(self):
        config = self.config()
        config["principals"].append(dict(config["principals"][0]))
        with self.assertRaises(ValueError):
            validate_config(config)

        config = self.config()
        duplicate_epoch = dict(config["principals"][0])
        duplicate_epoch["key_id"] = "OTHER_KEY_SAME_SENDER_EPOCH"
        config["principals"].append(duplicate_epoch)
        with self.assertRaises(ValueError):
            validate_config(config)

    def test_short_secret_fails_closed(self):
        with self.assertRaises(ValueError):
            load_principal_lookup(
                self.config(),
                environ={"JANUS_NEXUS_GUARDIAN_KEY_E1": "too-short"},
            )

    def test_self_test_passes(self):
        self.assertEqual(self_test()["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
