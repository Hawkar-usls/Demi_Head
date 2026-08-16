'use strict';

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');
const transport = require(path.join('..', 'examples', 'bicameral-transport.js'));

function canonicalize(value) {
  if (Array.isArray(value)) return value.map(canonicalize);
  if (value && typeof value === 'object') {
    const out = {};
    for (const key of Object.keys(value).sort()) out[key] = canonicalize(value[key]);
    return out;
  }
  return value;
}

function canonicalJson(value) {
  return JSON.stringify(canonicalize(value));
}

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function leftPacket(revision) {
  return {
    schema: transport.PACKET_SCHEMA,
    packet_id: 'holdout-left-valid',
    hemisphere: 'LEFT_HRAIN',
    role: 'STRUCTURAL_CONTEXT',
    captured_at: '2026-08-16T09:40:00Z',
    source: {
      repository: 'Hawkar-usls/Hrain',
      bridge_contract: transport.BRIDGE_CONTRACT,
      source_revision: revision,
      workspace_mode: 'LOCAL_EDITABLE_GRAPH'
    },
    graph: {
      nodes: [
        {id: 1, label: 'Context', origin: 'USER'},
        {id: 2, label: 'Evidence', origin: 'LEGACY_UNKNOWN'}
      ],
      links: [{source: 1, target: 2}]
    },
    control: {
      read_only_transfer: true,
      direct_cross_hemisphere_mutation: false,
      authority_delta: 0,
      mass_effect_budget_delta: 0
    }
  };
}

function rightPacket(revision, divergent) {
  return {
    schema: transport.PACKET_SCHEMA,
    packet_id: divergent ? 'holdout-right-divergent' : 'holdout-right-valid',
    hemisphere: 'RIGHT_INAIHR',
    role: 'ASSOCIATIVE_CONTEXT',
    captured_at: '2026-08-16T09:40:00Z',
    source: {
      repository: 'Hawkar-usls/iNaiHR',
      bridge_contract: transport.BRIDGE_CONTRACT,
      source_revision: revision,
      workspace_mode: 'SEMANTIC_GRAPH'
    },
    graph: divergent ? {
      nodes: [
        {id: 1, label: 'Metaphor', origin: 'SYSTEM'},
        {id: 2, label: 'Association', origin: 'LOCAL_FALLBACK'},
        {id: 3, label: 'Remote branch', origin: 'REMOTE_AI'}
      ],
      links: [{source: 1, target: 2}, {source: 1, target: 3}]
    } : {
      nodes: [
        {id: 1, label: '🧩 Context', origin: 'SYSTEM'},
        {id: 2, label: 'Evidence', origin: 'LOCAL_FALLBACK'},
        {id: 3, label: 'Remote branch', origin: 'REMOTE_AI'}
      ],
      links: [{source: 1, target: 2}, {source: 1, target: 3}]
    },
    control: {
      read_only_transfer: true,
      direct_cross_hemisphere_mutation: false,
      authority_delta: 0,
      mass_effect_budget_delta: 0
    }
  };
}

function nearestRank(values, q) {
  if (!values.length) return null;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.max(0, Math.ceil(q * sorted.length) - 1);
  return sorted[index];
}

