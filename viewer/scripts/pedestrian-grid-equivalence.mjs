// Isolated CPU equivalence evidence. This never edits or imports runtime modules.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import * as T from 'three/webgpu';

const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const manifestBytes=fs.readFileSync('public/assets/characters/crowd_manifest.json');
const manifest=JSON.parse(manifestBytes);
const runtimeText=fs.readFileSync('src/characters.ts','utf8');
const entries=manifest.npcs;
assert.equal(entries.length,164);

// Persistent membership lists, updated immediately after each accepted movement.
// Only the candidate enumeration changes; original distance predicates stay exact.
class Grid {
 constructor(actors){this.actors=actors;this.cell=1.25;this.cells=new Map();this.next=new Int32Array(actors.length).fill(-1);this.prev=new Int32Array(actors.length).fill(-1);this.keys=new Array(actors.length);for(let i=0;i<actors.length;i++)this.move(i);}
 key(x,z){return `${Math.floor(x/this.cell)},${Math.floor(z/this.cell)}`;}
 move(i){const p=this.actors[i].object.position,key=this.key(p.x,p.z),old=this.keys[i];if(key===old)return;if(old!==undefined){const prev=this.prev[i],next=this.next[i];if(prev<0)this.cells.set(old,next);else this.next[prev]=next;if(next>=0)this.prev[next]=prev;}const head=this.cells.get(key)??-1;this.next[i]=head;this.prev[i]=-1;if(head>=0)this.prev[head]=i;this.cells.set(key,i);this.keys[i]=key;}
 visit(actor,callback){const x=Math.floor(actor.object.position.x/this.cell),z=Math.floor(actor.object.position.z/this.cell);for(let dx=-1;dx<=1;dx++)for(let dz=-1;dz<=1;dz++){let i=this.cells.get(`${x+dx},${z+dz}`)??-1;while(i>=0){if(callback(this.actors[i]))return true;i=this.next[i];}}return false;}
}

function simulation(source,useGrid){
 const actors=source.map(e=>({e,object:{position:new T.Vector3().fromArray(e.position||e.path[0]),rotation:{y:e.rotationY||0}},pathIndex:e.pathIndex??1,waiting:false,waitReason:'',dwell:0,stoppedSeconds:0}));
 const grid=useGrid?new Grid(actors):null,target=new T.Vector3(),delta=new T.Vector3(),candidate=new T.Vector3();
 let pairVisits=0,distanceChecks=0,playerWaits=0,pedestrianWaits=0;
 function update(dt,player=null){
  for(let index=0;index<actors.length;index++){
   const actor=actors[index],route=actor.e.path;if(!route?.length)continue;
   let reason='';if(actor.dwell>0){actor.dwell=Math.max(0,actor.dwell-dt);reason='waypoint';}
   let remaining=(actor.e.speed??.7)*dt;
   for(let segment=0;segment<=route.length&&remaining>0&&!reason;segment++){
    target.fromArray(route[actor.pathIndex]);delta.copy(target).sub(actor.object.position);
    const distance=delta.length(),travel=Math.min(distance,remaining);if(distance>0)delta.divideScalar(distance);
    candidate.copy(actor.object.position).addScaledVector(delta,travel);
    if(player&&Math.abs(player.y-actor.object.position.y)<1.8){const safe=.32+(actor.e.personalSpace??.58);const current=Math.hypot(actor.object.position.x-player.x,actor.object.position.z-player.z);const next=Math.hypot(candidate.x-player.x,candidate.z-player.z);if(next<safe&&next<=current)reason='player';}
    const blocks=other=>{pairVisits++;if(other===actor||Math.abs(other.object.position.y-actor.object.position.y)>1.5)return false;const current=Math.hypot(actor.object.position.x-other.object.position.x,actor.object.position.z-other.object.position.z);distanceChecks++;if(current>1.25)return false;const next=Math.hypot(candidate.x-other.object.position.x,candidate.z-other.object.position.z);return next<.64&&next<current-.0001;};
    if(!reason){if(grid){if(grid.visit(actor,blocks))reason='pedestrian';}else for(const other of actors){if(blocks(other)){reason='pedestrian';break;}}}
    if(reason)break;
    actor.object.position.copy(candidate);remaining-=travel;if(grid)grid.move(index);
    if(travel>0)actor.object.rotation.y=Math.atan2(delta.x,delta.z);
    if(distance<=travel+1e-8){actor.dwell=Number(actor.e.waypointPauses?.[actor.pathIndex]??actor.e.pauseSeconds??0);actor.pathIndex=(actor.pathIndex+1)%route.length;if(actor.dwell>0)reason='waypoint';}
   }
   const waiting=!!reason;if(actor.waiting!==waiting&&waiting){if(reason==='player')playerWaits++;if(reason==='pedestrian')pedestrianWaits++;}
   actor.waiting=waiting;actor.waitReason=reason;actor.stoppedSeconds=waiting?actor.stoppedSeconds+dt:0;
  }
 }
 return {actors,update,counts:()=>({pairVisits,distanceChecks,playerWaits,pedestrianWaits})};
}

