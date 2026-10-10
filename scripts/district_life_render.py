"""Render named district cameras from the saved editable source without mutating it."""
from pathlib import Path
import bpy,sys,json,hashlib
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['final']
tag=args[0]
loaded_source_hash=hashlib.sha256((R/'Aurelia_Arena.blend').read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
s=bpy.context.scene;s.frame_set(1);s.cycles.samples=32
override_path=R/'district_review_views.json'
overrides=json.loads(override_path.read_text()).get('cameras',{}) if override_path.exists() else {}
names=args[1:] or list(json.loads((R/'district_life_layout.json').read_text())['cameras'])
evidence=[]
for name in names:
    assert bpy.data.objects.get('CAM_'+name),name
    camera=bpy.data.objects['CAM_'+name]
    if name in overrides:
        view=overrides[name]
        camera.location=view['position'];camera.data.lens=view['lens']
        camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
    B.render(name,f'district_life_{tag}_{name}.png',100)
    evidence.append({'name':name,'position':list(camera.location),'rotationEuler':list(camera.rotation_euler),'lens':camera.data.lens})
    print('DISTRICT_CAMERA_DONE',tag,name,flush=True)
(R/'comparisons'/f'district_render_{tag}_cameras.json').write_text(json.dumps({'sourceSHA256':loaded_source_hash,'cameras':evidence},indent=2))
