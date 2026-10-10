import bpy,json
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
R=Path(__file__).resolve().parents[1];bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
p=Vector((-103.58742,-95.65385,0));deps=bpy.context.evaluated_depsgraph_get();records=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or o.get('runtime_skip') or o.hide_render:continue
 points=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[k] for v in points) for k in range(3)];hi=[max(v[k] for v in points) for k in range(3)]
 if not(lo[0]-.01<=p.x<=hi[0]+.01 and lo[1]-.01<=p.y<=hi[1]+.01 and lo[2]<2 and hi[2]>-10):continue
 ev=o.evaluated_get(deps);output={'name':o.name,'collision':o.get('collision'),'bounds':[lo,hi],'vertices':len(o.data.vertices),'faces':len(o.data.polygons),'modifiers':[(m.name,m.type) for m in o.modifiers]}
 for label,ob in [('data',o),('evaluated',ev)]:
  tree=BVHTree.FromPolygons([ob.matrix_world@v.co for v in ob.data.vertices],[list(poly.vertices) for poly in ob.data.polygons])
  hit,normal,index,distance=tree.ray_cast(p+Vector((0,0,.35)),Vector((0,0,-1)),20)
  output[label]={'hit':list(hit) if hit else None,'normal':list(normal) if normal else None,'face':index,'distance':distance}
 records.append(output)
print('GROUND_DEBUG',json.dumps(records,indent=2),flush=True)
(R/'characters/street_ground_debug.json').write_text(json.dumps(records,indent=2))
