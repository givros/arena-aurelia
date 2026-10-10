import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {chromium} from 'playwright';

const viewerRoot = fileURLToPath(new URL('../', import.meta.url));
const target = new URL(process.argv[2] || 'http://127.0.0.1:4180/arena-aurelia/');
assert(['localhost', '127.0.0.1', '[::1]'].includes(target.hostname), 'This check accepts only a local test server.');
assert(target.pathname.endsWith('/'), 'The test URL must end with its application directory and a slash.');
const basePath = target.pathname;
target.searchParams.set('debug', '1');
const output = path.resolve(process.argv[3] || path.join(viewerRoot, 'pages_validation.json'));
const manifestBytes = fs.readFileSync(path.join(viewerRoot, 'public/assets/environment.json'));
const manifest = JSON.parse(manifestBytes);
const expectedBytes = fs.statSync(path.join(viewerRoot, 'public/assets/environment.bin')).size;
const timeout = Math.min(600000, Math.max(30000, Number(process.env.ARENA_PAGES_TIMEOUT_MS) || 360000));
const report = {
  status: 'failed', timestamp: new Date().toISOString(), url: target.href,
  sourceSHA256: manifest.sourceHash,
  manifestSHA256: crypto.createHash('sha256').update(manifestBytes).digest('hex'),
  viewport: {width: 1440, height: 1080, dpr: 1}, checks: [], errors: [], requests: [],
};
const check = (name, passed, detail) => {
  report.checks.push({name, status: passed ? 'passed' : 'failed', detail});
  assert(passed, name);
};
const windowsChrome = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const executablePath = process.env.CHROME_PATH || (fs.existsSync(windowsChrome) ? windowsChrome : undefined);
let browser;
try {
  browser = await chromium.launch({
    executablePath, headless: true,
    args: ['--enable-unsafe-webgpu', '--ignore-gpu-blocklist', '--disable-background-timer-throttling'],
  });
  report.browser = browser.version();
  const context = await browser.newContext({viewport: {width: report.viewport.width, height: report.viewport.height}, deviceScaleFactor: 1});
  const page = await context.newPage();
  page.on('pageerror', error => report.errors.push(error.message));
  page.on('console', message => {if (message.type() === 'error') report.errors.push(message.text());});
  page.on('request', request => report.requests.push(request.url()));
  page.on('requestfailed', request => report.errors.push(`${request.failure()?.errorText}: ${request.url()}`));
  page.on('response', response => {
    if (response.status() >= 400) report.errors.push(`${response.status()}: ${response.url()}`);
  });
  const documentResponse = await page.goto(target.href, {waitUntil: 'domcontentloaded', timeout: 30000});
  check('Application responds at the project subdirectory', documentResponse?.status() === 200, documentResponse?.status());
  await page.waitForFunction(() => window.__arena?.ready || window.__arenaFailure, null, {timeout});
  const failure = await page.evaluate(() => window.__arenaFailure || null);
  check('World initialization succeeds', !failure, failure);
  await page.waitForFunction(() => window.__arenaFailure || window.__arena.stats().frames.length >= 12, null, {timeout: 30000});
  report.runtime = await page.evaluate(() => {
    const world = window.__arena, stats = world.stats();
    const info = world.renderer.backend.device?.adapterInfo;
    return {
      backend: stats.backend, sourceSHA256: world.environment.manifest.sourceHash,
      loadMs: world.loadMs, transfer: stats.transfer, characters: stats.characters,
      frames: stats.frames.length, failure: window.__arenaFailure || null,
      fog: [world.scene.fog.near, world.scene.fog.far], pointLights: world.atmosphere.lights.length,
      pixelRatio: world.renderer.getPixelRatio(), samples: world.renderer.samples,
      shadows: world.atmosphere.sun.shadow.mapSize.toArray(),
      adapter: info ? {vendor: info.vendor, architecture: info.architecture, description: info.description, isFallbackAdapter: info.isFallbackAdapter} : null,
    };
  });
  const runtime = report.runtime;
  check('Actual hardware WebGPU renders frames', runtime.backend === 'webgpu' && runtime.adapter?.isFallbackAdapter === false && runtime.frames >= 12 && !runtime.failure, {backend: runtime.backend, adapter: runtime.adapter, frames: runtime.frames, failure: runtime.failure});
  check('Canonical architecture remains complete', runtime.sourceSHA256 === manifest.sourceHash && runtime.transfer.sourceInstances === 25332 && runtime.transfer.runtimeTriangles === 6690777 && runtime.transfer.bytes === expectedBytes, runtime.transfer);
  check('Canonical characters and animation remain complete', runtime.characters.count === 15688 && runtime.characters.animated === 164 && runtime.characters.triangles === 78613716 && runtime.characters.allCastAndReceiveShadows, {count: runtime.characters.count, animated: runtime.characters.animated, triangles: runtime.characters.triangles, allCastAndReceiveShadows: runtime.characters.allCastAndReceiveShadows});
  check('Fog and rendering quality are preserved', runtime.fog[0] === 1200 && runtime.fog[1] === 4500 && runtime.pointLights === 53 && runtime.pixelRatio === 1 && runtime.samples === 4 && runtime.shadows.every(value => value === 4096), {fog: runtime.fog, pointLights: runtime.pointLights, pixelRatio: runtime.pixelRatio, samples: runtime.samples, shadows: runtime.shadows});
  const requests = [...new Set(report.requests)].filter(url => /^https?:/.test(url));
  const outsideBase = requests.filter(url => {const parsed = new URL(url); return parsed.origin !== target.origin || !parsed.pathname.startsWith(basePath);});
  check('Every HTTP request stays inside the project subdirectory', outsideBase.length === 0, outsideBase);
  const requestedAssets = requests.map(url => new URL(url).pathname).filter(value => value.startsWith(`${basePath}assets/`));
  check('Manifest, binary, population, textures and character assets load', ['environment.json', 'environment.bin', 'characters/crowd_manifest.json', 'arena_sand_atlas.png', 'mediterranean_earth.png', 'paving.png', 'travertine.png'].every(name => requestedAssets.includes(`${basePath}assets/${name}`)) && requestedAssets.filter(name => name.endsWith('.glb')).length === 14, {assetRequests: requestedAssets.length, characterAssets: requestedAssets.filter(name => name.endsWith('.glb')).length});
  await page.evaluate(() => window.__arena.dispose());
  check('No runtime, network or graphics errors', report.errors.length === 0, report.errors);
  report.status = 'passed';
} catch (error) {
  report.errors.push(error instanceof Error ? error.message : String(error));
} finally {
  await browser?.close();
  report.requests = [...new Set(report.requests)];
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n');
}
console.log(JSON.stringify({status: report.status, output, loadMs: report.runtime?.loadMs, checks: report.checks.length, errors: report.errors}));
if (report.status !== 'passed') process.exitCode = 1;
