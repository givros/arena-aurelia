import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import ts from 'typescript';
import * as T from 'three/webgpu';
import {attributeArray} from 'three/tsl';
import WGSLNodeBuilder from 'three/src/renderers/webgpu/nodes/WGSLNodeBuilder.js';
import Original from 'three/addons/tsl/lighting/ClusteredLightsNode.js';
import Candidate, {ClusteredLighting} from '../src/stable-clustered-lighting.js';

const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const originalFile = 'performance/pinned-clustered-lighting-reference.js';
const candidateFile = 'src/stable-clustered-lighting.js';
const originalText = fs.readFileSync(originalFile, 'utf8');
const candidateText = fs.readFileSync(candidateFile, 'utf8');
assert.equal(hash(fs.readFileSync(new URL(import.meta.resolve('three/addons/tsl/lighting/ClusteredLightsNode.js')))), hash(originalText), 'Installed addon differs from pinned reference');
const methods = text => {
  const source = ts.createSourceFile('lighting.js', text, ts.ScriptTarget.Latest, true, ts.ScriptKind.JS);
  const node = source.statements.find(n => ts.isClassDeclaration(n) && n.name?.text === 'ClusteredLightsNode');
  return Object.fromEntries(node.members.filter(n => n.body).map(n => [n.name?.getText(source) || 'constructor', n.body.getText(source)]));
};
const tokens = text => {
  const scanner = ts.createScanner(ts.ScriptTarget.Latest, true, ts.LanguageVariant.Standard, text);
  const out = []; while(scanner.scan() !== ts.SyntaxKind.EndOfFileToken) out.push(scanner.getTokenText()); return out.join(' ');
};
const originalMethods = methods(originalText), candidateMethods = methods(candidateText);
const unchangedMethods = Object.keys(originalMethods).filter(k => !['constructor','create','dispose','updateProgram'].includes(k));
for(const key of unchangedMethods) assert.equal(tokens(candidateMethods[key]), tokens(originalMethods[key]), key + ' changed');
assert.equal(tokens(candidateMethods.constructor.replace('this._capacityClusterCount = 0;', '').replace('this._maxStorageBytes = 128 * 1024 * 1024;', '').replace('this.gridReallocations = 0;', '')), tokens(originalMethods.constructor));
assert.equal(tokens(candidateMethods.updateProgram.replace('const limits = renderer.backend?.device?.limits;', '').replace('if ( limits ) this._maxStorageBytes = Math.min( limits.maxStorageBufferBindingSize, limits.maxBufferSize );', '')), tokens(originalMethods.updateProgram));
const kernel = body => body.slice(body.indexOf('// compute-side accessors'), body.indexOf('this._compute = compute;') + 'this._compute = compute;'.length);
const expectedKernel = kernel(originalMethods.create)
  .replace('instanceIndex.mod( NX )', 'instanceIndex.mod( uint( NX ) )')
  .replace('instanceIndex.div( NX ).mod( NY )', 'instanceIndex.div( uint( NX ) ).mod( uint( NY ) )')
  .replace('instanceIndex.div( NX * NY )', 'instanceIndex.div( uint( NX.mul( NY ) ) )')
  .replaceAll('2.0 / NX', 'float( 2.0 ).div( NX )')
  .replaceAll('2.0 / NY', 'float( 2.0 ).div( NY )')
  .replace('int( NX * NY )', 'NX.mul( NY )');
assert.equal(tokens(kernel(candidateMethods.create)), tokens(expectedKernel), 'Kernel differs beyond declared uniform substitutions');
assert.equal(hash(originalText), 'b1fb1034d84a3c3a6a68e416a58b3fb16817d8e9f903e67d4d1b9f72e8ae2d80');

