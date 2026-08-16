from __future__ import annotations

import argparse
import base64
import binascii
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


CONFIG_SCHEMA = "janus.demihead.nexus_transport_keyring.v1"
FORBIDDEN_INLINE_FIELDS = {"key", "secret", "token", "password", "key_material"}


def _decode_secret(raw: str) -> bytes:
    if raw.startswith("base64:"):
        try:
            return base64.b64decode(raw[7:], validate=True)
        except (binascii.Error, ValueError) as exc:
            raise ValueError("Invalid base64 transport secret") from exc
    if raw.startswith("hex:"):
        try:
            return bytes.fromhex(raw[4:])
        except ValueError as exc:
            raise ValueError("Invalid hex transport secret") from exc
    return raw.encode("utf-8")


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict) or config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("Unexpected transport keyring config schema")
    if config.get("inline_secret_material_allowed") is not False:
        raise ValueError("inline_secret_material_allowed must be false")
    principals = config.get("principals")
    if not isinstance(principals, list) or not principals:
        raise ValueError("principals must be a non-empty array")

    seen: set[str] = set()
    for principal in principals:
        if not isinstance(principal, dict):
            raise ValueError("Every principal must be an object")
        forbidden = FORBIDDEN_INLINE_FIELDS & set(principal)
        if forbidden:
            raise ValueError(f"Inline secret fields are forbidden: {sorted(forbidden)}")
        key_id = principal.get("key_id")
        sender_id = principal.get("sender_id")
        secret_env = principal.get("secret_env")
        allowed = principal.get("allowed_source_heads")
        enabled = principal.get("enabled")
        if not isinstance(key_id, str) or not key_id.strip():
            raise ValueError("principal.key_id must be a non-empty string")
        if key_id in seen:
            raise ValueError(f"Duplicate key_id: {key_id}")
        seen.add(key_id)
        if not isinstance(sender_id, str) or not sender_id.strip():
            raise ValueError(f"{key_id}: sender_id must be non-empty")
        if not isinstance(secret_env, str) or not secret_env.strip():
            raise ValueError(f"{key_id}: secret_env must be non-empty")
        if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
            raise ValueError(f"{key_id}: allowed_source_heads must be a non-empty string array")
        if not isinstance(enabled, bool):
            raise ValueError(f"{key_id}: enabled must be boolean")


def load_principal_lookup(
    config: dict[str, Any],
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, dict[str, Any]]:
    validate_config(config)
    env = os.environ if environ is None else environ
    result: dict[str, dict[str, Any]] = {}

    for principal in config["principals"]:
        key_id = principal["key_id"]
        secret_env = principal["secret_env"]
        enabled = principal["enabled"]
        if not enabled:
            result[key_id] = {
                "key": b"disabled-principal-placeholder",
                "sender_id": principal["sender_id"],
                "allowed_source_heads": list(principal["allowed_source_heads"]),
                "enabled": False,
            }
            continue
        raw_secret = env.get(secret_env)
        if raw_secret is None:
            raise ValueError(f"Missing required transport secret environment variable: {secret_env}")
        key = _decode_secret(raw_secret)
        if len(key) < 16:
            raise ValueError(f"{key_id}: decoded transport secret must be at least 16 bytes")
        result[key_id] = {
            "key": key,
            "sender_id": principal["sender_id"],
            "allowed_source_heads": list(principal["allowed_source_heads"]),
            "enabled": True,
        }
    return result


def load_config(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError("Expected top-level JSON object")
    return value


def public_summary(config: dict[str, Any]) -> dict[str, Any]:
    validate_config(config)
    return {
        "schema": "janus.demihead.nexus_transport_keyring_summary.v1",
        "principal_count": len(config["principals"]),
        "principals": [
            {
                "key_id": row["key_id"],
                "sender_id": row["sender_id"],
                "allowed_source_heads": list(row["allowed_source_heads"]),
                "enabled": row["enabled"],
                "secret_source": "ENVIRONMENT_REFERENCE_ONLY",
            }
            for row in config["principals"]
        ],
        "inline_secret_material_present": False,
    }


def self_test() -> dict[str, Any]:
    config = {
        "schema": CONFIG_SCHEMA,
        "inline_secret_material_allowed": False,
        "principals": [
            {
                "key_id": "GUARDIAN_TEST",
                "sender_id": "DEMIHEAD.GUARDIAN",
                "allowed_source_heads": ["GUARDIAN"],
                "secret_env": "JANUS_TEST_KEY",
                "enabled": True,
            }
        ],
    }
    lookup = load_principal_lookup(config, environ={"JANUS_TEST_KEY": "hex:" + "11" * 32})
    checks = {
        "principal_loaded": lookup["GUARDIAN_TEST"]["sender_id"] == "DEMIHEAD.GUARDIAN",
        "secret_decoded": lookup["GUARDIAN_TEST"]["key"] == bytes.fromhex("11" * 32),
        "source_allowlist_preserved": lookup["GUARDIAN_TEST"]["allowed_source_heads"] == ["GUARDIAN"],
        "public_summary_has_no_secret": "key" not in public_summary(config)["principals"][0],
    }

    try:
        load_principal_lookup(config, environ={})
    except ValueError:
        checks["missing_secret_fails_closed"] = True
    else:
        checks["missing_secret_fails_closed"] = False

    inline = json.loads(json.dumps(config))
    inline["principals"][0]["key"] = "should-not-be-here"
    try:
        validate_config(inline)
    except ValueError:
        checks["inline_secret_field_rejected"] = True
    else:
        checks["inline_secret_field_rejected"] = False

    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "summary": public_summary(config),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public Nexus transport principal policy without exposing secrets.")
    parser.add_argument("--config", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        elif args.config is not None:
            result = public_summary(load_config(args.config))
        else:
            parser.error("provide --config or --self-test")
        sys.stdout.write(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
        return 0 if result.get("status", "PASS") == "PASS" else 1
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"nexus_transport_keyring: {exc}\n")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
