"""Restore pinned Tachyon v0.2 research candidate from repository text checkpoint.

No remote downloads, dynamic code execution, inference endpoint or auto-promotion.
The .pt checkpoint is compressed base64 solely because the GitHub connector
only writes UTF-8 files. Verify SHA256 before torch.load(weights_only=True).
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
from pathlib import Path

import torch

from .causal import TachyonCausalTransformer, VERSION

REPO=Path(__file__).resolve().parents[1]
MANIFEST=REPO/'data/tachyon/weights/tachyon_v02_manifest.json'


def load_candidate(manifest_path: Path = MANIFEST) -> TachyonCausalTransformer:
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    if manifest['model_id']!='tachyon-v0.2-causal-numerical' or manifest['deployment_authorized'] is not False:
        raise ValueError('invalid_checkpoint_manifest')
    path=REPO/manifest['checkpoint_path']
    encoded=''.join(path.read_text(encoding='ascii').split())
    compressed=base64.b64decode(encoded,validate=True)
    if hashlib.sha256(compressed).hexdigest()!=manifest['checkpoint_gzip_sha256']:
        raise ValueError('packed_checkpoint_sha256_mismatch')
    raw=gzip.decompress(compressed)
    if len(raw)!=manifest['checkpoint_unpacked_size_bytes'] or hashlib.sha256(raw).hexdigest()!=manifest['checkpoint_unpacked_sha256']:
        raise ValueError('checkpoint_sha256_mismatch')
    try:
        payload=torch.load(io.BytesIO(raw),map_location='cpu',weights_only=True)
    except Exception as exc:
        raise ValueError('checkpoint_load_failed') from exc
    if payload.get('version')!=VERSION or payload.get('source_sha256')!=manifest['sha256_source_json']:
        raise ValueError('checkpoint_provenance_mismatch')
    model=TachyonCausalTransformer()
    model.load_state_dict(payload['state_dict'],strict=True)
    model.eval()
    return model
