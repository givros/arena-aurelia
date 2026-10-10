// Optional diagnostics. Sampling never changes scene quality or simulation.
export class PerformanceSampler {
 enabled = new URLSearchParams(location.search).has('profile');
 names=['frame','navigation','atmosphere','characters','interface','submission','callback'];
 capacity=12000; values=this.names.map(()=>new Float64Array(this.capacity));
 cursor=0; count=0; epoch=0; firstFrame=0; pending=false; gpu:number[]=[]; longTasks:any[]=[];
 observer:PerformanceObserver|null=null;
 constructor(){if(this.enabled&&PerformanceObserver.supportedEntryTypes.includes('longtask')){this.observer=new PerformanceObserver(list=>{for(const e of list.getEntries())this.longTasks.push({start:e.startTime,duration:e.duration});});this.observer.observe({type:'longtask'});}}
 clear(renderer:any){this.cursor=this.count=0;this.epoch++;this.firstFrame=renderer.info.frame+1;this.gpu.length=this.longTasks.length=0;}
 record(samples:number[],renderer:any){if(!this.enabled)return;for(let i=0;i<samples.length;i++)this.values[i][this.cursor]=samples[i];this.cursor=(this.cursor+1)%this.capacity;this.count=Math.min(this.count+1,this.capacity);if(renderer.backend.trackTimestamp&&!this.pending&&renderer.info.frame%24===0){const epoch=this.epoch;this.pending=true;renderer.resolveTimestampsAsync('render').then(()=>{if(epoch!==this.epoch)return;const pool=renderer.backend.timestampQueryPool.render,frames=new Map<number,number>();for(const [id,duration]of pool?.timestamps||[]){const frame=Number(id.match(/:f(\d+)$/)?.[1]);if(frame>=this.firstFrame)frames.set(frame,(frames.get(frame)||0)+duration);}this.gpu.push(...frames.values());}).finally(()=>{this.pending=false;});}}
 snapshot(renderer:any){return {enabled:this.enabled,gpuTimestampSupported:!!renderer.backend.trackTimestamp,samples:Object.fromEntries(this.names.map((name,i)=>[name,Array.from({length:this.count},(_,n)=>this.values[i][(this.cursor-this.count+n+this.capacity)%this.capacity])])),gpuRenderMs:this.gpu.slice(),longTasks:this.longTasks.slice(),heap:(performance as any).memory?{used:(performance as any).memory.usedJSHeapSize,total:(performance as any).memory.totalJSHeapSize,limit:(performance as any).memory.jsHeapSizeLimit}:null};}
 dispose(){this.observer?.disconnect();}
}
