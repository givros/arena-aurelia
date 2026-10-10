import bpy,sys,json,bmesh
from pathlib import Path
from math import pi,cos,sin
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
bpy.ops.wm.open_mainfile(filepath=str(R/'checkpoints/current.blend'));B.mats()
# Replace the solid loggia foundation with real supporting side walls around the ceremonial route.
old=bpy.data.objects.get('VIP/Foundation')
if old:bpy.data.objects.remove(old,do_unlink=True)
for side in [-1,1]:B.box(f'VIP/Load bearing side{side}',(side*6.4,60,6.9),(4.0,13,13.8),'warm',collection='Imperial')
for o in list(bpy.data.objects):
    if o.name.startswith('VIP/Side balustrade') or o.name.startswith('STAIRS/Lower'):bpy.data.objects.remove(o,do_unlink=True)
for side in [-1,1]:
    B.box('VIP/Side access bridge',(side*10,59,14.1),(4,3,.6),'light',collection='Imperial')
    for y in [55,63.5]:B.box('VIP/Balustrade segment',(side*8.3,y,15.2),(.6,3,1.6),'light',collection='Imperial')
# Two lower flights sit away from the east service ramp; the remaining podium gates stay clear.
for sec in [2,10]:
    a=2*pi*sec/16
    for j in range(20):
        r=62.6+j*.535;z=.4+(j+1)*.2375
        B.arc(f'STAIRS/Lower{sec}/{j}',r+.535,r-23+.535,r,r-23,z-.25,z,a-.025,a+.025,'light','Circulation',n=3)
    B.arc(f'STAIRS/Lower threshold{sec}',62.7,39.7,62.0,39.0,.28,.46,a-.025,a+.025,'light','Circulation',n=3)
# Scale architecture only; terrain, sand, humans and underground retain human-scale datums.
for name in ['Facade','Masonry','Seating','Podium','Circulation','Imperial','Foundations']:
    c=bpy.data.collections.get(name)
    if c:
        for o in c.objects:
            o.location.z*=1.3;o.scale.z*=1.3
for i,x in enumerate([-28,0,28]):
    ld=bpy.data.lights.new(f'Hypogeum lamp{i}','POINT');ld.energy=400;ld.color=(1,.48,.18);ld.shadow_soft_size=1.5;o=bpy.data.objects.new(ld.name,ld);B.coll('Lighting').objects.link(o);o.location=(x,0,-1.8);o['distance']=24
    B.cylinder('HYPOGEUM/Brazier base',(x,8,-5.2),.6,.8,'stone',collection='HypogeumProps')
    B.cylinder('HYPOGEUM/Fire bowl',(x,8,-4.58),.8,.4,'iron',collection='HypogeumProps')
    B.cylinder('HYPOGEUM/Coals',(x,8,-4.35),.65,.09,'flame',collection='HypogeumProps',collision='none')
# All solid meshes outward-facing; this also corrects side spandrel winding.
seen=set()
for o in bpy.data.objects:
    if o.type!='MESH' or o.data.as_pointer() in seen:continue
    seen.add(o.data.as_pointer());me=o.data;bm=bmesh.new();bm.from_mesh(me);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(me);bm.free()
sp=json.loads((R/'scene_spec.json').read_text());sp['arena']['height']=34.3;sp['arena']['verticalRefinement']=1.3;sp['arena']['vipCenter']=[0,59,18.72];sp['cameras']['reference']={'position':[38,-266,163],'target':[0,-15,8],'lens':44};(R/'scene_spec.json').write_text(json.dumps(sp,indent=2))
o=bpy.data.objects['CAM_reference'];o.rotation_euler=(Vector((0,-15,8))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
B.render('reference','checkpoint_07_refined.png');B.render('hypogeum','checkpoint_07_hypogeum.png')
