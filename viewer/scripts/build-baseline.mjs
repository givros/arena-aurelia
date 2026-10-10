import fs from 'node:fs';import path from 'node:path';import {build} from 'vite';import crypto from 'node:crypto';
const root=path.resolve('performance/baseline-app');fs.mkdirSync(path.join(root,'src'),{recursive:true});
for(const name of fs.readdirSync('src'))if(name.endsWith('.ts')||name.endsWith('.css'))fs.copyFileSync(path.join('src',name),path.join(root,'src',name));
for(const name of fs.readdirSync('performance/baseline-source'))fs.copyFileSync(path.join('performance/baseline-source',name),path.join(root,'src',name));
// The correctness-only controller repair is shared by both performance arms.
fs.copyFileSync('src/navigation.ts',path.join(root,'src/navigation.ts'));
// The explicit lighter-fog request is identical in both rendering arms.
const atmospherePath=path.join(root,'src/atmosphere.ts');
fs.writeFileSync(atmospherePath,fs.readFileSync(atmospherePath,'utf8').replace('Fog(0xc1c6c5,420,1350)','Fog(0xc1c6c5,1200,4500)'));
fs.copyFileSync('index.html',path.join(root,'index.html'));
await build({root,publicDir:path.resolve('public'),build:{outDir:path.resolve('performance/baseline-dist'),emptyOutDir:true},logLevel:'info'});
const sha=file=>crypto.createHash('sha256').update(fs.readFileSync(file)).digest('hex');
fs.writeFileSync('performance/baseline-build-provenance.json',JSON.stringify({timestamp:new Date().toISOString(),purpose:'Original pre-optimization rendering modules rebuilt against the final unchanged-quality source, with the same corrected controller and user-requested lighter fog as the optimized build.',source:JSON.parse(fs.readFileSync('public/assets/environment.json')).sourceHash,commonFog:{near:1200,far:4500,effectiveAtmosphereSHA256:sha(path.join(root,'src/atmosphere.ts')),reason:'User-requested lighter distance haze, identical in both arms.'},commonController:{file:'src/navigation.ts',sha256:sha('src/navigation.ts'),reason:'Grounded-only stair stepping; identical in both performance arms.'},effectiveModules:Object.fromEntries(fs.readdirSync(path.join(root,'src')).filter(n=>n.endsWith('.ts')).map(name=>[name,sha(path.join(root,'src',name))])),originalModules:Object.fromEntries(fs.readdirSync('performance/baseline-source').map(name=>[name,sha(path.join('performance/baseline-source',name))])),build:Object.fromEntries(fs.readdirSync('performance/baseline-dist/assets').filter(n=>/\.(js|css)$/.test(n)).map(name=>[name,sha(path.join('performance/baseline-dist/assets',name))]))},null,2));
