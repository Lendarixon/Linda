const {chromium}=require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('fs'),path=require('path'),assert=require('assert/strict');
const OUT=path.resolve(__dirname,'../evidence/ui_overhaul_20261024');
(async()=>{
const browser=await chromium.launch({channel:'msedge',headless:true});const results=[];
try{for(const lang of ['ru','en','pl']){
 const ctx=await browser.newContext();const page=await ctx.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const state=JSON.parse(fs.readFileSync(path.join(OUT,'fixture.json')));state.settings.preload=true;state.settings.language=lang;state.startup={phase:'warming'};
 await page.route('**/api/status',r=>r.fulfill({json:state}));
 await page.route('**/api/packs/status',r=>r.fulfill({json:{licensed:true,trace:{installed:true},humanizer:{lite:{installed:true}},job:{phase:'idle'}}}));
 await page.route('http://127.0.0.1:18826/?*',async r=>{const resp=await r.fetch();let body=await resp.text();body=body.replace(/"preload": false/g,'"preload": true');body=body.replace(/__never__/g,'');
 // Startup boot is embedded as base64, not a JS object literal.
 body=body.replace(/atob\((['"])([A-Za-z0-9+/=]+)\1\)/g,(all,q,b64)=>{try{const obj=JSON.parse(Buffer.from(b64,'base64'));obj.settings.preload=true;return `atob('${Buffer.from(JSON.stringify(obj)).toString('base64')}')`;}catch{return all;}});
 await r.fulfill({response:resp,body});});
 await page.goto('http://127.0.0.1:18826/?language='+lang);await page.waitForFunction(()=>!!window.LINDA_desktop);
 await page.evaluate(()=>{window.LINDA_startupRender({settings:{preload:true},models_ready:true,startup:{phase:'warming'}});});
 assert(await page.locator('#lindaStartup').isVisible());
 await page.evaluate(()=>window.LINDA_startupRender({settings:{preload:true},models_ready:true,startup:{phase:'ready'}}));state.startup.phase='ready';
 for(const [route,selector] of [['check','#textInput'],['trace','#trText'],['humanize','#huText']]){
  await page.locator(`#desktopNav [data-route="${route}"]`).click();await page.locator(selector).click();await page.keyboard.type('Editable '+lang);assert.equal(await page.locator(selector).inputValue(),'Editable '+lang);
 }
 // Suitability warnings remain visible outside the folded guidance.
 await page.locator('#desktopNav [data-route="check"]').click();
 await page.locator('#textInput').fill('A short text with only a few words.');assert(await page.locator('#preflightWarning').isVisible());
 await page.locator('#textInput').fill(Array.from({length:100},(_,i)=>'- item '+i+' word word').join('\n'));assert(await page.locator('#preflightWarning').isVisible());
  await page.route('**/api/detect', r => r.fulfill({json: {result: {verdict: 'uncertain', mode: 'sensitive', ens_z: .12, p_ai: .55, ai_share: .5, voters: {linda_essay: .1, linda_multi_v2: .2, stylo7c: .3}, sentences: [], sentence_stats: {ai_pct: 0, total: 0, granularity: 'sentence'}, heatmap_available: false, routing: 'linda_loupe', language: 'en'}}}));
 await page.locator('#textInput').press('Control+Enter');
 await page.waitForFunction(() => !document.getElementById('resultsContent').classList.contains('hidden'));
 assert.equal(await page.locator('#huCta').isVisible(), true);
 await page.locator('#huCta').click();assert.equal(await page.locator('#huText').inputValue(),await page.locator('#textInput').inputValue());
 let runs=0;await page.route('**/api/humanize',r=>{runs++;return r.fulfill({json:{text:'test'}});});
 await page.route('**/api/upload',async r=>{const name=r.request().postDataBuffer().toString();if(name.includes('bad.pdf'))return r.fulfill({status:422,json:{detail:'invalid'}});return r.fulfill({json:{text:'Extracted complete document',filename:'input-test.docx'}});});
 await page.locator('#huFile').setInputFiles(path.join(OUT,'input-test.docx'));await page.waitForFunction(()=>document.querySelector('#huText').value==='Extracted complete document');assert.equal(runs,0);
 await page.locator('#huFile').setInputFiles({name:'bad.pdf',mimeType:'application/pdf',buffer:Buffer.from('bad')});await page.waitForFunction(()=>!document.querySelector('#huFileBtn').disabled);assert.equal(await page.locator('#huText').inputValue(),'Extracted complete document');
 // Stop keeps controls busy until the server acknowledges worker termination.
 let finishRewrite;let cancelId;
 await page.route('**/api/humanize',r=>new Promise(resolve=>{finishRewrite=async()=>{await r.fulfill({status:499,json:{detail:'cancelled'}});resolve();};}));
 await page.route('**/api/detect/cancel',async r=>{cancelId=r.request().postDataJSON().job_id;await r.fulfill({json:{status:'ok'}});await finishRewrite();});
 await page.locator('#huGo').click();await page.waitForFunction(()=>window.LINDA_tools.active.length===1);
 assert(await page.locator('#huStop').isVisible());assert(await page.locator('#desktopGlobalStop').isVisible());
 await page.locator('#desktopGlobalStop').click();await page.waitForFunction(()=>window.LINDA_tools.active.length===0);
 assert(cancelId);assert.equal(await page.locator('#huText').inputValue(),'Extracted complete document');assert.equal(await page.locator('#huGo').isEnabled(),true);
 const untranslated=[];
 for(const route of ['check','history','batch','compare','trace','humanize','models','settings','help','license']){
  await page.locator(`#desktopNav [data-route="${route}"]`).click();await page.waitForTimeout(80);
  const missing=await page.locator('[data-i18n]').evaluateAll(nodes=>nodes.filter(n=>n.getClientRects().length&&getComputedStyle(n).visibility!=='hidden'&&n.textContent.trim()===n.dataset.i18n).map(n=>n.dataset.i18n));
  untranslated.push(...missing.map(key=>({route,key})));
 }
 assert.deepEqual(untranslated,[],'raw localization keys '+lang);
 assert.deepEqual(errors,[]);results.push({lang,startup_release:true,typed:['main','trace','humanize'],import:true,failure_preserves:true,automatic_runs:runs,localization_routes:10,untranslated});await ctx.close();
}
fs.writeFileSync(path.join(OUT,'input-fix-acceptance.json'),JSON.stringify(results,null,2));console.log(JSON.stringify(results));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
