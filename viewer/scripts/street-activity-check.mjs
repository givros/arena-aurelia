import {chromium} from 'playwright';
import fs from 'node:fs';
import crypto from 'node:crypto';

const bytes=fs.readFileSync('public/assets/environment.json'),manifest=JSON.parse(bytes);
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,
 args:['--enable-unsafe-webgpu','--ignore-gpu-blocklist','--disable-background-timer-throttling']});
const page=await browser.newPage({viewport:{width:1440,height:1080},deviceScaleFactor:1});
const errors=[];page.on('pageerror',error=>errors.push(error.message));
await page.goto('http://127.0.0.1:4178/?debug=1');
await page.waitForFunction(()=>window.__arena||window.__arenaFailure,null,{timeout:180000});
const failure=await page.evaluate(()=>window.__arenaFailure);if(failure)throw new Error(failure);
const tests=await page.evaluate(()=>{
 const w=window.__arena,c=w.characters,moving=c.instances.filter(a=>a.e.path?.length>1),fixed=c.instances.filter(a=>!a.e.path?.length);
 const results=[],check=(name,passed,detail)=>results.push({name,status:passed?'passed':'failed',detail});
 w.renderer.setAnimationLoop(null);
 check('Multiple independently animated pedestrians, vendors and staff exist',moving.length>=24&&fixed.length>=4,{walking:moving.length,stationaryActors:fixed.length});
 const actor=moving.find(a=>/citizen/i.test(a.e.role))||moving[0];
 if(!actor)return results;
 const target=actor.object.position.clone().fromArray(actor.e.path[actor.pathIndex]);
 const direction=target.clone().sub(actor.object.position).normalize();
 const player=actor.object.position.clone().addScaledVector(direction,1.3);
 const original=actor.object.position.clone();
 for(let frame=0;frame<180;frame++)c.update(1/60,{player,playerRadius:.32});
 const waited=actor.object.position.clone(),distance=Math.hypot(waited.x-player.x,waited.z-player.z);
 check('Approaching pedestrian waits before reaching the player',actor.waitReason==='player'&&distance>=.88&&distance<1.05,
  {actor:actor.e.id,start:original.toArray(),stop:waited.toArray(),personalSpace:distance,reason:actor.waitReason,idleWeight:actor.idle?.getEffectiveWeight()});
 check('Waiting uses the bundled Idle animation',!!actor.idle&&actor.idle.getEffectiveWeight()>.95,{weight:actor.idle?.getEffectiveWeight()});
 for(let frame=0;frame<120;frame++)c.update(1/60,{player:null});
 check('Pedestrian resumes walking after the player leaves',actor.object.position.distanceTo(waited)>.5&&!actor.waiting,
  {actor:actor.e.id,displacement:actor.object.position.distanceTo(waited),reason:actor.waitReason});
 const starts=moving.map(a=>a.object.position.clone()),progress=moving.map(()=>0);
 let worstWait=0,minimumPairSpacing=Infinity;
 for(let frame=0;frame<7200;frame++){
  c.update(1/60,{player:null});
  if(frame%60===0){
   moving.forEach((a,i)=>{progress[i]=Math.max(progress[i],a.object.position.distanceTo(starts[i]));worstWait=Math.max(worstWait,a.stoppedSeconds);});
   for(let i=0;i<moving.length;i++)for(let j=i+1;j<moving.length;j++){
    const a=moving[i].object.position,b=moving[j].object.position;
    if(Math.abs(a.y-b.y)<1.5)minimumPairSpacing=Math.min(minimumPairSpacing,Math.hypot(a.x-b.x,a.z-b.z));
   }
  }
 }
 check('Every walking actor advances along its authored lane',progress.every(p=>p>2),{minimumDisplacement:Math.min(...progress),actors:moving.map((a,i)=>({id:a.e.id,maxDisplacement:progress[i],waitReason:a.waitReason,stoppedSeconds:a.stoppedSeconds}))});
 check('Personal-space waiting does not produce a persistent jam',worstWait<12,{simulatedSeconds:120,longestWaitSeconds:worstWait,minimumMovingPairSpacing:minimumPairSpacing});
 const tint=[];for(const a of moving){let tunic; a.object.traverse(o=>{if(o.isMesh&&/RomanTunic|cloth/i.test(o.name+' '+o.material.name))tunic=o.material.color.getHexString();});tint.push(tunic);}
 check('Walking tunics retain authored palette variety',new Set(tint).size>=3,{uniqueColors:[...new Set(tint)]});
 const fixedBefore=fixed.map(a=>a.object.position.toArray());for(let f=0;f<60;f++)c.update(1/60,{player:null});
 check('Stationary vendors and staff stay at their authored positions',fixed.every((a,i)=>a.object.position.toArray().every((v,j)=>v===fixedBefore[i][j])),{count:fixed.length});
 w.dispose();return results;
});

const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const report={timestamp:new Date().toISOString(),status:tests.every(t=>t.status==='passed')&&!errors.length?'passed':'failed',
 sourceHash:manifest.sourceHash,manifestSHA256:crypto.createHash('sha256').update(bytes).digest('hex'),
 characterManifestSHA256:sha('public/assets/'+manifest.navigation.crowdManifest),
 layoutHashes:Object.fromEntries(['streetLifeLayout','districtLifeLayout','civicCourtLayout','arenaInteriorLifeLayout','masterSpineLifeLayout','masterWorldLayout','masterWorldBoundary','worldBoundaryGeometry'].map(field=>manifest.navigation[field]).filter(Boolean).map(file=>[file,sha('public/assets/'+file)])),
 scope:'Production canonical actors and actual pedestrian update; input-driven waiting preserves authored path geometry. Two simulated minutes test lane progress without rendering overhead.',tests,errors};
fs.writeFileSync('street_activity_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));await browser.close();
