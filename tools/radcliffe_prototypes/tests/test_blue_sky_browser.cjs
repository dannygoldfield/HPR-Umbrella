/* Run only against an isolated review copy, in a fresh browser context. */
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {chromium}=require(process.env.HPR_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.HPR_REVIEW_TEST_URL||'http://127.0.0.1:18769/';
const output=fs.mkdtempSync(path.join(os.tmpdir(),'hpr-blue-sky-qa-'));
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.HPR_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1360,height:1080}}),page=await context.newPage(),errors=[],checks={};
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelectorAll('.option').length===6&&document.querySelector('#film').readyState>=2);
  assert.equal(await page.locator('#saved').textContent(),'No background chosen yet.');
  checks.noAutomaticChoice=true;
  checks.playback=[];
  for(const kind of ['current','monument','orbit','weather','rooms','reference']){
   await page.locator('[data-kind="'+kind+'"]').click();
   await page.waitForFunction(()=>{const v=document.querySelector('#film');return v.readyState>=2&&!v.paused&&v.currentTime>.3});
   assert(Math.abs(await page.locator('#film').evaluate(v=>v.duration)-33)<.05);
   const joins=[];
   for(const time of [10.8,21.8]){
    await page.locator('#film').evaluate((v,t)=>{v.currentTime=t;return v.play()},time);
    await page.waitForFunction(t=>{const v=document.querySelector('#film');return v.currentTime>t+.65&&!v.paused},time);
    joins.push(Math.round(time+.2));
   }
   await page.locator('#film').evaluate(v=>{v.currentTime=32.6;return v.play()});
   await page.waitForFunction(()=>document.querySelector('#film').ended);
   checks.playback.push({kind,durationSec:33,internalJoinsPlayed:joins,endedNormally:true});
  }
  await page.locator('[data-kind="current"]').click();
  await page.waitForFunction(()=>!document.querySelector('#choose').disabled);
  await page.locator('#film').evaluate(v=>v.pause());
  await page.waitForFunction(()=>document.querySelector('#status').textContent==='Paused.');
  checks.pauseFeedback=true;
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  await page.locator('#choose').click();
  assert.equal(await page.locator('#choose').getAttribute('aria-pressed'),'true');
  assert.match(await page.locator('#saved').textContent(),/Blue current/);
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#saved').textContent.includes('Blue current'));
  checks.choiceSavedAndRestored=true;
  const second=await context.newPage();await second.goto(base,{waitUntil:'domcontentloaded'});
  await second.waitForFunction(()=>document.querySelectorAll('.option').length===6&&document.querySelector('#film').readyState>=2);
  await second.locator('[data-kind="weather"]').click();await second.waitForFunction(()=>!document.querySelector('#choose').disabled);
  await second.locator('#choose').click();
  await page.waitForFunction(()=>document.querySelector('#saved').textContent.includes('Color weather'));
  checks.crossTabChoiceUpdated=true;await second.close();
  for(const kind of ['rooms','orbit','current','monument','weather'])await page.locator('[data-kind="'+kind+'"]').click();
  await page.waitForFunction(()=>document.querySelector('#film').currentTime>.3&&!document.querySelector('#film').paused);
  assert.match(await page.locator('#film').getAttribute('src'),/weather/);
  checks.rapidPreviewSwitches=true;
  await page.locator('#film').evaluate(v=>v.pause());
  await page.setViewportSize({width:390,height:844});
  await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  checks.mobileFits=true;
  assert.deepEqual(errors,[]);checks.errors=errors;checks.isolatedBrowser=true;checks.userProfileAccessed=false;
  fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify(checks,null,2)+'\n');
  console.log(JSON.stringify({output,...checks},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
