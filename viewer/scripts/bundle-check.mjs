import {chromium}from'playwright';import fs from'node:fs';import path from'node:path';
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-webgpu','--ignore-gpu-blocklist','--disable-background-timer-throttling']});
const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1}),errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
await page.goto('http://127.0.0.1:4178/?debug=1&profile=1');await page.waitForFunction(()=>window.__arena||window.__arenaFailure,null,{timeout:600000});if(await page.evaluate(()=>window.__arenaFailure))throw new Error(await page.evaluate(()=>window.__arenaFailure));
await page.evaluate(()=>{window.__arena.pauseRendering();document.getElementById('app').style.visibility='hidden';});
const cases=[['reference',15],['street_market_lane',15],['street_district_east_quay',15],['street_district_upper_city',17.5],['hypogeum',15],['reference',22],['street_market_lane',22]];
fs.mkdirSync('performance/bundle-images',{recursive:true});const results=[];
for(const [view,hour]of cases){
 const stats=await page.evaluate(async({view,hour})=>{const w=window.__arena;w.bundles.setEnabled(false);w.view(view);w.setHour(hour);w.atmosphere.focus.copy(w.nav.orbit.target).setY(0);w.atmosphere.update(0);w.scene.updateMatrixWorld(true);w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();return w.stats();},{view,hour});
 const base=`performance/bundle-images/${view}_${hour}`;await page.screenshot({path:path.resolve(base+'_normal.png')});
 await page.evaluate(async()=>{const w=window.__arena;w.bundles.setEnabled(true);w.bundles.update();w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();});await page.screenshot({path:path.resolve(base+'_bundle.png')});
 await page.evaluate(async()=>{const w=window.__arena;w.bundles.update();w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();});await page.screenshot({path:path.resolve(base+'_reuse.png')});
 results.push({view,hour,base,triangles:stats.transfer.runtimeTriangles+stats.characters.triangles,bundleStats:await page.evaluate(()=>window.__arena.bundles.stats())});console.log(JSON.stringify(results.at(-1)));
}
const temporal=[];
await page.evaluate(()=>{const w=window.__arena;w.view('street_market_lane');w.setHour(15);w.atmosphere.focus.copy(w.nav.orbit.target).setY(0);w.atmosphere.update(0);w.bundles.setEnabled(true);w.bundles.update();w.renderer.render(w.scene,w.camera);});
for(const change of ['camera','night']){
 const base=`performance/bundle-images/reuse_${change}`;
 const state=await page.evaluate(async change=>{const w=window.__arena,before=w.bundles.groups.map(g=>g.version);if(change==='camera'){w.camera.position.x+=.005;w.camera.lookAt(w.nav.orbit.target);}else{w.setHour(22);w.atmosphere.focus.copy(w.nav.orbit.target).setY(0);w.atmosphere.update(0);}w.bundles.update();w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();return {unchangedGroups:w.bundles.groups.filter((g,i)=>g.version===before[i]).length,totalGroups:w.bundles.groups.length};},change);
 await page.screenshot({path:path.resolve(base+'_cached.png')});await page.evaluate(async()=>{const w=window.__arena;w.bundles.setEnabled(false);w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();});await page.screenshot({path:path.resolve(base+'_normal.png')});temporal.push({change,base,...state});
 await page.evaluate(()=>{const w=window.__arena;w.bundles.setEnabled(true);w.bundles.update();w.renderer.render(w.scene,w.camera);});
}
const metrics=[];
for(const enabled of [false,true]){await page.evaluate(enabled=>{const w=window.__arena;w.view('reference');w.setHour(15);w.bundles.setEnabled(enabled);w.resumeRendering();},enabled);await page.waitForTimeout(3000);await page.evaluate(()=>window.__arena.clearPerformance());await page.waitForTimeout(12000);metrics.push({enabled,stats:await page.evaluate(()=>window.__arena.stats())});await page.evaluate(()=>window.__arena.pauseRendering());}
const report={temporal,sourceHash:JSON.parse(fs.readFileSync('public/assets/environment.json')).sourceHash,results,metrics,errors};fs.writeFileSync('performance/bundle_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify({phase:'complete',errors}));await browser.close();
