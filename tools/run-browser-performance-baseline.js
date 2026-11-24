'use strict';

const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { chromium } = require('playwright');

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
function sha256(value) { return crypto.createHash('sha256').update(value).digest('hex'); }
function assert(condition, message) { if (!condition) throw new Error(message); }
function nowNs() { return process.hrtime.bigint(); }
function elapsedMs(start) { return Number(nowNs() - start) / 1e6; }
function nearestRank(values, q) {
  if (!values.length) return null;
  const sorted = [...values].sort((a,b)=>a-b);
  return sorted[Math.max(0, Math.ceil(q * sorted.length) - 1)];
}
function stats(values) {
  const sum = values.reduce((a,b)=>a+b,0);
  return {
    n: values.length,
    min_ms: values.length ? Math.min(...values) : null,
    mean_ms: values.length ? sum / values.length : null,
    p50_ms: nearestRank(values, 0.50),
    p95_ms: nearestRank(values, 0.95),
    p99_ms: nearestRank(values, 0.99),
    max_ms: values.length ? Math.max(...values) : null
  };
}
function clone(value) { return JSON.parse(JSON.stringify(value)); }
function sleep(ms) { return new Promise((resolve)=>setTimeout(resolve, ms)); }

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

async function waitForText(page, selector, fragment, timeoutMs=15000) {
  const started = Date.now();
  while (true) {
    const text = (await page.textContent(selector)) || '';
    if (text.includes(fragment)) return text;
    if (Date.now() - started > timeoutMs) {
      const error = new Error(`TIMEOUT waiting for ${selector} containing ${fragment}; last=${text}`);
      error.code = 'BASELINE_TIMEOUT';
      throw error;
    }
    await sleep(20);
  }
}

async function seedWorkspace(page, baseUrl) {
  await page.goto(`${baseUrl}/examples/hemisphere_proposal_lab.html`, {waitUntil:'load'});
  await page.evaluate(({keys,hrain,inaihr,meta})=>{
    localStorage.clear();
    localStorage.setItem(keys.hrain, JSON.stringify(hrain));
    localStorage.setItem(keys.inaihr, JSON.stringify(inaihr));
    localStorage.setItem(keys.meta, JSON.stringify(meta));
  }, {keys:KEYS,hrain:HRAIN_SEED,inaihr:INAIHR_SEED,meta:META_EMPTY});
}

function procRssBytes(pid) {
  try {
    const status = fs.readFileSync(`/proc/${pid}/status`, 'utf8');
    const match = status.match(/^VmRSS:\s+(\d+)\s+kB$/m);
    return match ? Number(match[1]) * 1024 : 0;
  } catch (_) { return 0; }
}

function createResourceTracker(browserSession, pageSession) {
  const cpuMin = new Map();
  const cpuMax = new Map();
  let peakBrowserRss = 0;
  let peakJsHeapUsed = 0;
  let peakJsHeapTotal = 0;
  let samples = 0;

  async function sample() {
    const info = await browserSession.send('SystemInfo.getProcessInfo');
    let rssSum = 0;
    for (const processInfo of info.processInfo || []) {
      const pid = Number(processInfo.id);
      const cpu = Number(processInfo.cpuTime);
      if (Number.isFinite(cpu)) {
        if (!cpuMin.has(pid)) cpuMin.set(pid, cpu);
        cpuMin.set(pid, Math.min(cpuMin.get(pid), cpu));
        cpuMax.set(pid, Math.max(cpuMax.get(pid) ?? cpu, cpu));
      }
      if (Number.isFinite(pid) && pid > 0) rssSum += procRssBytes(pid);
    }
    peakBrowserRss = Math.max(peakBrowserRss, rssSum);

    const perf = await pageSession.send('Performance.getMetrics');
    const metricMap = Object.fromEntries((perf.metrics || []).map((item)=>[item.name,item.value]));
    if (Number.isFinite(metricMap.JSHeapUsedSize)) peakJsHeapUsed = Math.max(peakJsHeapUsed, metricMap.JSHeapUsedSize);
    if (Number.isFinite(metricMap.JSHeapTotalSize)) peakJsHeapTotal = Math.max(peakJsHeapTotal, metricMap.JSHeapTotalSize);
    samples += 1;
  }

  function receipt() {
    let cpuDelta = 0;
    let observedProcessCount = 0;
    for (const [pid, min] of cpuMin) {
      const max = cpuMax.get(pid);
      if (Number.isFinite(max) && max >= min) {
        cpuDelta += max - min;
        observedProcessCount += 1;
      }
    }
    return {
      sample_count: samples,
      observed_chromium_process_count: observedProcessCount,
      observed_chromium_process_cpu_time_delta_s: cpuDelta,
      peak_sum_rss_bytes_for_observed_chromium_processes: peakBrowserRss,
      peak_js_heap_used_bytes: peakJsHeapUsed,
      peak_js_heap_total_bytes: peakJsHeapTotal,
      cpu_scope_note: 'Observed Chromium process cpuTime min/max across resource samples; process lifetime before first observation is not reconstructed.',
      rss_scope_note: 'Linux /proc VmRSS summed for Chromium process IDs returned by CDP at each resource sample.'
    };
  }

  return {sample, receipt};
}

