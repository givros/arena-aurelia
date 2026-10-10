import bpy,json
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
groups={}
for o in bpy.context.scene.objects:
    if o.type!='MESH':continue
    sem=str(o.get('semantic',''));name=o.name.split('/')[0]
    if sem.startswith('city/building/') or name.startswith('Tree_') or name in ['District_routes','Block_courtyard_boundaries']:
        pts=[o.matrix_world@Vector(p) for p in o.bound_box]
        groups.setdefault(name,[]).append({'name':o.name,'semantic':sem,'matrix':[list(r) for r in o.matrix_world],
          'lo':[min(p[i] for p in pts) for i in range(3)],'hi':[max(p[i] for p in pts) for i in range(3)],'mesh':o.data.name,'location':list(o.location)})
(R/'comparisons/master_world_source_groups.json').write_text(json.dumps(groups,indent=2))
print('MASTER_GROUP_QUERY',len(groups))
