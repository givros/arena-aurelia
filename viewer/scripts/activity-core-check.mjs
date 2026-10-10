import assert from 'node:assert/strict';
import * as THREE from 'three/webgpu';
import {loadCharacters} from '../src/characters.ts';

globalThis.location={href:'http://127.0.0.1:4178/'};
globalThis.ProgressEvent=class ProgressEvent{constructor(type,details){this.type=type;Object.assign(this,details);}};
const scene=new THREE.Scene();
const characters=await loadCharacters(scene,{navigation:{npcs:[{id:'fixture-walker',asset:'characters/animated-citizen.glb',
 clip:'Walk',position:[0,0,0],path:[[0,0,0],[0,0,5],[5,0,5],[5,0,0],[0,0,0]],speed:1}]}});
const actor=characters.instances[0],player=new THREE.Vector3(0,0,1.3);
for(let frame=0;frame<180;frame++)characters.update(1/60,{player});
assert.equal(actor.waitReason,'player');assert(actor.object.position.distanceTo(player)>=.9);
assert(actor.idle.getEffectiveWeight()>.99);
const stop=actor.object.position.clone();
for(let frame=0;frame<120;frame++)characters.update(1/60,{player:null});
assert.equal(actor.waiting,false);assert(Math.abs(actor.object.position.distanceTo(stop)-2)<1e-6);
const start=actor.object.position.clone();
for(let frame=0;frame<1200;frame++)characters.update(1/60,{player:null});
assert(actor.object.position.distanceTo(start)<1e-6);
console.log(JSON.stringify({status:'passed',checks:['Canonical full-body GLB loads without a renderer','Player personal space causes Idle wait','Leaving resumes exact constant-speed translation','20m authored loop closes after20seconds without waypoint drift'],triangles:characters.triangles}));
