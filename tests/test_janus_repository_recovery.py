import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.janus_repository_recovery import create_snapshot, refs, verify_bundle


class RepositoryRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.source.mkdir()
        self.git("init", "-b", "main")
        self.git("config", "user.email", "fixture@example.invalid")
        self.git("config", "user.name", "Fixture")
        (self.source / "state.json").write_text('{"generation": 1}')
        self.git("add", ".")
        self.git("commit", "-m", "Generation one")
        self.git("branch", "beetle-memory")
        self.git("tag", "prior-state")
        (self.source / "state.json").write_text('{"generation": 2}')
        self.git("commit", "-am", "Generation two")

    def git(self, *args):
        return subprocess.check_output(["git", *args], cwd=self.source,
                                       text=True, stderr=subprocess.DEVNULL).strip()

    def snapshot(self):
        output = self.root / "snapshot"
        manifest = create_snapshot(str(self.source), output)
        return output, manifest

    def test_full_history_and_memory_refs_restore_exactly(self):
        output, manifest = self.snapshot()
        self.assertEqual(manifest["source_main_sha"], self.git("rev-parse", "HEAD"))
        self.assertTrue(all(manifest["checks"][key] for key in
                            ("all_refs_match", "bundle_verify", "git_fsck_full_strict")))
        self.assertEqual(manifest["checks"]["restored_ref_count"], 3)
        self.assertFalse(manifest["whole_organism_recovery_verified"])
        self.assertEqual(manifest["functional_drill"]["status"], "NOT_RUN")
        self.assertEqual(json.loads((output / "refs.json").read_text()), refs(self.source))

    def test_tampered_bundle_is_rejected_before_restore(self):
        output, manifest = self.snapshot()
        bundle = output / "janus-demiurge.bundle"
        with bundle.open("ab") as stream:
            stream.write(b"corruption")
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            verify_bundle(bundle, self.root / "new", refs(self.source), manifest["bundle_sha256"])
        self.assertFalse((self.root / "new").exists())

    def test_existing_destination_is_never_overwritten(self):
        output, manifest = self.snapshot()
        destination = self.root / "existing"
        destination.mkdir()
        sentinel = destination / "keep.txt"
        sentinel.write_text("keep")
        with self.assertRaisesRegex(ValueError, "MUST_BE_NEW"):
            verify_bundle(output / "janus-demiurge.bundle", destination,
                          refs(self.source), manifest["bundle_sha256"])
        self.assertEqual(sentinel.read_text(), "keep")
        with self.assertRaises(FileExistsError):
            create_snapshot(str(self.source), output)

    def test_mismatched_expected_refs_fail_closed(self):
        output, manifest = self.snapshot()
        with self.assertRaisesRegex(ValueError, "REFS_MISMATCH"):
            verify_bundle(output / "janus-demiurge.bundle", self.root / "wrong",
                          {}, manifest["bundle_sha256"])


if __name__ == "__main__":
    unittest.main()