function makeEnvelope(code, atMs, ids, revisions) {
  const left = () => leftPacket(revisions.HRain);
  const right = (divergent = false) => rightPacket(revisions.iNaiHR, divergent);
  let origin = transport.PAGES_ORIGIN;
  let source_kind = 'LEFT_FRAME';
  let request_id = ids.current;
  let type = transport.RESPONSE_TYPE;
  let packet = left();

  switch (code) {
    case 'L': break;
    case 'R': source_kind = 'RIGHT_FRAME'; packet = right(); break;
    case 'RD': source_kind = 'RIGHT_FRAME'; packet = right(true); break;
    case 'LE': origin = 'https://evil.invalid'; break;
    case 'LX': source_kind = 'UNKNOWN_FRAME'; break;
    case 'LS': request_id = ids.stale; break;
    case 'LBS': packet.schema = 'janus.demihead.hemisphere_packet.v999'; break;
    case 'LBA': packet.control.authority_delta = 1; break;
    case 'RBM': source_kind = 'RIGHT_FRAME'; packet = right(); packet.control.direct_cross_hemisphere_mutation = true; break;
    case 'RSL': packet = right(); source_kind = 'LEFT_FRAME'; break;
    case 'RL': source_kind = 'RIGHT_FRAME'; packet = right(); break;
    case 'LWT': type = 'JANUS_DEMIHEAD_OTHER_MESSAGE'; break;
    case 'LBP': packet.graph.nodes[1].origin = 'UNKNOWN_MAGIC'; break;
    case 'LM': request_id = undefined; break;
    case 'RS': source_kind = 'RIGHT_FRAME'; packet = right(); request_id = ids.stale; break;
    case 'LN': request_id = ids.current; break;
    case 'RN': source_kind = 'RIGHT_FRAME'; packet = right(); request_id = ids.current; break;
    default: throw new Error(`unknown event code: ${code}`);
  }

  const data = {type, packet};
  if (request_id !== undefined) data.request_id = request_id;
  return {origin, source_kind, received_at_ms: atMs, data};
}

function runCase(spec, payload, latencySamples) {
  const [id, evaluateAt, events, expectedStatus, expectedAccepted, expectedIgnored, expectedRefused] = spec;
  const ids = {
    current: `req-current-${id.replace(/[^A-Za-z0-9]/g, '-')}-0001`,
    stale: `req-stale-${id.replace(/[^A-Za-z0-9]/g, '-')}-0000`
  };
  let state = transport.beginRequest(ids.current, 0, payload.timeout_ms);
  let accepted = 0;
  let ignored = 0;
  let refused = 0;
  const dispositions = [];

  for (const [code, atMs] of events) {
    if (code === 'RESTART') {
      ids.stale = ids.current;
      ids.current = `req-next-${id.replace(/[^A-Za-z0-9]/g, '-')}-0002`;
      state = transport.beginRequest(ids.current, atMs, payload.timeout_ms);
      dispositions.push({code, disposition: 'ROTATED', at_ms: atMs, request_id: ids.current});
      continue;
    }

    const envelope = makeEnvelope(code, atMs, ids, payload.component_revisions);
    const outcome = transport.ingestEnvelope(state, envelope);
    dispositions.push({code, disposition: outcome.disposition, reason: outcome.reason, at_ms: atMs});
    if (outcome.disposition === 'ACCEPTED') {
      accepted += 1;
      latencySamples.push(outcome.latency_ms);
    } else if (outcome.disposition === 'IGNORED') {
      ignored += 1;
    } else if (outcome.disposition === 'REFUSED') {
      refused += 1;
    }
  }

  const result = transport.evaluate(state, evaluateAt);
  const checks = {
    status: result.status === expectedStatus,
    accepted: accepted === expectedAccepted,
    ignored: ignored === expectedIgnored,
    refused: refused === expectedRefused,
    no_external_effect: result.routing.external_effect_permitted === false,
    no_direct_write: result.routing.direct_cross_hemisphere_write_permitted === false,
    no_truth_promotion: result.claim_ceiling.truth_claim_made === false && result.claim_ceiling.agreement_is_truth === false,
    zero_authority: result.claim_ceiling.authority_delta === 0,
    zero_mass_effect: result.claim_ceiling.mass_effect_budget_delta === 0
  };

  if (id === 'nominal_overlap') {
    checks.shared_keys = JSON.stringify(result.comparison.shared_semantic_keys) === JSON.stringify(['context', 'evidence']);
    checks.left_provenance_preserved = JSON.stringify(state.left.graph.nodes.map((node) => node.origin)) === JSON.stringify(['USER', 'LEGACY_UNKNOWN']);
    checks.right_provenance_preserved = JSON.stringify(state.right.graph.nodes.map((node) => node.origin)) === JSON.stringify(['SYSTEM', 'LOCAL_FALLBACK', 'REMOTE_AI']);
  }
  if (id === 'nominal_divergence') {
    checks.no_shared_keys = result.comparison.shared_semantic_keys.length === 0;
    checks.disagreement_preserved = result.routing.disagreement_preserved === true;
  }
  if (id === 'session_rotation') {
    checks.final_request_rotated = result.request_id === ids.current && result.request_id.startsWith('req-next-');
    checks.old_reply_not_accepted = dispositions.some((entry) => entry.code === 'RS' && entry.reason === 'STALE_OR_REPLAYED_REQUEST');
  }

  return {
    id,
    status: Object.values(checks).every(Boolean) ? 'PASS' : 'FAIL',
    expected: {status: expectedStatus, accepted: expectedAccepted, ignored: expectedIgnored, refused: expectedRefused},
    observed: {status: result.status, accepted, ignored, refused},
    checks,
    dispositions
  };
}

