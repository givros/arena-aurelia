"""Re-export only neutral GLB with the skill's exact preparation and no compression."""
import bpy,sys,json,hashlib,struct,importlib.util
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]/'characters'
source=ROOT/'CharacterBase.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
assert Path(bpy.data.filepath).resolve()==source.resolve()
report_path=ROOT/'reports/CharacterBase_export.json';report=json.loads(report_path.read_text())
assert before==report['source_blend_sha256_after']
module_path=Path('C:/Users/limou/.codex/skills/blender-lowpoly-character/scripts/export/export_character_assets.py')
spec=importlib.util.spec_from_file_location('skill_character_exporter',module_path);exporter=importlib.util.module_from_spec(spec);spec.loader.exec_module(exporter)
rig=bpy.data.objects[report['rig']];meshes=[bpy.data.objects[n] for n in report['mesh_objects']]
snapshot=exporter.snapshot_scene_state(rig,meshes)
try:
    exporter.prepare_objects_for_export(rig,meshes)
    exporter.replace_bone_weights_with_top_four(meshes,rig)
    animation=rig.animation_data_create();animation.action=None
    for track in animation.nla_tracks:track.mute=True
    rig.data.pose_position='REST';bpy.context.scene.frame_set(0);bpy.context.view_layer.update()
    exporter.select_objects([rig,*meshes],rig)
    options=dict(report['files']['tpose_glb']['options'])
    options['filepath']=str(ROOT/'CharacterBase.glb');options['export_draco_mesh_compression_enable']=False
    for key in list(options):
        if key.startswith('export_draco_') and key!='export_draco_mesh_compression_enable':del options[key]
    bpy.ops.export_scene.gltf(**options)
finally:exporter.restore_scene_state(snapshot,rig,meshes)
asset=ROOT/'CharacterBase.glb';data=asset.read_bytes();size=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+size])
assert not any('draco' in e.lower() or 'meshopt' in e.lower() for e in gltf.get('extensionsRequired',[]))
assert not gltf.get('animations') and len(gltf['meshes'])==10
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
report['files']['tpose_glb']={'path':str(asset),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'draco':False,'options':options}
report['source_blend_sha256_after']=before;report['source_saved']=False
report_path.write_text(json.dumps(report,indent=2))
print('NEUTRAL_GLB_UNCOMPRESSED',json.dumps(report['files']['tpose_glb']))
