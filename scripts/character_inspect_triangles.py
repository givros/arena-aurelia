"""Read-only audit of character GLB nodes versus Blender-imported rig helpers."""
import bpy,json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'Aurelia_Arena.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
collection=bpy.data.collections['CharacterLibrary/animated-citizen']
meshes=[]
for o in collection.objects:
    if o.type=='MESH':
        o.data.calc_loop_triangles()
        meshes.append({'name':o.name,'data':o.data.name,'triangles':len(o.data.loop_triangles),'hideRender':o.hide_render,'hideViewport':o.hide_viewport,'hideSet':o.hide_get(),'collections':[c.name for c in o.users_collection],
                       'customShapeFor':[p.name for rig in collection.objects if rig.type=='ARMATURE' for p in rig.pose.bones if p.custom_shape==o]})
report={'source':str(source),'sourceSHA256':before,'meshes':meshes,'sourceUnchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before}
(ROOT/'characters/triangle-inventory-inspection.json').write_text(json.dumps(report,indent=2))
print('TRIANGLE_INVENTORY',json.dumps(report))
