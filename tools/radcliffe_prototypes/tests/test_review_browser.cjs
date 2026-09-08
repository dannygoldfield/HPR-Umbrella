const {chromium}=require(process.env.HPR_PLAYWRIGHT_MODULE||'playwright');
const assert=require('node:assert/strict');const fs=require('node:fs');
const base=process.env.HPR_REVIEW_TEST_URL||'http://127.0.0.1:18769',key='hpr-next-20260907';
const path=require('node:path'),os=require('node:os');
const output=fs.mkdtempSync(path.join(os.tmpdir(),'hpr-review-qa-'));
(async()=>{
 const browser=await chromium.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,args:['--mute-audio']});
 try{
  const draft={develop:{10000:'200%',NYChildren:'175%',Infinity:'150%'},field:'static',audio:{}};
  const context=await browser.newContext({viewport:{width:1440,height:1100},storageState:{cookies:[],origins:[{origin:base,localStorage:[{name:key,value:JSON.stringify(draft)}]}]}});
  const page=await context.newPage(),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base+'/#develop');await page.waitForSelector('#develop-grid section');
  await page.waitForFunction(()=>[...document.querySelectorAll('#develop-grid video')].every(v=>v.readyState>=2));
  assert.deepEqual(await page.locator('#develop-grid select').evaluateAll(ss=>ss.map(s=>s.value)),['200','175','150']);
  assert.deepEqual(await page.locator('#develop-grid .choose').evaluateAll(bs=>bs.map(b=>b.getAttribute('aria-pressed'))),['true','true','true']);
  assert.equal(await page.locator('#all-strength').inputValue(),'');
  await page.locator('[data-portrait="NYChildren"] select').selectOption('200');
  await page.waitForFunction(()=>!document.querySelector('[data-portrait="NYChildren"] .choose').disabled);
  await page.locator('[data-portrait="NYChildren"] .choose').click();
  assert.equal(await page.locator('[data-portrait="NYChildren"] .choose').textContent(),'✓ Chosen: 200%');
  await page.getByRole('button',{name:'Reload review',exact:true}).click();
  await page.waitForSelector('#develop-grid select');
  assert.deepEqual(await page.locator('#develop-grid select').evaluateAll(ss=>ss.map(s=>s.value)),['200','200','150']);
  console.log('Saved previews, choice feedback, and in-page reload passed.');
  await page.locator('#all-strength').evaluate(select=>{for(const value of ['100','200','125','175']){select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}))}});
  await page.waitForFunction(()=>[...document.querySelectorAll('#develop-grid video')].every(v=>v.currentSrc.includes('develop-175-33s.mp4')&&v.readyState>=2)&&[...document.querySelectorAll('#develop-grid .variant')].every(v=>v.textContent==='175% · continuous timing'));
  await page.click('#play-develop');
  await page.waitForFunction(()=>[...document.querySelectorAll('#develop-grid video')].every(v=>!v.paused&&v.currentTime>.25));
  await page.locator('[data-portrait="NYChildren"] select').evaluate(select=>{for(const value of ['150','200','175','200']){select.value=value;select.dispatchEvent(new Event('change',{bubbles:true}))}});
  await page.waitForFunction(()=>{const v=document.querySelector('[data-portrait="NYChildren"] video');return v.currentSrc.includes('develop-200-33s.mp4')&&!v.paused&&v.currentTime>.25});
  await page.click('#pause-develop');
  const seekAll=async(selector,time)=>{
   await page.locator(selector).evaluateAll((vs,t)=>vs.forEach(v=>v.currentTime=t),time);
   await page.waitForFunction(({selector,time})=>[...document.querySelectorAll(selector)].every(v=>!v.seeking&&Math.abs(v.currentTime-time)<.12),{selector,time});
  };
  await seekAll('#develop-grid video',17.5);
  console.log('Rapid source changes and video seeking passed.');
  await page.click('[data-tab="infinity"]');
  assert.equal(new URL(page.url()).hash,'#infinity');
  await page.click('#play-fields');
  await page.waitForFunction(()=>[...document.querySelectorAll('#field-grid video')].every(v=>v.currentTime>.3&&!v.paused));
  for(const seam of [11,22]){
   await page.locator('#field-grid video').evaluateAll((vs,t)=>vs.forEach(v=>v.currentTime=t-.3),seam);
   await page.waitForFunction(t=>[...document.querySelectorAll('#field-grid video')].every(v=>v.currentTime>t+.25&&!v.paused),seam);
  }
  await page.locator('#field-grid video').evaluateAll(vs=>vs.forEach(v=>v.currentTime=32.8));
  await page.waitForFunction(()=>[...document.querySelectorAll('#field-grid video')].every(v=>v.ended));
  await page.click('[data-field="pressure"]');
  assert.equal(await page.locator('[data-field="pressure"]').textContent(),'✓ Chosen field');
  console.log('All four Infinity players, both joins, and stopping at 33 seconds passed.');
  await page.click('[data-tab="sound"]');
  await page.waitForFunction(()=>[...document.querySelectorAll('#sound-grid audio')].every(a=>a.readyState>=1&&a.duration===33));
  await seekAll('#sound-grid audio',17.5);
  for(let i=0;i<10;i++){
   await page.locator('#sound-grid audio').evaluateAll(async a=>{a.forEach(v=>v.pause());await Promise.allSettled([a[0].play(),a[1].play()])});
   await page.waitForFunction(()=>{const a=document.querySelectorAll('#sound-grid audio');return a[0].paused&&!a[1].paused});
  }
  await page.locator('#sound-grid audio').evaluateAll(as=>as.forEach(a=>a.pause()));
  console.log('Audio seeking and ten rapid playback switches passed.');
  const other=await context.newPage();other.on('pageerror',e=>errors.push(e.message));
  await other.goto(base+'/#sound');await other.waitForSelector('#sound-grid audio');
  await page.locator('[data-sound="10000"]').getByRole('button',{name:'Choose bed 25% quieter',exact:true}).click();
  await other.locator('[data-sound="NYChildren"]').getByRole('button',{name:'Choose bed 50% quieter',exact:true}).click();
  const saved=await other.evaluate(k=>JSON.parse(localStorage.getItem(k)),key);
  assert.deepEqual(saved.audio,{'10000':'Bed 25% quieter',NYChildren:'Bed 50% quieter'});
  assert.deepEqual(saved.develop,{'10000':'200%',NYChildren:'200%',Infinity:'150%'});
  assert.equal(saved.field,'pressure');
  await page.waitForFunction(()=>document.querySelector('[data-sound="NYChildren"] [data-choice="Bed 50% quieter"]').getAttribute('aria-pressed')==='true');
  await page.screenshot({path:path.join(output,'repaired-sound.png'),fullPage:true});
  console.log('Choice feedback and preservation across two tabs passed.');
  const slow=await context.newPage();slow.on('pageerror',e=>errors.push(e.message));
  await slow.route('**/Infinity-field-wave-125-33s.mp4',async route=>{await new Promise(r=>setTimeout(r,700));await route.continue().catch(()=>{})});
  await slow.goto(base+'/#infinity',{waitUntil:'domcontentloaded'});await slow.waitForSelector('#play-fields');
  await slow.click('#play-fields');await slow.click('[data-tab="sound"]');
  await slow.waitForTimeout(1500);
  assert(await slow.locator('video').evaluateAll(vs=>vs.every(v=>v.paused)));
  await page.click('[data-tab="develop"]');
  await page.waitForFunction(()=>[...document.querySelectorAll('#develop-grid video')].every(v=>v.readyState>=2));
  await page.screenshot({path:path.join(output,'repaired-develop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  const result={savedPreviewsRestored:true,visibleChoiceFeedback:true,inPageReload:true,rapidDevelopmentSwitches:true,
   audioAndVideoSeeking:true,infinityFourPlayerPlayback:true,infinityBothJoinsAndEnd:true,rapidAudioSwitches:10,
   crossTabChoicesPreserved:true,hiddenPlaybackCancelled:true,mobileFits:true,errors,
   isolatedStagingBrowser:true,userBrowserProfileAccessed:false};
  fs.writeFileSync(path.join(output,'browser-checks.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
