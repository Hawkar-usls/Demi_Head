#!/usr/bin/env python3
"""Preserve public JANUS Git history and prove a clean, byte-exact restoration.

No snapshot Python, hooks, filters or workflows are executed by this module.
The independent runner optionally tests restored code in a restricted container.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

SOURCE = "https://github.com/Hawkar-usls/Janus-Demiurge.git"
SCHEMA = "janus.repository_recovery.v1"


def git(*args: str, cwd: Path | None = None) -> str:
    env = {key: value for key, value in os.environ.items()
           if not key.startswith(("GIT_", "GH_", "GITHUB_TOKEN"))}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0")
    result = subprocess.run(["git", "-c", "core.hooksPath=" + os.devnull,
                             "-c", "protocol.file.allow=always", *args],
                            cwd=cwd, env=env, text=True, capture_output=True,
                            timeout=600, check=True)
    return result.stdout.strip()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def refs(repo: Path) -> dict[str, str]:
    rows = git("for-each-ref", "--format=%(refname) %(objectname)", cwd=repo)
    return dict(row.split(" ", 1) for row in rows.splitlines())


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode()


def verify_bundle(bundle: Path, destination: Path, expected_refs: dict[str, str],
                  expected_digest: str) -> dict:
    if sha256(bundle) != expected_digest:
        raise ValueError("BUNDLE_HASH_MISMATCH")
    if destination.exists():
        raise ValueError("RESTORE_DESTINATION_MUST_BE_NEW")
    git("clone", "--mirror", str(bundle.resolve()), str(destination.resolve()))
    git("bundle", "verify", str(bundle.resolve()), cwd=destination)
    git("fsck", "--full", "--strict", cwd=destination)
    restored_refs = refs(destination)
    if restored_refs != expected_refs:
        raise ValueError("RESTORED_REFS_MISMATCH")
    return {"bundle_sha256_matches": True, "bundle_verify": True,
            "git_fsck_full_strict": True, "all_refs_match": True,
            "restored_ref_count": len(restored_refs)}


def create_snapshot(source: str, output: Path) -> dict:
    # The CLI always uses SOURCE. The function accepts local repositories for tests.
    output.mkdir(parents=True, exist_ok=False)
    with tempfile.TemporaryDirectory(prefix="janus-recovery-") as temp:
        root = Path(temp)
        mirror = root / "source.git"
        git("clone", "--mirror", source, str(mirror))
        expected_refs = refs(mirror)
        if "refs/heads/main" not in expected_refs:
            raise ValueError("MAIN_REF_MISSING")
        bundle = output / "janus-demiurge.bundle"
        git("bundle", "create", str(bundle.resolve()), "--all", cwd=mirror)
        digest = sha256(bundle)
        checks = verify_bundle(bundle, root / "restored.git", expected_refs, digest)
        ref_bytes = json_bytes(expected_refs)
        (output / "refs.json").write_bytes(ref_bytes)
        manifest = {
            "schema": SCHEMA, "status": "REPOSITORY_RECOVERY_VERIFIED",
            "source_repository": "Hawkar-usls/Janus-Demiurge",
            "storage_repository": "Hawkar-usls/Demi_Head",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "source_main_sha": expected_refs["refs/heads/main"],
            "source_memory_sha": expected_refs.get("refs/heads/beetle-memory"),
            "bundle_file": bundle.name, "bundle_sha256": digest,
            "bundle_bytes": bundle.stat().st_size,
            "refs_sha256": hashlib.sha256(ref_bytes).hexdigest(),
            "checks": checks,
            "scope": "All fetched Git refs and reachable history, tracked code, configuration, state and model weights",
            "excludes": ["local Habitat private journal", "credentials and runtime secrets",
                         "untracked files", "external databases and NAS files",
                         "Git LFS objects and submodule repositories"],
            "whole_organism_recovery_verified": False,
            "restored_code_executed_on_host": False,
            "functional_drill": {"status": "NOT_RUN"},
        }
        # Published repositories must not imply that LFS pointers are actual weights.
        tracked = git("ls-tree", "-r", "--name-only", "refs/heads/main", cwd=mirror)
        manifest["tracked_main_file_count"] = len(tracked.splitlines())
        (output / "manifest.json").write_bytes(json_bytes(manifest))
        return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = create_snapshot(SOURCE, args.output.resolve())
    print(json.dumps({key: manifest[key] for key in
                      ("status", "source_main_sha", "bundle_sha256", "bundle_bytes")}))


if __name__ == "__main__":
    main()
