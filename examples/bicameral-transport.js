(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.JANUSDemiHeadBicameralTransport = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const PAGES_ORIGIN = 'https://hawkar-usls.github.io';
  const REQUEST_TYPE = 'JANUS_DEMIHEAD_REQUEST_PACKET_V1';
  const RESPONSE_TYPE = 'JANUS_DEMIHEAD_HEMISPHERE_PACKET_V1';
  const PACKET_SCHEMA = 'janus.demihead.hemisphere_packet.v1';
  const BRIDGE_CONTRACT = 'JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V1';
  const DEFAULT_TIMEOUT_MS = 2000;
  const REQUEST_ID_RE = /^[A-Za-z0-9._:-]{8,128}$/;
  const ORIGINS = new Set(['USER', 'REMOTE_AI', 'LOCAL_FALLBACK', 'LEGACY_UNKNOWN', 'SYSTEM']);
  const FRAME_RULES = {
    LEFT_FRAME: {
      slot: 'left',
      hemisphere: 'LEFT_HRAIN',
      role: 'STRUCTURAL_CONTEXT',
      repository: 'Hawkar-usls/Hrain',
      workspace_mode: 'LOCAL_EDITABLE_GRAPH'
    },
    RIGHT_FRAME: {
      slot: 'right',
      hemisphere: 'RIGHT_INAIHR',
      role: 'ASSOCIATIVE_CONTEXT',
      repository: 'Hawkar-usls/iNaiHR',
      workspace_mode: 'SEMANTIC_GRAPH'
    }
  };

  function validateRequestId(value) {
    if (typeof value !== 'string' || !REQUEST_ID_RE.test(value)) {
      throw new Error('request_id must be 8-128 safe ASCII characters');
    }
    return value;
  }

  function finiteMs(value, name) {
    if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) {
      throw new Error(`${name} must be a finite non-negative number`);
    }
    return value;
  }

  function endpointId(value) {
    if (typeof value === 'boolean' || (typeof value !== 'string' && typeof value !== 'number')) {
      throw new Error('Node/link identifiers must be string or number');
    }
    return String(value);
  }

  function semanticKey(label) {
    const text = String(label || '').trim().replace(/\s+/g, ' ');
    const match = text.match(/[\p{L}\p{N}].*$/u);
    return (match ? match[0] : text).toLocaleLowerCase();
  }

  function packetKeys(packet) {
    return new Set((packet.graph.nodes || []).map((node) => semanticKey(node.label)).filter(Boolean));
  }

  function validatePacket(packet, sourceKind) {
    const rules = FRAME_RULES[sourceKind];
    if (!rules) throw new Error('unknown source frame');
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) throw new Error('packet must be an object');
    if (packet.schema !== PACKET_SCHEMA) throw new Error('unexpected packet schema');
    if (packet.hemisphere !== rules.hemisphere) throw new Error('hemisphere/source-frame mismatch');
    if (packet.role !== rules.role) throw new Error('role mismatch');
    if (!packet.source || typeof packet.source !== 'object') throw new Error('source object missing');
    if (packet.source.repository !== rules.repository) throw new Error('repository mismatch');
    if (packet.source.workspace_mode !== rules.workspace_mode) throw new Error('workspace mode mismatch');
    if (packet.source.bridge_contract !== BRIDGE_CONTRACT) throw new Error('bridge contract mismatch');
    if (!packet.control || typeof packet.control !== 'object') throw new Error('control object missing');
    if (packet.control.read_only_transfer !== true) throw new Error('packet is not explicitly read-only');
    if (packet.control.direct_cross_hemisphere_mutation !== false) throw new Error('direct mutation requested');
    if (packet.control.authority_delta !== 0) throw new Error('authority delta is non-zero');
    if (packet.control.mass_effect_budget_delta !== 0) throw new Error('mass-effect delta is non-zero');
    if (!packet.graph || !Array.isArray(packet.graph.nodes) || !Array.isArray(packet.graph.links)) throw new Error('invalid graph');

    const ids = new Set();
    for (const node of packet.graph.nodes) {
      if (!node || typeof node !== 'object') throw new Error('graph node must be an object');
      const id = endpointId(node.id);
      if (ids.has(id)) throw new Error(`duplicate node id: ${id}`);
      ids.add(id);
      if (typeof node.label !== 'string' || !node.label.trim()) throw new Error(`node ${id} has empty label`);
      if (!ORIGINS.has(node.origin)) throw new Error(`node ${id} has unknown provenance origin`);
    }

    const edges = new Set();
    for (const link of packet.graph.links) {
      if (!link || typeof link !== 'object') throw new Error('graph link must be an object');
      const source = endpointId(link.source);
      const target = endpointId(link.target);
      if (!ids.has(source) || !ids.has(target)) throw new Error(`dangling link: ${source} -> ${target}`);
      const edge = `${source}\u0000${target}`;
      if (edges.has(edge)) throw new Error(`duplicate directed link: ${source} -> ${target}`);
      edges.add(edge);
    }
    return packet;
  }

  function beginRequest(requestId, startedAtMs, timeoutMs) {
    const id = validateRequestId(requestId);
    const start = finiteMs(startedAtMs, 'started_at_ms');
    const timeout = timeoutMs === undefined ? DEFAULT_TIMEOUT_MS : finiteMs(timeoutMs, 'timeout_ms');
    if (timeout <= 0) throw new Error('timeout_ms must be greater than zero');
    return {
      active_request_id: id,
      started_at_ms: start,
      deadline_ms: start + timeout,
      timeout_ms: timeout,
      left: null,
      right: null,
      arrivals_ms: {},
      event_ledger: []
    };
  }

  function buildRequest(requestId) {
    return { type: REQUEST_TYPE, request_id: validateRequestId(requestId) };
  }

  function record(state, disposition, reason, envelope, extra) {
    const entry = Object.assign({
      disposition,
      reason,
      source_kind: envelope && envelope.source_kind || null,
      received_at_ms: envelope && envelope.received_at_ms !== undefined ? envelope.received_at_ms : null
    }, extra || {});
    state.event_ledger.push(entry);
    return entry;
  }

  function ingestEnvelope(state, envelope) {
    if (!state || typeof state !== 'object' || !state.active_request_id) throw new Error('active request state required');
    if (!envelope || typeof envelope !== 'object') throw new Error('envelope must be an object');
    const receivedAt = finiteMs(envelope.received_at_ms, 'received_at_ms');
    const sourceKind = envelope.source_kind;
    const data = envelope.data;

    if (envelope.origin !== PAGES_ORIGIN) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'WRONG_ORIGIN', envelope));
    }
    if (!data || typeof data !== 'object' || data.type !== RESPONSE_TYPE) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'WRONG_MESSAGE_TYPE', envelope));
    }

    let requestId;
    try { requestId = validateRequestId(data.request_id); }
    catch (_) {
      return Object.assign({accepted: false}, record(state, 'REFUSED', 'INVALID_REQUEST_ID', envelope));
    }
    if (requestId !== state.active_request_id) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'STALE_OR_REPLAYED_REQUEST', envelope, {request_id: requestId}));
    }
    if (receivedAt > state.deadline_ms) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'LATE_AFTER_DEADLINE', envelope, {request_id: requestId}));
    }

    const rules = FRAME_RULES[sourceKind];
    if (!rules) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'WRONG_SOURCE', envelope, {request_id: requestId}));
    }

    try { validatePacket(data.packet, sourceKind); }
    catch (error) {
      return Object.assign({accepted: false}, record(state, 'REFUSED', 'INVALID_PACKET', envelope, {request_id: requestId, detail: error.message}));
    }

    if (state[rules.slot] !== null) {
      return Object.assign({accepted: false}, record(state, 'IGNORED', 'DUPLICATE_HEMISPHERE_RESPONSE', envelope, {request_id: requestId}));
    }

    state[rules.slot] = data.packet;
    state.arrivals_ms[rules.hemisphere] = receivedAt;
    const latencyMs = receivedAt - state.started_at_ms;
    return Object.assign({accepted: true, latency_ms: latencyMs, hemisphere: rules.hemisphere}, record(state, 'ACCEPTED', 'PACKET_ACCEPTED', envelope, {request_id: requestId, hemisphere: rules.hemisphere, latency_ms: latencyMs}));
  }

  function evaluate(state, nowMs) {
    if (!state || typeof state !== 'object' || !state.active_request_id) throw new Error('active request state required');
    const now = finiteMs(nowMs, 'now_ms');
    const left = state.left;
    const right = state.right;
    let status;
    let mode;

    if (left && right) {
      const leftKeys = packetKeys(left);
      const rightKeys = packetKeys(right);
      const shared = [...leftKeys].filter((value) => rightKeys.has(value)).sort();
      status = shared.length ? 'BICAMERAL_OVERLAP_PRESENT' : 'BICAMERAL_DIVERGENCE_PRESERVED';
      mode = 'BICAMERAL_REVIEW';
      return {
        status,
        mode,
        request_id: state.active_request_id,
        deadline_elapsed: now >= state.deadline_ms,
        hemispheres_present: ['LEFT_HRAIN', 'RIGHT_INAIHR'],
        latency_ms: {
          LEFT_HRAIN: state.arrivals_ms.LEFT_HRAIN - state.started_at_ms,
          RIGHT_INAIHR: state.arrivals_ms.RIGHT_INAIHR - state.started_at_ms
        },
        comparison: {
          shared_semantic_keys: shared,
          left_only_semantic_keys: [...leftKeys].filter((value) => !rightKeys.has(value)).sort(),
          right_only_semantic_keys: [...rightKeys].filter((value) => !leftKeys.has(value)).sort(),
          automatic_graph_merge_performed: false
        },
        routing: {
          external_effect_permitted: false,
          direct_cross_hemisphere_write_permitted: false,
          disagreement_preserved: true
        },
        claim_ceiling: {
          truth_claim_made: false,
          agreement_is_truth: false,
          hemisphere_count_is_authority: false,
          authority_delta: 0,
          mass_effect_budget_delta: 0
        }
      };
    }

    if (now < state.deadline_ms) {
      status = left || right ? 'WAITING_FOR_PEER_HEMISPHERE' : 'WAITING_FOR_HEMISPHERES';
      mode = 'WAITING_NO_EFFECT';
    } else if (left || right) {
      status = 'DEGRADED_SINGLE_HEMISPHERE';
      mode = 'DEGRADED_SINGLE_HEMISPHERE_HOLD';
    } else {
      status = 'NO_HEMISPHERE_TIMEOUT_HOLD';
      mode = 'NO_HEMISPHERE_TIMEOUT_HOLD';
    }

    return {
      status,
      mode,
      request_id: state.active_request_id,
      deadline_elapsed: now >= state.deadline_ms,
      hemispheres_present: [left ? 'LEFT_HRAIN' : null, right ? 'RIGHT_INAIHR' : null].filter(Boolean),
      latency_ms: Object.fromEntries(Object.entries(state.arrivals_ms).map(([key, value]) => [key, value - state.started_at_ms])),
      comparison: {
        shared_semantic_keys: [],
        left_only_semantic_keys: left ? [...packetKeys(left)].sort() : [],
        right_only_semantic_keys: right ? [...packetKeys(right)].sort() : [],
        automatic_graph_merge_performed: false
      },
      routing: {
        external_effect_permitted: false,
        direct_cross_hemisphere_write_permitted: false,
        disagreement_preserved: true
      },
      claim_ceiling: {
        truth_claim_made: false,
        agreement_is_truth: false,
        hemisphere_count_is_authority: false,
        authority_delta: 0,
        mass_effect_budget_delta: 0
      }
    };
  }

  return {
    PAGES_ORIGIN,
    REQUEST_TYPE,
    RESPONSE_TYPE,
    PACKET_SCHEMA,
    BRIDGE_CONTRACT,
    DEFAULT_TIMEOUT_MS,
    FRAME_RULES,
    validateRequestId,
    validatePacket,
    semanticKey,
    beginRequest,
    buildRequest,
    ingestEnvelope,
    evaluate
  };
});
