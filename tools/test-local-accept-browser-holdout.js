'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

function assert(condition, message) {
  if (!condition) throw new Error(message);
}

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

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function waitForText(page, selector, pattern, timeout = 5000) {
  const started = Date.now();
  for (;;) {
    const text = (await page.textContent(selector)) || '';
    if (typeof pattern === 'string' ? text.includes(pattern) : pattern.test(text)) return text;
    if (Date.now() - started > timeout) throw new Error(`timeout waiting for ${selector} to match ${pattern}; last=${text}`);
    await sleep(40);
  }
}

const KEYS = {
  hrain: 'hrain_v10_4_restore',
  inaihr: 'inaihr_v2',
  meta: 'inaihr_demihead_provenance_v1'
};

const HRAIN_SEED = {
  nodes: [
    {id:1,label:'Context',emoji:'🧩',type:'default',x:10,y:20,parentId:null,chatHistory:[],origin:'USER'},
    {id:2,label:'Evidence',emoji:'🔎',type:'info',x:30,y:40,parentId:null,chatHistory:[],origin:'USER'},
    {id:3,label:'Release',emoji:'◇',type:'default',x:50,y:60,parentId:null,chatHistory:[],origin:'SYSTEM'}
  ],
  links: [{source:1,target:2},{source:2,target:3}]
};

const INAIHR_SEED = {
  nodes: [
    {id:1,label:'Origin',x:10,y:20,isAI:false},
    {id:2,label:'Remote concept',x:30,y:40,isAI:true},
    {id:3,label:'Local branch',x:50,y:60,isAI:false}
  ],
  links: [{source:1,target:2},{source:1,target:3}]
};

const META_EMPTY = {schema:'janus.inaihr.demihead_provenance.v1',nodes:{}};

async function snapshot(page) {
  return page.evaluate((keys) => ({
    hrain: localStorage.getItem(keys.hrain),
    inaihr: localStorage.getItem(keys.inaihr),
    meta: localStorage.getItem(keys.meta)
  }), KEYS);
}

async function seed(page, baseUrl) {
  await page.goto(`${baseUrl}/examples/hemisphere_proposal_lab.html`, {waitUntil:'load'});
  await page.evaluate(({keys, hrain, inaihr, meta}) => {
    localStorage.clear();
    localStorage.setItem(keys.hrain, JSON.stringify(hrain));
    localStorage.setItem(keys.inaihr, JSON.stringify(inaihr));
    localStorage.setItem(keys.meta, JSON.stringify(meta));
  }, {keys:KEYS, hrain:HRAIN_SEED, inaihr:INAIHR_SEED, meta:META_EMPTY});
}

async function exportPacket(page, baseUrl, kind) {
  const before = await snapshot(page);
  const relative = kind === 'hrain' ? '_browser/Hrain/demihead.html' : '_browser/iNaiHR/demihead.html';
  await page.goto(`${baseUrl}/${relative}`, {waitUntil:'load'});
  await waitForText(page, '#status', /nodes/);
  const raw = await page.inputValue('#packet');
  const packet = JSON.parse(raw);
  const after = await snapshot(page);
  assert(canonicalJson(before) === canonicalJson(after), `${kind}: sidecar export changed storage`);
  if (kind === 'hrain') {
    assert(packet.hemisphere === 'LEFT_HRAIN', 'HRain sidecar wrong hemisphere');
    assert(packet.source.repository === 'Hawkar-usls/Hrain', 'HRain sidecar wrong repository');
  } else {
    assert(packet.hemisphere === 'RIGHT_INAIHR', 'iNaiHR sidecar wrong hemisphere');
    assert(packet.source.repository === 'Hawkar-usls/iNaiHR', 'iNaiHR sidecar wrong repository');
  }
  assert(packet.control.read_only_transfer === true, `${kind}: sidecar not read-only`);
  assert(packet.control.direct_cross_hemisphere_mutation === false, `${kind}: sidecar direct mutation enabled`);
  assert(packet.control.authority_delta === 0, `${kind}: authority drift`);
  assert(packet.control.mass_effect_budget_delta === 0, `${kind}: mass-effect drift`);
  return packet;
}

