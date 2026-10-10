"""Integrate the additive citywide life revision with preservation checks."""
from pathlib import Path
import bpy, sys, json, hashlib, struct, importlib, shutil

R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B

def signature(obj):
    h=hashlib.sha256()
    h.update(obj.name.encode())
    h.update(struct.pack('<16f',*[v for row in obj.matrix_world for v in row]))
    if obj.type=='MESH':
        for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
        for p in obj.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
    if obj.instance_type=='COLLECTION' and obj.instance_collection:
        h.update(obj.instance_collection.name.encode())
    return h.hexdigest()

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['geometry']
stage=args[0]
source=R/'Aurelia_Arena.blend'
backup=R/'checkpoints/13_before_district_life.blend'
if not backup.exists():
    shutil.copy2(source,backup)
    for rel in ['characters/runtime/crowd_manifest.json','scene_spec.json','source_reopen_validation.json']:
        shutil.copy2(R/rel,R/'checkpoints'/('13_before_district_life_'+Path(rel).name))
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.scene.frame_set(1)
B.mats()
earth=bpy.data.materials.get('Continuous Mediterranean earth')
if earth and earth.use_nodes:
    for node in earth.node_tree.nodes:
        if node.type=='TEX_IMAGE':
            node.image=bpy.data.images.load(str(R/'textures/mediterranean_earth.png'),check_existing=False)
            node.image.pack()
before={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
if stage=='geometry':
    result=importlib.import_module('district_life_geometry').apply(B)
    # The original oblique gate camera fell inside a relocated house.
    from mathutils import Vector
    gate_camera=bpy.data.objects.get('CAM_district_south_gate')
    if gate_camera:
        gate_camera.location=(0,-207,1.685);gate_camera.data.lens=25
        gate_camera.rotation_euler=(Vector((0,-229,5.5))-gate_camera.location).to_track_quat('-Z','Y').to_euler()
elif stage=='population':
    result=importlib.import_module('district_life_population').apply_population(R)
    # Camera-only refinements can follow the geometry pass without moving any mesh.
    from mathutils import Vector
    for name,view in json.loads((R/'district_life_layout.json').read_text()).get('cameras',{}).items():
        camera=bpy.data.objects.get('CAM_'+name)
        if camera:
            camera.location=view['position'];camera.data.lens=view['lens']
            camera.rotation_euler=(Vector(view['target'])-camera.location).to_track_quat('-Z','Y').to_euler()
        else:B.camera(name,view['position'],view['target'],view['lens'])
    gate_camera=bpy.data.objects.get('CAM_district_south_gate')
    if gate_camera:
        gate_camera.location=(0,-207,1.685);gate_camera.data.lens=25
        gate_camera.rotation_euler=(Vector((0,-229,5.5))-gate_camera.location).to_track_quat('-Z','Y').to_euler()
    interior_path=R/'arena_interior_life_layout.json'
    if interior_path.exists():
        for view in json.loads(interior_path.read_text()).get('cameraCandidates',[]):
            if not bpy.data.objects.get('CAM_'+view['id']):
                B.camera(view['id'],view['position'],view['target'],view.get('lens',28))
else:raise ValueError(stage)
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
after={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
changed=[n for n,h in before.items() if after.get(n)!=h]
assert not changed, f'Existing source components changed: {changed[:20]}'
bpy.context.scene['district_life_revision']=stage
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'stage':stage,'preservedComponents':len(before),'changedExistingComponents':changed,
        'newComponents':len(set(after)-set(before)),'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'result':result}
(R/'comparisons'/f'district_life_{stage}_integration.json').write_text(json.dumps(report,indent=2,default=str))
print('DISTRICT_LIFE_INTEGRATED',stage,len(before),report['newComponents'],flush=True)
