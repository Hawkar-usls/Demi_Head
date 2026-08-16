'use strict';

const fs = require('fs');
const path = require('path');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function verifySidecar({root, kind, expectedRevision, expectedHemisphere, expectedRepository, expectedRole, workspace, expectedOrigins}) {
  const bridgePath = path.join(root, 'demihead-bridge.js');
  const sidecarPath = path.join(root, 'demihead.html');
  assert(fs.existsSync(bridgePath), `${kind}: missing demihead-bridge.js`);
  assert(fs.existsSync(sidecarPath), `${kind}: missing demihead.html`);

  const bridge = require(path.resolve(bridgePath));
  const requestId = `req-frozen-${kind.toLowerCase()}-0001`;
  assert(bridge.REQUEST_TYPE === 'JANUS_DEMIHEAD_REQUEST_PACKET_V1', `${kind}: request type drift`);
  assert(bridge.RESPONSE_TYPE === 'JANUS_DEMIHEAD_HEMISPHERE_PACKET_V1', `${kind}: response type drift`);
  assert(bridge.validateRequestId(requestId) === requestId, `${kind}: request id rejected`);

  const response = bridge.buildResponse(requestId, workspace, {
    capturedAt: '2026-08-16T09:40:00Z',
    packetId: `frozen-${kind.toLowerCase()}-packet`,
    sourceRevision: expectedRevision
  });
  assert(response.request_id === requestId, `${kind}: exact request id not echoed`);
  assert(response.packet.hemisphere === expectedHemisphere, `${kind}: hemisphere mismatch`);
  assert(response.packet.role === expectedRole, `${kind}: role mismatch`);
  assert(response.packet.source.repository === expectedRepository, `${kind}: repository mismatch`);
  assert(response.packet.source.source_revision === expectedRevision, `${kind}: source revision option not preserved`);
  assert(JSON.stringify(response.packet.graph.nodes.map((node) => node.origin)) === JSON.stringify(expectedOrigins), `${kind}: provenance normalization drift`);
  assert(response.packet.control.read_only_transfer === true, `${kind}: read-only transfer lost`);
  assert(response.packet.control.direct_cross_hemisphere_mutation === false, `${kind}: direct mutation enabled`);
  assert(response.packet.control.authority_delta === 0, `${kind}: authority delta changed`);
  assert(response.packet.control.mass_effect_budget_delta === 0, `${kind}: mass-effect delta changed`);

  const sidecar = fs.readFileSync(sidecarPath, 'utf8');
  for (const forbidden of [
    'localStorage.setItem',
    'localStorage.removeItem',
    'localStorage.clear',
    'fetch(',
    'XMLHttpRequest',
    'api.github.com/repos/'
  ]) {
    assert(!sidecar.includes(forbidden), `${kind}: forbidden sidecar surface ${forbidden}`);
  }
  assert(sidecar.includes('bridge.validateRequestId(event.data.request_id)'), `${kind}: request id validation missing in sidecar`);
  assert(sidecar.includes('request_id: requestId'), `${kind}: request id echo missing in sidecar`);
  assert(sidecar.includes('event.origin'), `${kind}: exact-origin response path missing`);
  assert(!sidecar.includes("packet: current}, '*')"), `${kind}: wildcard packet response forbidden`);
  assert(sidecar.includes('REQUEST_ID_ECHO != AUTHENTICATION'), `${kind}: claim ceiling missing`);

  return {
    kind,
    expected_revision: expectedRevision,
    hemisphere: response.packet.hemisphere,
    repository: response.packet.source.repository,
    origins: response.packet.graph.nodes.map((node) => node.origin),
    request_binding: true,
    read_only: true,
    authority_delta: 0,
    mass_effect_budget_delta: 0
  };
}

function main() {
  const base = process.argv[2] || '_frozen';
  const expected = {
    HRain: 'c1c4e61e18e1adf15ed1d43da51129b262119985',
    iNaiHR: 'a79cc9affa733bf3d2d6b0ed4815fccf938f3292'
  };

  const left = verifySidecar({
    root: path.join(base, 'Hrain'),
    kind: 'HRain',
    expectedRevision: expected.HRain,
    expectedHemisphere: 'LEFT_HRAIN',
    expectedRepository: 'Hawkar-usls/Hrain',
    expectedRole: 'STRUCTURAL_CONTEXT',
    workspace: {
      nodes: [{id: 1, label: 'Context'}, {id: 2, label: 'Evidence', origin: 'USER'}],
      links: [{source: 1, target: 2}]
    },
    expectedOrigins: ['LEGACY_UNKNOWN', 'USER']
  });

  const right = verifySidecar({
    root: path.join(base, 'iNaiHR'),
    kind: 'iNaiHR',
    expectedRevision: expected.iNaiHR,
    expectedHemisphere: 'RIGHT_INAIHR',
    expectedRepository: 'Hawkar-usls/iNaiHR',
    expectedRole: 'ASSOCIATIVE_CONTEXT',
    workspace: {
      nodes: [
        {id: 1, label: 'Context'},
        {id: 2, label: 'Remote', isAI: true},
        {id: 3, label: 'Fallback', origin: 'LOCAL_FALLBACK', isAI: false}
      ],
      links: [{source: 1, target: 2}, {source: 1, target: 3}]
    },
    expectedOrigins: ['LEGACY_UNKNOWN', 'REMOTE_AI', 'LOCAL_FALLBACK']
  });

  const receipt = {
    status: 'PASS',
    exact_frozen_revisions_verified: true,
    sidecars: [left, right],
    claim_ceiling: {
      request_id_is_authentication: false,
      live_pages_revision_attested_by_packet: false,
      independent_evidence_roots_established: false,
      production_readiness_established: false
    }
  };
  console.log(JSON.stringify(receipt, null, 2));
}

try { main(); }
catch (error) {
  console.error(`verify_frozen_hemisphere_sidecars: ${error.message}`);
  process.exitCode = 1;
}
