import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];p=R/'district_review_views.json';d=json.loads(p.read_text());s=bpy.context.scene;s.frame_set(1);deps=bpy.context.evaluated_depsgraph_get();source=R/'Aurelia_Arena.blend';sha=hashlib.sha256(source.read_bytes()).hexdigest()
for name,v in d['cameras'].items():
 x,y=v['position'][:2];hit,loc,normal,idx,obj,matrix=s.ray_cast(deps,Vector((x,y,.4)),Vector((0,0,-1)),distance=3)
 assert hit and normal.z>.5,(name,hit,normal,obj.name if obj else None)
 headroom=[]
 for i in range(9):
  dx=0 if i==8 else .32*math.cos(math.tau*i/8);dy=0 if i==8 else .32*math.sin(math.tau*i/8)
  blocked,hl,hn,hi,ho,hm=s.ray_cast(deps,Vector((x+dx,y+dy,loc.z+.065)),Vector((0,0,1)),distance=1.985)
  if blocked:headroom.append({'object':ho.name,'position':list(hl),'sample':[dx,dy]})
 assert not headroom,(name,headroom)
 v['headroom']={'sampleRays':9,'radius':.32,'minimumClearHeight':2.05,'hits':headroom}
 v['groundZ']=loc.z;v['position'][2]=loc.z+1.72;v['actualSupportPending']=False;v['actualSourceSupport']={'object':obj.name,'position':list(loc),'normal':list(normal)}
d['sourceSHA256']=sha;d['sourceUnchanged']=hashlib.sha256(source.read_bytes()).hexdigest()==sha;assert d['sourceUnchanged'];p.write_text(json.dumps(d,indent=2));print('REVIEW_VIEWS_READY',len(d['cameras']),sha)
