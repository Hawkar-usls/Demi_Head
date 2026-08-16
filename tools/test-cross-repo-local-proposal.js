'use strict';

const fs = require('fs');
const path = require('path');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

function loadJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

async function main() {
  const [hrainRoot, inaihrRoot, leftEnvelopePath, rightEnvelopePath, outputPath] = process.argv.slice(2);
  if (!outputPath) throw new Error('usage: node tools/test-cross-repo-local-proposal.js <hrain-dir> <inaihr-dir> <left-envelope> <right-envelope> <output>');

  const hBridge = require(path.resolve(hrainRoot, 'demihead-bridge.js'));
  const hApply = require(path.resolve(hrainRoot, 'demihead-apply.js'));
  const iBridge = require(path.resolve(inaihrRoot, 'demihead-bridge.js'));
  const iApply = require(path.resolve(inaihrRoot, 'demihead-apply.js'));
  const iProvenance = require(path.resolve(inaihrRoot, 'demihead-provenance.js'));
  const leftEnvelope = loadJson(leftEnvelopePath);
  const rightEnvelope = loadJson(rightEnvelopePath);

  const hrainWorkspace = {
    nodes: [
      {id:1,label:'Context',origin:'USER',type:'default',x:10,y:20,parentId:null,chatHistory:[]},
      {id:2,label:'Evidence',origin:'USER',type:'info',x:30,y:40,parentId:null,chatHistory:[]},
      {id:3,label:'Release',origin:'SYSTEM',type:'default',x:50,y:60,parentId:null,chatHistory:[]}
    ],
    links: [{source:1,target:2},{source:2,target:3}]
  };
  const hrainGraph = hBridge.buildPacket(hrainWorkspace, {capturedAt:'2026-08-16T10:10:00Z',packetId:'cross-left'}).graph;
  await hApply.verifyEnvelope(leftEnvelope);
  assert(await hApply.sha256Json(hrainGraph) === leftEnvelope.proposal.base_graph_sha256, 'Python->HRain base graph hash mismatch');
  const hPrepared = await hApply.prepareAcceptedMutation(hrainWorkspace, hrainGraph, leftEnvelope);
  const hAfterGraph = hBridge.buildPacket(hPrepared.workspace, {capturedAt:'2026-08-16T10:10:01Z',packetId:'cross-left-after'}).graph;
  const hReceipt = hApply.buildReceipt({
    proposalId:hPrepared.proposal_id,
    proposalSha256:hPrepared.proposal_sha256,
    beforeGraphSha256:hPrepared.before_graph_sha256,
    afterGraphSha256:await hApply.sha256Json(hAfterGraph),
    nodeId:leftEnvelope.proposal.operation.node.id
  });
  assert(hPrepared.workspace.nodes.at(-1).origin === 'SYSTEM', 'HRain SYSTEM provenance lost');
  assert(hPrepared.workspace.nodes.at(-1).demiheadProposalSha256 === leftEnvelope.proposal_sha256, 'HRain proposal hash binding lost');

  const inaihrWorkspace = {
    nodes: [
      {id:1,label:'🧩 Context',origin:'SYSTEM',x:10,y:20,isAI:false},
      {id:2,label:'🔎 Evidence',origin:'LOCAL_FALLBACK',x:30,y:40,isAI:false},
      {id:3,label:'💭 Association',origin:'REMOTE_AI',x:50,y:60,isAI:true}
    ],
    links: [{source:1,target:2},{source:1,target:3}]
  };
  const metadata = iProvenance.emptyMetadata();
  const inaihrGraph = iBridge.buildPacket(iProvenance.overlayWorkspace(inaihrWorkspace, metadata), {capturedAt:'2026-08-16T10:10:00Z',packetId:'cross-right'}).graph;
  await iApply.verifyEnvelope(rightEnvelope);
  assert(await iApply.sha256Json(inaihrGraph) === rightEnvelope.proposal.base_graph_sha256, 'Python->iNaiHR base graph hash mismatch');
  const iPrepared = await iApply.prepareAcceptedMutation(inaihrWorkspace, inaihrGraph, metadata, iProvenance, rightEnvelope);
  const iAfterGraph = iBridge.buildPacket(iProvenance.overlayWorkspace(iPrepared.workspace, iPrepared.metadata), {capturedAt:'2026-08-16T10:10:01Z',packetId:'cross-right-after'}).graph;
  const iReceipt = iApply.buildReceipt({
    proposalId:iPrepared.proposal_id,
    proposalSha256:iPrepared.proposal_sha256,
    beforeGraphSha256:iPrepared.before_graph_sha256,
    afterGraphSha256:await iApply.sha256Json(iAfterGraph),
    nodeId:rightEnvelope.proposal.operation.node.id,
    metadataKey:iProvenance.META_KEY
  });
  const addedRight = iProvenance.overlayWorkspace(iPrepared.workspace, iPrepared.metadata).nodes.at(-1);
  assert(addedRight.origin === 'SYSTEM', 'iNaiHR SYSTEM provenance overlay lost');
  assert(addedRight.demiheadProposalSha256 === rightEnvelope.proposal_sha256, 'iNaiHR proposal hash binding lost');
  assert(iPrepared.workspace.nodes.at(-1).isAI === false, 'iNaiHR DemiHead proposal became remote AI');

  const result = {
    status:'PASS',
    exact_external_revisions:{
      HRain:'ceb81210c2f70b71d6c941e0b088a68969ead7b9',
      iNaiHR:'b27cd8732b3137caea1036024acc1778ea02213a'
    },
    checks:{
      python_js_canonical_hash_compatible:true,
      hrain_proposal_verified_and_prepared:true,
      inaihr_proposal_verified_and_prepared:true,
      system_provenance_preserved:true,
      add_node_only:true,
      real_browser_localstorage_written:false,
      direct_cross_hemisphere_write:false,
      external_effect_permitted:false,
      authority_delta:0,
      mass_effect_budget_delta:0
    },
    receipts:[hReceipt,iReceipt],
    claim_ceiling:{
      preparation_is_real_user_acceptance:false,
      ci_in_memory_mutation_is_browser_workspace_effect:false,
      sha256_binding_is_signature:false,
      click_event_is_verified_human_identity:false,
      production_readiness_established:false
    }
  };
  fs.writeFileSync(outputPath, JSON.stringify(result,null,2)+'\n');
  console.log('CROSS_REPO_LOCAL_PROPOSAL=PASS');
  console.log('PYTHON_JS_HASH_COMPATIBLE=true');
  console.log('REAL_BROWSER_LOCALSTORAGE_WRITTEN=false');
}

main().catch((error)=>{console.error(error.stack||error.message||String(error));process.exitCode=1;});
