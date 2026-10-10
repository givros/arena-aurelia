import bpy,sys,json,math,random
from math import cos,sin
from pathlib import Path
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'));B.mats()
from market_refinement import refine_market
meta=refine_market(B,B.SPEC);(R/'market_refinement_registry.json').write_text(json.dumps(meta,indent=2))
# Darker, less regular cloth and warm stone preserve reference color hierarchy.
for key,color in [('faded',(.30,.076,.038)),('red',(.26,.026,.018)),('light',(.66,.56,.40)),('warm',(.44,.33,.21))]:
    m=B.M[key];m.diffuse_color=(*color,1);m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*color,1)
for o in bpy.data.objects:
    if o.name.startswith('VELARIUM/Canvas panel'):
        i=int(o.name.split('panel')[-1]);o.data.materials[0]=B.M['linen' if i%5==0 else 'faded']
# Continuous masonry risers close visible slots beneath the seating while preserving every tread.
seen=set()
for o in bpy.data.objects:
    if o.type=='MESH' and o.name.startswith('CAVEA/Sector') and '/Row' in o.name and o.data.as_pointer() not in seen:
        seen.add(o.data.as_pointer());z=min(v.co.z for v in o.data.vertices)
        for v in o.data.vertices:
            if abs(v.co.z-z)<.0001:v.co.z-=.12
# The last seven actual stair treads remain open under the final concourse lip.
for o in list(bpy.data.objects):
    if o.name.startswith('CONCOURSE/Annular floor') and o.location.z+max(v.co.z*o.scale.z for v in o.data.vertices)>30:bpy.data.objects.remove(o,do_unlink=True)
for s in range(16):
    a=2*math.pi*s/16
    B.arc('CONCOURSE/Upper gallery clear',103.1,80.1,97.6,74.6,31.018,31.304,a+.025,a+2*math.pi/16-.025,'stone','Circulation',n=14)
    B.arc('CONCOURSE/Upper stair landing',103.1,80.1,102.0,79.0,31.018,31.304,a-.025,a+.025,'stone','Circulation',n=3)
# Stone ornament: dentils, rosette medallions, and recessed podium panels.
for i in range(128):
    a=2*math.pi*i/128;x,y=B.ellipse_pos(a,106.8,83.8);rot=B.angle_frame(a)
    for z in [14.85,30.02]:B.box(f'ORNAMENT/Dentil{i}_{z}',(x,y,z),(.40,.68,.38),'light',rot,collection='Ornament',collision='none')
for i in range(64):
    a=2*math.pi*(i+.5)/64;x,y=B.ellipse_pos(a,106.1,83.1)
    # Mounted disks use local front normal, not unsupported floating geometry.
    o=B.cylinder('ORNAMENT/Laurel boss',(x,y,15.95),.43,.16,'gold',16,collection='Ornament',collision='none');o.rotation_euler=Vector((cos(a),sin(a),0)).to_track_quat('Z','Y').to_euler()
for i in range(16):
    a=2*math.pi*(i+.5)/16;x,y=B.ellipse_pos(a,70.05,47.05);rot=B.angle_frame(a)
    B.box('PODIUM/Inset framed panel',(x,y,3.2),(3.8,.15,3.2),'warm',rot,collection='Ornament',collision='none')
    for dx in [-2.05,2.05]:
        p=B.localpos((x,y),rot,(dx,-.02,3.2));B.box('PODIUM/Panel border',p,(.16,.2,3.5),'light',rot,collection='Ornament',collision='none')
# Enlarge selected combat machinery while retaining the open fighting space.
for o in bpy.data.objects:
    if o.name.startswith('SANDS/Cage'):
        o.location.x=43+(o.location.x-43)*1.45;o.location.y=11+(o.location.y-11)*1.45;o.location.z=.4+(o.location.z-.4)*1.25;o.scale.x*=1.45;o.scale.y*=1.45;o.scale.z*=1.25
    if o.name.startswith('SANDS/Combat marker'):
        o.location.z=.4+(o.location.z-.4)*1.4;o.scale*=1.4
