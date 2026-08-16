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


def _validate_epoch_fields(principal: dict[str, Any], key_id: str) -> None:
    epoch = principal.get("epoch")
    not_before_ms = principal.get("not_before_ms")
    not_after_ms = principal.get("not_after_ms")
    revoked = principal.get("revoked")
    if isinstance(epoch, bool) or not isinstance(epoch, int) or epoch < 1:
        raise ValueError(f"{key_id}: epoch must be an integer >= 1")
    if isinstance(not_before_ms, bool) or not isinstance(not_before_ms, int) or not_before_ms < 0:
        raise ValueError(f"{key_id}: not_before_ms must be an integer >= 0")
    if isinstance(not_after_ms, bool) or not isinstance(not_after_ms, int) or not_after_ms <= not_before_ms:
        raise ValueError(f"{key_id}: not_after_ms must be greater than not_before_ms")
    if not isinstance(revoked, bool):
        raise ValueError(f"{key_id}: revoked must be boolean")


def validate_config(config: dict[str, Any]) -> None:
    if not isinstance(config, dict) or config.get("schema") != CONFIG_SCHEMA:
        raise ValueError("Unexpected transport keyring config schema")
    if config.get("inline_secret_material_allowed") is not False:
        raise ValueError("inline_secret_material_allowed must be false")
    principals = config.get("principals")
    if not isinstance(principals, list) or not principals:
        raise ValueError("principals must be a non-empty array")

    seen_ids: set[str] = set()
    seen_sender_epoch: set[tuple[str, int]] = set()
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
        if key_id in seen_ids:
            raise ValueError(f"Duplicate key_id: {key_id}")
        seen_ids.add(key_id)
        if not isinstance(sender_id, str) or not sender_id.strip():
            raise ValueError(f"{key_id}: sender_id must be non-empty")
        if not isinstance(secret_env, str) or not secret_env.strip():
            raise ValueError(f"{key_id}: secret_env must be non-empty")
        if not isinstance(allowed, list) or not allowed or any(not isinstance(item, str) or not item for item in allowed):
            raise ValueError(f"{key_id}: allowed_source_heads must be a non-empty string array")
        if not isinstance(enabled, bool):
            raise ValueError(f"{key_id}: enabled must be boolean")
        _validate_epoch_fields(principal, key_id)
        sender_epoch = (sender_id, principal["epoch"])
        if sender_epoch in seen_sender_epoch:
            raise ValueError(f"Duplicate sender/epoch binding: {sender_id} epoch {principal['epoch']}")
        seen_sender_epoch.add(sender_epoch)


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
        active = principal["enabled"] and not principal["revoked"]
        base = {
            "sender_id": principal["sender_id"],
            "allowed_source_heads": list(principal["allowed_source_heads"]),
            "enabled": principal["enabled"],
            "revoked": principal["revoked"],
            "epoch": principal["epoch"],
            "not_before_ms": principal["not_before_ms"],
            "not_after_ms": principal["not_after_ms"],
        }
        if not active:
            result[key_id] = {"key": b"inactive-principal-placeholder", **base}
            continue
        secret_env = principal["secret_env"]
        raw_secret = env.get(secret_env)
        if raw_secret is None:
            raise ValueError(f"Missing required transport secret environment variable: {secret_env}")
        key = _decode_secret(raw_secret)
        if len(key) < 16:
            raise ValueError(f"{key_id}: decoded transport secret must be at least 16 bytes")
        result[key_id] = {"key": key, **base}
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
                "revoked": row["revoked"],
                "epoch": row["epoch"],
                "not_before_ms": row["not_before_ms"],
                "not_after_ms": row["not_after_ms"],
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
                "key_id": "GUARDIAN_TEST_E1",
                "sender_id": "DEMIHEAD.GUARDIAN",
                "allowed_source_heads": ["GUARDIAN"],
                "secret_env": "JANUS_TEST_KEY",
                "enabled": True,
                "revoked": False,
                "epoch": 1,
                "not_before_ms": 1_700_000_000_000,
                "not_after_ms": 1_900_000_000_000,
            }
        ],
    }
    lookup = load_principal_lookup(config, environ={"JANUS_TEST_KEY": "hex:" + "11" * 32})
    principal = lookup["GUARDIAN_TEST_E1"]
    checks = {
        "principal_loaded": principal["sender_id"] == "DEMIHEAD.GUARDIAN",
        "secret_decoded": principal["key"] == bytes.fromhex("11" * 32),
        "source_allowlist_preserved": principal["allowed_source_heads"] == ["GUARDIAN"],
        "epoch_preserved": principal["epoch"] == 1,
        "revocation_preserved": principal["revoked"] is False,
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

    revoked = json.loads(json.dumps(config))
    revoked["principals"][0]["revoked"] = True
    revoked_lookup = load_principal_lookup(revoked, environ={})
    checks["revoked_principal_requires_no_secret_load"] = revoked_lookup["GUARDIAN_TEST_E1"]["revoked"] is True

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