function main() {
  const corpusPath = process.argv[2];
  const outputPath = process.argv[3] || null;
  if (!corpusPath) throw new Error('usage: node tools/test-bicameral-transport-holdout.js <corpus.json> [output.json]');
  const corpus = JSON.parse(fs.readFileSync(corpusPath, 'utf8'));
  assert(corpus.schema === 'janus.demihead.bicameral_transport_holdout.v1', 'unexpected holdout schema');
  const actualFreeze = sha256(canonicalJson(corpus.freeze_payload));
  assert(actualFreeze === corpus.freeze_sha256, `freeze hash mismatch: expected ${corpus.freeze_sha256}, got ${actualFreeze}`);
  assert(corpus.freeze_payload.frozen_before_first_execution === true, 'corpus must declare frozen_before_first_execution=true');
  assert(corpus.freeze_payload.latency_semantics === 'frozen_synthetic_event_trace_not_wall_clock', 'latency semantics drift');
  assert(corpus.freeze_payload.cases.length === 18, 'expected exactly 18 frozen cases');

  const latencySamples = [];
  const cases = corpus.freeze_payload.cases.map((spec) => runCase(spec, corpus.freeze_payload, latencySamples));
  const passed = cases.filter((item) => item.status === 'PASS').length;
  const metrics = {
    sample_count: latencySamples.length,
    p50_ms: nearestRank(latencySamples, 0.50),
    p95_ms: nearestRank(latencySamples, 0.95),
    p99_ms: nearestRank(latencySamples, 0.99),
    measurement_kind: 'FROZEN_SYNTHETIC_EVENT_TRACE_NOT_WALL_CLOCK'
  };

  const receipt = {
    schema: 'janus.demihead.bicameral_transport_holdout_result.v1',
    status: passed === cases.length ? 'PASS' : 'FAIL',
    freeze_sha256: actualFreeze,
    frozen_case_count: cases.length,
    passed,
    failed: cases.length - passed,
    component_revisions: corpus.freeze_payload.component_revisions,
    metrics,
    cases,
    claim_ceiling: {
      real_browser_network_latency_measured: false,
      production_readiness_established: false,
      request_id_is_authentication: false,
      independent_evidence_roots_established: false,
      truth_from_agreement_established: false,
      authority_delta: 0,
      mass_effect_budget_delta: 0
    }
  };

  const text = JSON.stringify(receipt, null, 2) + '\n';
  if (outputPath) fs.writeFileSync(outputPath, text);
  else process.stdout.write(text);
  if (receipt.status !== 'PASS') process.exitCode = 1;
}

try { main(); }
catch (error) {
  console.error(`bicameral_transport_holdout: ${error.message}`);
  process.exitCode = 2;
}