async function buildProposal(page, baseUrl, packet, label, tag) {
  const before = await snapshot(page);
  await page.goto(`${baseUrl}/examples/hemisphere_proposal_lab.html`, {waitUntil:'load'});
  await page.setInputFiles('#packetFile', {
    name:`${tag}-packet.json`,
    mimeType:'application/json',
    buffer:Buffer.from(JSON.stringify(packet))
  });
  await waitForText(page, '#status', 'No mutation performed');
  await page.fill('#label', label);
  await page.click('#build');
  await waitForText(page, '#status', 'Proposal built locally');
  const envelope = JSON.parse((await page.textContent('#preview')) || '{}');
  assert(envelope.type === 'JANUS_DEMIHEAD_LOCAL_PROPOSAL_V1', `${tag}: wrong proposal envelope type`);
  assert(envelope.proposal.operation.type === 'ADD_NODE', `${tag}: proposal operation drifted`);
  assert(envelope.proposal.operation.node.origin === 'SYSTEM', `${tag}: proposal provenance drifted`);
  assert(envelope.proposal.control.auto_apply === false, `${tag}: auto-apply enabled`);
  assert(envelope.proposal.control.requires_explicit_local_accept === true, `${tag}: explicit accept lost`);
  assert(envelope.proposal.control.direct_cross_hemisphere_write === false, `${tag}: direct cross-write enabled`);
  assert(envelope.proposal.control.external_effect_permitted === false, `${tag}: external effect enabled`);

  const downloadPromise = page.waitForEvent('download');
  await page.click('#download');
  const download = await downloadPromise;
  const file = path.join(os.tmpdir(), `${tag}-${envelope.proposal.proposal_id}.json`);
  await download.saveAs(file);
  const fromDownload = JSON.parse(fs.readFileSync(file, 'utf8'));
  assert(canonicalJson(fromDownload) === canonicalJson(envelope), `${tag}: downloaded proposal differs from preview`);
  const after = await snapshot(page);
  assert(canonicalJson(before) === canonicalJson(after), `${tag}: Proposal Lab changed storage`);
  return {envelope, file};
}

async function previewApply(page, url, proposalFile, relevantKeys) {
  const before = await snapshot(page);
  await page.goto(url, {waitUntil:'load'});
  await page.setInputFiles('#proposalFile', proposalFile);
  await waitForText(page, '#status', 'Nothing has been written');
  const after = await snapshot(page);
  for (const key of relevantKeys) assert(before[key] === after[key], `preview mutated ${key}`);
  return {before, after};
}

async function declineApply(page, relevantKeys) {
  const before = await snapshot(page);
  await page.click('#decline');
  await waitForText(page, '#status', 'no write');
  const after = await snapshot(page);
  for (const key of relevantKeys) assert(before[key] === after[key], `decline mutated ${key}`);
}

async function acceptApply(page, url, proposalFile) {
  await page.goto(url, {waitUntil:'load'});
  await page.setInputFiles('#proposalFile', proposalFile);
  await waitForText(page, '#status', 'Nothing has been written');
  await page.click('#accept');
  await waitForText(page, '#status', 'LOCAL_MUTATION_COMMITTED_AFTER_EXPLICIT_ACCEPT');
  return snapshot(page);
}

