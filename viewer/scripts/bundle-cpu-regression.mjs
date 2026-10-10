// Short CPU regression: installed renderer methods with a no-op GPU backend.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import ts from 'typescript';
import * as T from 'three/webgpu';
import Renderer from '../node_modules/three/src/renderers/common/Renderer.js';
import Observer from '../node_modules/three/src/materials/nodes/manager/NodeMaterialObserver.js';

const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const source=fs.readFileSync('performance/rejected-bundle.ts','utf8');
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText.replaceAll("'three/webgpu'",JSON.stringify(import.meta.resolve('three/webgpu')));
const {preserveNestedBundleOwnership,StaticBundles}=await import('data:text/javascript;base64,'+Buffer.from(compiled).toString('base64'));
const mat=new T.MeshStandardMaterial({emissive:0xff8000,emissiveIntensity:.6}),mesh=new T.Mesh(new T.BoxGeometry(),mat),scene=new T.Scene();
const ro={object:mesh,geometry:mesh.geometry,material:mat,bundle:{static:true,version:1},context:{width:1440,height:1080},scene,lightsNode:{getBuiltinLights:()=>[]}};
const observer=new Observer({material:mat,object:mesh,context:{}}),frame={renderId:1,renderer:{getMRT:()=>null}};
const initial=observer.needsRefresh(ro,frame);mat.emissiveIntensity=2.5;frame.renderId=2;const unchangedBundleRefresh=observer.needsRefresh(ro,frame);
assert.equal(initial,T.RenderObjectRefreshType.FULL);assert.equal(unchangedBundleRefresh,T.RenderObjectRefreshType.SHARED);

function nestedOwnership(wrapped){
 const data=new Map(),bundles=new Map(),objects=new Map(),getData=o=>{if(!data.has(o))data.set(o,{renderObjects:[]});return data.get(o);};
 const mainGroup={version:1,id:'main'},shadowGroup={version:1,id:'shadow'},camera={},sunCamera={},context={},light={};let nested=false;
 const mainItems=[{id:'mainFirst',geometry:{drawRange:{}}},{id:'mainSecond',geometry:{drawRange:{}}}],shadowItems=[{id:'shadowFirst',geometry:{drawRange:{}}}];
 const fake={_currentRenderContext:context,_currentRenderBundle:null,opaque:true,transparent:true,backend:{get:getData,beginBundle:()=>{},finishBundle:(c,b)=>getData(b).bundleGPU={},addBundle:()=>{}},_bundles:{get:g=>{if(!bundles.has(g))bundles.set(g,{bundleGroup:g});return bundles.get(g);}},_bundleNeedsUpdate:Renderer.prototype._bundleNeedsUpdate,_nodes:{needsRefresh:()=>T.RenderObjectRefreshType.FULL,updateBefore:ro=>{if(ro.object.id==='mainFirst'&&!nested){nested=true;fake._renderScene(shadowGroup,sunCamera,shadowItems);}},updateForRender:()=>{},updateAfter:()=>{}},_objects:{get:object=>{if(!objects.has(object))objects.set(object,{object});return objects.get(object);}},_geometries:{updateForRender:()=>{}},_bindings:{updateForRender:()=>{},updateSharedForRender:()=>{}},_pipelines:{updateForRender:()=>{},isReady:()=>false},_renderObjects:(items,cam,s,ln)=>items.forEach(o=>Renderer.prototype._renderObjectDirect.call(fake,o,mat,s,cam,ln,null,null)),_renderScene(group,cam,items){return Renderer.prototype._renderBundle.call(this,{bundleGroup:group,camera:cam,renderList:{opaque:items,transparent:[],transparentDoublePass:[]}},scene,light);}};
 if(wrapped)preserveNestedBundleOwnership(fake);
 fake._renderScene(mainGroup,camera,mainItems);
 return {expected:mainItems.map(o=>o.id),recorded:getData(bundles.get(mainGroup)).renderObjects.map(ro=>ro.object.id),ownerRestored:fake._currentRenderBundle===null};
}
const original=nestedOwnership(false),fixed=nestedOwnership(true);
assert.deepEqual(original.recorded,['mainFirst']);assert.deepEqual(fixed.recorded,fixed.expected);assert(fixed.ownerRestored);
const exceptionOwner={},throwing={_currentRenderBundle:exceptionOwner,_renderScene(){this._currentRenderBundle=null;throw new Error('fixture');}};
preserveNestedBundleOwnership(throwing);assert.throws(()=>throwing._renderScene(),/fixture/);assert.equal(throwing._currentRenderBundle,exceptionOwner);

const testScene=new T.Scene(),root=new T.Group(),nested=new T.Group();testScene.add(root);root.position.set(4,2,-7);root.rotation.y=.3;root.add(nested);nested.position.set(2,3,4);nested.rotation.y=-.2;
const opaque=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial()),embers=new T.Mesh(new T.BoxGeometry(),mat),transparent=new T.Mesh(new T.BoxGeometry(),new T.MeshStandardMaterial({transparent:true,opacity:.8})),skinned=new T.SkinnedMesh(new T.BoxGeometry(),new T.MeshStandardMaterial());
opaque.position.set(3,1,5);nested.add(opaque,embers,transparent,skinned);testScene.updateMatrixWorld(true);const expected=opaque.matrixWorld.clone();
const groups=new StaticBundles(testScene,new T.PerspectiveCamera(),new T.DirectionalLight(),[root]),members=groups.members.flat();
assert(members.includes(opaque));assert(!members.includes(embers));assert(!members.includes(transparent));assert(!members.includes(skinned));
const transformDelta=Math.max(...expected.elements.map((v,i)=>Math.abs(v-opaque.matrixWorld.elements[i])));assert(transformDelta<1e-12);
groups.setEnabled(true);groups.setEnabled(false);const disabledStaticFlags=groups.groups.map(g=>g.static);
const disabledControlPassed=disabledStaticFlags.every(x=>x===false);
const report={schema:'roman-arena.bundle-cpu-regression/v1',timestamp:new Date().toISOString(),passed:disabledControlPassed,threeRevision:T.REVISION,bundleModuleSHA256:sha(source),scope:'CPU tests of installed Observer/Renderer methods and actual transpiled project bundle adapter; no renderer initialization, browser, GPU calls, shader execution or visual assertions.',emissiveRegression:{initial,unchangedBundleRefresh,enum:T.RenderObjectRefreshType,emissiveExcluded:true},nestedOwnership:{original,fixed,exceptionFinallyRestoresOwner:true},membership:{opaqueIncluded:true,emissiveExcluded:true,transparentExcluded:true,skinnedExcluded:true,maxWorldTransformDelta:transformDelta},disabledControl:{passed:disabledControlPassed,groupStaticFlags:disabledStaticFlags},limits:'GPU image, shadow membership, camera motion and day/night comparisons remain required. Pipeline/bind-group resource replacement is not exercised here.'};
fs.writeFileSync('bundle_cpu_regression_validation.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report));if(!report.passed)process.exitCode=1;
