"""Save street review cameras while proving all non-camera scene objects unchanged."""
from pathlib import Path
import bpy,json,hashlib,struct,shutil
from mathutils import Vector

R=Path(__file__).resolve().parents[1]
source=R/'Aurelia_Arena.blend'
backup=R/'checkpoints/15_before_review_cameras.blend'
before_hash=hashlib.sha256(source.read_bytes()).hexdigest()
if not backup.exists():shutil.copy2(source,backup)
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.scene.frame_set(1)
views=json.loads((R/'district_review_views.json').read_text())['cameras']

def signature(obj):
    h=hashlib.sha256(obj.name.encode())
    h.update(struct.pack('<16f',*[v for row in obj.matrix_world for v in row]))
    if obj.type=='MESH':
        for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
        for p in obj.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
        h.update('|'.join(m.name if m else '' for m in obj.data.materials).encode())
    if obj.instance_type=='COLLECTION' and obj.instance_collection:h.update(obj.instance_collection.name.encode())
    return h.hexdigest()

before={o.name:signature(o) for o in bpy.context.scene.objects if o.type!='CAMERA'}
for name,view in views.items():
    camera=bpy.data.objects['CAM_'+name]
    camera.location=view['position'];camera.data.lens=view['lens']
    camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
after={o.name:signature(o) for o in bpy.context.scene.objects if o.type!='CAMERA'}
assert before==after,'Non-camera source content changed'
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'passed':True,'previousSourceSHA256':before_hash,'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'protectedNonCameraObjects':len(before),'changedNonCameraObjects':[],
    'cameraAuthority':'district_review_views.json','cameraAuthoritySHA256':hashlib.sha256((R/'district_review_views.json').read_bytes()).hexdigest(),
    'changedCameras':list(views),'reason':'Review views follow active lanes instead of looking directly into shaded shop entrances.'}
(R/'comparisons/district_review_camera_integration.json').write_text(json.dumps(report,indent=2))
print('STREET_REVIEW_CAMERAS_SAVED',json.dumps(report),flush=True)
