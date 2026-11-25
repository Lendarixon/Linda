const {chromium}=require('C:/Users/ninja/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve(__dirname,'../evidence/ui_overhaul_20261024');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 const page=await browser.newPage({viewport:{width:1440,height:960},reducedMotion:'reduce'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://127.0.0.1:18826/?legacy=1');await page.waitForTimeout(1800);
 await page.screenshot({path:path.join(out,'before-main.png'),fullPage:true});
 await page.locator('#btnSettings').click();await page.screenshot({path:path.join(out,'before-settings.png'),fullPage:true});
 fs.writeFileSync(path.join(out,'baseline-errors.json'),JSON.stringify(errors,null,2));
 console.log(JSON.stringify({errors,title:await page.title(),page:await page.locator('body').innerText().then(s=>s.slice(0,350))}));
 await browser.close();
})().catch(e=>{console.error(e);process.exitCode=1;});
