"""Read-only uncompressed animated citizen for the local viewer."""
import bpy,json,hashlib
import sys
from pathlib import Path
ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena/characters')
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
rig=bpy.data.objects['CharacterRig'];scale=1.8/1.0514808893203735
names=['CharacterBase','RomanTunic','LeatherBelt','HairCap','RomanSandals']
bpy.ops.object.select_all(action='DESELECT')
for o in bpy.data.objects:
    if o.type=='MESH' and o.get('codex_clothing'):
        for p in ['hide_render','hide_viewport']:
            try:o.driver_remove(p)
            except:pass
        o.hide_viewport=False;o.hide_render=False;o.hide_set(False)
    o.select_set(o.name in names or o==rig)
rig.scale=(scale,scale,scale);rig.location.z=-0.0033749055583029985*scale
bpy.context.view_layer.objects.active=rig
path=ROOT/'runtime'/'animated-citizen.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='ACTIONS',export_anim_single_armature=True,export_bake_animation=True,export_frame_range=False,export_force_sampling=True,export_apply=True,export_yup=True,export_extras=True,export_draco_mesh_compression_enable=False)
sys.path.insert(0,str(Path(__file__).parent))
from character_normalize_animation import normalize_animated_glb
normalize_animated_glb(path)
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
(ROOT/'runtime'/'animated-report.json').write_text(json.dumps({'passed':True,'source_sha256':before,'asset':str(path),'clips':['Idle','Walk','Run','Jump'],'scale':scale,'source_unchanged':True},indent=2))
