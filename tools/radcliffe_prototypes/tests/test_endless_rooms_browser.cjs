/* Exercise only an isolated review copy in a fresh browser context. */
const assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path');
const {chromium}=require(process.env.HPR_PLAYWRIGHT_MODULE||'playwright');
const base=process.env.HPR_REVIEW_TEST_URL||'http://127.0.0.1:18769/';
const output=fs.mkdtempSync(path.join(os.tmpdir(),'hpr-rooms-qa-'));
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.HPR_CHROME||'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true});
 const context=await browser.newContext({viewport:{width:1360,height:1080}}),page=await context.newPage(),errors=[],checks={};
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(base,{waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelectorAll('[data-color]').length===5&&document.querySelector('#film').readyState>=2);
  assert.equal(await page.locator('[data-speed]').count(),3);
  assert.match(await page.locator('#saved').textContent(),/^No color/);checks.noAutomaticChoice=true;
  await page.evaluate(()=>localStorage.setItem('hpr-next-20260907','earlier-choice-test-sentinel'));
  checks.playback=[];
  for(const color of ['green','blue','plum','copper','ivory']){
   await page.locator('[data-color="'+color+'"]').click();
   assert.equal(await page.locator('[data-speed="original"]').getAttribute('aria-pressed'),'true');
   for(const speed of ['slow','medium','original']){
    await page.locator('[data-speed="'+speed+'"]').click();
    const id='rooms-'+color+'-'+speed;
    await page.waitForFunction(id=>{const v=document.querySelector('#film');return v.currentSrc.includes(id)&&v.readyState>=2&&!v.paused&&v.currentTime>.2},id);
    assert.equal(await page.locator('[data-color="'+color+'"]').getAttribute('aria-pressed'),'true');
    assert.equal(await page.locator('#film').evaluate(v=>v.playbackRate),1);
    assert(Math.abs(await page.locator('#film').evaluate(v=>v.duration)-33)<.05);
    for(const t of [10.8,21.8]){
     await page.locator('#film').evaluate((v,t)=>{v.currentTime=t;return v.play()},t);
     await page.waitForFunction(t=>{const v=document.querySelector('#film');return v.currentTime>t+.6&&!v.paused},t);
    }
    await page.locator('#film').evaluate(v=>{v.currentTime=32.6;return v.play()});await page.waitForFunction(()=>document.querySelector('#film').ended);
    checks.playback.push({id,durationSec:33,playbackRate:1,joinsPlayed:[11,22],endedNormally:true});
   }
   console.log('Playback checked: '+color);
  }
  checks.colorAndSpeedIndependent=true;
  await page.locator('[data-color="plum"]').click();await page.locator('[data-speed="slow"]').click();
  await page.waitForFunction(()=>!document.querySelector('#choose').disabled);
  await page.locator('#choose').click();assert.equal(await page.locator('#choose').getAttribute('aria-pressed'),'true');
  await page.reload({waitUntil:'domcontentloaded'});
  await page.waitForFunction(()=>document.querySelector('#film').readyState>=2&&document.querySelector('#saved').textContent.includes('Plum'));
  assert.equal(await page.locator('[data-color="plum"]').getAttribute('aria-pressed'),'true');
  assert.equal(await page.locator('[data-speed="slow"]').getAttribute('aria-pressed'),'true');
  assert.match(await page.locator('#film').getAttribute('src'),/rooms-plum-slow/);checks.choiceAndPreviewRestored=true;
  assert.equal(await page.evaluate(()=>localStorage.getItem('hpr-next-20260907')),'earlier-choice-test-sentinel');checks.earlierChoicesUntouched=true;
  await page.locator('#restart').click();await page.waitForFunction(()=>!document.querySelector('#film').paused);
  await page.locator('#film').evaluate(v=>v.pause());await page.waitForFunction(()=>document.querySelector('#status').textContent==='Paused.');checks.pauseFeedback=true;
  await page.screenshot({path:path.join(output,'desktop.png'),fullPage:true});
  const other=await context.newPage();await other.goto(base,{waitUntil:'domcontentloaded'});await other.waitForFunction(()=>document.querySelector('#film').readyState>=2);
  await other.locator('[data-color="ivory"]').click();await other.locator('[data-speed="medium"]').click();await other.waitForFunction(()=>!document.querySelector('#choose').disabled);
  await other.locator('#choose').click();await page.waitForFunction(()=>document.querySelector('#saved').textContent.includes('Ivory'));await other.close();checks.crossTabChoiceUpdated=true;
  for(const [c,s] of [['blue','medium'],['copper','slow'],['green','original'],['ivory','medium']]){
   await page.locator('[data-color="'+c+'"]').click();await page.locator('[data-speed="'+s+'"]').click();
  }
  await page.waitForFunction(()=>{const v=document.querySelector('#film');return v.currentSrc.includes('rooms-ivory-medium')&&v.currentTime>.2&&!v.paused});checks.rapidSwitching=true;
  await page.locator('#reference').click();await page.waitForFunction(()=>{const v=document.querySelector('#film');return v.currentSrc.includes('previous-endless')&&v.currentTime>.2&&!v.paused});checks.previousReferencePlays=true;
  await page.locator('[data-color="ivory"]').click();await page.waitForFunction(()=>!document.querySelector('#choose').disabled);
  await page.locator('#film').evaluate(v=>v.pause());
  await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(output,'mobile.png'),fullPage:true});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks.mobileFits=true;
  assert.deepEqual(errors,[]);checks.errors=errors;checks.isolatedBrowser=true;checks.userProfileAccessed=false;
  fs.writeFileSync(path.join(output,'checks.json'),JSON.stringify(checks,null,2)+'\n');console.log(JSON.stringify({output,...checks},null,2));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