for o in list(bpy.data.objects):
    if o.name.startswith('SANDS/Old spectacle stain'):bpy.data.objects.remove(o,do_unlink=True)
m=B.M['sand'];p=m.node_tree.nodes['Principled BSDF']
for link in list(m.node_tree.links):
    if link.to_node==p and link.to_socket.name in ['Base Color','Normal']:m.node_tree.links.remove(link)
t=m.node_tree.nodes.new('ShaderNodeTexImage');t.image=bpy.data.images.load(str(R/'textures/arena_sand_atlas.png'),check_existing=True);m.node_tree.links.new(t.outputs['Color'],p.inputs['Base Color']);m['map']='arena_sand_atlas.png'
if 'bumpMap' in m:del m['bumpMap']
for o in bpy.data.objects:
    if o.name.startswith('SANDS/Deck_'):
        me=o.data;uv=me.uv_layers.active or me.uv_layers.new(name='ArenaAtlasUV')
        for loop in me.loops:
            v=me.vertices[loop.vertex_index].co;uv.data[loop.index].uv=(v.x/140+.5,v.y/94+.5)
# Warmer angled sunlight reveals the structural depth rather than flattening it.
for i in range(24):
    if i<16:
        a=2*math.pi*(i+.5)/16;x,y=B.ellipse_pos(a,104.1,81.1);base=31.304
    else:
        a=2*math.pi*(i-16+.5)/8;x,y=B.ellipse_pos(a,111.6,88.6);base=0
    B.box(f'BRAZIER/District{i}/foot',(x,y,base+.14),(.8,.8,.28),'light',collection='Ornament')
    B.cylinder(f'BRAZIER/District{i}/stem',(x,y,base+.78),.22,1.0,'iron',12,collection='Ornament')
    B.cylinder(f'BRAZIER/District{i}/bowl',(x,y,base+1.42),.63,.34,'iron',16,r2=.82,collection='Ornament')
    B.cylinder(f'BRAZIER/District{i}/coals',(x,y,base+1.60),.71,.035,'flame',16,collection='Ornament',collision='none')
    for j in range(5):
        q=2*math.pi*j/5;B.cylinder(f'BRAZIER/District{i}/flame{j}',(x+.37*cos(q),y+.37*sin(q),base+1.83),.12,.47,'flame',7,r2=.015,collection='Ornament',collision='none')
    ld=bpy.data.lights.new(f'District brazier {i}','POINT');ld.energy=550;ld.color=(1,.32,.07);ld.shadow_soft_size=.65
    lo=bpy.data.objects.new(f'District brazier {i}',ld);lo.location=(x,y,base+2.0);lo['distance']=28;B.coll('Lighting').objects.link(lo)
s=bpy.context.scene;s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.40
bpy.data.lights['Afternoon sun'].energy=3.0;bpy.data.lights['Afternoon sun'].color=(1,.92,.79)
s.view_settings.exposure=.0
# A slightly wider master includes more of the foreground assemblies and urban background.
o=bpy.data.objects['CAM_reference'];o.data.lens=41.5;o.rotation_euler=(Vector((0,-5,8))-o.location).to_track_quat('-Z','Y').to_euler()
for name,loc,target,lens in [('vip',(7,54,20.44),(0,61,21.9),28),('market',(39,-128,1.72),(64,-134,3),30)]:
    o=bpy.data.objects['CAM_'+name];o.location=loc;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();o.data.lens=lens
sp=json.loads((R/'scene_spec.json').read_text());sp['cameras']['reference']['lens']=41.5;sp['cameras']['reference']['target']=[0,-5,8];sp['viewer']['spawn']=[0,-119,1.72];sp['arena']['seatingPopulation']=12000;(R/'scene_spec.json').write_text(json.dumps(sp,indent=2))
# Persistent source dependencies are embedded in the editable world.
bpy.ops.file.pack_all();s.frame_set(1)
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'));bpy.ops.wm.save_as_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
print('ART_REFINEMENT_COMPLETE',flush=True)
