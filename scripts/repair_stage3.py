import bpy,sys,json,bmesh
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1]
bpy.ops.wm.open_mainfile(filepath=str(R/'checkpoints/current.blend'))
sys.path.insert(0,str(R/'scripts'));import build_arena as B
B.mats()
o=bpy.data.objects.get('ARENA/Foundation ring')
if o:
    for v in o.data.vertices:
        if v.co.z>-.01:v.co.z=-.025
for me in bpy.data.meshes:
    bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
for name,filename in [('Travertine • weathered warm limestone','travertine.png'),('Worn plaza slabs','paving.png'),('Compacted ochre arena sand','sand.png')]:
    m=bpy.data.materials.get(name);p=m.node_tree.nodes.get('Principled BSDF');n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(R/'textures'/filename),check_existing=True);m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color']);m['map']=filename
    bump=m.node_tree.nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.22;bump.inputs['Distance'].default_value=.065;m.node_tree.links.new(n.outputs['Color'],bump.inputs['Height']);m.node_tree.links.new(bump.outputs['Normal'],p.inputs['Normal'])
    m['bumpMap']=filename;m['bumpScale']=.025
sp=json.loads((R/'scene_spec.json').read_text());sp['cameras']['reference']={'position':[38,-266,163],'target':[0,16,8],'lens':44};(R/'scene_spec.json').write_text(json.dumps(sp,indent=2))
o=bpy.data.objects['CAM_reference'];o.location=(38,-266,163);o.rotation_euler=(Vector((0,16,8))-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=44
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'));B.render('reference','checkpoint_03_refined.png')
