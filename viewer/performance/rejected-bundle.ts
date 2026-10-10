import * as T from 'three/webgpu';

export function preserveNestedBundleOwnership(renderer:any){
 // Three r186 restores render context during nested shadow passes but omits
 // the active bundle owner. Preserve it so every captured object participates
 // in later uniform refreshes, including camera and day/night changes.
 if(T.REVISION!=='186')throw new Error('Render bundle adapter requires revalidation for this Three.js revision.');
 const renderScene=renderer._renderScene;
 renderer._renderScene=function(...args:any[]){const owner=this._currentRenderBundle;try{return renderScene.apply(this,args);}finally{this._currentRenderBundle=owner;}};
}

// Retain exact meshes/materials. Only reusable opaque GPU command lists are cached.
// Camera and sun-frustum membership are tracked independently; a changed member
// invalidates both cached passes before either pass is submitted.
export class StaticBundles {
 enabled=false; groups:any[]=[]; members:T.Mesh[][]=[]; masks:Uint8Array[]=[]; invalidations=0;
 mainFrustum=new T.Frustum();shadowFrustum=new T.Frustum();projection=new T.Matrix4();
 constructor(public scene:T.Scene,public camera:T.Camera,public sun:T.DirectionalLight,roots:T.Object3D[]){
  const buckets=new Map<string,{parent:T.Object3D,meshes:T.Mesh[]}>();
  for(const root of roots){const meshes:T.Mesh[]=[];root.traverse((o:any)=>{if(o.isMesh&&!o.isSkinnedMesh&&!Array.isArray(o.material)&&!o.material.transparent&&(!o.material.emissive||o.material.emissive.getHex()===0))meshes.push(o);});
   for(const mesh of meshes){mesh.geometry.computeBoundingBox();const center=((mesh as any).boundingBox||mesh.geometry.boundingBox!).getCenter(new T.Vector3()).applyMatrix4(mesh.matrixWorld);const key=`${root.uuid}|${Math.floor(center.x/90)},${Math.floor(center.z/90)}`;if(!buckets.has(key))buckets.set(key,{parent:root,meshes:[]});buckets.get(key)!.meshes.push(mesh);}
  }
  for(const {parent,meshes}of buckets.values()){
   const group:any=new T.Group();group.name='StaticCommandGroup';group.static=false;group.version=0;group.isBundleGroup=false;parent.add(group);
   for(const mesh of meshes){group.attach(mesh);mesh.updateMatrixWorld(true);mesh.matrixAutoUpdate=false;mesh.matrixWorldAutoUpdate=false;}
   group.updateMatrixWorld(true);group.matrixAutoUpdate=false;group.matrixWorldAutoUpdate=false;
   this.groups.push(group);this.members.push(meshes);this.masks.push(new Uint8Array(meshes.length).fill(255));
  }
 }
 setEnabled(enabled:boolean){this.enabled=enabled;for(const group of this.groups){group.isBundleGroup=enabled;group.static=enabled;group.version++;}for(const mask of this.masks)mask.fill(255);}
 invalidate(){for(const group of this.groups)group.version++;for(const mask of this.masks)mask.fill(255);}
 update(){if(!this.enabled)return;this.camera.updateMatrixWorld();this.sun.updateMatrixWorld();this.sun.target.updateMatrixWorld();this.sun.shadow.updateMatrices(this.sun);const shadowCamera=this.sun.shadow.camera;
  this.projection.multiplyMatrices(this.camera.projectionMatrix,this.camera.matrixWorldInverse);this.mainFrustum.setFromProjectionMatrix(this.projection,this.camera.coordinateSystem,this.camera.reversedDepth);
  this.projection.multiplyMatrices(shadowCamera.projectionMatrix,shadowCamera.matrixWorldInverse);this.shadowFrustum.setFromProjectionMatrix(this.projection,shadowCamera.coordinateSystem,shadowCamera.reversedDepth);
  for(let i=0;i<this.groups.length;i++){let changed=false;const mask=this.masks[i];for(let j=0;j<this.members[i].length;j++){const mesh=this.members[i][j] as any;const value=(mesh.visible&&(mesh.frustumCulled===false||mesh.intersectsFrustum(this.mainFrustum))?1:0)|(mesh.visible&&mesh.castShadow&&(mesh.frustumCulled===false||mesh.intersectsFrustum(this.shadowFrustum))?2:0);if(mask[j]!==value){mask[j]=value;changed=true;}}if(changed){this.groups[i].version++;this.invalidations++;}}
 }
 stats(){return {enabled:this.enabled,groups:this.groups.length,meshes:this.members.reduce((n,m)=>n+m.length,0),invalidations:this.invalidations};}
}