async function measure(samples, hemisphere, name, fn, resourceTracker, record=true) {
  const start = nowNs();
  const value = await fn();
  const ms = elapsedMs(start);
  if (record) {
    samples.combined[name].push(ms);
    samples.by_hemisphere[hemisphere][name].push(ms);
    await resourceTracker.sample();
  }
  return {value, ms};
}

async function runCycle({page, baseUrl, hemisphere, index, samples, resourceTracker, record}) {
  const isLeft = hemisphere === 'LEFT_HRAIN';
  const sidecarUrl = `${baseUrl}/${isLeft ? '_perf/Hrain' : '_perf/iNaiHR'}/demihead.html`;
  const applyUrl = `${baseUrl}/${isLeft ? '_perf/Hrain' : '_perf/iNaiHR'}/demihead-apply.html`;
  const label = `${isLeft ? 'Structural' : 'Associative'} baseline candidate ${index}`;
  await seedWorkspace(page, baseUrl);
  const fullStart = nowNs();

  const exportResult = await measure(samples, hemisphere, 'sidecar_export', async()=>{
    await page.goto(sidecarUrl, {waitUntil:'load'});
    await waitForText(page, '#status', 'nodes');
    return JSON.parse(await page.inputValue('#packet'));
  }, resourceTracker, record);
  const packet = exportResult.value;
  assert(packet.hemisphere === hemisphere, `${hemisphere}: exported packet hemisphere mismatch`);

  const labResult = await measure(samples, hemisphere, 'proposal_build', async()=>{
    await page.goto(`${baseUrl}/examples/hemisphere_proposal_lab.html`, {waitUntil:'load'});
    await page.setInputFiles('#packetFile', {name:`${hemisphere}-${index}-packet.json`,mimeType:'application/json',buffer:Buffer.from(JSON.stringify(packet))});
    await waitForText(page, '#status', 'No mutation performed');
    await page.fill('#label', label);
    await page.click('#build');
    await waitForText(page, '#status', 'Proposal built locally');
    return JSON.parse((await page.textContent('#preview')) || '{}');
  }, resourceTracker, record);
  const envelope = labResult.value;
  assert(envelope.proposal.operation.type === 'ADD_NODE', `${hemisphere}: proposal operation drift`);

  const tempFile = path.join(os.tmpdir(), `janus-perf-${hemisphere}-${process.pid}-${index}-${Date.now()}.json`);
  await measure(samples, hemisphere, 'proposal_download', async()=>{
    const downloadPromise = page.waitForEvent('download');
    await page.click('#download');
    const download = await downloadPromise;
    await download.saveAs(tempFile);
    const saved = JSON.parse(fs.readFileSync(tempFile,'utf8'));
    assert(canonicalJson(saved) === canonicalJson(envelope), `${hemisphere}: downloaded proposal mismatch`);
  }, resourceTracker, record);

  await measure(samples, hemisphere, 'apply_preview', async()=>{
    await page.goto(applyUrl, {waitUntil:'load'});
    await page.setInputFiles('#proposalFile', tempFile);
    await waitForText(page, '#status', 'Nothing has been written');
  }, resourceTracker, record);

  await measure(samples, hemisphere, 'apply_decline', async()=>{
    await page.click('#decline');
    await waitForText(page, '#status', 'no write');
  }, resourceTracker, record);

  await measure(samples, hemisphere, 'apply_repreview', async()=>{
    await page.goto(applyUrl, {waitUntil:'load'});
    await page.setInputFiles('#proposalFile', tempFile);
    await waitForText(page, '#status', 'Nothing has been written');
  }, resourceTracker, record);

  await measure(samples, hemisphere, 'apply_accept', async()=>{
    await page.click('#accept');
    await waitForText(page, '#status', 'LOCAL_MUTATION_COMMITTED_AFTER_EXPLICIT_ACCEPT');
  }, resourceTracker, record);

  await measure(samples, hemisphere, 'reload_verify', async()=>{
    await page.goto(sidecarUrl, {waitUntil:'load'});
    await waitForText(page, '#status', 'nodes');
    const afterPacket = JSON.parse(await page.inputValue('#packet'));
    const nodeId = envelope.proposal.operation.node.id;
    const node = afterPacket.graph.nodes.find((item)=>String(item.id)===String(nodeId));
    assert(node && node.origin === 'SYSTEM', `${hemisphere}: accepted node/provenance missing after reload`);
  }, resourceTracker, record);

  if (record) {
    const fullMs = elapsedMs(fullStart);
    samples.combined.full_validation_cycle.push(fullMs);
    samples.by_hemisphere[hemisphere].full_validation_cycle.push(fullMs);
  }
  try { fs.unlinkSync(tempFile); } catch (_) {}
}

