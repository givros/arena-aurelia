"""Read-only obstacle evidence for the ceremonial facade detour."""
import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
records=[]
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.get('collision','solid') in ['none',False]:continue
    p=[o.matrix_world@Vector(v) for v in o.bound_box]
    lo=[min(v[i] for v in p) for i in range(3)];hi=[max(v[i] for v in p) for i in range(3)]
    if hi[0]<-30 or lo[0]>30 or hi[1]<-100 or lo[1]>-78 or lo[2]>2 or hi[2]<.22:continue
    if hi[0]-lo[0]>45 or hi[1]-lo[1]>25:continue
    records.append({'name':o.name,'lo':lo,'hi':hi})
(R/'comparisons/south_forecourt_obstacles.json').write_text(json.dumps(records,indent=2))
print('SOUTH_OBSTACLES',json.dumps(records),flush=True)
