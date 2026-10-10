import fs from 'node:fs';
import * as T from 'three/webgpu';
import {CollisionWorld} from '../src/collision.ts';
const manifest=JSON.parse(fs.readFileSync('public/assets/environment.json'));
const bytes=fs.readFileSync('public/assets/'+manifest.binary),buffer=bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength);
const geometries=new Map(),world=new CollisionWorld();
for(const mesh of manifest.meshes){const geometry=new T.BufferGeometry();geometry.setAttribute('position',new T.BufferAttribute(new Float32Array(buffer,mesh.positions.offset,mesh.positions.count),3));geometry.setIndex(new T.BufferAttribute(new Uint32Array(buffer,mesh.indices.offset,mesh.indices.count),1));geometries.set(mesh.id,geometry);}
for(const instance of manifest.instances)if(instance.collision&&instance.collision!=='none'&&instance.collision!=='false')world.add(instance.id,geometries.get(instance.mesh),new T.Matrix4().fromArray(instance.matrix));
const bounds=manifest.navigation.bounds,edgeSamples=[],missing=[];
for(const [edge,axis,value] of [['west',0,bounds.min[0]+.32],['east',0,bounds.max[0]-.32],['north',1,bounds.min[1]+.32],['south',1,bounds.max[1]-.32]]){
 const other=1-axis;for(let v=bounds.min[other]+.32;v<=bounds.max[other]-.32;v+=5){const p=[];p[axis]=value;p[other]=v;const support=world.support(p[0],p[1],2,9);const sample={edge,x:p[0],z:p[1],support:support?.id||null,height:support?.point.y??null};edgeSamples.push(sample);if(!support)missing.push(sample);}
}
const report={timestamp:new Date().toISOString(),sourceHash:manifest.sourceHash,bounds,scope:'Exact production triangle collision, CPU only. Upward-facing support sampled every 5m at the controller boundary, from 2m down to −7m. Roofs above 2m are intentionally excluded.',edgeSamples:edgeSamples.length,missingCount:missing.length,missing,heights:[...new Set(edgeSamples.filter(s=>s.height!==null).map(s=>Number(s.height.toFixed(3))))],supports:[...new Set(edgeSamples.map(s=>s.support))]};
fs.writeFileSync('edge_audit.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));
