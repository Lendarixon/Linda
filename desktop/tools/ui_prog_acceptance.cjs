const {chromium} = require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs'), path = require('path'), assert = require('assert/strict');
const OUT = path.resolve(__dirname, '../evidence/ui_overhaul_20261024');
(async () => {
const browser = await chromium.launch({channel: 'msedge', headless: true});
const results = [];
try {
for (const lang of ['ru', 'en', 'pl']) {
  const ctx = await browser.newContext(); const page = await ctx.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
  const state = JSON.parse(fs.readFileSync(path.join(OUT, 'fixture.json'))); state.settings.preload = true; state.settings.language = lang; state.startup = {phase: 'ready'};
  await page.route('**/api/status', r => r.fulfill({json: state}));
  await page.route('**/api/packs/status', r => r.fulfill({json: {licensed: true, trace: {installed: true}, humanizer: {lite: {installed: true}} }}));
  await page.goto('http://127.0.0.1:18826/?language=' + lang); await page.waitForFunction(() => !!window.LINDA_desktop);
  await page.evaluate(() => window.LINDA_startupRender({settings: {preload: true}, models_ready: true, startup: {phase: 'ready'}}));
  // ---- inline style panel progress: real check first, then humanize ----
  const sample = Array(45).fill('This is a connected sample paragraph for a synthetic interface test.').join(' ');
  const result = {verdict: 'uncertain', mode: 'sensitive', ens_z: .12, p_ai: .55, ai_share: .5, voters: {linda_essay: .1, linda_multi_v2: .2, stylo7c: .3}, sentences: [], sentence_stats: {ai_pct: 0, total: 0, granularity: 'sentence'}, heatmap_available: false, routing: 'linda_loupe', language: 'en'};
  await page.route('**/api/detect', r => r.fulfill({json: {result: structuredClone(result)}}));
  let finishHum;
  await page.route('**/api/humanize', r => new Promise(res => { finishHum = async () => { await r.fulfill({json: {result: {text: 'rewritten', variant: 'lite', changed: 3}}}); res(); }; }));
  await page.route('**/api/detect/cancel', r => r.fulfill({json: {status: 'ok'}}));
  await page.locator('#textInput').fill(sample);
  await page.locator('#textInput').press('Control+Enter');
  await page.waitForFunction(() => !document.getElementById('resultsContent').classList.contains('hidden'));
  await page.evaluate(() => window.LINDA_packsTick({packs: {trace: {installed: true}, humanizer: {lite: {installed: true}}}}));
  await page.locator('#textInput').press('Control+Enter');
  await page.waitForFunction(() => !document.getElementById('resultsContent').classList.contains('hidden') && document.getElementById('styleLock').classList.contains('hidden'));
  await page.waitForFunction(() => { const b = document.getElementById('styleGo'); if (!b) return false; const r = b.getBoundingClientRect(); return r.width > 0 && r.height > 0 && !b.disabled; });
  await page.locator('[data-smode="all"]').evaluate(b => b.click());
  await page.evaluate(() => document.getElementById('styleGo').click());
  await page.waitForFunction(() => !document.getElementById('styleProg').classList.contains('hidden'));
  await page.waitForFunction(() => document.getElementById('styleProgWrap').classList.contains('busy'));
  assert.ok((await page.evaluate(() => document.getElementById('styleProgLabel').textContent || '')).length > 0, 'style prog label ' + lang);
  await finishHum();
  await page.waitForFunction(() => document.getElementById('styleProg').classList.contains('hidden'));
  assert.equal(await page.locator('#styleOut').inputValue(), 'rewritten', 'style result ' + lang);
  // ---- trace corpus progress ----
  const docs = Array(4).fill(0).map((_, i) => ({id: 'd' + i, title: 'Doc ' + i, text: 'word '.repeat(50)}));
  await page.evaluate(d => localStorage.setItem('linda-trace-corpus', JSON.stringify(d)), docs);
  let finishTr;
  await page.route('**/api/trace/corpus', r => new Promise(res => { finishTr = async () => { await r.fulfill({json: {result: {ranking: []}}}); res(); }; }));
  await page.locator('#desktopNav [data-route="trace"]').click();
  await page.waitForFunction(() => document.body.dataset.route === 'trace');
  await page.locator('#trGo').click();
  await page.waitForFunction(() => !document.getElementById('trProg').hidden && document.getElementById('trProgWrap').classList.contains('busy'));
  await finishTr();
  await page.waitForFunction(() => document.getElementById('trProg').hidden);
  assert.deepEqual(errors, []); results.push({lang, prog: true}); await ctx.close();
}
fs.writeFileSync(path.join(OUT, 'prog-acceptance.json'), JSON.stringify(results, null, 2)); console.log(JSON.stringify(results));
} finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
