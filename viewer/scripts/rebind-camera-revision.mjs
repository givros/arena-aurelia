import fs from 'node:fs';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';

const read=file=>JSON.parse(fs.readFileSync(file));
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
const checkpoint='checkpoints/pre-camera-revision';
const before=read(checkpoint+'/environment.json'),after=read('public/assets/environment.json');
const oldAudit=read(checkpoint+'/source_validation.json'),audit=read('source_validation.json');
const authority=read('public/assets/'+after.navigation.reviewViewAuthority);
const reviewed=new Set(after.navigation.reviewedDestinations);
assert.equal(audit.status,'passed');
assert.equal(audit.sourceHash,after.sourceHash);
assert.equal(audit.binarySHA256,oldAudit.binarySHA256,'Geometry binary changed');
assert.deepEqual(audit.textures,oldAudit.textures,'Texture content changed');
assert.equal(audit.characters.manifestSHA256,oldAudit.characters.manifestSHA256,'Population changed');
assert.deepEqual(audit.characters.assets,oldAudit.characters.assets,'Character assets changed');
assert.equal(reviewed.size,Object.keys(authority.cameras).length);
assert.equal(sha('public/assets/'+after.navigation.reviewViewAuthority),after.navigation.reviewViewAuthoritySHA256);
const clean=manifest=>{
 const doc=structuredClone(manifest);
 delete doc.sourceHash;delete doc.cameras;
 for(const key of ['reviewedDestinations','reviewViewAuthority','reviewViewAuthoritySHA256'])delete doc.navigation[key];
 for(const destination of doc.navigation.destinations)if(reviewed.has(destination.id)){
  delete destination.position;delete destination.lookAt;
 }
 return doc;
};
assert.deepEqual(clean(after),clean(before),'Non-camera/non-reviewed-destination manifest content changed');
assert.deepEqual(Object.keys(after.cameras).sort(),Object.keys(before.cameras).sort());
const changedCameras=[];
for(const [id,camera] of Object.entries(after.cameras)){
 if(JSON.stringify(camera)!==JSON.stringify(before.cameras[id])){
  assert.ok(reviewed.has(id),'Unexpected camera change: '+id);changedCameras.push(id);
 }
}
for(const id of reviewed){
 const destination=after.navigation.destinations.find(d=>d.id===id),view=authority.cameras[id];
 const convert=v=>[v[0],v[2],-v[1]];
 assert.deepEqual(destination.position,convert(view.position));
 assert.deepEqual(destination.lookAt,convert(view.target));
}
const proof={status:'passed',timestamp:new Date().toISOString(),testedSourceHash:before.sourceHash,
 finalSourceHash:after.sourceHash,binarySHA256:audit.binarySHA256,characterManifestSHA256:audit.characters.manifestSHA256,
 oldManifestSHA256:sha(checkpoint+'/environment.json'),finalManifestSHA256:sha('public/assets/environment.json'),
 allowedChanges:['sourceHash','cameras','reviewed destination positions/look targets','review camera authority metadata'],
 changedCameras,reviewedDestinations:[...reviewed],
 unchanged:'Binary geometry, materials, textures, instances, collision, routes, bounds, lighting, population, character assets and all layout authorities.'};
for(const filename of ['route_validation.json','street_activity_validation.json']){
 const report=read(filename);
 assert.equal(report.sourceHash,before.sourceHash,'Unexpected executed source for '+filename);
 if(report.results)assert.ok(report.results.every(r=>r.status==='passed'));
 if(report.boundaryResults)assert.ok(report.boundaryResults.every(r=>r.status==='passed'));
 assert.equal(report.errors?.length||0,0);
 if(report.status)assert.equal(report.status,'passed');
 fs.copyFileSync(filename,checkpoint+'/'+filename);
 report.executedSourceHash=report.sourceHash;
 if(report.manifestSHA256)report.executedManifestSHA256=report.manifestSHA256;
 report.sourceHash=after.sourceHash;
 if(report.manifestSHA256)report.manifestSHA256=proof.finalManifestSHA256;
 report.sourceRevisionEvidence='camera_only_revision_validation.json';
 report.sourceRevisionScope=proof.unchanged;
 fs.writeFileSync(filename,JSON.stringify(report,null,2));
}
fs.writeFileSync('camera_only_revision_validation.json',JSON.stringify(proof,null,2));
console.log(JSON.stringify(proof));
