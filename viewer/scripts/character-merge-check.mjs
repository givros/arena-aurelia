import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import ts from 'typescript';
import * as T from 'three/webgpu';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
globalThis.ProgressEvent=class{};
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const moduleBytes=fs.readFileSync('src/character-merge.ts');
const code=ts.transpileModule(moduleBytes.toString(),{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText.replaceAll("'three/webgpu'",JSON.stringify(import.meta.resolve('three/webgpu')));
const {mergeCharacterPrimitives}=await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'));
const assets=[],loader=new GLTFLoader();
const meshes=root=>{const out=[];root.traverse(o=>{if(o.isMesh)out.push(o);});return out;};
const attrBytes=a=>Buffer.from(a.array.buffer,a.array.byteOffset,a.array.byteLength);
function fingerprint(root){const h=crypto.createHash('sha256');for(const o of meshes(root)){h.update(o.name);h.update(JSON.stringify(o.material.toJSON()));for(const k of Object.keys(o.geometry.attributes).sort()){h.update(k);h.update(attrBytes(o.geometry.attributes[k]));}if(o.geometry.index)h.update(attrBytes(o.geometry.index));}return h.digest('hex');}
function materialState(m){const d=m.toJSON();for(const k of ['metadata','uuid','name','color','vertexColors','userData'])delete d[k];return d;}

const p=new T.Vector3(),n=new T.Vector3(),skin=new T.Matrix4(),bone=new T.Matrix4(),m3=new T.Matrix3();
function sample(mesh,index,position,normal){
 mesh.getVertexPosition(index,position);position.applyMatrix4(mesh.matrixWorld);
 normal.fromBufferAttribute(mesh.geometry.attributes.normal,index);
 if(mesh.isSkinnedMesh){
  skin.elements.fill(0);const indices=mesh.geometry.attributes.skinIndex,weights=mesh.geometry.attributes.skinWeight;
  for(let j=0;j<4;j++){const w=weights.getComponent(index,j);if(!w)continue;const id=indices.getComponent(index,j);bone.multiplyMatrices(mesh.skeleton.bones[id].matrixWorld,mesh.skeleton.boneInverses[id]);for(let k=0;k<16;k++)skin.elements[k]+=bone.elements[k]*w;}
  skin.premultiply(mesh.bindMatrixInverse).multiply(mesh.bindMatrix);normal.applyMatrix3(m3.setFromMatrix4(skin));
 }
 normal.applyMatrix3(m3.getNormalMatrix(mesh.matrixWorld)).normalize();
}

for(const filename of fs.readdirSync('public/assets/characters').filter(n=>n.endsWith('.glb')).sort()){
 const bytes=fs.readFileSync('public/assets/characters/'+filename),gltf=await loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset+bytes.byteLength),'');
 const original=gltf.scene,optimized=clone(original),sourceFingerprint=fingerprint(original),before=new Map(meshes(optimized).map(m=>[m.uuid,m]));
 const stats=mergeCharacterPrimitives(optimized,gltf.animations);assert.equal(sourceFingerprint,fingerprint(original),'Original prototype mutated');
 const mapping=new Map(),materials=[],groups=meshes(optimized).filter(m=>m.userData.characterMerge);let attributesCompared=0,indexValuesCompared=0,colorValuesCompared=0;
 for(const merged of groups){
  assert.equal(merged.material.vertexColors,true);assert.deepEqual(merged.material.color.toArray(),[1,1,1]);
  for(const range of merged.userData.characterMerge.components){
   const old=before.get(range.sourceUUID);assert(old);assert.equal(old.parent,null);assert.equal(merged.parent.name,stats.groups.find(g=>g.name===merged.name).parent);
   assert(merged.matrix.equals(old.matrix));assert.deepEqual(materialState(merged.material),materialState(old.material));
   assert.notEqual(merged.material,old.material);assert.notEqual(merged.geometry,old.geometry);
   for(const [name,a]of Object.entries(old.geometry.attributes)){
    const b=merged.geometry.attributes[name];assert.equal(a.array.constructor,b.array.constructor);assert.equal(a.itemSize,b.itemSize);assert.equal(a.normalized,b.normalized);assert.equal(a.gpuType,b.gpuType);
    for(let i=0;i<a.array.length;i++){assert.equal(a.array[i],b.array[range.firstVertex*a.itemSize+i],filename+':'+name);attributesCompared++;}
   }
   if(old.geometry.index){assert(merged.geometry.index);for(let i=0;i<old.geometry.index.count;i++){assert.equal(old.geometry.index.getX(i)+range.firstVertex,merged.geometry.index.getX(range.firstIndex+i));indexValuesCompared++;}}
   else assert.equal(merged.geometry.index,null);
   for(let i=0;i<range.vertexCount;i++)for(let j=0;j<3;j++){assert.equal(merged.geometry.attributes.color.array[(range.firstVertex+i)*3+j],Math.fround(old.material.color.toArray()[j]));colorValuesCompared++;}
   if(old.isSkinnedMesh){assert.equal(merged.bindMode,old.bindMode);assert(merged.bindMatrix.equals(old.bindMatrix));assert(merged.bindMatrixInverse.equals(old.bindMatrixInverse));assert(merged.skeleton.bones.every((b,i)=>b===old.skeleton.bones[i]&&merged.skeleton.boneInverses[i].equals(old.skeleton.boneInverses[i])));}
   mapping.set(old.name,{target:merged,offset:range.firstVertex});materials.push({component:old.name,parent:merged.parent.name,roughness:old.material.roughness,metalness:old.material.metalness,side:old.material.side,colorLinear:old.material.color.toArray(),attributesExact:true,triangleOrderExact:true});
  }
 }
 for(const o of meshes(original))if(!mapping.has(o.name)){const target=optimized.getObjectByName(o.name);assert(target?.isMesh);mapping.set(o.name,{target,offset:0});if(/RomanTunic|cloth/i.test(o.name+' '+o.material.name))assert.equal(target.material,o.material,'Tunic material must remain unchanged before palette application');}
 const aMixer=new T.AnimationMixer(original),bMixer=new T.AnimationMixer(optimized),samples=[];let verticesCompared=0,maxPositionDelta=0,maxNormalDelta=0,maxParentMatrixDelta=0;
 const expectedP=new T.Vector3(),expectedN=new T.Vector3();
 const check=(clip,time)=>{
  if(clip){aMixer.setTime(time);bMixer.setTime(time);}original.updateMatrixWorld(true);optimized.updateMatrixWorld(true);
  for(const mesh of meshes(original)){
   const {target,offset}=mapping.get(mesh.name);assert.equal(mesh.parent.name,target.parent.name,'Bone/structural parent differs');
   for(let k=0;k<16;k++)maxParentMatrixDelta=Math.max(maxParentMatrixDelta,Math.abs(mesh.parent.matrixWorld.elements[k]-target.parent.matrixWorld.elements[k]));
   for(let i=0;i<mesh.geometry.attributes.position.count;i++){sample(mesh,i,expectedP,expectedN);sample(target,i+offset,p,n);maxPositionDelta=Math.max(maxPositionDelta,expectedP.distanceTo(p));maxNormalDelta=Math.max(maxNormalDelta,expectedN.distanceTo(n));verticesCompared++;}
  }
  samples.push({clip:clip?.name||'Static',timeSeconds:time});
 };
 if(gltf.animations.length){for(const clip of gltf.animations){aMixer.stopAllAction();bMixer.stopAllAction();aMixer.clipAction(clip).play();bMixer.clipAction(clip).play();for(const time of [0,.37,.73,Math.min(2,clip.duration)])check(clip,time);}}
 else check(null,0);
 assert.equal(maxPositionDelta,0);assert.equal(maxNormalDelta,0);assert.equal(maxParentMatrixDelta,0);
 assert.equal(sourceFingerprint,fingerprint(original),'Source geometry or materials mutated during sampling');
 assert.equal(sha(bytes),sha(fs.readFileSync('public/assets/characters/'+filename)),'Source GLB bytes changed');
 const item={asset:filename,sha256:sha(bytes),passed:true,...stats,attributesCompared,indexValuesCompared,colorValuesCompared,verticesCompared,maxWorldPositionDelta:maxPositionDelta,maxWorldNormalDelta:maxNormalDelta,maxParentMatrixDelta,materials,samples,originalPrototypeAttributesAndMaterialsUnchanged:true};assets.push(item);
 console.log(JSON.stringify({asset:filename,before:stats.beforeMeshes,after:stats.afterMeshes,triangles:stats.afterTriangles,verticesCompared,maxPositionDelta,maxNormalDelta}));
}

