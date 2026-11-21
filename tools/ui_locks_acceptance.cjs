const {chromium} = require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs = require('fs'), path = require('path'), assert = require('assert/strict');
const OUT = path.resolve(__dirname, '../evidence/ui_overhaul_20261024');
async function newPage(browser, lang, statusMode) {
  const ctx = await browser.newContext(); const page = await ctx.newPage(); const errors = []; page.on('pageerror', e => errors.push(e.message));
  const state = JSON.parse(fs.readFileSync(path.join(OUT, 'fixture.json'))); state.settings.preload = true; state.settings.language = lang; state.startup = {phase: 'ready'};
  if (statusMode === 'unlicensed') {
    state.license = {licensed: false, status: 'none'};
    await page.route('**/api/status', r => r.fulfill({json: state}));
    await page.route('**/api/packs/status', r => r.fulfill({json: {licensed: false}}));
  } else if (statusMode === 'licensed-nopack') {
    state.license = {licensed: true, status: 'granted', tier: 'personal'};
    await page.route('**/api/status', r => r.fulfill({json: state}));
    await page.route('**/api/packs/status', r => r.fulfill({json: {licensed: true, trace: {installed: false}, humanizer: {}}}));
  } else {
    await page.route('**/api/status', r => r.abort());
    await page.route('**/api/packs/status', r => r.abort());
  }
  await page.goto('http://127.0.0.1:18826/?language=' + lang); await page.waitForFunction(() => !!window.LINDA_desktop);
  await page.evaluate(() => window.LINDA_startupRender({settings: {preload: true}, models_ready: true, startup: {phase: 'ready'}}));
  return {ctx, page, errors};
}
(async () => {
const browser = await chromium.launch({channel: 'msedge', headless: true});
const results = [];
try {
for (const lang of ['ru', 'en', 'pl']) {
  { const {ctx, page, errors} = await newPage(browser, lang, 'unlicensed');
    // trace/humanize cabinet tabs carry the lock (shell nav redirects to licence instead)
    await page.locator('#desktopNav [data-route="trace"]').click();
    assert.ok(await page.locator('#lpLic.show').isVisible(), 'licence dialog opens for trace ' + lang);
    await page.locator('#lpLicClose').click();
    const trTab = await page.locator('.cab-tab[data-pane="trace"]').textContent();
    const huTab = await page.locator('.cab-tab[data-pane="humanize"]').textContent();
    assert.ok(trTab.trim().startsWith('🔒'), 'trace tab lock ' + lang);
    assert.ok(huTab.trim().startsWith('🔒'), 'humanize tab lock ' + lang);
    const trTitle = await page.locator('.cab-tab[data-pane="trace"]').getAttribute('title');
    assert.ok(trTitle && trTitle.length > 0, 'trace tab tooltip ' + lang);
    // shell nav shows locks too (status poll -> linda-license -> syncNavLocks)
    await page.waitForFunction(() => (document.querySelector('#desktopNav [data-route="trace"] svg path') || {}).getAttribute && document.querySelector('#desktopNav [data-route="trace"] svg path').getAttribute('d').indexOf('M7 11V8') === 0);
    assert.ok((await page.evaluate(() => document.querySelector('#desktopNav [data-route="humanize"] svg path').getAttribute('d'))).startsWith('M7 11V8'));
    assert.ok((await page.evaluate(() => document.querySelector('#desktopNav [data-route="trace"] span').textContent)).indexOf('🔒') === -1, 'no emoji prefix, styled icon instead');
    // models page lists packs with statuses even without a licence, plus the lock on top
    await page.evaluate(() => window.LINDA_desktop.navigate('models'));
    await page.waitForFunction(() => document.body.dataset.route === 'models');
    await page.waitForFunction(() => (document.getElementById('packRows') || {}).innerText.includes('Trace'));
    assert.ok(await page.locator('#packLock:not([hidden])').isVisible(), 'models lock ' + lang);
    await page.locator('#desktopNav [data-route="humanize"]').click();
    assert.ok(await page.locator('#lpLic.show').isVisible(), 'licence dialog opens ' + lang);
    await page.locator('#lpLicClose').click();
    assert.deepEqual(errors, []); await ctx.close(); }
  { const {ctx, page, errors} = await newPage(browser, lang, 'offline');
    // offline race: status unreachable -> cabinet tab opens the pane with inner locks
    await page.evaluate(() => document.querySelector('#cabView').classList.add('open'));
    await page.locator('.cab-tab[data-pane="humanize"]').evaluate(b => b.click());
    await page.waitForFunction(() => window._cabPane === 'humanize' && !document.getElementById('huLock').hidden);
    assert.ok(await page.locator('#huLock:not([hidden])').isVisible(), 'hu inner lock ' + lang);
    await page.locator('#huLockBtn').click();
    assert.ok(await page.locator('#lpLic.show').isVisible(), 'hu lock opens licence ' + lang);
    await page.locator('#lpLicClose').click();
    await page.locator('.cab-tab[data-pane="trace"]').evaluate(b => b.click());
    await page.waitForFunction(() => window._cabPane === 'trace' && !document.getElementById('trLock').hidden);
    assert.ok(await page.locator('#trLock:not([hidden])').isVisible(), 'tr inner lock ' + lang);
    assert.deepEqual(errors, []); await ctx.close(); }
  { const {ctx, page, errors} = await newPage(browser, lang, 'licensed-nopack');
    // shell nav has no locks when licensed
    await page.waitForFunction(() => (window.__lindaLicense || {}).licensed === true);
    await page.waitForTimeout(300);
    assert.equal(await page.evaluate(() => document.querySelector('#desktopNav [data-route="trace"] svg path').getAttribute('d').indexOf('M7 11V8')), -1, 'no nav lock when licensed ' + lang);
    // licensed but packs missing: banners point to Models and packs, Go explains instead of crashing
    await page.evaluate(() => document.querySelector('#cabView').classList.add('open'));
    await page.locator('.cab-tab[data-pane="humanize"]').evaluate(b => b.click());
    await page.waitForFunction(() => window._cabPane === 'humanize' && !document.getElementById('huLock').hidden);
    assert.ok((await page.evaluate(() => document.getElementById('huLockBtn').textContent || '')).length > 10, 'hu pack banner text ' + lang);
    await page.locator('#huLockBtn').click();
    await page.waitForFunction(() => document.body.dataset.route === 'models');
    await page.locator('#desktopNav [data-route="check"]').click().catch(() => {});
    await page.evaluate(() => { document.querySelector('#cabView').classList.add('open'); });
    await page.locator('.cab-tab[data-pane="trace"]').evaluate(b => b.click());
    await page.waitForFunction(() => window._cabPane === 'trace' && !document.getElementById('trLock').hidden);
    assert.ok((await page.evaluate(() => document.getElementById('trLockBtn').textContent || '')).length > 10, 'tr pack banner text ' + lang);
    await page.locator('#trGo').evaluate(b => b.click());
    assert.ok((await page.evaluate(() => document.getElementById('trInfo').textContent || '')).length > 10, 'tr go explains ' + lang);
    assert.deepEqual(errors, []); await ctx.close(); }
  results.push({lang, locks: true});
}
fs.writeFileSync(path.join(OUT, 'locks-acceptance.json'), JSON.stringify(results, null, 2)); console.log(JSON.stringify(results));
} finally { await browser.close(); }
})().catch(e => { console.error(e); process.exit(1); });
