"""Torch-free checksum tests for standard DemiHead contract CI."""
import base64
import gzip
import hashlib
import json
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]
SOURCE=REPO/'data/tachyon/source_video_relativity_20261111.json'
MANIFEST=REPO/'data/tachyon/weights/tachyon_v02_manifest.json'


class TachyonArtifactTests(unittest.TestCase):
    def test_video_source_pinned(self):
        actual=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
        manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
        self.assertEqual(actual,manifest['sha256_source_json'])
        self.assertFalse(manifest['deployment_authorized'])

    def test_checkpoint_bytes_hash_pinned_without_torch(self):
        item=json.loads(MANIFEST.read_text(encoding='utf-8'))
        b64=''.join((REPO/item['checkpoint_path']).read_text(encoding='ascii').split())
        compressed=base64.b64decode(b64,validate=True)
        self.assertEqual(hashlib.sha256(compressed).hexdigest(),item['checkpoint_gzip_sha256'])
        raw=gzip.decompress(compressed)
        self.assertEqual(hashlib.sha256(raw).hexdigest(),item['checkpoint_unpacked_sha256'])
        self.assertEqual(len(raw),item['checkpoint_unpacked_size_bytes'])


if __name__=='__main__':
    unittest.main()
