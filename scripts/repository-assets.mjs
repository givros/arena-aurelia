import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const store = path.join(root, 'repository-assets');
const manifestFile = path.join(store, 'manifest.json');
const chunkSize = 48 * 1024 * 1024;
const sources = [
  {path: 'viewer/public/assets/environment.bin', runtime: true},
  {path: 'viewer/checkpoints/pre-bank-boundary/environment.bin', runtime: false},
];
const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
function safePath(relative) {
  assert(typeof relative === 'string' && !path.isAbsolute(relative), 'Expected a relative asset path');
  const resolved = path.resolve(root, relative);
  assert(resolved.startsWith(root + path.sep), 'Asset path escapes the repository');
  return resolved;
}
function writeChanged(file, bytes) {
  if (fs.existsSync(file) && fs.readFileSync(file).equals(bytes)) return;
  fs.mkdirSync(path.dirname(file), {recursive: true});
  fs.writeFileSync(file, bytes);
}

function pack() {
  const files = sources.map(source => {
    const bytes = fs.readFileSync(safePath(source.path));
    const parts = [];
    for (let offset = 0; offset < bytes.length; offset += chunkSize) {
      const chunk = bytes.subarray(offset, Math.min(offset + chunkSize, bytes.length));
      const sha256 = digest(chunk);
      const relative = `repository-assets/${sha256}.chunk`;
      writeChanged(safePath(relative), chunk);
      parts.push({path: relative, bytes: chunk.length, sha256});
    }
    return {...source, bytes: bytes.length, sha256: digest(bytes), parts};
  });
  writeChanged(manifestFile, Buffer.from(JSON.stringify({version: 1, chunkSize, files}, null, 2) + '\n'));
  console.log(`Packed ${files.length} full-resolution source files into verified Git-sized chunks.`);
}

function restore() {
  const manifest = JSON.parse(fs.readFileSync(manifestFile, 'utf8'));
  assert.equal(manifest.version, 1, 'Unsupported repository asset manifest');
  const selected = manifest.files.filter(file => !process.argv.includes('--runtime') || file.runtime);
  for (const file of selected) {
    const destination = safePath(file.path);
    // Validate tracked chunks even when a local reconstructed file already exists.
    const chunks = file.parts.map(part => {
      const bytes = fs.readFileSync(safePath(part.path));
      assert.equal(bytes.length, part.bytes, `Truncated asset chunk: ${part.path}`);
      assert.equal(digest(bytes), part.sha256, `Corrupt asset chunk: ${part.path}`);
      return bytes;
    });
    const bytes = Buffer.concat(chunks);
    assert.equal(bytes.length, file.bytes, `Wrong source length: ${file.path}`);
    assert.equal(digest(bytes), file.sha256, `Wrong source hash: ${file.path}`);
    if (fs.existsSync(destination)) {
      assert.equal(digest(fs.readFileSync(destination)), file.sha256,
        `Local asset differs from the repository: ${file.path}. Run npm run pack:assets after an intentional source export.`);
    } else {
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      const temporary = destination + '.restore-tmp';
      fs.writeFileSync(temporary, bytes, {flag: 'wx'});
      fs.renameSync(temporary, destination);
    }
    console.log(`Verified ${file.path} (${file.bytes} bytes, SHA-256 ${file.sha256}).`);
  }
}

const command = process.argv[2];
if (command === 'pack') pack();
else if (command === 'restore') restore();
else throw new Error('Usage: node scripts/repository-assets.mjs pack|restore [--runtime]');
