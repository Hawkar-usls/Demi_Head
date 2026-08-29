from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "repository_awareness.py"
SPEC = importlib.util.spec_from_file_location("repository_awareness", MODULE_PATH)
assert SPEC and SPEC.loader
repository_awareness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repository_awareness)


class RepositoryAwarenessTests(unittest.TestCase):
    def test_public_snapshot_is_complete_public_boundary(self) -> None:
        snapshot = json.loads((ROOT / "configs" / "repository_portfolio.public.json").read_text(encoding="utf-8"))
        repos = snapshot["repositories"]
        self.assertEqual(snapshot["accounting"]["public_repository_count"], len(repos))
        self.assertEqual(snapshot["accounting"]["public_other_repository_count"], len(repos) - 1)
        self.assertIn("Hawkar-usls/Demi_Head", {repo["full_name"] for repo in repos})
        self.assertTrue(all(repo["visibility"] == "public" for repo in repos))
        self.assertFalse(snapshot["privacy_boundary"]["committed_private_repository_metadata"])

    def test_runtime_inventory_can_include_private_without_authority(self) -> None:
        raw = [
            {"name":"Public-One","full_name":"Hawkar-usls/Public-One","default_branch":"main","private":False,"archived":False,"fork":False},
            {"name":"Private-One","full_name":"Hawkar-usls/Private-One","default_branch":"main","private":True,"archived":False,"fork":False},
        ]
        inventory = repository_awareness.build_inventory(
            owner="Hawkar-usls",
            self_repository="Hawkar-usls/Demi_Head",
            repositories=raw,
            source="test",
            authenticated=True,
        )
        self.assertEqual(inventory["accounting"]["repository_count"], 2)
        self.assertEqual(inventory["accounting"]["private_repository_count"], 1)
        self.assertFalse(inventory["invariants"]["discovery_grants_write_permission"])

    def test_private_cache_is_gitignored(self) -> None:
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn(".janus/repository_portfolio.local.json", gitignore)


if __name__ == "__main__":
    unittest.main()
