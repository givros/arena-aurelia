"""Verify actual saved district transforms and complete projections against final authority."""
from pathlib import Path
from collections import defaultdict
import bpy,sys,json,math,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
source=R/'Aurelia_Arena.blend';digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
layout=json.loads((R/'district_life_layout.json').read_text())
review_path=R/'district_review_views.json'
review_views=json.loads(review_path.read_text()).get('cameras',{}) if review_path.exists() else {}
groups=defaultdict(list)
district_ids={item['id'] for item in layout['items']}
for obj in bpy.context.scene.objects:
    if obj.type=='MESH' and obj.get('assembly_id') in district_ids:groups[obj['assembly_id']].append(obj)
errors=[]
for item in layout['items']:
    a=item['rotation'];ca,sa=math.cos(a),math.sin(a);w,d=item['full_dimensions'];x,y=item['center']
    objects=groups[item['id']]
    if not objects:errors.append({'id':item['id'],'error':'Missing complete assembly'})
    for obj in objects:
        if (obj.location-Vector((x,y,item['ground_z']))).length>.001 or abs(obj.rotation_euler.z-a)>.0001:
            errors.append({'id':item['id'],'object':obj.name,'error':'Transform differs from authority'})
        for corner in obj.bound_box:
            p=obj.matrix_world@Vector(corner);u=(p.x-x)*ca+(p.y-y)*sa;v=-(p.x-x)*sa+(p.y-y)*ca
            if abs(u)>w/2+.035 or abs(v)>d/2+.035:errors.append({'id':item['id'],'object':obj.name,'error':'Complete projection exceeds parcel'})
for name,view in layout['cameras'].items():
    view=review_views.get(name,view)
    obj=bpy.data.objects.get('CAM_'+name)
    if obj is None or (obj.location-Vector(view['position'])).length>.001:errors.append({'id':name,'error':'Camera authority mismatch'})
result={'passed':not errors,'sourceSHA256':digest,'layoutSHA256':hashlib.sha256((R/'district_life_layout.json').read_bytes()).hexdigest(),
        'assembliesTested':len(layout['items']),'camerasTested':len(layout['cameras']),'failures':errors,
        'reviewCameraAuthoritySHA256':hashlib.sha256(review_path.read_bytes()).hexdigest() if review_path.exists() else None,
        'uniqueDistrictMeshes':len({o.data.as_pointer() for group in groups.values() for o in group}),
        'fullMeshInstances':sum(len(g) for g in groups.values()),'sourceUnchanged':digest==hashlib.sha256(source.read_bytes()).hexdigest()}
(R/'comparisons/district_life_saved_geometry.json').write_text(json.dumps(result,indent=2))
print('SAVED_DISTRICT_GEOMETRY',json.dumps(result),flush=True)
assert result['passed'] and result['sourceUnchanged']
