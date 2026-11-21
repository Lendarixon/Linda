const {chromium}=require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve(__dirname,'../evidence/ui_overhaul_20261024');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:18826/');await page.waitForTimeout(1600);
 console.log('DOM',JSON.stringify(await page.locator('body').evaluate(el=>[...el.children].filter(n=>!['SCRIPT','STYLE'].includes(n.tagName)).map(n=>({tag:n.tagName,id:n.id,cls:n.className,height:Math.round(n.getBoundingClientRect().height),text:n.innerText?.slice(0,70)})))));
 for(const route of ['check','history','batch','compare','trace','humanize','models','settings','help','license']){
   await page.locator(`#desktopNav [data-route="${route}"]`).click();await page.waitForTimeout(300);
   await page.screenshot({path:path.join(out,`after-${route}.png`),fullPage:true});
   console.log(route,await page.locator('body').getAttribute('data-route'),await page.locator('#desktopWorkspace').evaluate(e=>({scroll:e.scrollWidth,width:e.clientWidth,height:e.clientHeight,lic:document.getElementById('lpLic').className})));
 }
 fs.writeFileSync(path.join(out,'smoke-errors.json'),JSON.stringify(errors,null,2));
 console.log('ERRORS',JSON.stringify(errors));await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
