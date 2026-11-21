const {chromium}=require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..'),OUT=path.join(ROOT,'evidence/ui_overhaul_20261024');
const BASE='http://127.0.0.1:18826',results=[];
const fixture=JSON.parse(fs.readFileSync(path.join(OUT,'fixture.json'),'utf8'));
async function context(browser,language='ru',theme='dark',viewport={width:1360,height:900},extra={}){
 const ctx=await browser.newContext({viewport,reducedMotion:'reduce',permissions:['clipboard-read','clipboard-write']});
 const page=await ctx.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const state=structuredClone(fixture);state.settings={...state.settings,language,theme,preload:false,tour_done:true,...extra};
 state.startup={phase:'ready'};state.models_ready=true;state.installer_job={phase:'idle'};
 const pending=[];
 await page.route('**/api/status',r=>r.fulfill({json:state}));
 await page.route('**/api/settings',async r=>{Object.assign(state.settings,r.request().postDataJSON());pending.push(r.request().postDataJSON());await r.fulfill({json:{settings:state.settings}});});
 await page.goto(`${BASE}/?language=${language}&theme=${theme}`);
 await page.waitForFunction(()=>Boolean(window.LINDA_desktop));await page.waitForTimeout(250);
 return {ctx,page,errors,state,pending};
}
async function layout(page,label){
 const m=await page.evaluate(()=>({width:innerWidth,body:document.body.scrollWidth,workspace:document.getElementById('desktopWorkspace').scrollWidth,client:document.getElementById('desktopWorkspace').clientWidth,title:document.getElementById('desktopPageTitle').innerText,nav:document.getElementById('desktopNav').getBoundingClientRect().toJSON()}));
 assert(m.body<=m.width+1,`${label}: body overflows ${JSON.stringify(m)}`);
 assert(m.workspace<=m.client+1,`${label}: workspace overflows ${JSON.stringify(m)}`);
 const active=page.locator('#desktopNav [aria-current="page"]');assert.equal(await active.count(),1,label+': one active route');
 assert.equal(await page.locator('#desktopPageTitle').isVisible(),true,label+': page title');
}
async function navigate(page,route){
 const button=page.locator(`#desktopNav .ld-nav-button[data-route="${route}"]`);await button.scrollIntoViewIfNeeded();await button.click();
 await page.waitForFunction(r=>document.body.dataset.route===r,route);
 await page.waitForTimeout(35);
}
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
  for(const lang of (process.env.LINDA_UI_FUNCTIONAL_ONLY?[]:['ru','en','pl']))for(const theme of ['dark','light','contrast'])for(const size of [[1360,900],[980,640],[480,800]]){
   const {ctx,page,errors}=await context(browser,lang,theme,{width:size[0],height:size[1]});
   const name=`${lang}-${theme}-${size.join('x')}`;
   await layout(page,name);assert.equal(await page.locator('html').getAttribute('lang'),lang);
   assert.match(await page.locator('.ld-recommendation').innerText(),/300/);
   assert.equal(await page.locator('.ld-preflight-limit').isVisible(),true);
   for(const route of ['history','batch','compare','trace','humanize','models','settings','help','license','check']){
    await navigate(page,route);await layout(page,name+'/'+route);
    if(route==='history'){await page.locator('#desktopHistorySwitch').click();await page.waitForFunction(()=>document.body.dataset.route==='audit');await layout(page,name+'/audit');await page.locator('#desktopHistorySwitch').click();await page.waitForFunction(()=>document.body.dataset.route==='history');}
    if(route==='settings')for(const group of ['checking','storage','updates','appearance']){await page.locator(`[data-setting="${group}"]`).click();assert.equal(await page.locator(`#desktopGroup-${group}`).isVisible(),true);}
   }
   if(size[0]!==480||theme==='light')await page.screenshot({path:path.join(OUT,`matrix-${name}.png`)});
   assert.deepEqual(errors,[],name);results.push({name,pages:11,pass:true});await ctx.close();
  }
  if(process.env.LINDA_UI_FUNCTIONAL_ONLY)results.push(...JSON.parse(fs.readFileSync(path.join(OUT,'layout-acceptance.json'),'utf8')));
  else fs.writeFileSync(path.join(OUT,'layout-acceptance.json'),JSON.stringify(results,null,2));
  // Functional workflow: editing is separate from checking, drafts survive routes/tabs.
  const {ctx,page,errors,state,pending}=await context(browser);
  let detectCount=0,cancelCount=0,mode='success';
  const sample=Array(45).fill('This is a connected sample paragraph for a synthetic interface test.').join(' ');
  const result={verdict:'uncertain',mode:'sensitive',ens_z:.12,p_ai:.55,ai_share:.5,voters:{linda_essay:.1,linda_multi_v2:.2,stylo7c:.3},sentences:[],sentence_stats:{ai_pct:0,total:0,granularity:'sentence'},heatmap_available:false,routing:'linda_loupe',language:'en'};
  await page.route('**/api/detect',async r=>{
   detectCount++;
   if(mode==='pending'){await new Promise(resolve=>setTimeout(resolve,3000));try{await r.fulfill({json:{result}});}catch{}return;}
   if(mode==='error')return r.fulfill({status:503,json:{detail:'Synthetic service failure'}});
   await r.fulfill({json:{result:structuredClone(result)}});
  });
  await page.route('**/api/detect/cancel',r=>{cancelCount++;return r.fulfill({json:{ok:true}});});
  await page.evaluate(text=>navigator.clipboard.writeText(text),sample);
  await page.locator('#btnPaste').click();await page.waitForFunction(text=>document.getElementById('textInput').value===text,sample);assert.equal(detectCount,0,'paste must not start a check');
  await navigate(page,'history');await navigate(page,'check');assert.equal(await page.locator('#textInput').inputValue(),sample,'navigation preserves text');
  await page.locator('#tabsBar .plus').click();await page.locator('#textInput').fill('Second independent text');
  await page.locator('#tabsBar .tab').first().click();assert.equal(await page.locator('#textInput').inputValue(),sample,'tabs preserve text');
  await page.locator('#textInput').press('Control+Enter');await page.waitForFunction(()=>!document.getElementById('resultsContent').classList.contains('hidden'));
  assert.equal(detectCount,1,'one keyboard shortcut must start exactly one check');
  assert(await page.locator('#desktopRewriteResult').isVisible(),'rewrite is beside the verdict in the simple interface');
  await page.screenshot({path:path.join(OUT,'after-result.png')});
  let reportBody=null;
  await page.route('**/api/report',r=>{reportBody=r.request().postDataJSON();return r.fulfill({contentType:'text/csv',body:'type,value\nsynthetic,ui-fixture\n'});});
  await page.locator('#svMore').click();await page.waitForFunction(()=>document.documentElement.dataset.detail==='1');
  const downloadEvent=page.waitForEvent('download');await page.locator('.exp-fmt[data-f="csv"]').click();const download=await downloadEvent;
  assert.equal(download.suggestedFilename(),'linda_report.csv');assert.equal(reportBody.fmt,'csv');assert.equal(reportBody.text,sample);
  await page.screenshot({path:path.join(OUT,'after-result-detailed.png')});
  // File failure leaves the previous text and blocks analysis until an edit.
  await page.locator('#filePicker').setInputFiles({name:'slides.pptx',mimeType:'application/octet-stream',buffer:Buffer.from('test')});
  assert.equal(await page.locator('#textInput').inputValue(),sample);assert.equal(await page.locator('#btnAnalyze').isDisabled(),true);
  assert.equal(await page.locator('#statusIndicator').isVisible(),true);assert((await page.locator('#statusIndicator').innerText()).length>20);
  await page.locator('#textInput').fill(sample+' Edited.');assert.equal(await page.locator('#btnAnalyze').isDisabled(),false);
  mode='error';let dialogs=0;page.on('dialog',async d=>{dialogs++;await d.dismiss();});
  await page.locator('#btnAnalyze').click();await page.locator('#statusIndicator[data-error="true"]').waitFor();assert.equal(dialogs,0,'analysis errors must be inline');
  await page.screenshot({path:path.join(OUT,'after-error.png')});
  mode='pending';await page.locator('#btnAnalyze').click();await page.locator('#desktopStop').waitFor({state:'visible'});await navigate(page,'history');await page.locator('#desktopTask').click();await page.waitForFunction(()=>document.body.dataset.route==='check');await page.locator('#desktopStop').click();
  await page.waitForTimeout(100);assert(cancelCount>=1,'Stop must request backend cancellation');assert.match(await page.locator('#textInput').inputValue(),/Edited/);
  // Settings preview/cancel, save, keyboard categories and global language selector.
  await navigate(page,'settings');await page.locator('#lpTheme').selectOption('light');assert.equal(await page.locator('html').getAttribute('data-theme'),'light');
  await page.locator('#lpSetClose').click();await page.waitForFunction(()=>document.body.dataset.route==='check');assert.equal(await page.locator('html').getAttribute('data-theme'),'dark','Cancel restores preferences');
  await navigate(page,'settings');await page.locator('#desktopSetting-appearance').focus();await page.keyboard.press('ArrowDown');assert.equal(await page.locator('#desktopGroup-checking').isVisible(),true);
  await page.locator('[data-setting="appearance"]').click();await page.locator('#lpTheme').selectOption('light');await page.locator('#lpSetSave').click();
  await page.waitForFunction(()=>document.body.dataset.route==='check');assert(pending.some(x=>x.theme==='light'),'save must persist preferences');
  await page.locator('#desktopLanguage').selectOption('pl');await page.waitForFunction(()=>document.documentElement.lang==='pl');assert(pending.some(x=>x.language==='pl'));
  await navigate(page,'settings');assert.equal(await page.locator('#desktopLanguage').inputValue(),'pl');
  await page.screenshot({path:path.join(OUT,'after-settings-light-pl.png')});
  assert.deepEqual(errors,[]);results.push({name:'functional-edit-paste-tabs-check-error-cancel-settings-language',pass:true});await ctx.close();
  const gated=await context(browser);gated.state.license={licensed:false,status:'none',tier:'',key_hint:''};
  await gated.page.reload();await gated.page.waitForFunction(()=>Boolean(window.LINDA_desktop));await gated.page.waitForTimeout(200);
  await gated.page.locator('[data-route="trace"]').click();await gated.page.waitForFunction(()=>document.body.dataset.route==='license');
  assert.equal(await gated.page.locator('#lpLic').isVisible(),true,'licence gate must be understandable');
  await navigate(gated.page,'check');
  await gated.page.evaluate(()=>{window.LINDA_desktop.navigate('trace');window.LINDA_desktop.navigate('check');});
  await gated.page.waitForTimeout(150);assert.equal(await gated.page.locator('body').getAttribute('data-route'),'check','stale navigation must not reopen a tool');
  // The actual model setup keeps keyboard focus and makes the workspace inert.
  await gated.page.evaluate(()=>document.getElementById('lpSetup').classList.add('show'));
  await gated.page.waitForFunction(()=>document.getElementById('desktopShell').inert);
  assert.equal(await gated.page.evaluate(()=>document.getElementById('lpSetup').contains(document.activeElement)),true);
  await gated.page.evaluate(()=>document.getElementById('lpSetup').classList.remove('show'));
  await gated.page.waitForFunction(()=>!document.getElementById('desktopShell').inert);
  assert.deepEqual(gated.errors,[]);results.push({name:'licence-gate-stale-navigation-modal-focus',pass:true});await gated.ctx.close();
  const offline=await context(browser);
  await offline.page.unroute('**/api/status');await offline.page.route('**/api/status',r=>r.abort());
  await offline.page.reload();await offline.page.waitForFunction(()=>Boolean(window.LINDA_desktop));
  await navigate(offline.page,'settings');
  await offline.page.locator('[data-route="trace"]').click();await offline.page.locator('#lpToast.show.bad').waitFor();
  assert.equal(await offline.page.locator('body').getAttribute('data-route'),'check');assert.deepEqual(offline.errors,[]);results.push({name:'unreachable-service-navigation-recovery',pass:true});await offline.ctx.close();
  // Large text scaling: UI remains operable; no horizontal clipping.
  for(const lang of ['ru','en','pl']){
   const c=await context(browser,lang,'light',{width:980,height:700},{font_scale:150});
   await layout(c.page,lang+'/150%');await navigate(c.page,'settings');await layout(c.page,lang+'/150%/settings');
   await c.page.screenshot({path:path.join(OUT,`large-font-${lang}.png`)});assert.deepEqual(c.errors,[]);results.push({name:`${lang}-150-percent`,pass:true});await c.ctx.close();
  }
  fs.writeFileSync(path.join(OUT,'acceptance.json'),JSON.stringify({cases:results.length,results},null,2));
  console.log('PASS',results.length,'cases;',results.reduce((n,r)=>n+(r.pages||0),0),'route checks; editing/paste/tabs/check/error/stop/settings/language; no JS errors');
 } finally {await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