const manifest = JSON.parse(fs.readFileSync('public/assets/environment.json'));
const lights = manifest.navigation.lights.map(l => {
  const result = new T.PointLight(new T.Color().fromArray(l.color), l.intensity, l.distance, 2);
  result.position.fromArray(l.position); result.updateMatrixWorld(true); return result;
});
assert.equal(lights.length, 53);
const original = new Original(64,32,24,64).setLights(lights);
const candidate = new ClusteredLighting(64,32,24,64).createNode(lights);
assert(candidate instanceof Candidate);
const sizes = [[1440,1080],[1600,1080],[1440,1080],[1920,1080],[3840,2160],[1080,1920],[1017,733]];
const identityRecords = [];
const storageRecords = [];
function validateStorage(node,label){
  const storage=node._lightIndexes,array=storage.value.array;
  assert.equal(typeof storage.bufferCount,'number');
  assert.equal(storage.bufferCount,node._capacityClusterCount*node._chunksPerCluster);
  assert(array instanceof Int32Array);
  assert.equal(array.length,storage.bufferCount*4);
  assert.equal(storage.value.itemSize,4);
  assert.equal(array.some(value=>value!==0),false,'New CPU storage must be zero-filled');
  storageRecords.push({label,bufferCount:storage.bufferCount,bufferCountType:typeof storage.bufferCount,arrayType:array.constructor.name,arrayLength:array.length,byteLength:array.byteLength,allValuesZero:true});
}
let initial = null;
for(const [width,height] of sizes){
  candidate.setSize(width,height);
  const nx = Math.ceil(width/32), ny = Math.ceil(height/32), count = nx*ny*24;
  const identities = {compute:candidate._compute,storage:candidate._lightIndexes,attribute:candidate._lightIndexes.value,fragment:candidate._screenClusterIndex,grid:candidate._gridDimensions};
  const keys = {compute:candidate._compute.getCacheKey(true),light:candidate.customCacheKey(),fragment:candidate._screenClusterIndex.getCacheKey(true)};
  if(!initial) {initial = {...identities, keys};validateStorage(candidate,'initial reserve');}
  for(const key of Object.keys(identities)) assert.strictEqual(identities[key], initial[key], key+' identity changed');
  assert.deepEqual(keys, initial.keys, 'Grid resize changes shader cache key');
  assert.equal(candidate._compute.count, count);
  assert.deepEqual(candidate._gridDimensions.value.toArray(), [nx,ny]);
  assert.equal(candidate._lightIndexes.value.array.byteLength, 50135040);
  assert.equal(candidate.gridReallocations,1);
  assert(count*64 <= candidate._lightIndexes.value.array.length);
  identityRecords.push({width,height,grid:[nx,ny,24],activeCount:count,reservedCount:candidate._capacityClusterCount,bufferBytes:candidate._lightIndexes.value.array.byteLength,stableIdentities:true,cacheKeys:keys});
}

