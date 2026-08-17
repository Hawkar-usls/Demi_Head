(function (root, factory) {
  const api = factory(root);
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.JANUSDemiHeadProposalLab = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function (root) {
  'use strict';

  const PACKET_SCHEMA = 'janus.demihead.hemisphere_packet.v2';
  const PROPOSAL_SCHEMA = 'janus.demihead.local_proposal.v1';
  const ENVELOPE_TYPE = 'JANUS_DEMIHEAD_LOCAL_PROPOSAL_V1';
  const BRIDGE_CONTRACT = 'JANUS_DEMIHEAD_BICAMERAL_BRIDGE_V2';
  const RECEIPT_SCHEMA = 'janus.goldprompt.face_startup_receipt.v1_1';
  const MANIFEST_DIGEST = '4bd935ae033c80f090b91a6a5009a51abeb06b99defdc8836763bd9506023a86';
  const SAFE_ID = /^[A-Za-z0-9._:-]{8,128}$/;
  const GIT_REV = /^(?:[0-9a-f]{40}|[0-9a-f]{64})$/;
  const SHA256 = /^[0-9a-f]{64}$/;
  const TARGETS = {
    LEFT_HRAIN: {repository:'Hawkar-usls/Hrain', role:'STRUCTURAL_CONTEXT'},
    RIGHT_INAIHR: {repository:'Hawkar-usls/iNaiHR', role:'ASSOCIATIVE_CONTEXT'}
  };

  function canonicalize(value) {
    if (Array.isArray(value)) return value.map(canonicalize);
    if (value && typeof value === 'object') {
      const out = {};
      for (const key of Object.keys(value).sort()) out[key] = canonicalize(value[key]);
      return out;
    }
    return value;
  }

  function canonicalJson(value) { return JSON.stringify(canonicalize(value)); }

  async function sha256Text(text) {
    if (root && root.crypto && root.crypto.subtle) {
      const bytes = new TextEncoder().encode(text);
      const digest = await root.crypto.subtle.digest('SHA-256', bytes);
      return Array.from(new Uint8Array(digest), (b) => b.toString(16).padStart(2, '0')).join('');
    }
    if (typeof require === 'function') {
      const crypto = require('crypto');
      return crypto.createHash('sha256').update(text).digest('hex');
    }
    throw new Error('SHA-256 implementation unavailable');
  }

  async function sha256Json(value) { return sha256Text(canonicalJson(value)); }

  function safeId(value, name) {
    if (typeof value !== 'string' || !SAFE_ID.test(value)) throw new Error(`${name} must be 8-128 safe ASCII characters`);
    return value;
  }

  function validatePacket(packet) {
    if (!packet || typeof packet !== 'object' || Array.isArray(packet)) throw new Error('hemisphere packet must be an object');
    if (packet.schema !== PACKET_SCHEMA) throw new Error('unexpected hemisphere packet schema');
    const rule = TARGETS[packet.hemisphere];
    if (!rule) throw new Error('unsupported hemisphere');
    if (packet.role !== rule.role) throw new Error('hemisphere role mismatch');
    if (!packet.source || packet.source.repository !== rule.repository) throw new Error('hemisphere repository mismatch');
    if (packet.source.bridge_contract !== BRIDGE_CONTRACT) throw new Error('hemisphere bridge contract mismatch');
    if (typeof packet.source.source_revision !== 'string' || !GIT_REV.test(packet.source.source_revision)) throw new Error('trusted source revision required');
    if (typeof packet.source.goldprompt_receipt_sha256 !== 'string' || !SHA256.test(packet.source.goldprompt_receipt_sha256)) throw new Error('packet receipt SHA binding required');
    const receipt = packet.goldprompt_receipt;
    if (!receipt || typeof receipt !== 'object' || Array.isArray(receipt)) throw new Error('embedded GoldPrompt receipt required');
    if (receipt.schema !== RECEIPT_SCHEMA) throw new Error('embedded GoldPrompt receipt schema mismatch');
    if (receipt.face_id !== packet.hemisphere) throw new Error('embedded GoldPrompt receipt face mismatch');
    if (receipt.face_role !== rule.role) throw new Error('embedded GoldPrompt receipt role mismatch');
    if (receipt.repository !== rule.repository || receipt.repository !== packet.source.repository) throw new Error('embedded GoldPrompt receipt repository mismatch');
    if (receipt.source_revision !== packet.source.source_revision) throw new Error('embedded GoldPrompt receipt source revision mismatch');
    if (receipt.receipt_sha256 !== packet.source.goldprompt_receipt_sha256) throw new Error('embedded GoldPrompt receipt SHA mismatch');
    if (receipt.dependency_manifest_digest_sha256 !== MANIFEST_DIGEST) throw new Error('embedded GoldPrompt dependency manifest mismatch');
    if (receipt.compliance_state !== 'COMPLIANT' || receipt.authority_weight !== 0) throw new Error('embedded GoldPrompt receipt policy mismatch');
    if (!packet.graph || !Array.isArray(packet.graph.nodes) || !Array.isArray(packet.graph.links)) throw new Error('normalized graph missing');
    if (!packet.control || packet.control.read_only_transfer !== true) throw new Error('source packet must be read-only');
    if (packet.control.direct_cross_hemisphere_mutation !== false) throw new Error('source packet requests direct mutation');
    if (packet.control.authority_delta !== 0 || packet.control.mass_effect_budget_delta !== 0) throw new Error('source packet authority boundary drifted');
    return rule;
  }

  async function buildEnvelope(packet, params) {
    const rule = validatePacket(packet);
    const p = params || {};
    const label = typeof p.label === 'string' ? p.label.trim() : '';
    if (!label || label.length > 240 || label !== p.label) throw new Error('label must be pre-trimmed and 1-240 characters');
    if (typeof p.createdAt !== 'string' || !p.createdAt) throw new Error('createdAt required');
    const proposal = {
      schema: PROPOSAL_SCHEMA,
      proposal_id: safeId(p.proposalId, 'proposalId'),
      created_at: p.createdAt,
      target: {hemisphere:packet.hemisphere, repository:rule.repository},
      base_graph_sha256: await sha256Json(packet.graph),
      operation: {type:'ADD_NODE', node:{id:safeId(p.nodeId,'nodeId'), label, origin:'SYSTEM'}},
      control: {
        auto_apply:false,
        requires_explicit_local_accept:true,
        direct_cross_hemisphere_write:false,
        external_effect_permitted:false,
        authority_delta:0,
        mass_effect_budget_delta:0
      }
    };
    return {type:ENVELOPE_TYPE, proposal_sha256:await sha256Json(proposal), proposal};
  }

  return {PACKET_SCHEMA,PROPOSAL_SCHEMA,ENVELOPE_TYPE,TARGETS,canonicalJson,sha256Json,validatePacket,buildEnvelope};
});
