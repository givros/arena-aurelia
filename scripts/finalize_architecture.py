import bpy,sys,json,bmesh,math
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
bpy.ops.wm.open_mainfile(filepath=str(R/'checkpoints/current.blend'));B.mats()
# Clear the tall cross-aisle edges from all stair slots while keeping each real promenade.
for o in list(bpy.data.objects):
    if o.name.startswith('CAVEA/Cross aisle'):bpy.data.objects.remove(o,do_unlink=True)
for row in [8,16,24]:
    r=73.3+row*.86+(1.8 if row>=8 else 0)+(1.8 if row>=16 else 0);z=(5.15+(row-1)*.74)*1.3
    for sec in range(16):B.arc(f'CAVEA/Cross aisle clear{row}_{sec}',r,r-23,r-1.8,r-24.8,z-.364,z,2*math.pi*sec/16+.025,2*math.pi*(sec+1)/16-.025,'stone','Seating',n=12)
# Last imperial stair treads meet a shortened horizontal landing without a tall blocking edge.
for o in bpy.data.objects:
    if o.name.startswith('VIP/Side access bridge'):
        o.location.x=math.copysign(9.5,o.location.x);o.scale.x=.75
B.box('CITY/Temple approach landing',(10,146.5,6),(27,1.6,12),'stone',collection='City_Infrastructure')
# Foreground rim is clear stone in the reference; shade canvas remains rear and flanking.
for o in list(bpy.data.objects):
    if o.name.startswith('VELARIUM/Canvas panel'):
        try:i=int(o.name.split('panel')[-1])
        except:continue
        if 18<=i<=29:bpy.data.objects.remove(o,do_unlink=True)
# Lower framing reflects the longer facade while leaving room for foreground market life.
views={
 'seating':((68.1,-51.8,29.3),(0,22,9),30),
 'floor':((30,-25,2.12),(0,59,21),24),
 'market':((29,-111,1.72),(-41,-123,4),30),
 'vip':((6,49,9),(0,60,27),28),
 'hypogeum':((20,-11,-3.88),(0,4,-3.7),24)
}
for name,(p,t,lens) in views.items():
    o=bpy.data.objects['CAM_'+name];o.location=p;o.rotation_euler=(Vector(t)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens
# Consistent outward normals for new masonry solids, excluding authoritative human assets.
seen=set()
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.get('runtime_skip') or o.data.as_pointer() in seen:continue
    seen.add(o.data.as_pointer());bm=bmesh.new();bm.from_mesh(o.data);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(o.data);bm.free()
bpy.context.scene.frame_set(1);bpy.context.scene.render.resolution_percentage=100
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
print('FINAL_ARCHITECTURE_READY',flush=True)
