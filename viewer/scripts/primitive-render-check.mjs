import {chromium} from 'playwright';
import * as T from 'three';
import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';
const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
const chunks=[];let offset=0;const cube=new T.BoxGeometry(1,1,1),add=a=>{const b=Buffer.from(a.buffer,a.byteOffset,a.byteLength);const r={offset,count:a.length};offset+=b.length;chunks.push(b);return r;};
const mesh={id:'cube',positions:add(cube.attributes.position.array),normals:add(cube.attributes.normal.array),uvs:add(cube.attributes.uv.array),indices:add(new Uint32Array(cube.index.array)),material:'stone'};
const source=JSON.parse(fs.readFileSync('public/assets/environment.json')),crowdSource=JSON.parse(fs.readFileSync('public/assets/'+source.navigation.crowdManifest));
const files=[...new Set(Object.values(crowdSource.prototypes).concat(crowdSource.npcs.map(n=>n.asset)))];
const crowd={prototypes:Object.fromEntries(files.map((f,i)=>['role'+i,f])),palette:crowdSource.palette,materialOverrides:crowdSource.materialOverrides,instances:[],npcs:[]},cases=[];
let index=0;
for(const [i,file]of files.entries()){
 const position=[(index%6)*5-12.5,0,Math.floor(index/6)*6-12];
 const e={id:'static_'+i,role:'role'+i,position,rotationY:0,colorIndex:i%crowd.palette.length};crowd.instances.push(e);cases.push({id:e.id,asset:file,position,kind:'static'});index++;
}
const animated=files.filter(f=>f.includes('animated-'));
for(const file of animated)for(const clip of ['Idle','Walk','Run','Jump']){
 const position=[(index%6)*5-12.5,0,Math.floor(index/6)*6-12],id=file.split('/').at(-1).replace('.glb','')+'_'+clip;
 crowd.npcs.push({id,role:'animated',asset:file,position,rotationY:0,colorIndex:index%crowd.palette.length,animated:true,clip,animationPhase:.73});cases.push({id,asset:file,position,kind:'animated',clip});index++;
}
const stoneAsset=files.find(f=>f.endsWith('/guard.glb')),stoneRole='role'+files.indexOf(stoneAsset);const position=[(index%6)*5-12.5,0,Math.floor(index/6)*6-12];crowd.instances.push({id:'stone',role:stoneRole,position,materialOverride:'stone'});cases.push({id:'stone',asset:stoneAsset,position,kind:'override'});
const manifest={binary:'fixture.bin',materials:[{id:'stone',name:'Limestone',color:[.52,.46,.36],roughness:.8,metalness:0}],meshes:[mesh],instances:[{id:'ground',mesh:'cube',matrix:new T.Matrix4().compose(new T.Vector3(0,-.25,0),new T.Quaternion(),new T.Vector3(80,.5,80)).toArray(),collision:'solid'}],cameras:{reference:{position:[0,8,35],target:[0,1,0]}},navigation:{crowdManifest:'merge-fixture.json',bounds:{min:[-35,-35],max:[35,35]},spawn:[0,1.72,30],destinations:[],lights:[]}};
fs.mkdirSync('performance/primitive-images',{recursive:true});const errors=[],metrics=[];
const browser=await chromium.launch({executablePath:'C:/Program Files/Google/Chrome/Application/chrome.exe',headless:true,args:['--enable-unsafe-webgpu','--ignore-gpu-blocklist','--disable-background-timer-throttling']});
for(const arm of ['original','merged']){
 const page=await browser.newPage({viewport:{width:1000,height:1000},deviceScaleFactor:1});page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.route('**/assets/environment.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(manifest)}));await page.route('**/assets/fixture.bin',r=>r.fulfill({body:Buffer.concat(chunks)}));await page.route('**/assets/merge-fixture.json',r=>r.fulfill({contentType:'application/json',body:JSON.stringify(crowd)}));
 await page.goto('http://127.0.0.1:4178/?debug=1&primitiveMerge='+(arm==='original'?'0':'1'));await page.waitForFunction(()=>window.__arena||window.__arenaFailure,null,{timeout:180000});if(await page.evaluate(()=>window.__arenaFailure))throw new Error(await page.evaluate(()=>window.__arenaFailure));
 await page.evaluate(()=>{const w=window.__arena;w.pauseRendering();document.getElementById('app').style.visibility='hidden';for(const a of w.characters.instances){a.mixer.setTime(.73);a.object.position.fromArray(a.e.position);a.object.rotation.y=a.e.rotationY||0;}w.scene.updateMatrixWorld(true);});
 metrics.push({arm,stats:await page.evaluate(()=>window.__arena.stats())});
 for(const item of cases)for(const view of ['front','rear']){
  await page.evaluate(async({item,view})=>{const w=window.__arena;w.setHour(15);w.camera.fov=38;w.camera.updateProjectionMatrix();const p=item.position;w.camera.position.set(p[0]+(view==='front'?1.4:-1.4),p[1]+1.35,p[2]+(view==='front'?4.7:-4.7));w.nav.orbit.target.set(p[0],p[1]+.94,p[2]);w.camera.lookAt(w.nav.orbit.target);w.atmosphere.focus.set(p[0],0,p[2]);w.atmosphere.update(0);w.renderer.render(w.scene,w.camera);await w.renderer.backend.device.queue.onSubmittedWorkDone();},{item,view});
  await page.screenshot({path:path.resolve(`performance/primitive-images/${item.id}_${view}_${arm}.png`)});
 }
 await page.evaluate(()=>window.__arena.dispose());await page.close();console.log(JSON.stringify({arm,cases:cases.length,errors}));
}
await browser.close();fs.writeFileSync('performance/primitive_render_validation.json',JSON.stringify({timestamp:new Date().toISOString(),sourceHash:source.sourceHash,cases,assets:Object.fromEntries(files.map(f=>[f,sha('public/assets/'+f)])),metrics,errors},null,2));
