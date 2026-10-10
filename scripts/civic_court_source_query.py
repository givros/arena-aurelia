import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];out=[]
for o in bpy.context.scene.objects:
 if o.type!='MESH' or not o.name.startswith('Tree_'):continue
 vs=[o.matrix_world@Vector(v) for v in o.bound_box];lo=[min(v[i] for v in vs) for i in range(3)];hi=[max(v[i] for v in vs) for i in range(3)]
 if hi[0]>140 and lo[0]<200 and hi[1]>108 and lo[1]<150:out.append({'id':o.name,'lo':lo,'hi':hi})
(R/'comparisons/civic_court_tree_bounds.json').write_text(json.dumps(out,indent=2));print('TREE_BOUNDS',len(out))