function rejection(reason,change){const root=new T.Group(),geometry=new T.BoxGeometry();geometry.clearGroups();const a=new T.Mesh(geometry,new T.MeshStandardMaterial({color:0x123456})),b=new T.Mesh(a.geometry,new T.MeshStandardMaterial({color:0xabcdef}));a.name='AccessoryA';b.name='AccessoryB';root.add(a,b);const clips=change(a,b,root)||[];root.updateMatrixWorld(true);const result=mergeCharacterPrimitives(root,clips);assert.equal(result.afterMeshes,2,reason);return {reason,passed:true};}
const rejectionGuards=[rejection('roughness differs',(a,b)=>{b.material.roughness=.1;}),rejection('local matrix differs',(a,b)=>{b.position.x=1;}),rejection('parents differ',(a,b,r)=>{const other=new T.Group();r.add(other);other.add(b);}),rejection('palette tunic excluded',(a,b)=>{b.name='RomanTunic';}),rejection('direct mesh animation excluded',(a,b)=>[new T.AnimationClip('test',1,[new T.VectorKeyframeTrack('AccessoryB.position',[0,1],[0,0,0,0,1,0])])]),rejection('different attribute layouts',(a,b)=>{b.geometry=b.geometry.clone();b.geometry.deleteAttribute('uv');}),rejection('custom material callback excluded',(a,b)=>{b.material.onBeforeCompile=()=>{};})];
const countMap=new Map(assets.map(a=>[a.asset,a]));const manifestBytes=fs.readFileSync('public/assets/characters/crowd_manifest.json'),crowd=JSON.parse(manifestBytes),buckets=new Map();
for(const e of crowd.instances){const asset=crowd.prototypes[e.role].split('/').at(-1),bucket=e.role==='seated-spectator'?'seating-'+Math.floor((e.sector||0)/2):`district-${Math.floor(e.position[0]/64)}-${Math.floor(e.position[2]/64)}`;buckets.set(asset+'|'+(e.materialOverride||'')+'|'+bucket,{asset,override:!!e.materialOverride});}
let staticBefore=0,staticAfter=0,animatedBefore=0,animatedAfter=0;
for(const {asset,override}of buckets.values()){const a=countMap.get(asset);staticBefore+=a.beforeMeshes;staticAfter+=override?a.beforeMeshes:a.afterMeshes;}
for(const e of crowd.npcs){const a=countMap.get(e.asset.split('/').at(-1));animatedBefore+=a.beforeMeshes;animatedAfter+=a.afterMeshes;}
const report={schema:'roman-arena.character-merge-equivalence/v1',timestamp:new Date().toISOString(),passed:true,threeRevision:T.REVISION,moduleSHA256:sha(moduleBytes),characterManifestSHA256:sha(manifestBytes),scope:'CPU-only exact geometry, material and animation equivalence; actual full world-space vertex and normal sampling. No GPU image or frame-time assertion.',assets,rejectionGuards,population:{characters:crowd.instances.length+crowd.npcs.length,staticBefore,staticAfter,animatedBefore,animatedAfter,statuesUseOriginalPrototype:true},totalWorldVertexComparisons:assets.reduce((n,a)=>n+a.verticesCompared,0),totalRawAttributeValuesCompared:assets.reduce((n,a)=>n+a.attributesCompared,0),sourceGLBFilesUnchanged:true};
fs.writeFileSync('character_merge_equivalence_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify({passed:true,totalWorldVertexComparisons:report.totalWorldVertexComparisons,population:report.population}));
