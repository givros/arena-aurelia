"""Bake complete static Idle snapshots without editing the canonical character."""
from pathlib import Path
import bpy,json,hashlib,math
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parents[1];C=R/'characters';asset=C/'runtime/animated-citizen.glb'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
canonical_before=sha(C/'CharacterBase.blend');source_before=sha(asset);records=[]
for index,frame in enumerate([8,38,78,122]):
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(asset))
    rig=next(o for o in bpy.data.objects if o.type=='ARMATURE');action=next(a for a in bpy.data.actions if a.name.lower().split('.')[0]=='idle')
    rig.animation_data_create();rig.animation_data.action=action
    if hasattr(action,'slots') and len(action.slots):rig.animation_data.action_slot=action.slots[0]
    for track in rig.animation_data.nla_tracks:track.mute=True
    for bone in rig.pose.bones:bone.custom_shape=None
    helpers={o for o in bpy.data.objects if o.name.startswith('Icosphere')}
    bpy.context.scene.frame_set(frame)
    frozen={b.name:b.matrix_basis.copy() for b in rig.pose.bones};rig.animation_data.action=None
    for name,matrix in frozen.items():rig.pose.bones[name].matrix_basis=matrix
    bpy.context.view_layer.update()
    # Small editorial arm gestures make static conversations readable. These
    # affect only this in-memory pose; all canonical rest meshes/actions remain.
    def rotate_world(name,degrees):
        bone=rig.pose.bones[name];world=rig.matrix_world@bone.matrix;pivot=world.translation.copy()
        bone.matrix=rig.matrix_world.inverted()@Matrix.Translation(pivot)@Matrix.Rotation(math.radians(degrees),4,'X')@Matrix.Translation(-pivot)@world
        bpy.context.view_layer.update()
    gestures=[[],[('forearm.R',-76)],[('forearm.R',-65),('forearm.L',-70)],[('upper_arm.L',-22),('forearm.L',-80),('forearm.R',-38)]][index]
    for name,degrees in gestures:rotate_world(name,degrees)
    deps=bpy.context.evaluated_depsgraph_get()
    originals=[o for o in bpy.data.objects if o.type=='MESH' and o not in helpers];baked=[]
    for obj in originals:
        ev=obj.evaluated_get(deps);mesh=bpy.data.meshes.new_from_object(ev,preserve_all_data_layers=True,depsgraph=deps)
        mesh.transform(ev.matrix_world);result=bpy.data.objects.new('Ambient_'+obj.name,mesh);bpy.context.collection.objects.link(result);baked.append(result)
    shoes=next(o for o in baked if 'romansandals' in o.name.lower());z=min(v.co.z for v in shoes.data.vertices)
    for obj in baked:obj.data.transform(Matrix.Translation((0,0,-z)))
    body=next(o for o in baked if 'characterbase' in o.name.lower());body.data.calc_loop_triangles();assert len(body.data.loop_triangles)==3134
    triangle_count=0
    for obj in baked:obj.data.calc_loop_triangles();triangle_count+=len(obj.data.loop_triangles)
    assert triangle_count==5002
    gaps=[min(v.co.z for v in shoes.data.vertices if v.co.x*sign>0) for sign in [-1,1]]
    assert max(gaps)<.025,(index,gaps)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in baked:obj.select_set(True)
    target=C/'runtime'/f'citizen-idle-{index}.glb'
    bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_animations=False,export_skins=False,
        export_apply=True,export_draco_mesh_compression_enable=False,export_extras=True)
    points=[v.co for o in baked for v in o.data.vertices]
    records.append({'id':target.stem,'path':'runtime/'+target.name,'sha256':sha(target),'pose':['Relaxed Idle','Conversational right hand','Both hands forward at waist','Open left-hand explanation'][index],
        'basePose':'Bundled Idle frame '+str(frame),'editorialPoseOnlyArmRotations':gestures,
        'clip':'Idle','importedFPS':bpy.context.scene.render.fps,'frame':frame,'triangles':triangle_count,'bodyTriangles':3134,
        'shoeSoleGaps':gaps,'heightMeters':max(p.z for p in points)-min(p.z for p in points),
        'sourceAnimatedAssetSHA256':source_before,'meshSimplification':False,'compression':'none'})
assert sha(C/'CharacterBase.blend')==canonical_before and sha(asset)==source_before
report={'passed':True,'canonicalUnchanged':True,'canonicalSHA256':canonical_before,'animatedSourceUnchanged':True,
    'sourceAnimatedAssetSHA256':source_before,'fullCanonicalBodyPreserved':True,'assets':records}
(C/'ambient_pose_assets.json').write_text(json.dumps(report,indent=2));print('AMBIENT_POSES',json.dumps(report),flush=True)
