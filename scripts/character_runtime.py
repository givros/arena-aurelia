"""Read-only role exports from the exact canonical CharacterBase and managed wardrobe."""
import bpy, math, json, hashlib, sys, argparse
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

OUT=Path('E:/Dev/underwater-colony/artifacts/roman-arena/characters')
RUNTIME=OUT/'runtime'; RUNTIME.mkdir(exist_ok=True)
parser=argparse.ArgumentParser();parser.add_argument('--role',choices=['citizen','merchant','worker','noble','seated-spectator','guard','gladiator'])
options=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
source=Path(bpy.data.filepath); source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
rig=bpy.data.objects['CharacterRig']; body=bpy.data.objects['CharacterBase']
managed=[o for o in bpy.data.objects if o.type=='MESH' and o.get('codex_clothing')]
scale=1.8/1.0514808893203735
base_names=['CharacterBase','RomanTunic','LeatherBelt','HairCap','RomanSandals']
roles={
 'citizen':(base_names,'#B6AA87','standing'),
 'merchant':(base_names,'#AF7140','standing'),
 'worker':(base_names,'#8F8D75','standing'),
 'noble':(base_names,'#6D3158','standing'),
 'seated-spectator':(base_names,'#C9B78A','seated'),
 'guard':(base_names+['BronzeArmor','RomanHelmet','GuardShield','GuardSpear'],'#922F24','standing'),
 'gladiator':(base_names+['BronzeArmor','RomanHelmet','GuardShield','GladiatorSword'],'#9A4630','standing'),
}
def refresh():
    bpy.context.scene.update_tag();rig.update_tag();bpy.context.view_layer.update();bpy.context.evaluated_depsgraph_get().update()
def reset():
    if rig.animation_data:rig.animation_data.action=None
    for p in rig.pose.bones:
        p.matrix_basis=Matrix.Identity(4)
        for c in p.constraints:c.influence=0
    refresh()
def rotate(name,axis,degrees):
    b=rig.pose.bones[name];q=b.bone.matrix_local.to_quaternion()
    b.rotation_mode='QUATERNION';b.rotation_quaternion=q.inverted()@Quaternion(Vector(axis),math.radians(degrees))@q
def pose(kind):
    reset()
    for side,sign in [('L',1),('R',-1)]:
        rotate('upper_arm.'+side,(0,1,0),sign*(90 if kind=='seated' else 80))
        if kind!='seated':rotate('forearm.'+side,(1,0,0),-10)
        if kind=='seated':
            rotate('thigh.'+side,(1,0,0),-90)
            rotate('shin.'+side,(1,0,0),90)
    refresh()
    if kind=='seated':
        for side in ['L','R']:
            arm=rig.pose.bones['forearm.'+side];pivot=arm.head.copy()
            arm.matrix=Matrix.Translation(pivot)@Matrix.Rotation(math.radians(-70),4,'X')@Matrix.Translation(-pivot)@arm.matrix
        refresh()
        p=rig.pose.bones['pelvis'];p.matrix=Matrix.Translation((0,0,-0.246))@p.matrix;refresh()
def color_material(mat,hex_color):
    rgb=[int(hex_color[i:i+2],16)/255 for i in [1,3,5]]
    linear=[v/12.92 if v<0.04045 else ((v+0.055)/1.055)**2.4 for v in rgb]
    mat.diffuse_color=(*linear,1)
    if mat.use_nodes:
        p=mat.node_tree.nodes.get('Principled BSDF')
        if p:p.inputs['Base Color'].default_value=(*linear,1)
def extract(role,names,color,kind):
    pose(kind)
    for o in managed:
        rig[o.get('visibility_property','show_'+o.get('garment_id',''))]=True
        o.hide_set(False);o.hide_viewport=False;o.hide_render=False
        for prop in ['hide_viewport','hide_render']:
            try:o.driver_remove(prop)
            except:pass
    refresh()
    objects=[];deps=bpy.context.evaluated_depsgraph_get()
    for name in names:
        original=bpy.data.objects[name];evaluated=original.evaluated_get(deps)
        mesh=bpy.data.meshes.new_from_object(evaluated,preserve_all_data_layers=True,depsgraph=deps)
        obj=bpy.data.objects.new(role+'_'+name,mesh);bpy.context.collection.objects.link(obj)
        for v in mesh.vertices:
            if kind=='seated' and name=='RomanTunic':
                rest=original.data.vertices[v.index % len(original.data.vertices)].co
                if rest.z<0.598:
                    f=max(0,min(1,(0.598-rest.z)/0.203))
                    # A bent cloth skirt drapes over the thighs, without altering the canonical body.
                    v.co=Vector((rest.x,rest.y-f*0.235,(1-f)*0.352+f*(0.321-0.040*rest.y/0.100)))
                    if v.index>=len(original.data.vertices):v.co.z-=0.002
            v.co=(original.matrix_world@v.co)*scale
        if name=='RomanTunic':
            mat=mesh.materials[0].copy();mat.name=role+'_cloth';color_material(mat,color);mesh.materials[0]=mat
        obj['source_character']='CharacterBase';obj['source_blend_sha256']=source_hash;obj['role']=role
        objects.append(obj)
    zmin=min(v.co.z for o in objects if 'GuardSpear' not in o.name for v in o.data.vertices)
    # Feet are always the origin; held objects can extend beyond the body bounds.
    foot_min=min(v.co.z for o in objects if o.name.endswith('CharacterBase') or o.name.endswith('RomanSandals') for v in o.data.vertices)
    for o in objects:
        for v in o.data.vertices:v.co.z-=foot_min
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    path=RUNTIME/(role+'.glb')
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=False,export_apply=True,export_yup=True,export_extras=True,export_draco_mesh_compression_enable=False)
    verts=[v.co for o in objects for v in o.data.vertices]
    triangles=0
    for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    report={'asset':str(path),'role':role,'pose':kind,'source_blend_sha256':source_hash,'scale_from_exact_base':scale,
       'bounds_blender':[[min(v[a] for v in verts) for a in range(3)],[max(v[a] for v in verts) for a in range(3)]],
       'triangles':triangles,'source_base_triangles':3134,'instancing':'Merge geometries per material, preserve GLTF root transforms; standing height about 1.8m; forward is +Z in glTF.',
       'parts':names,'feet_ground_origin':True,'compressed':False}
    for o in objects:bpy.data.objects.remove(o,do_unlink=True)
    return report

reports=[extract(role,*data) for role,data in roles.items() if options.role is None or role==options.role]
if options.role and (RUNTIME/'role-manifest.json').exists():
    prior=json.loads((RUNTIME/'role-manifest.json').read_text())['roles']
    revised={item['role']:item for item in reports}
    reports=[revised.get(item['role'],item) for item in prior]
reset()
# Read-only evaluated role catalogue is independent of the editable canonical file.
assert hashlib.sha256(source.read_bytes()).hexdigest()==source_hash
(RUNTIME/'role-manifest.json').write_text(json.dumps({'passed':True,'source_blend':str(source),'source_sha256':source_hash,'roles':reports},indent=2))
print('CHARACTER_ROLE_EXPORTS',json.dumps(reports))
