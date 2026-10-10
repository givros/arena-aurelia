import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const viewer = fileURLToPath(new URL('../', import.meta.url));
const publicRoot = path.join(viewer, 'public');
const dist = path.join(viewer, 'dist');
const sha = file => crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
function files(directory) {
  return fs.readdirSync(directory, {withFileTypes: true}).flatMap(entry => {
    const file = path.join(directory, entry.name);
    assert(!entry.isSymbolicLink(), `Unexpected symlink: ${file}`);
    return entry.isDirectory() ? files(file) : [file];
  });
}
const assets = files(publicRoot);
for (const asset of assets) {
  const built = path.join(dist, path.relative(publicRoot, asset));
  assert.equal(sha(built), sha(asset), `Build changed or omitted ${path.relative(publicRoot, asset)}`);
}
const manifest = JSON.parse(fs.readFileSync(path.join(publicRoot, 'assets/environment.json')));
const assetManifest = JSON.parse(fs.readFileSync(path.join(viewer, '../repository-assets/manifest.json')));
const geometry = assetManifest.files.find(file => file.path === 'viewer/public/assets/environment.bin');
assert.equal(sha(path.join(dist, 'assets/environment.bin')), geometry.sha256, 'Geometry differs from the verified source');
const totalBytes = files(dist).reduce((sum, file) => sum + fs.statSync(file).size, 0);
assert(totalBytes < 1024 ** 3, 'Website exceeds the GitHub Pages size limit');
assert(fs.readFileSync(path.join(dist, 'index.html'), 'utf8').includes('type="module"'), 'Missing application entrypoint');
console.log(JSON.stringify({status: 'passed', assets: assets.length, totalBytes, sourceSHA256: manifest.sourceHash, geometrySHA256: geometry.sha256}));