function makeSampleStore(operations) {
  const names = [...operations, 'full_validation_cycle'];
  const build = () => Object.fromEntries(names.map((name)=>[name,[]]));
  return {
    combined: build(),
    by_hemisphere: {LEFT_HRAIN:build(),RIGHT_INAIHR:build()}
  };
}

function summarizeSamples(samples) {
  const summarizeGroup = (group)=>Object.fromEntries(Object.entries(group).map(([name,values])=>[name,stats(values)]));
  return {
    combined: summarizeGroup(samples.combined),
    by_hemisphere: {
      LEFT_HRAIN:summarizeGroup(samples.by_hemisphere.LEFT_HRAIN),
      RIGHT_INAIHR:summarizeGroup(samples.by_hemisphere.RIGHT_INAIHR)
    }
  };
}

async function main() {
  const protocolPath = process.argv[2];
  const outputPath = process.argv[3];
  if (!protocolPath || !outputPath) throw new Error('usage: node tools/run-browser-performance-baseline.js <frozen_protocol.json> <output.json>');
  const protocol = JSON.parse(fs.readFileSync(protocolPath,'utf8'));
  const payload = protocol.freeze_payload;
  assert(protocol.schema === 'janus.demihead.browser_performance_baseline.v1', 'unexpected performance baseline schema');
  const actualFreeze = sha256(canonicalJson(payload));
  assert(actualFreeze === protocol.freeze_sha256, `performance freeze hash mismatch: ${actualFreeze}`);
  assert(payload.frozen_before_first_execution === true, 'performance protocol not frozen before first execution');
  assert(payload.admission.performance_tuning_permitted_before_baseline === false, 'protocol illegally permits tuning before baseline');
  assert(payload.admission.candidate_comparison === false, 'baseline protocol cannot compare candidates');
  assert(payload.admission.latency_thresholds === null, 'baseline cannot set post-hoc latency threshold');
  assert(payload.admission.resource_thresholds === null, 'baseline cannot set post-hoc resource threshold');

  const baseUrl = payload.browser.fixture_origin;
  const externalRequests = [];
  const pageErrors = [];
  let errorCount = 0;
  let timeoutCount = 0;
  let browser = null;
  let result = null;

  try {
    browser = await chromium.launch({headless:payload.browser.headless});
    const browserVersion = browser.version();
    const context = await browser.newContext({acceptDownloads:true});
    await context.route('**/*', async (route)=>{
      const url = route.request().url();
      if (url.startsWith('http://') || url.startsWith('https://')) {
        const origin = new URL(url).origin;
        if (origin !== new URL(baseUrl).origin) {
          externalRequests.push(url);
          await route.abort();
          return;
        }
      }
      await route.continue();
    });
    const page = await context.newPage();
    page.on('pageerror', (error)=>pageErrors.push(String(error.message || error)));
    page.setDefaultTimeout(15000);

    const pageSession = await context.newCDPSession(page);
    await pageSession.send('Performance.enable');
    const browserSession = await browser.newBrowserCDPSession();

    // Observer/control-plane overhead calibration. It is reported and never subtracted.
    const observerSamples = [];
    for (let i=0;i<payload.workload.observer_roundtrips;i++) {
      const start = nowNs();
      await page.evaluate(()=>performance.now());
      observerSamples.push(elapsedMs(start));
    }

    const operations = payload.workload.operation_order;
    const samples = makeSampleStore(operations);

    // Warmups are run exactly as frozen but are excluded from latency/resource samples.
    for (const hemisphere of payload.workload.hemispheres) {
      for (let i=0;i<payload.workload.warmup_cycles_per_hemisphere;i++) {
        await runCycle({page,baseUrl,hemisphere,index:`warmup-${i}`,samples,resourceTracker:{sample:async()=>{}},record:false});
      }
    }

    const resourceTracker = createResourceTracker(browserSession, pageSession);
    await resourceTracker.sample();
    for (const hemisphere of payload.workload.hemispheres) {
      for (let i=0;i<payload.workload.measured_cycles_per_hemisphere;i++) {
        try {
          await runCycle({page,baseUrl,hemisphere,index:i,samples,resourceTracker,record:true});
        } catch (error) {
          errorCount += 1;
          if (error && (error.code === 'BASELINE_TIMEOUT' || error.name === 'TimeoutError')) timeoutCount += 1;
          throw error;
        }
      }
    }
    await resourceTracker.sample();

    const latency = summarizeSamples(samples);
    const required = payload.admission.required_operation_samples_per_operation;
    for (const name of [...operations,'full_validation_cycle']) {
      assert(samples.combined[name].length === required, `${name}: expected ${required} samples, got ${samples.combined[name].length}`);
    }
    assert(errorCount === payload.admission.required_error_count, `error count ${errorCount}`);
    assert(timeoutCount === payload.admission.required_timeout_count, `timeout count ${timeoutCount}`);
    assert(externalRequests.length === payload.admission.required_external_network_requests, 'external request count drifted');
    assert(pageErrors.length === payload.admission.required_page_errors, `page errors: ${pageErrors.join(' | ')}`);

    result = {
      schema:'janus.demihead.browser_performance_baseline_result.v1',
      status:'PASS',
      freeze_sha256:actualFreeze,
      baseline_only:true,
      candidate_comparison_performed:false,
      tuning_performed:false,
      component_revisions:payload.component_revisions,
      browser:{engine:'chromium',version:browserVersion,fixture_origin:new URL(baseUrl).origin,headless:true},
      workload:{
        warmup_cycles_per_hemisphere:payload.workload.warmup_cycles_per_hemisphere,
        measured_cycles_per_hemisphere:payload.workload.measured_cycles_per_hemisphere,
        measured_cycles_total:payload.workload.measured_cycles_per_hemisphere * payload.workload.hemispheres.length,
        operation_order:payload.workload.operation_order
      },
      observer_roundtrip_overhead_ms:stats(observerSamples),
      latency_ms:latency,
      resources:resourceTracker.receipt(),
      errors:{count:errorCount,timeouts:timeoutCount,page_errors:pageErrors,external_network_requests:externalRequests},
      claim_ceiling:clone(payload.claim_ceiling)
    };

    await context.close();
  } catch (error) {
    if (!result) {
      result = {
        schema:'janus.demihead.browser_performance_baseline_result.v1',
        status:'FAIL',
        freeze_sha256:actualFreeze,
        baseline_only:true,
        candidate_comparison_performed:false,
        tuning_performed:false,
        errors:{count:errorCount || 1,timeouts:timeoutCount,page_errors:pageErrors,external_network_requests:externalRequests,fatal:String(error.stack || error.message || error)},
        claim_ceiling:clone(payload.claim_ceiling)
      };
    }
  } finally {
    if (browser) await browser.close().catch(()=>{});
    fs.writeFileSync(outputPath, JSON.stringify(result,null,2)+'\n');
  }

  if (result.status !== 'PASS') {
    console.error('BROWSER_PERFORMANCE_BASELINE=FAIL');
    console.error(result.errors.fatal || 'baseline admission failed');
    process.exitCode = 1;
    return;
  }
  console.log('BROWSER_PERFORMANCE_BASELINE=PASS');
  console.log(`FREEZE_SHA256=${result.freeze_sha256}`);
  console.log(`MEASURED_CYCLES=${result.workload.measured_cycles_total}`);
  console.log(`FULL_CYCLE_P50_MS=${result.latency_ms.combined.full_validation_cycle.p50_ms}`);
  console.log(`FULL_CYCLE_P95_MS=${result.latency_ms.combined.full_validation_cycle.p95_ms}`);
  console.log(`FULL_CYCLE_P99_MS=${result.latency_ms.combined.full_validation_cycle.p99_ms}`);
  console.log(`PEAK_BROWSER_RSS_BYTES=${result.resources.peak_sum_rss_bytes_for_observed_chromium_processes}`);
  console.log(`OBSERVED_BROWSER_CPU_DELTA_S=${result.resources.observed_chromium_process_cpu_time_delta_s}`);
  console.log('FASTER_THAN_BASELINE_ESTABLISHED=false');
}

main().catch((error)=>{console.error(error.stack||error.message||String(error));process.exitCode=2;});
