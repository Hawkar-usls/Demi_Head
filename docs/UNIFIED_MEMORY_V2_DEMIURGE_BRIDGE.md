# DemiHead → JANUS Demiurge: Unified Memory v2 (read-only probation)

This is an operator-invoked, read-only data bridge, not a live agent, a second graph owner, a source-of-truth registry, or an autonomous action channel.

## Role separation

1. Meta Registry / HRain v2 pilot indexes tracked JSON in the selected **current commit** as a disposable SQLite FTS5 cache with source SHA-256 and explicit JSON-path/URL references. Upstream engine: Hawkar-usls/janus-meta-registry PR #503 (merged; current index rebuilt on every bounded validation run).
2. DemiHead tools/unified_memory_v2_bridge.py reads the local snapshot and emits bounded janus.demihead.unified_memory_search.v1 JSON. It requires independently verified source commit and source-manifest SHA256; no GitHub APIs, tokens, private NAS data, network calls, or database writes.
3. Demiurge tools/demiurge_unified_memory_v2_consumer.py independently checks the packet digest and both source pins. It produces janus.demiurge.unified_memory_context.v1 with a bounded graph compatible with existing read-only restored/memory_graph_query.py. No runtime activation or evidence promotion.

## Reproducible local pipeline

Build and verify the upstream index first in a disposable environment:

    python /path/to/meta/experiments/unified-memory-v2/janus_unified_memory.py build --registry-root /path/to/meta --db /tmp/umv2.sqlite
    python /path/to/meta/experiments/unified-memory-v2/janus_unified_memory.py verify --registry-root /path/to/meta --db /tmp/umv2.sqlite

Pass exact independently verified source_commit and source_manifest_sha256 values:

    python tools/unified_memory_v2_bridge.py --index /tmp/umv2.sqlite --query SCOBY --expected-source-commit EXACT_VERIFIED_COMMIT_SHA --expected-manifest-sha256 EXACT_VERIFIED_MANIFEST_SHA256 --limit 8 --output /tmp/demihead-memory-packet.json
    python /path/to/Janus-Demiurge/tools/demiurge_unified_memory_v2_consumer.py --packet /tmp/demihead-memory-packet.json --expect-source-commit EXACT_VERIFIED_COMMIT_SHA --expect-manifest-sha256 EXACT_VERIFIED_MANIFEST_SHA256 --output /tmp/demiurge-context.json

No secret or private files are transmitted. No network delivery to Demiurge or private NAS is implied: the packet path is provided by the authorized operator. Cross-repository transport requires its own gate.

## Real-corpus local acceptance (2026-11-10, isolated Yaksa)

- Upstream source current-tree corpus: 7,157 JSON at commit 7da4d8aaa1c228ea398e3f820ba8bcec7c2b519c.
- Manifest digest: 32eafed4eaa27900355be80280145f1929c754cbdfd2cf6cda1dbde41b471abc.
- SCOBY, limit 8: 8 results, 36 context nodes, 44 explicit graph edges; packet/consumer digest chain matched.
- Output: CONTEXT_CANDIDATE_READ_ONLY (not verified scientific truth).
- No production HRain or NAS write; no Demiurge control-plane registration.

## Bounded continuous verification

Workflow `.github/workflows/unified-memory-v2-e2e.yml` checks out **current public main commits**, verifies the entire Meta Registry index, exercises DemiHead search and the Demiurge consumer, checks the existing graph-query interface, and saves only a bounded metadata receipt (no database, content snippets, or graph dump). It runs on manual invocation and, after the PR is merged, once daily at 03:17 UTC. Its GITHUB_TOKEN is read-only, source credentials are not persisted, job timeout is 25 minutes and results are retained for 7 days. This workflow does not write to the Demiurge repository or invoke its active agent runtime.

## Gates

- SHA consistency is not authenticated identity or scientific truth.
- Textual references are not independent corroboration.
- No second writable graph owner, automated admission, inference of authority, or auto-publishing.
- Production Demiurge runtime wiring, private NAS ingestion and any automatic model-training or effectful execution remain outside scope. The scheduled cloud verification is read-only and bounded.
