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
  state.license = {licensed: true, status: 'granted', tier: 'personal'};
  await page.route('**/api/status', r => r.fulfill({json: state}));
  await page.route('**/api/packs/status', r => r.fulfill({json: {licensed: true, trace: {installed: true}, humanizer: {lite: {installed: true}}}}));
  let uploads = 0, detects = 0;
  await page.route('**/api/upload', async r => { uploads++; return r.fulfill({json: {text: 'Extracted document number ' + uploads, filename: 'f' + uploads + '.txt'}}); });
  await page.route('**/api/detect', r => { detects++; return r.fulfill({json: {result: null, history_id: 100 + detects}}); });
  await page.route('**/api/history?limit=500', r => r.fulfill({json: {items: [{id: 101, title: 'Doc A', ts: 1}, {id: 102, title: 'Doc B', ts: 2}]}}));
  await page.goto('http://127.0.0.1:18826/?language=' + lang); await page.waitForFunction(() => !!window.LINDA_desktop);
  await page.evaluate(() => window.LINDA_startupRender({settings: {preload: true}, models_ready: true, startup: {phase: 'ready'}}));
  // trace: multi-file import appends both texts
  await page.locator('#desktopNav [data-route="trace"]').click();
  await page.waitForFunction(() => document.body.dataset.route === 'trace');
  await page.locator('#trFile').setInputFiles([
    {name: 'a.txt', mimeType: 'text/plain', buffer: Buffer.from('alpha')},
    {name: 'b.txt', mimeType: 'text/plain', buffer: Buffer.from('beta')}]);
  await page.waitForFunction(() => document.querySelector('#trText').value.includes('Extracted document number 2'));
  assert.ok((await page.locator('#trText').inputValue()).includes('Extracted document number 1'), 'trace multi import ' + lang);
  // batch: folder picker button exists and feeds the queue
  await page.locator('#desktopNav [data-route="batch"]').click();
  assert.ok(await page.locator('#bFolderPick').isVisible(), 'folder picker button ' + lang);
  const before = await page.locator('#bBody tr').count();
  await page.evaluate(() => {
    const dt = new DataTransfer();
    [['d1.txt', 'one'], ['d2.txt', 'two']].forEach(([n, t], i) => {
      const f = new File([t], n, {type: 'text/plain'});
      Object.defineProperty(f, 'webkitRelativePath', {value: 'picked/' + n});
      dt.items.add(f);
    });
    const inp = document.getElementById('bFolderFiles');
    inp.files = dt.files;
    inp.dispatchEvent(new Event('change', {bubbles: true}));
  });
  await page.waitForFunction((n) => document.querySelectorAll('#bBody tr').length >= n, before + 2);
  // compare: file A import checks the file and selects it
  await page.locator('#desktopNav [data-route="compare"]').click();
  await page.waitForFunction(() => document.body.dataset.route === 'compare');
  await page.locator('#cFileAInput').setInputFiles({name: 'cmp-a.txt', mimeType: 'text/plain', buffer: Buffer.from('aaa')});
  await page.waitForFunction(() => document.querySelector('#cA').value === '101', null, {timeout: 15000});
  assert.ok(detects >= 1, 'compare import runs a check ' + lang);
  assert.deepEqual(errors, []); results.push({lang, imports: true}); await ctx.close();
}
fs.writeFileSync(path.join(OUT, 'import-acceptance.json'), JSON.stringify(results, null, 2)); console.log(JSON.stringify(results));
} finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