async function main() {
  const corpusPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!corpusPath || !outputPath) throw new Error('usage: node tools/test-local-accept-browser-holdout.js <frozen_corpus.json> <output.json>');
  const corpus = JSON.parse(fs.readFileSync(corpusPath, 'utf8'));
  assert(corpus.schema === 'janus.demihead.local_accept_browser_holdout.v1', 'unexpected browser holdout schema');
  const actualFreeze = sha256(canonicalJson(corpus.freeze_payload));
  assert(actualFreeze === corpus.freeze_sha256, `browser holdout freeze hash mismatch: ${actualFreeze}`);
  assert(corpus.freeze_payload.frozen_before_first_execution === true, 'browser corpus not frozen before first execution');
  assert(corpus.freeze_payload.cases.length === 17, 'browser corpus must contain exactly 17 cases');

  const baseUrl = corpus.freeze_payload.browser.server;
  const expectedCases = corpus.freeze_payload.cases.map(([id]) => id);
  const cases = new Map();
  const pageErrors = [];
  const externalRequests = [];
  const record = (id, details = {}) => {
    if (!expectedCases.includes(id)) throw new Error(`unregistered browser case: ${id}`);
    if (cases.has(id)) throw new Error(`duplicate browser case result: ${id}`);
    cases.set(id, {id, status:'PASS', ...details});
  };

  const browser = await chromium.launch({headless:true});
  const context = await browser.newContext({acceptDownloads:true});
  await context.route('**/*', async (route) => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith('http://') || requestUrl.startsWith('https://')) {
      const origin = new URL(requestUrl).origin;
      if (origin !== new URL(baseUrl).origin) {
        externalRequests.push(requestUrl);
        await route.abort();
        return;
      }
    }
    await route.continue();
  });
  const page = await context.newPage();
  page.on('pageerror', (error) => pageErrors.push(String(error.message || error)));

  // HRain: export + browser proposal + preview/decline/accept/reload/isolation.
  await seed(page, baseUrl);
  const leftPacket = await exportPacket(page, baseUrl, 'hrain');
  record('hrain_sidecar_export', {node_count:leftPacket.graph.nodes.length});
  const leftBuilt = await buildProposal(page, baseUrl, leftPacket, 'Browser structural candidate', 'hrain');
  record('hrain_proposal_lab', {proposal_sha256:leftBuilt.envelope.proposal_sha256});
  const hrainApplyUrl = `${baseUrl}/_browser/Hrain/demihead-apply.html`;
  await previewApply(page, hrainApplyUrl, leftBuilt.file, ['hrain','inaihr','meta']);
  record('hrain_preview');
  await declineApply(page, ['hrain','inaihr','meta']);
  record('hrain_decline');
  const beforeHrainAccept = await snapshot(page);
  const afterHrainAccept = await acceptApply(page, hrainApplyUrl, leftBuilt.file);
  const hrainWorkspace = JSON.parse(afterHrainAccept.hrain);
  assert(hrainWorkspace.nodes.length === HRAIN_SEED.nodes.length + 1, 'HRain accept did not add exactly one node');
  const hrainNodeId = leftBuilt.envelope.proposal.operation.node.id;
  const hrainAdded = hrainWorkspace.nodes.find((node) => String(node.id) === hrainNodeId);
  assert(hrainAdded, 'HRain accepted node missing');
  assert(hrainAdded.origin === 'SYSTEM', 'HRain accepted node provenance is not SYSTEM');
  assert(hrainAdded.demiheadProposalSha256 === leftBuilt.envelope.proposal_sha256, 'HRain proposal hash binding missing');
  await page.goto(`${baseUrl}/_browser/Hrain/demihead.html`, {waitUntil:'load'});
  const leftReloadPacket = JSON.parse(await page.inputValue('#packet'));
  const leftReloadNode = leftReloadPacket.graph.nodes.find((node) => String(node.id) === hrainNodeId);
  assert(leftReloadNode && leftReloadNode.origin === 'SYSTEM', 'HRain SYSTEM provenance did not survive reload');
  record('hrain_accept_reload', {node_id:hrainNodeId});
  assert(beforeHrainAccept.inaihr === afterHrainAccept.inaihr && beforeHrainAccept.meta === afterHrainAccept.meta, 'HRain accept changed iNaiHR keys');
  record('hrain_cross_key_isolation');

  // HRain: stale base after preview must fail on accept recheck.
  await seed(page, baseUrl);
  const leftStalePacket = await exportPacket(page, baseUrl, 'hrain');
  const leftStale = await buildProposal(page, baseUrl, leftStalePacket, 'Stale structural candidate', 'hrain-stale');
  await previewApply(page, hrainApplyUrl, leftStale.file, ['hrain','inaihr','meta']);
  await page.evaluate((key) => {
    const w = JSON.parse(localStorage.getItem(key));
    w.nodes[0].label = 'Context changed after preview';
    localStorage.setItem(key, JSON.stringify(w));
  }, KEYS.hrain);
  await page.click('#accept');
  await waitForText(page, '#status', 'BASE_WORKSPACE_CHANGED_REPROPOSE_REQUIRED');
  const staleHrain = JSON.parse((await snapshot(page)).hrain);
  assert(!staleHrain.nodes.some((node) => String(node.id) === leftStale.envelope.proposal.operation.node.id), 'HRain stale proposal node was applied');
  record('hrain_stale_base');

  // HRain: tampered proposal must fail hash validation without writes.
  await seed(page, baseUrl);
  const leftTamperPacket = await exportPacket(page, baseUrl, 'hrain');
  const leftTamper = await buildProposal(page, baseUrl, leftTamperPacket, 'Tamper structural candidate', 'hrain-tamper');
  const tamperedLeft = clone(leftTamper.envelope);
  tamperedLeft.proposal.operation.node.label = 'Tampered after hash';
  const beforeLeftTamper = await snapshot(page);
  await page.goto(hrainApplyUrl, {waitUntil:'load'});
  await page.setInputFiles('#proposalFile', {name:'tampered-left.json', mimeType:'application/json', buffer:Buffer.from(JSON.stringify(tamperedLeft))});
  await waitForText(page, '#status', 'proposal hash mismatch');
  const afterLeftTamper = await snapshot(page);
  assert(canonicalJson(beforeLeftTamper) === canonicalJson(afterLeftTamper), 'HRain tamper refusal changed storage');
  record('hrain_tamper');

  // iNaiHR: export + browser proposal + preview/decline/accept/reload/isolation.
  await seed(page, baseUrl);
  const rightPacket = await exportPacket(page, baseUrl, 'inaihr');
  record('inaihr_sidecar_export', {node_count:rightPacket.graph.nodes.length});
  const rightBuilt = await buildProposal(page, baseUrl, rightPacket, 'Browser associative candidate', 'inaihr');
  record('inaihr_proposal_lab', {proposal_sha256:rightBuilt.envelope.proposal_sha256});
  const inaihrApplyUrl = `${baseUrl}/_browser/iNaiHR/demihead-apply.html`;
  await previewApply(page, inaihrApplyUrl, rightBuilt.file, ['hrain','inaihr','meta']);
  await declineApply(page, ['hrain','inaihr','meta']);
  record('inaihr_preview_decline');
  const beforeRightAccept = await snapshot(page);
  const afterRightAccept = await acceptApply(page, inaihrApplyUrl, rightBuilt.file);
  const rightWorkspace = JSON.parse(afterRightAccept.inaihr);
  const rightMeta = JSON.parse(afterRightAccept.meta);
  const rightNodeId = rightBuilt.envelope.proposal.operation.node.id;
  const rightAdded = rightWorkspace.nodes.find((node) => String(node.id) === rightNodeId);
  assert(rightWorkspace.nodes.length === INAIHR_SEED.nodes.length + 1, 'iNaiHR accept did not add exactly one node');
  assert(rightAdded && rightAdded.isAI === false, 'iNaiHR accepted node missing or became remote AI');
  assert(rightMeta.nodes[rightNodeId] && rightMeta.nodes[rightNodeId].origin === 'SYSTEM', 'iNaiHR SYSTEM metadata missing');
  assert(rightMeta.nodes[rightNodeId].proposal_sha256 === rightBuilt.envelope.proposal_sha256, 'iNaiHR proposal hash metadata missing');
  await page.goto(`${baseUrl}/_browser/iNaiHR/demihead.html`, {waitUntil:'load'});
  const rightReloadPacket = JSON.parse(await page.inputValue('#packet'));
  const rightReloadNode = rightReloadPacket.graph.nodes.find((node) => String(node.id) === rightNodeId);
  assert(rightReloadNode && rightReloadNode.origin === 'SYSTEM', 'iNaiHR SYSTEM provenance did not survive sidecar reload');
  record('inaihr_accept_reload', {node_id:rightNodeId});
  assert(beforeRightAccept.hrain === afterRightAccept.hrain, 'iNaiHR accept changed HRain key');
  record('inaihr_cross_key_isolation');

  // Simulate the current core serializer inside a real browser storage area and
  // verify the sidecar metadata restores provenance only for a still-existing node.
  await page.evaluate(({key, metaKey}) => {
    const w = JSON.parse(localStorage.getItem(key));
    const narrow = {
      nodes:w.nodes.map((node)=>({id:node.id,label:node.label,x:node.x,y:node.y,isAI:!!node.isAI})),
      links:w.links.map((link)=>({source:link.source && link.source.id !== undefined ? link.source.id : link.source,target:link.target && link.target.id !== undefined ? link.target.id : link.target}))
    };
    localStorage.setItem(key, JSON.stringify(narrow));
    if (!localStorage.getItem(metaKey)) throw new Error('metadata unexpectedly missing');
  }, {key:KEYS.inaihr, metaKey:KEYS.meta});
  await page.goto(`${baseUrl}/_browser/iNaiHR/demihead.html`, {waitUntil:'load'});
  let serializerPacket = JSON.parse(await page.inputValue('#packet'));
  let serializerNode = serializerPacket.graph.nodes.find((node)=>String(node.id)===rightNodeId);
  assert(serializerNode && serializerNode.origin === 'SYSTEM', 'iNaiHR metadata did not restore provenance after narrow serializer');
  await page.evaluate(({key, nodeId}) => {
    const w = JSON.parse(localStorage.getItem(key));
    w.nodes = w.nodes.filter((node)=>String(node.id)!==nodeId);
    w.links = w.links.filter((link)=>String(link.source)!==nodeId && String(link.target)!==nodeId);
    localStorage.setItem(key, JSON.stringify(w));
  }, {key:KEYS.inaihr, nodeId:rightNodeId});
  await page.reload({waitUntil:'load'});
  serializerPacket = JSON.parse(await page.inputValue('#packet'));
  assert(!serializerPacket.graph.nodes.some((node)=>String(node.id)===rightNodeId), 'orphan iNaiHR metadata created a missing graph node');
  record('inaihr_serializer_roundtrip');

  // iNaiHR stale base after preview.
  await seed(page, baseUrl);
  const rightStalePacket = await exportPacket(page, baseUrl, 'inaihr');
  const rightStale = await buildProposal(page, baseUrl, rightStalePacket, 'Stale associative candidate', 'inaihr-stale');
  await previewApply(page, inaihrApplyUrl, rightStale.file, ['hrain','inaihr','meta']);
  await page.evaluate((key) => {
    const w = JSON.parse(localStorage.getItem(key));
    w.nodes[0].label = 'Origin changed after preview';
    localStorage.setItem(key, JSON.stringify(w));
  }, KEYS.inaihr);
  await page.click('#accept');
  await waitForText(page, '#status', 'BASE_WORKSPACE_CHANGED_REPROPOSE_REQUIRED');
  const staleRight = JSON.parse((await snapshot(page)).inaihr);
  assert(!staleRight.nodes.some((node)=>String(node.id)===rightStale.envelope.proposal.operation.node.id), 'iNaiHR stale proposal node was applied');
  record('inaihr_stale_base');

  // iNaiHR tamper refusal.
  await seed(page, baseUrl);
  const rightTamperPacket = await exportPacket(page, baseUrl, 'inaihr');
  const rightTamper = await buildProposal(page, baseUrl, rightTamperPacket, 'Tamper associative candidate', 'inaihr-tamper');
  const tamperedRight = clone(rightTamper.envelope);
  tamperedRight.proposal.operation.node.label = 'Tampered after hash';
  const beforeRightTamper = await snapshot(page);
  await page.goto(inaihrApplyUrl, {waitUntil:'load'});
  await page.setInputFiles('#proposalFile', {name:'tampered-right.json', mimeType:'application/json', buffer:Buffer.from(JSON.stringify(tamperedRight))});
  await waitForText(page, '#status', 'proposal hash mismatch');
  const afterRightTamper = await snapshot(page);
  assert(canonicalJson(beforeRightTamper) === canonicalJson(afterRightTamper), 'iNaiHR tamper refusal changed storage');
  record('inaihr_tamper');

  assert(cases.get('hrain_cross_key_isolation')?.status === 'PASS' && cases.get('inaihr_cross_key_isolation')?.status === 'PASS', 'shared-origin key separation dependency failed');
  record('shared_origin_key_separation', {origin:new URL(baseUrl).origin, keys:Object.values(KEYS)});

  await context.close();
  const browserVersion = browser.version();
  await browser.close();

  assert(externalRequests.length === 0, `external requests attempted: ${externalRequests.join(', ')}`);
  assert(pageErrors.length === 0, `browser page errors: ${pageErrors.join(' | ')}`);
  for (const id of expectedCases) assert(cases.has(id), `missing frozen browser case result: ${id}`);
  assert(cases.size === expectedCases.length, 'browser case result count drifted');

  const result = {
    schema:'janus.demihead.local_accept_browser_holdout_result.v1',
    status:'PASS',
    freeze_sha256:actualFreeze,
    browser:{engine:'chromium',version:browserVersion,server:new URL(baseUrl).origin},
    component_revisions:corpus.freeze_payload.component_revisions,
    frozen_case_count:expectedCases.length,
    passed:expectedCases.length,
    failed:0,
    cases:expectedCases.map((id)=>cases.get(id)),
    external_network_requests:externalRequests,
    page_errors:pageErrors,
    verified:{
      real_browser_localstorage_exercised:true,
      live_user_workspace_touched:false,
      proposal_lab_download_exercised:true,
      preview_no_mutation:true,
      decline_no_mutation:true,
      explicit_accept_mutation:true,
      reload_persistence:true,
      stale_base_recheck:true,
      tamper_refusal:true,
      shared_origin_key_isolation:true,
      inaihr_metadata_overlay_roundtrip:true,
      direct_cross_hemisphere_write:false,
      external_effect_permitted:false,
      authority_delta:0,
      mass_effect_budget_delta:0
    },
    claim_ceiling:{
      production_network_latency_measured:false,
      authenticated_human_identity_established:false,
      sha256_binding_is_signature:false,
      real_user_workspace_touched:false,
      production_readiness_established:false,
      authority_delta:0,
      mass_effect_budget_delta:0
    }
  };
  fs.writeFileSync(outputPath, JSON.stringify(result,null,2)+'\n');
  console.log('LOCAL_ACCEPT_BROWSER_HOLDOUT=PASS');
  console.log(`FROZEN_CASES=${expectedCases.length}/${expectedCases.length}`);
  console.log(`CHROMIUM_VERSION=${browserVersion}`);
  console.log('REAL_BROWSER_LOCALSTORAGE_EXERCISED=true');
  console.log('LIVE_USER_WORKSPACE_TOUCHED=false');
  console.log('EXTERNAL_NETWORK_REQUESTS=0');
}

main().catch(async (error) => {
  console.error(error.stack || error.message || String(error));
  process.exitCode = 1;
});