let computeDisposeEvents=0,storageDisposeEvents=0;
candidate._compute.addEventListener('dispose',()=>computeDisposeEvents++);
candidate._lightIndexes.value.addEventListener('dispose',()=>storageDisposeEvents++);
candidate.setSize(4096,2160);
assert.notStrictEqual(candidate._compute, initial.compute);
assert.notStrictEqual(candidate._lightIndexes, initial.storage);
assert.equal(candidate._compute.count,128*68*24);
assert.equal(candidate._lightIndexes.value.array.byteLength,50135040*2);
assert.equal(candidate.gridReallocations,2);
validateStorage(candidate,'geometric growth');
assert.equal(computeDisposeEvents,1); assert.equal(storageDisposeEvents,1);
const grown = {compute:candidate._compute,storage:candidate._lightIndexes,bytes:candidate._lightIndexes.value.array.byteLength,cache:candidate._compute.getCacheKey(true)};
candidate.setSize(4128,2160);
assert.strictEqual(candidate._compute,grown.compute); assert.strictEqual(candidate._lightIndexes,grown.storage);
assert.equal(candidate.gridReallocations,2); assert.equal(candidate._compute.count,129*68*24);
candidate.setSize(1440,1080);
assert.strictEqual(candidate._compute,grown.compute); assert.strictEqual(candidate._lightIndexes,grown.storage);
assert.equal(candidate._compute.getCacheKey(true),grown.cache); assert.equal(candidate.gridReallocations,2);
const state = node => ({compute:node._compute,storage:node._lightIndexes,fragment:node._screenClusterIndex,grid:node._gridDimensions.value.toArray(),size:node._bufferSize?.toArray(),count:node._compute?.count,capacity:node._capacityClusterCount,reallocations:node.gridReallocations});
const beforeRejection=state(candidate);
assert.throws(()=>candidate.setSize(16384,16384),/exceeds the GPU lighting-buffer limit/);
assert.deepEqual(state(candidate),beforeRejection,'Unsupported pre-device setSize mutated grid');
const renderer={backend:{device:{limits:{maxStorageBufferBindingSize:256*1024*1024,maxBufferSize:128*1024*1024}}},getDrawingBufferSize:target=>target.set(16384,16384)};
assert.throws(()=>candidate.updateProgram(renderer),/exceeds the GPU lighting-buffer limit/);
assert.equal(candidate._maxStorageBytes,128*1024*1024);
assert.deepEqual(state(candidate),beforeRejection,'Unsupported device-limit resize mutated grid');
const empty=new Candidate(64,32,24,64),emptyState=state(empty);
assert.throws(()=>empty.setSize(16384,16384),/exceeds the GPU lighting-buffer limit/);
assert.deepEqual(state(empty),emptyState,'Rejected initial allocation mutated empty grid');
renderer.getDrawingBufferSize=target=>target.set(1440,1080);
candidate.updateProgram(renderer); assert.deepEqual(state(candidate),beforeRejection);

// Invoke the installed declaration generator itself. Keep the expensive historical
// TypedArray coercion bounded to one compute and one fragment declaration.
const oldStorage=attributeArray(initial.attribute.array,'ivec4').setName('lightIndexes');
assert.strictEqual(oldStorage.bufferCount,initial.attribute.array);
assert.strictEqual(oldStorage.value.array,initial.storage.value.array);
const declaration=(storage,stage)=>{
  const builder=new WGSLNodeBuilder(null,{backend:{}});
  builder.uniforms[stage]=[{name:'lightIndexes',type:'storageBuffer',node:storage,value:storage.value,groupNode:{name:'object'}}];
  builder.bindingsIndexes.object={binding:0,group:0};
  return builder.getUniforms(stage);
};
let coercions=0;
const originalToString=initial.attribute.array.toString;
initial.attribute.array.toString=function(){coercions++;return originalToString.call(this);};
const declarationRecords=[];
try{
  for(const stage of ['compute','fragment']){
    const before=coercions,startOld=performance.now(),oldCode=declaration(oldStorage,stage),oldMs=performance.now()-startOld;
    assert.equal(coercions,before+1,'Historical bufferCount must demonstrate actual TypedArray string coercion');
    const startNew=performance.now(),newCode=declaration(initial.storage,stage),newMs=performance.now()-startNew;
    assert.equal(coercions,before+1,'Numeric bufferCount must not coerce the underlying array');
    assert.equal(newCode,oldCode,'Numeric count changes the installed WGSL storage declaration');
    assert.match(newCode,/array< vec4<i32> >/);
    declarationRecords.push({stage,exactDeclarationMatch:true,declaration:newCode,declarationSHA256:hash(newCode),historicalTypedArrayCoercions:1,numericCountTypedArrayCoercions:0,oneCallHistoricalMs:oldMs,oneCallNumericMs:newMs});
  }
}finally{delete initial.attribute.array.toString;}

