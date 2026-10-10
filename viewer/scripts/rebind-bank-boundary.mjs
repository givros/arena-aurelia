import fs from 'node:fs';import crypto from 'node:crypto';import assert from 'node:assert/strict';
const read=file=>JSON.parse(fs.readFileSync(file)),sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex'),checkpoint='checkpoints/pre-bank-boundary';
const before=read(checkpoint+'/environment.json'),after=read('public/assets/environment.json'),oldAudit=read(checkpoint+'/source_validation.json'),audit=read('source_validation.json');
assert.equal(audit.status,'passed');assert.equal(audit.sourceHash,after.sourceHash);assert.notEqual(after.sourceHash,before.sourceHash);
assert.deepEqual(audit.textures,oldAudit.textures);assert.equal(audit.characters.manifestSHA256,oldAudit.characters.manifestSHA256);assert.deepEqual(audit.characters.assets,oldAudit.characters.assets);
const oldBin=fs.readFileSync(checkpoint+'/environment.bin'),newBin=fs.readFileSync('public/assets/environment.bin');
const oldMeshes=new Map(before.meshes.map(m=>[m.id,m])),newMeshes=new Map(after.meshes.map(m=>[m.id,m])),oldMaterials=new Map(before.materials.map(m=>[m.id,m])),newMaterials=new Map(after.materials.map(m=>[m.id,m])),newInstances=new Map();for(const item of after.instances){if(!newInstances.has(item.id))newInstances.set(item.id,[]);newInstances.get(item.id).push(item);}const slotOrdinal=new Map();
const checked=new Set();let triangles=0;
const materialState=m=>{const c=structuredClone(m);delete c.id;return c;};
for(const item of before.instances){
 const ordinal=slotOrdinal.get(item.id)||0;slotOrdinal.set(item.id,ordinal+1);const candidate=newInstances.get(item.id)?.[ordinal];assert(candidate,'Removed old instance material slot: '+item.id+' #'+ordinal);
 const a=structuredClone(item),b=structuredClone(candidate);delete a.mesh;delete b.mesh;delete a.material;delete b.material;assert.deepEqual(b,a,'Existing instance changed: '+item.id);
 const meshA=oldMeshes.get(item.mesh),meshB=newMeshes.get(candidate.mesh);assert(meshA&&meshB);
 assert.deepEqual(materialState(newMaterials.get(candidate.material??meshB.material)),materialState(oldMaterials.get(item.material??meshA.material)),'Material changed: '+item.id);
 const key=item.mesh+'|'+candidate.mesh;
 if(!checked.has(key)){
  for(const field of ['positions','normals','uvs','indices']){
   const x=meshA[field],y=meshB[field];assert.equal(!!x,!!y,'Attribute presence changed: '+key+' '+field);if(!x)continue;
   assert.equal(x.count,y.count,'Attribute count changed: '+key+' '+field);assert(oldBin.subarray(x.offset,x.offset+x.count*4).equals(newBin.subarray(y.offset,y.offset+y.count*4)),'Full attribute bytes changed: '+key+' '+field);
  }
  checked.add(key);
 }
 triangles+=meshA.indices.count/3;
}
const existing=new Set(before.instances.map(i=>i.id)),added=after.instances.filter(i=>!existing.has(i.id));assert(added.length>0);assert(added.every(i=>i.id.includes('WATERGATE_BANK/')),'Unexpected added geometry');
assert.deepEqual(after.cameras,before.cameras);
for(const [field,value]of Object.entries(before.navigation))if(field!=='boundaryChecks')assert.deepEqual(after.navigation[field],value,'Existing navigation changed: '+field);
const oldChecks=new Map(before.navigation.boundaryChecks.map(c=>[c.id,c]));for(const [id,test]of oldChecks)assert.deepEqual(after.navigation.boundaryChecks.find(c=>c.id===id),test);
const addedChecks=after.navigation.boundaryChecks.filter(c=>!oldChecks.has(c.id));assert.equal(addedChecks.length,4);assert(addedChecks.every(c=>c.expectedBarrierContains.includes('WATERGATE_BANK/')));
const currentRoutes=read('route_validation.json');const freshRoutes=currentRoutes.sourceHash===after.sourceHash&&currentRoutes.results.every(r=>r.status==='passed')&&currentRoutes.boundaryResults.every(r=>r.status==='passed');const recheck=read(freshRoutes?'route_validation.json':'route_recheck.json');assert.equal(recheck.sourceHash,after.sourceHash);for(const c of addedChecks)assert(recheck.boundaryResults.some(r=>r.id===c.id&&r.status==='passed'),'New physical gate check missing: '+c.id);
assert(recheck.boundaryResults.every(r=>r.status==='passed'));assert.equal(recheck.errors.length,0);
const proof={status:'passed',timestamp:new Date().toISOString(),previousSourceHash:before.sourceHash,finalSourceHash:after.sourceHash,oldManifestSHA256:sha(checkpoint+'/environment.json'),finalManifestSHA256:sha('public/assets/environment.json'),oldBinarySHA256:sha(checkpoint+'/environment.bin'),finalBinarySHA256:sha('public/assets/environment.bin'),unchangedInstances:before.instances.length,unchangedGeometryPairs:checked.size,unchangedTriangleInstances:triangles,addedInstances:added.map(i=>i.id),addedBoundaryChecks:addedChecks.map(c=>c.id),characterManifestSHA256:audit.characters.manifestSHA256,unchanged:'All previous instance transforms/collision semantics, full geometry attribute/index bytes, materials, textures, cameras, navigation routes, destinations, authored population and all character GLBs. Only four physical watergate-bank closures and their metadata were added.',affectedChecks:freshRoutes?'route_validation.json':'route_recheck.json'};
for(const filename of ['route_validation.json','street_activity_validation.json']){
 if(filename==='route_validation.json'&&freshRoutes)continue;
 const report=read(checkpoint+'/'+filename);assert.equal(report.sourceHash,before.sourceHash);assert.equal(report.errors?.length||0,0);
 report.sourceRevisionChain??=report.sourceRevisionEvidence?[{from:report.executedSourceHash,to:before.sourceHash,evidence:report.sourceRevisionEvidence}]:[];report.sourceRevisionChain.push({from:before.sourceHash,to:after.sourceHash,evidence:'watergate_boundary_revision_validation.json',scope:proof.unchanged});
 report.sourceRevisionEvidence='watergate_boundary_revision_validation.json';report.sourceRevisionScope=proof.unchanged;report.sourceHash=after.sourceHash;report.layoutHashes??={};report.layoutHashes[after.navigation.watergateBoundaryRevision]=after.navigation.watergateBoundaryRevisionSHA256;if(report.manifestSHA256)report.manifestSHA256=proof.finalManifestSHA256;
 if(report.boundaryResults)report.boundaryResults.push(...recheck.boundaryResults.filter(r=>addedChecks.some(c=>c.id===r.id)));
 fs.writeFileSync(filename,JSON.stringify(report,null,2));
}
fs.writeFileSync('watergate_boundary_revision_validation.json',JSON.stringify(proof,null,2));console.log(JSON.stringify({status:proof.status,unchangedInstances:proof.unchangedInstances,geometryPairs:checked.size,newInstances:added.length,newChecks:addedChecks.length}));
