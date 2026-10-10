import fs from 'node:fs';
import assert from 'node:assert/strict';
const original=JSON.parse(fs.readFileSync('route_validation.json'));
const recheck=JSON.parse(fs.readFileSync('route_recheck.json'));
assert.equal(original.sourceHash,recheck.sourceHash,'A targeted recheck must use the same source geometry.');
const checked=[...recheck.results,...(recheck.boundaryResults||[])];
assert(checked.length>0&&checked.every(r=>r.status==='passed'),'Every rechecked route or physical boundary must pass.');
original.rechecks??=[];
original.rechecks.push({timestamp:recheck.timestamp,ids:checked.map(r=>r.id),sourceHash:recheck.sourceHash,streetLayoutSHA256:recheck.streetLayoutSHA256,layoutHashes:recheck.layoutHashes,characterManifestSHA256:recheck.characterManifestSHA256});
for(const result of recheck.results){const index=original.results.findIndex(r=>r.id===result.id);assert(index>=0);original.results[index]={...result,validatedAt:recheck.timestamp};}
for(const result of recheck.boundaryResults||[]){const index=original.boundaryResults.findIndex(r=>r.id===result.id);assert(index>=0);original.boundaryResults[index]={...result,validatedAt:recheck.timestamp};}
original.streetLayoutSHA256=recheck.streetLayoutSHA256;
original.layoutHashes=recheck.layoutHashes;
original.characterManifestSHA256=recheck.characterManifestSHA256;
original.errors.push(...recheck.errors);
original.status=[...original.results,...(original.boundaryResults||[])].every(r=>r.status==='passed')&&!original.errors.length?'passed':'failed';
fs.writeFileSync('route_validation.json',JSON.stringify(original,null,2));
console.log(JSON.stringify({status:original.status,routes:original.results.length,rechecked:checked.map(r=>r.id)}));
