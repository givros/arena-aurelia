import * as T from 'three/webgpu';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone} from 'three/addons/utils/SkeletonUtils.js';
import {mergeCharacterPrimitives} from './character-merge';
import {assetURL} from './assets';

type Actor = {
 e:any; object:T.Object3D; mixer:T.AnimationMixer; pathIndex:number;
 walk:T.AnimationAction; idle:T.AnimationAction|null; waiting:boolean;
 waitReason:string; dwell:number; stoppedSeconds:number;
};
type PedestrianContext = {player?:T.Vector3|null; playerRadius?:number};

export async function loadCharacters(scene:T.Scene,source:any){
 let crowd:any={instances:[],npcs:[],palette:[]};
 if(source.navigation?.crowdManifest){
  const response=await fetch(assetURL(source.navigation.crowdManifest));
  if(!response.ok)throw new Error('The district population could not be loaded.');
  crowd=await response.json();
 }
 const entries=[...(source.navigation?.npcs||source.npcs||[]),...(crowd.npcs||[]),
  ...(crowd.instances||[]).map((e:any)=>({...e,asset:crowd.prototypes[e.role]}))];
 const loader=new GLTFLoader(),cache=new Map<string,any>(),instances:Actor[]=[];
 let triangles=0;const primitiveMerge={enabled:new URLSearchParams(location.search).get('primitiveMerge')!=='0',prototypes:{} as Record<string,any>,originalOverrideInstances:entries.filter((e:any)=>e.materialOverride).length};
 await Promise.all([...new Set(entries.map((e:any)=>e.asset))].map(async(path:any)=>{
  const asset=await loader.loadAsync(assetURL(path)),originalScene=asset.scene;
  if(primitiveMerge.enabled){asset.scene=clone(originalScene) as T.Group;primitiveMerge.prototypes[path]=mergeCharacterPrimitives(asset.scene,asset.animations);}
  cache.set(path,{...asset,originalScene});
 }));
 const staticRoot=new T.Group();staticRoot.name='Full_Detail_Crowds';scene.add(staticRoot);
 const staticMeshes:T.InstancedMesh[]=[];const staticGroups=new Map<string,any[]>(),materialCache=new Map<string,T.Material>();
 const tintMaterial=(mesh:any,e:any)=>{
  if(!crowd.palette?.length||!/RomanTunic|cloth/i.test(mesh.name+' '+mesh.material.name))return mesh.material;
  const key=`animated|${e.asset}|${mesh.material.uuid}|${e.colorIndex||0}`;
  let material=materialCache.get(key) as T.MeshStandardMaterial|undefined;
  if(!material){material=mesh.material.clone();material!.color.set(crowd.palette[e.colorIndex||0]);materialCache.set(key,material!);}
  return material!;
 };
 for(const e of entries){
  const cached=cache.get(e.asset),asset=e.materialOverride?{...cached,scene:cached.originalScene}:cached;
  asset.scene.traverse((o:any)=>{if(o.isMesh)triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;});
  if((e.path?.length>1||e.animated)&&asset.animations.length){
   const object=clone(asset.scene);object.name=e.id;
   // GLTF primitives of one actor share a skin. SkeletonUtils clones one wrapper per mesh;
   // consolidate identical wrappers while keeping every actor's bones independent.
   const skins:T.Skeleton[]=[];
   object.traverse((o:any)=>{if(!o.isSkinnedMesh)return;const candidate=o.skeleton as T.Skeleton;const shared=skins.find(s=>s.bones.length===candidate.bones.length&&s.bones.every((bone,i)=>bone===candidate.bones[i]&&s.boneInverses[i].equals(candidate.boneInverses[i])));if(shared)o.skeleton=shared;else skins.push(candidate);});
   object.position.fromArray(e.position||e.path[0]);object.rotation.y=e.rotationY||0;object.scale.setScalar(e.scale||1);
   object.traverse((o:any)=>{if(o.isMesh){o.castShadow=o.receiveShadow=true;o.material=tintMaterial(o,e);}});
   scene.add(object);
   const mixer=new T.AnimationMixer(object),clip=asset.animations.find((c:any)=>c.name===e.clip)||asset.animations[0];
   const walk=mixer.clipAction(clip),idleClip=asset.animations.find((c:any)=>c.name==='Idle');
   const idle=idleClip&&idleClip!==clip?mixer.clipAction(idleClip):null;
   walk.play();mixer.setTime(e.animationPhase||0);
   instances.push({e,object,mixer,walk,idle,pathIndex:e.pathIndex??1,waiting:false,waitReason:'',dwell:0,stoppedSeconds:0});
  }else{
   const bucket=e.role==='seated-spectator'?`seating-${Math.floor((e.sector||0)/2)}`:`district-${Math.floor(e.position[0]/64)}-${Math.floor(e.position[2]/64)}`;
   const key=e.asset+'|'+(e.materialOverride||'')+'|'+bucket;
   if(!staticGroups.has(key))staticGroups.set(key,[]);staticGroups.get(key)!.push(e);
  }
 }
 for(const [path,list] of staticGroups){
  const cached=cache.get(list[0].asset),asset=list[0].materialOverride?{...cached,scene:cached.originalScene}:cached;asset.scene.updateMatrixWorld(true);
  asset.scene.traverse((o:any)=>{
   if(!o.isMesh)return;
   let geometry=o.geometry;
   if(o.isSkinnedMesh){
    geometry=o.geometry.clone();const p=geometry.attributes.position.clone(),n=geometry.attributes.normal.clone(),v=new T.Vector3();
    for(let i=0;i<p.count;i++){v.fromBufferAttribute(p,i);o.applyBoneTransform(i,v);p.setXYZ(i,v.x,v.y,v.z);}
    geometry.setAttribute('position',p);geometry.setAttribute('normal',n);geometry.computeVertexNormals();geometry.computeBoundingBox();geometry.computeBoundingSphere();
   }
   const override=crowd.materialOverrides?.[list[0].materialOverride];
   const tint=!override&&/RomanTunic|cloth/i.test(o.name+' '+o.material.name)&&crowd.palette?.length;
   const materialKey=list[0].asset+'|'+(list[0].materialOverride||'')+'|'+o.uuid;
   const material:any=materialCache.get(materialKey)||(tint||override?o.material.clone():o.material);
   materialCache.set(materialKey,material);
   if(tint)material.color.set(0xffffff);
   if(override){material.color.fromArray(override.colorLinear);material.roughness=override.roughness??.8;material.metalness=override.metalness??0;material.emissive?.set(0);}
   const mesh=new T.InstancedMesh(geometry,material,list.length);mesh.name=`Citizens_${path}_${o.name}`;
   const temp=new T.Object3D();
   list.forEach((e,i)=>{
    temp.position.fromArray(e.position);temp.rotation.set(0,e.rotationY||0,0);temp.scale.setScalar(e.scale||1);temp.updateMatrix();
    mesh.setMatrixAt(i,temp.matrix.clone().multiply(o.matrixWorld));
    if(tint)mesh.setColorAt(i,new T.Color(crowd.palette[e.colorIndex||0]));
   });
   mesh.castShadow=mesh.receiveShadow=true;mesh.computeBoundingSphere();mesh.computeBoundingBox();staticRoot.add(mesh);staticMeshes.push(mesh);
  });
 }
 const target=new T.Vector3(),delta=new T.Vector3(),candidate=new T.Vector3();
 let playerWaits=0,pedestrianWaits=0;
 const setWaiting=(actor:Actor,reason:string,dt:number)=>{
  const waiting=!!reason;
  if(actor.waiting!==waiting){
   if(waiting&&actor.idle){actor.idle.reset().fadeIn(.18).play();actor.walk.fadeOut(.18);}
   if(!waiting){actor.walk.reset().fadeIn(.18).play();actor.idle?.fadeOut(.18);}
   if(waiting&&reason==='player')playerWaits++;
   if(waiting&&reason==='pedestrian')pedestrianWaits++;
  }
  actor.waiting=waiting;actor.waitReason=reason;actor.stoppedSeconds=waiting?actor.stoppedSeconds+dt:0;
 };
 const update=(dt:number,context:PedestrianContext={})=>{
  // Personal-space checks affect timing only. Authored lanes never become player collision walls.
  for(const actor of instances){
   const route=actor.e.path;
   if(!route?.length){actor.mixer.update(dt);continue;}
   let reason='';
   if(actor.dwell>0){actor.dwell=Math.max(0,actor.dwell-dt);reason='waypoint';}
   let remaining=(actor.e.speed??.7)*dt;
   for(let segment=0;segment<=route.length&&remaining>0&&!reason;segment++){
    target.fromArray(route[actor.pathIndex]);delta.copy(target).sub(actor.object.position);
    const distance=delta.length(),travel=Math.min(distance,remaining);
    if(distance>0)delta.divideScalar(distance);
    candidate.copy(actor.object.position).addScaledVector(delta,travel);
    const p=context.player;
    if(p&&Math.abs(p.y-actor.object.position.y)<1.8){
     const safe=(context.playerRadius??.32)+(actor.e.personalSpace??.58);
     const current=Math.hypot(actor.object.position.x-p.x,actor.object.position.z-p.z);
     const next=Math.hypot(candidate.x-p.x,candidate.z-p.z);
     if(next<safe&&next<=current)reason='player';
    }
    if(!reason)for(const other of instances){
      if(other===actor||Math.abs(other.object.position.y-actor.object.position.y)>1.5)continue;
      const current=Math.hypot(actor.object.position.x-other.object.position.x,actor.object.position.z-other.object.position.z);
      if(current>1.25)continue;
      const next=Math.hypot(candidate.x-other.object.position.x,candidate.z-other.object.position.z);
      if(next<.64&&next<current-.0001){reason='pedestrian';break;}
    }
    if(reason)break;
    actor.object.position.copy(candidate);remaining-=travel;
    if(travel>0)actor.object.rotation.y=Math.atan2(delta.x,delta.z);
    if(distance<=travel+1e-8){
     actor.dwell=Number(actor.e.waypointPauses?.[actor.pathIndex]??actor.e.pauseSeconds??0);
     actor.pathIndex=(actor.pathIndex+1)%route.length;
     if(actor.dwell>0)reason='waypoint';
    }
   }
   setWaiting(actor,reason,dt);
   actor.mixer.update(dt);
  }
 };
 let realizedTriangles=0,animatedMeshCount=0,allCastAndReceiveShadows=true;
 for(const mesh of staticMeshes){realizedTriangles+=(mesh.geometry.index?.count||mesh.geometry.attributes.position.count)/3*mesh.count;allCastAndReceiveShadows&&=mesh.castShadow&&mesh.receiveShadow;}
 for(const actor of instances)actor.object.traverse((o:any)=>{if(o.isMesh){animatedMeshCount++;realizedTriangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;allCastAndReceiveShadows&&=o.castShadow&&o.receiveShadow;}});
 if(realizedTriangles!==triangles)throw new Error('Character scene transfer lost source triangles.');
 const skeletons=new Set<T.Skeleton>();for(const actor of instances)actor.object.traverse((o:any)=>{if(o.isSkinnedMesh)skeletons.add(o.skeleton);});
 return {primitiveMerge,animatedMeshCount,count:entries.length,animatedCount:instances.length,uniqueSkeletons:skeletons.size,triangles:realizedTriangles,sourceTriangles:triangles,staticBatchCount:staticMeshes.length,allCastAndReceiveShadows,update,instances,staticRoot,
  activityStats:()=>({walking:instances.filter(a=>a.e.path?.length>1&&!a.waiting).length,stationary:instances.filter(a=>!a.e.path?.length).length,waiting:instances.filter(a=>a.waiting).length,playerWaits,pedestrianWaits,
   actors:instances.map(a=>({id:a.e.id,role:a.e.role,pathIndex:a.pathIndex,waiting:a.waitReason,stoppedSeconds:a.stoppedSeconds}))})};
}
