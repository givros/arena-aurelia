"""Read-only GLB reimport and close QC for portable animated market carriers."""
import bpy,json,math,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'characters'
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=30;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
scene.render.resolution_x=1000;scene.render.resolution_y=750;scene.render.resolution_percentage=100
scene.world.color=(.25,.25,.25);scene.view_settings.view_transform='AgX'
reports=[]
for i,role in enumerate(['merchant','porter']):
    path=OUT/'runtime'/('animated-'+role+'.glb');before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(path));objects=list(set(bpy.data.objects)-before)
    rigs=[o for o in objects if o.type=='ARMATURE'];helpers={b.custom_shape for rig in rigs for b in rig.pose.bones if b.custom_shape}
    for rig in rigs:
        for b in rig.pose.bones:b.custom_shape=None
    for helper in helpers:
        if helper in objects:objects.remove(helper);bpy.data.objects.remove(helper,do_unlink=True)
    triangles=0;body=0
    for o in objects:
        if o.type=='MESH':
            o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
            if o.name.startswith('CharacterBase'):body+=len(o.data.loop_triangles)
    root=bpy.data.objects.new('QC '+role,None);scene.collection.objects.link(root)
    for o in objects:
        if o.parent is None:o.parent=root
    root.location.x=(i-.5)*1.2
    if i==1:root.rotation_euler.z=math.pi
    action=next(a for a in bpy.data.actions if a.name.lower().split('.')[0]=='walk')
    for rig in rigs:
        rig.animation_data_create();rig.animation_data.action=action
        if hasattr(action,'slots') and len(action.slots):rig.animation_data.action_slot=action.slots[0]
        for track in rig.animation_data.nla_tracks:track.mute=True
    samples=[]
    for frame in [1,8,15,22]:
        scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();all_points=[];body_points=[];ware_points=[]
        for o in objects:
            if o.type!='MESH':continue
            ev=o.evaluated_get(deps);points=[ev.matrix_world@v.co for v in ev.data.vertices];all_points.extend(points)
            if o.name.startswith('CharacterBase'):body_points.extend(points)
            if o.name.startswith('StreetWares'):ware_points.extend(points)
        samples.append({'frame':frame,'humanHeight':max(p.z for p in body_points)-min(p.z for p in body_points),
            'lowest':min(p.z for p in all_points),'waresBounds':[[min(p[k] for p in ware_points) for k in range(3)],[max(p[k] for p in ware_points) for k in range(3)]]})
    reports.append({'asset':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'triangles':triangles,'bodyTriangles':body,
        'bones':len(rigs[0].pose.bones),'samples':samples,'passed':body==3134 and len(rigs[0].pose.bones)==49 and all(1.65<s['humanHeight']<1.9 and abs(s['lowest'])<.06 for s in samples)})
scene.frame_set(8)
def material(name,color):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True;m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1);return m
bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.data.materials.append(material('QC ground',(.55,.54,.49)))
for pos,power,size in [((2,-4,6),1100,5),((-4,0,4),700,4)]:
    bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=power;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector((0,0,.8))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=(3.3,-6.5,3.1));cam=bpy.context.object;cam.rotation_euler=(Vector((0,0,.95))-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=3.8;scene.camera=cam
scene.render.filepath=str(OUT/'street_carriers_qc.png');bpy.ops.render.render(write_still=True)
report={'passed':all(r['passed'] for r in reports),'canonicalBlendUntouched':True,'assets':reports,'image':scene.render.filepath}
(OUT/'street_carriers_qc.json').write_text(json.dumps(report,indent=2));print('STREET_CARRIERS_QC',json.dumps(report),flush=True)
assert report['passed']
