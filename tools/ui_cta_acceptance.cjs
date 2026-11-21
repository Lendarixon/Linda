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
  const sample = Array(45).fill('This is a connected sample paragraph for a synthetic interface test.').join(' ');
  const result = {verdict: 'uncertain', mode: 'sensitive', ens_z: .12, p_ai: .55, ai_share: .5, voters: {linda_essay: .1, linda_multi_v2: .2, stylo7c: .3}, sentences: [], sentence_stats: {ai_pct: 0, total: 0, granularity: 'sentence'}, heatmap_available: false, routing: 'linda_loupe', language: 'en'};
  await page.route('**/api/detect', r => r.fulfill({json: {result: structuredClone(result)}}));
  await page.route('**/api/detect/cancel', r => r.fulfill({json: {ok: true}}));
  await page.goto('http://127.0.0.1:18826/?language=' + lang); await page.waitForFunction(() => !!window.LINDA_desktop);
  await page.evaluate(() => window.LINDA_startupRender({settings: {preload: true}, models_ready: true, startup: {phase: 'ready'}}));
  await page.evaluate(() => localStorage.removeItem('linda-hu-cta-seen'));
  assert.equal(await page.locator('#huCta').isHidden(), true, 'cta hidden before check ' + lang);
  await page.locator('#textInput').fill(sample);
  await page.locator('#textInput').press('Control+Enter');
  await page.waitForFunction(() => !document.getElementById('resultsContent').classList.contains('hidden'));
  const cta = page.locator('#huCta');
  assert.ok(await cta.isVisible(), 'cta visible after check ' + lang);
  assert.ok(await cta.evaluate(e => e.classList.contains('recommend')), 'cta highlighted once ' + lang);
  const label = await cta.locator('span').innerText();
  assert.ok(label.length > 2 && label !== 'hu_cta', 'cta label translated ' + lang + ': ' + label);
  assert.equal(await cta.locator('.hu-rec').count(), 0, 'no badge element ' + lang);
  await page.waitForFunction(() => !document.getElementById('huCta').classList.contains('recommend'), null, {timeout: 8000});
  assert.ok(await cta.isVisible(), 'cta stays ordinary after 5 s ' + lang);
  await cta.click();
  await page.waitForFunction(() => document.body.dataset.route === 'humanize');
  assert.equal(await page.locator('#huText').inputValue(), sample, 'cta carries text to humanizer ' + lang);
  assert.equal(await page.evaluate(() => localStorage.getItem('linda-hu-cta-seen')), '1', 'seen flag stored ' + lang);
  await page.locator('#desktopNav [data-route="check"]').click();
  await page.waitForFunction(() => !document.getElementById('huCta').classList.contains('recommend'), null, {timeout: 5000}).catch(() => {});
  assert.equal(await page.locator('#huCta.recommend').count(), 0, 'no second highlight ' + lang);
  assert.ok(await page.locator('#huCta').isVisible(), 'cta still offered ' + lang);
  await page.locator('#textInput').fill(sample + ' Edited.');
  assert.equal(await page.locator('#huCta').isHidden(), true, 'cta hides while editing ' + lang);
  assert.deepEqual(errors, []); results.push({lang, cta: true}); await ctx.close();
}
fs.writeFileSync(path.join(OUT, 'cta-acceptance.json'), JSON.stringify(results, null, 2)); console.log(JSON.stringify(results));
} finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