function runScenario(name,source,frames,dt,playerAt){
 const reference=simulation(source,false),grid=simulation(source,true);let checks=0,maxPositionDelta=0;
 for(let frame=0;frame<frames;frame++){
  const player=playerAt?.(frame,reference.actors)||null;reference.update(dt,player);grid.update(dt,player);
  for(let i=0;i<source.length;i++){
   const a=reference.actors[i],b=grid.actors[i];const difference=a.object.position.distanceTo(b.object.position);maxPositionDelta=Math.max(maxPositionDelta,difference);assert.equal(difference,0,`${name}:frame${frame}:actor${i}:position`);assert.equal(a.object.rotation.y,b.object.rotation.y,`${name}:rotation`);
   for(const k of ['pathIndex','waiting','waitReason','dwell','stoppedSeconds'])assert.equal(a[k],b[k],`${name}:frame${frame}:actor${i}:${k}`);checks++;
  }
 }
 assert.deepEqual({player:reference.counts().playerWaits,pedestrians:reference.counts().pedestrianWaits},{player:grid.counts().playerWaits,pedestrians:grid.counts().pedestrianWaits});
 return {name,actors:source.length,frames,seconds:frames*dt,stateComparisons:checks,maxPositionDelta,exactWaitAndWaypointDecisions:true,reference:reference.counts(),grid:grid.counts(),passed:true};
}

let visitor=null;
const authored=runScenario('All164authoredActors120Seconds',entries,7200,1/60,(frame,actors)=>{if(frame===1800){const actor=actors.find(a=>a.e.path?.length),target=new T.Vector3().fromArray(actor.e.path[actor.pathIndex]),direction=target.sub(actor.object.position).normalize();visitor=actor.object.position.clone().addScaledVector(direction,.85);}return frame>=1800&&frame<2400?visitor:null;});
const e=(id,x,z,path,y=0)=>({id,position:[x,y,z],path:path.map(p=>[p[0],y,p[1]]),speed:1,personalSpace:.58});
const fixture=[e('forward',0,0,[[0,0],[0,8],[4,8],[4,0],[0,0]]),e('following',0,-.72,[[0,-.72],[0,8],[4,8],[4,-.72],[0,-.72]]),e('crossing',-3,2,[[-3,2],[5,2],[5,6],[-3,6],[-3,2]]),{id:'idle',position:[0,0,4]},e('differentFloor',0,0,[[0,0],[0,8],[4,8],[4,0],[0,0]],3)];
fixture[0].waypointPauses={1:.4};
const synthetic=runScenario('NearbyCrossingFollowingIdleAndDifferentFloor',fixture,1800,1/60,frame=>frame>=300&&frame<480?new T.Vector3(4,0,5):null);
assert(authored.reference.playerWaits>0,'Authored scenario must exercise player waiting');assert(synthetic.reference.pedestrianWaits>0,'Synthetic scenario must exercise pedestrian waiting');
const report={schema:'roman-arena.pedestrian-grid-equivalence/v1',timestamp:new Date().toISOString(),passed:true,scope:'CPU-only movement decision equivalence. No skeletal animation sampling or renderer changes; not a frame-time or FPS benchmark.',characterManifestSHA256:sha(manifestBytes),inspectedRuntimeSourceSHA256:sha(runtimeText),narrowPhase:'Original sequential movement, waypoint dwell, player-radius test, height limits and Math.hypot distance predicates are unchanged. Dynamic grid membership updates after each accepted segment. Only actor candidate enumeration differs.',scenarios:[authored,synthetic],runtimeEdited:false};
fs.writeFileSync('pedestrian_grid_equivalence_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
