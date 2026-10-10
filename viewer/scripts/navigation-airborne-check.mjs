import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import ts from 'typescript';
import * as T from 'three/webgpu';
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
async function moduleAt(file){const source=fs.readFileSync(file);let code=ts.transpileModule(source.toString(),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;for(const id of ['three/webgpu','three/addons/controls/OrbitControls.js'])code=code.replaceAll(JSON.stringify(id),JSON.stringify(import.meta.resolve(id))).replaceAll("'"+id+"'",JSON.stringify(import.meta.resolve(id)));return {module:await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64')),sha256:sha(source)};}
const old=await moduleAt('checkpoints/airborne-step-before/navigation.ts'),current=await moduleAt('src/navigation.ts'),collision=await moduleAt('src/collision.ts');
function world(){const w=new collision.module.CollisionWorld();const cube=new T.BoxGeometry(1,1,1);const box=(id,p,s)=>w.add(id,cube,new T.Matrix4().compose(new T.Vector3(...p),new T.Quaternion(),new T.Vector3(...s)));box('floor',[0,-.25,0],[20,.5,20]);box('latch',[1.5,1,0],[1,.1,1]);for(let i=0;i<8;i++)box('step-'+i,[-3,(i+1)*.14,2-i*.6],[2,(i+1)*.28,.6]);return w;}
function nav(mod,position,grounded,velocityY){const n=Object.create(mod.module.Navigation.prototype);Object.assign(n,{mode:'walk',camera:new T.PerspectiveCamera(),collision:world(),keys:new Set(),yaw:0,pitch:0,velocityY,eyeHeight:1.72,radius:.32,step:.38,height:1.84,speed:4.2,runningSpeed:7.5,paused:false,collisions:0,lastObstacle:'',grounded,foot:new T.Vector3(...position),bounds:null,onMode:()=>{},onToast:()=>{}});return n;}
function run(mod){const results={};let n=nav(mod,[.68,.8,0],false,-1);n.moveHorizontal(.1,0);results.airborneHorizontalStep={foot:n.foot.toArray(),grounded:n.grounded};n=nav(mod,[1.2,.8,0],false,-1);n.update(1/60);results.airborneUpwardLanding={foot:n.foot.toArray(),grounded:n.grounded};n=nav(mod,[1.2,1.12,0],false,-5);n.update(1/60);results.legitimateLanding={foot:n.foot.toArray(),grounded:n.grounded};n=nav(mod,[-3,0,3],true,0);n.keys.add('KeyW');for(let i=0;i<82;i++)n.update(1/60);results.stairAscent={foot:n.foot.toArray(),grounded:n.grounded};n.keys.clear();n.keys.add('KeyS');for(let i=0;i<82;i++)n.update(1/60);results.stairDescent={foot:n.foot.toArray(),grounded:n.grounded};return results;}
const before=run(old),after=run(current);
assert(before.airborneHorizontalStep.foot[1]>.9);assert(before.airborneUpwardLanding.grounded);
assert.equal(after.airborneHorizontalStep.foot[1],.8);assert(after.airborneUpwardLanding.foot[1]<.8);assert(!after.airborneUpwardLanding.grounded);
assert(Math.abs(after.legitimateLanding.foot[1]-1.05)<1e-6&&after.legitimateLanding.grounded);
assert(after.stairAscent.foot[1]>2.2&&after.stairAscent.grounded);assert(Math.abs(after.stairDescent.foot[1])<1e-6&&after.stairDescent.grounded);
assert.deepEqual(before.stairAscent,after.stairAscent);assert.deepEqual(before.stairDescent,after.stairDescent);
const report={status:'passed',timestamp:new Date().toISOString(),beforeNavigationSHA256:old.sha256,afterNavigationSHA256:current.sha256,collisionSHA256:collision.sha256,scope:'Actual navigation and triangle-collision modules, isolated fixture; reproduces and prevents airborne upward stair snaps while retaining grounded ascent/descent and legitimate descending landings.',before,after};fs.writeFileSync('navigation_airborne_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
