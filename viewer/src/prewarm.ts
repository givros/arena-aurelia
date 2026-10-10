import * as T from 'three/webgpu';

/** Prepare every authored main/shadow pipeline without changing the released scene. */
export async function prepareWorld(renderer:T.WebGPURenderer,scene:T.Scene,camera:T.Camera,progress:(text:string)=>void){
 const original:Array<{object:T.Object3D;culled:boolean;visible:boolean}>=[];
 scene.traverse(object=>{if((object as T.Mesh).isMesh)original.push({object,culled:object.frustumCulled,visible:object.visible});});
 const phases={compileMs:0,fullShadowWarmupMs:0,shadowBatches:0},start=performance.now();
 try{
  for(const entry of original)entry.object.frustumCulled=false;
  await (renderer.compileAsync as any)(scene,camera,undefined,(event:any)=>progress(`Preparing the complete district... ${Math.round(event.loaded/event.total*100)}%`));
  phases.compileMs=performance.now()-start;
  const shadowStart=performance.now(),visible=original.filter(entry=>entry.visible),byObject=new Map(original.map(entry=>[entry.object,entry]));
  for(const entry of visible)entry.object.visible=false;
  for(let index=0;index<visible.length;index+=64){
   const batch=visible.slice(index,index+64);
   const enabled=new Set<T.Object3D>();
   for(const entry of batch)for(let object:T.Object3D|null=entry.object;object;object=object.parent)if(byObject.get(object)?.visible)enabled.add(object);
   for(const object of enabled)object.visible=true;
   progress(`Preparing the district's shadows... ${Math.round(Math.min(index+64,visible.length)/visible.length*100)}%`);
   await new Promise<void>(resolve=>requestAnimationFrame(()=>resolve()));
   await renderer.renderAsync(scene,camera);
   await (renderer.backend as any).device.queue.onSubmittedWorkDone();
   for(const object of enabled)object.visible=false;
   phases.shadowBatches++;
  }
  phases.fullShadowWarmupMs=performance.now()-shadowStart;
 }finally{
  for(const entry of original){entry.object.frustumCulled=entry.culled;entry.object.visible=entry.visible;}
 }
 await renderer.renderAsync(scene,camera);
 await (renderer.backend as any).device.queue.onSubmittedWorkDone();
 return phases;
}