const f = Math.fround;
let arithmeticComparisons=0,clusterIndicesCompared=0,maxFloat32Delta=0;
// Integer uniforms are represented exactly; compare each grid edge at all tested sizes.
for(const [width,height] of [...sizes,[4096,2160]]){
  const nx=Math.ceil(width/32),ny=Math.ceil(height/32);
  for(const n of [nx,ny]) for(let edge=0;edge<=n;edge++){
    const constant=f(2/n),dynamic=f(f(2)/f(n));
    const a=f(f(f(edge)*constant)-f(1)),b=f(f(f(edge)*dynamic)-f(1));
    maxFloat32Delta=Math.max(maxFloat32Delta,Math.abs(a-b)); assert.equal(a,b); arithmeticComparisons++;
  }
  for(let i=0;i<nx*ny*24;i++){
    const xyz=[i%nx,Math.floor(i/nx)%ny,Math.floor(i/(nx*ny))];
    const linear=xyz[0]+xyz[1]*nx+xyz[2]*(nx*ny);
    assert.equal(linear,i); assert(linear*64+63 < nx*ny*24*64); clusterIndicesCompared++;
  }
}

const cameraNames=['reference','street_district_gallery','street_district_civic_court','district_entire_world'].filter(n=>manifest.cameras[n]);
for(const name of Object.keys(manifest.cameras)) if(cameraNames.length<4&&!cameraNames.includes(name)) cameraNames.push(name);
let textureValuesCompared=0,zRangeValuesCompared=0,lightMembershipComparisons=0,boundsCompared=0;
const cameraRecords=[];
function bounds(i,nx,ny,camera,uniformDimensions){
  const cx=i%nx,cy=Math.floor(i/nx)%ny,cz=Math.floor(i/(nx*ny));
  const sx=uniformDimensions?f(f(2)/f(nx)):f(2/nx),sy=uniformDimensions?f(f(2)/f(ny)):f(2/ny);
  const x0=f(f(f(cx)*sx)-1),x1=f(f(f(cx+1)*sx)-1),y1=f(1-f(f(cy)*sy)),y0=f(1-f(f(cy+1)*sy));
  const ratio=f(f(camera.far)/f(camera.near));
  const zn=f(-f(f(camera.near)*f(Math.pow(ratio,f(f(cz)*f(1/24))))));
  const zf=f(-f(f(camera.near)*f(Math.pow(ratio,f(f(cz+1)*f(1/24))))));
  const ix=f(1/f(camera.projectionMatrix.elements[0])),iy=f(1/f(camera.projectionMatrix.elements[5]));
  const xn=f(-zn*ix),xf=f(-zf*ix),yn=f(-zn*iy),yf=f(-zf*iy);
  return [Math.min(f(x0*xn),f(x0*xf)),Math.min(f(y0*yn),f(y0*yf)),zf,Math.max(f(x1*xn),f(x1*xf)),Math.max(f(y1*yn),f(y1*yf)),zn];
}
function member(box,p,r){let sum=0;for(let k=0;k<3;k++){const d=f(p[k]-Math.max(box[k],Math.min(p[k],box[k+3])));sum=f(sum+f(d*d));}return sum<=f(r*r);}
for(const name of cameraNames){
  const c=manifest.cameras[name], camera=new T.PerspectiveCamera(c.fov,1440/1080,.08,6500);
  camera.position.fromArray(c.position); camera.lookAt(new T.Vector3().fromArray(c.target)); camera.updateMatrixWorld(true);
  original.updateLightsTexture(camera);candidate.updateLightsTexture(camera);
  assert.deepEqual(candidate._lightSortOrder,original._lightSortOrder);
  assert.deepEqual(candidate._lightsTexture.image.data,original._lightsTexture.image.data);
  assert.deepEqual(candidate._zSliceRangesData,original._zSliceRangesData);
  textureValuesCompared+=candidate._lightsTexture.image.data.length;zRangeValuesCompared+=candidate._zSliceRangesData.length;
  const positions=lights.map(l=>l.position.clone().applyMatrix4(camera.matrixWorldInverse).toArray().map(f));
  for(const [width,height]of sizes){
    camera.aspect=width/height;camera.updateProjectionMatrix();const nx=Math.ceil(width/32),ny=Math.ceil(height/32),count=nx*ny*24;
    for(let sample=0;sample<128;sample++){
      const index=Math.floor(sample*(count-1)/127),a=bounds(index,nx,ny,camera,false),b=bounds(index,nx,ny,camera,true);
      assert.deepEqual(a,b);boundsCompared++;
      for(let light=0;light<lights.length;light++){assert.equal(member(a,positions[light],lights[light].distance),member(b,positions[light],lights[light].distance));lightMembershipComparisons++;}
    }
  }
  cameraRecords.push({name,lights:53,textureAndZSliceValuesExact:true});
}
const record={status:'passed',timestamp:new Date().toISOString(),scope:'CPU-only lifecycle, source-token preservation, actual 53-light texture/Z-range equivalence, integer indexing and Float32 arithmetic reference checks. Does not claim GPU image equivalence or actual GPU storage reclamation.',threeRevision:T.REVISION,sourceSHA256:manifest.sourceHash,environmentManifestSHA256:hash(fs.readFileSync('public/assets/environment.json')),moduleSHA256:hash(candidateText),pinnedOriginalSHA256:hash(originalText),unchangedMethods,kernelChangedOnlyByDeclaredUniformSubstitutions:true,parameters:{maxLights:64,tileSize:32,zSlices:24,maxLightsPerCluster:64,actualPointLights:53},identityRecords,growth:{size:[4096,2160],bufferBytes:grown.bytes,computeDisposeEvents,storageDisposeEvents,shrinkingReusesGrownAllocation:true,gpuStorageReclamationVerified:false},arithmetic:{arithmeticComparisons,clusterIndicesCompared,maxFloat32Delta,boundsCompared,lightMembershipComparisons,textureValuesCompared,zRangeValuesCompared},cameraRecords,limitations:['CPU Float32 reference arithmetic is not proof of GPU compiler division/constant-folding behavior. Actual storage-list and pixel comparisons remain required.','Dispose events are observed; standalone storage GPU-buffer reclamation must be verified separately.','Only active clusters dispatch or index the reserved storage. Capacity growth can recreate shaders; resize stability is bounded to allocated capacity.']};
record.pinnedAddonSHA256=record.pinnedOriginalSHA256;
record.growth.geometricCapacityDoubled=true;
record.growth.adjacentLargerSizeReusesAllocation=[4128,2160];
record.sizeLimits={defaultBytes:128*1024*1024,preDeviceSetSizeSupported:true,unsupportedInitialSizePreservesEmptyState:true,unsupportedExistingSizePreservesGridState:true,deviceMinimumOfStorageBindingAndBufferLimitsEnforced:true,rejectedSize:[16384,16384]};
record.growth.storageAllocationCaveat='Installed r186 does not reclaim standalone storage allocations from BufferAttribute.dispose events; above-capacity growth retains prior GPU allocation until renderer teardown.';
record.numericBufferCount={storageRecords,sameInt32StorageObjectCompared:true,installedWGSLBuilderSHA256:hash(fs.readFileSync(new URL(import.meta.resolve('three/src/renderers/webgpu/nodes/WGSLNodeBuilder.js')))),declarationRecords,totalHistoricalCoercions:coercions,timingScope:'Two single CPU declaration calls per arm, one compute and one fragment. Diagnostic only; not a statistically sampled benchmark or end-to-end startup measurement.'};
assert.equal(hash(fs.readFileSync(candidateFile)),hash(candidateText),'Candidate changed during CPU proof');
fs.writeFileSync('stable_grid_cpu_validation.json',JSON.stringify(record,null,2)+'\n');
console.log(JSON.stringify({status:record.status,moduleSHA256:record.moduleSHA256,arithmetic:record.arithmetic,resizeChecks:identityRecords.length,growth:record.growth}));
