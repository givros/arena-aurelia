import bpy, math, json, os, sys, argparse, random, hashlib, struct
from mathutils import Vector, Matrix
from pathlib import Path
from math import sin, cos, pi, sqrt, atan2

ROOT=Path(__file__).resolve().parents[1]
SPEC=json.loads((ROOT/'scene_spec.json').read_text())
RNG=random.Random(SPEC['seed'])
TAU=2*pi
CACHE={}

def coll(name):
    c=bpy.data.collections.get(name)
    if not c:
        c=bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c

def material(name,color,rough=.8,metal=0,emission=0,texture=None):
    m=bpy.data.materials.get(name)
    if m:return m
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;p.inputs['Metallic'].default_value=metal
    if emission:
        p.inputs['Emission Color'].default_value=(*color,1);p.inputs['Emission Strength'].default_value=emission
    if texture:
        n=m.node_tree.nodes.new('ShaderNodeTexImage');n.image=bpy.data.images.load(str(ROOT/'textures'/texture),check_existing=True);m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
        m['map']=texture
    return m

def mats():
    global M
    M={
    'stone':material('Travertine • weathered warm limestone',(.63,.52,.37),.86,texture='travertine.png' if (ROOT/'textures/travertine.png').exists() else None),
    'light':material('Carved ivory cornice',(.76,.66,.48)),
    'warm':material('Golden limestone',(.58,.43,.27)),
    'darkstone':material('Sheltered stone',(.39,.33,.24)),
    'mortar':material('Deep masonry joints',(.27,.25,.21)),
    'paving':material('Worn plaza slabs',(.49,.44,.35),texture='paving.png' if (ROOT/'textures/paving.png').exists() else None),
    'sand':material('Compacted ochre arena sand',(.67,.48,.26),texture='sand.png' if (ROOT/'textures/sand.png').exists() else None),
    'red':material('Imperial crimson linen',(.31,.031,.026),.88),
    'faded':material('Faded vermilion canvas',(.48,.16,.09),.9),
    'linen':material('Natural flax canvas',(.65,.53,.36),.98),
    'gold':material('Antique brass',(.6,.34,.075),.38,.68),
    'wood':material('Dark oak',(.19,.095,.036)),
    'woodlight':material('Worn cedar',(.35,.18,.068)),
    'iron':material('Forged black iron',(.085,.079,.064),.52,.7),
    'terracotta':material('Terracotta amphora',(.42,.19,.093)),
    'blood':material('Muted old combat stains',(.23,.085,.042),1),
    'flame':material('Brazier coals',(.99,.29,.035),.55,0,4),
    'leaves':material('Laurel olive green',(.18,.235,.075)),
    'water':material('Fountain water',(.08,.19,.16),.23,.25)
    }

def mesh(name,verts,faces,mat='stone',collection='Arena',collision='solid',uv=True):
    key=(tuple(tuple(round(float(q),6) for q in v) for v in verts),tuple(tuple(f) for f in faces),mat if isinstance(mat,str) else mat.name)
    h=hash(key)
    me=CACHE.get(h)
    if me is None:
        me=bpy.data.meshes.new(name+'_mesh');me.from_pydata(verts,[],faces);me.update()
        me.materials.append(M[mat] if isinstance(mat,str) else mat)
        if uv:
            layer=me.uv_layers.new(name='SurfaceUV')
            for poly in me.polygons:
                no=poly.normal;axis=max(range(3),key=lambda i:abs(no[i]))
                axes=([1,2] if axis==0 else [0,2] if axis==1 else [0,1])
                for li in poly.loop_indices:
                    v=me.vertices[me.loops[li].vertex_index].co;layer.data[li].uv=(v[axes[0]]/4,v[axes[1]]/4)
        CACHE[h]=me
    obj=bpy.data.objects.new(name,me);coll(collection).objects.link(obj);obj['semantic']=name;obj['collision']=collision
    return obj

def box(name,loc,scale,mat='stone',rot=0,collection='Arena',collision='solid'):
    x,y,z=[q/2 for q in scale]
    vs=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    fs=[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    o=mesh(name,vs,fs,mat,collection,collision);o.location=loc;o.rotation_euler.z=rot;return o

def cylinder(name,loc,radius,depth,mat='stone',vertices=16,r2=None,collection='Arena',collision='solid'):
    if r2 is None:r2=radius
    vs=[(r*cos(TAU*i/vertices),r*sin(TAU*i/vertices),z) for z,r in [(-depth/2,radius),(depth/2,r2)] for i in range(vertices)]
    fs=[tuple(range(vertices-1,-1,-1)),tuple(range(vertices,2*vertices))]+[(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
    o=mesh(name,vs,fs,mat,collection,collision);o.location=loc;return o

def beam(name,a,b,width,mat='wood',collection='Arena',collision='none'):
    a=Vector(a);b=Vector(b);o=box(name,(a+b)/2,(width,width,(b-a).length),mat,collection=collection,collision=collision);o.rotation_euler=(b-a).to_track_quat('Z','Y').to_euler();return o

def arc(name,rx,ry,rinx,riny,z0,z1,a0=0,a1=TAU,mat='stone',collection='Arena',n=None,collision='solid'):
    n=n or max(4,int((a1-a0)/TAU*256))
    vs=[]
    for z in [z0,z1]:
        for r1,r2 in [(rx,ry),(rinx,riny)]:
            vs +=[(r1*cos(a0+(a1-a0)*i/n),r2*sin(a0+(a1-a0)*i/n),z) for i in range(n+1)]
    p=n+1;fs=[]
    for i in range(n):
        fs.extend([(i,i+1,i+1+p,i+p),(i+2*p,i+3*p,i+3*p+1,i+2*p+1),(i,i+2*p,i+2*p+1,i+1),(i+p,i+p+1,i+3*p+1,i+3*p)])
    fs.extend([(0,p,3*p,2*p),(n,n+2*p,n+3*p,n+p)])
    return mesh(name,vs,[tuple(reversed(f)) for f in fs],mat,collection,collision)

def ellipse_pos(a,rx=106,ry=83):return (rx*cos(a),ry*sin(a))
def angle_frame(a,rx=106,ry=83):return atan2(ry*cos(a),-rx*sin(a))
def localpos(center,rot,p):return (center[0]+p[0]*cos(rot)-p[1]*sin(rot),center[1]+p[0]*sin(rot)+p[1]*cos(rot),p[2])

def arch(name,center,rot,width,spring,height,depth,bay,mat='stone',collection='Facade',collision='solid',segments=14):
    # Real open arch with voussoirs, full depth and spandrels up to shared floor datum.
    r=width/2;th=.55;zbase=center[2];rout=r+th
    for side in [-1,1]:
        pier=(bay-width)/2
        p=localpos(center,rot,(side*(width/2+pier/2),0,zbase+spring/2))
        box(name+f'/pier_{side}',p,(pier,depth,spring),mat,rot,collection,collision)
    for j in range(segments):
        a0=pi*j/segments+.003;a1=pi*(j+1)/segments-.003
        vs=[(r0*cos(a),y,zbase+spring+r0*sin(a)) for y in [-depth/2,depth/2] for r0 in [r,rout] for a in [a0,a1]]
        fs=[(0,1,3,2),(4,6,7,5),(0,4,5,1),(2,3,7,6),(0,2,6,4),(1,5,7,3)]
        o=mesh(name+f'/voussoir_{j:02}',vs,fs,'light' if j==segments//2 else mat,collection,collision);o.location=(center[0],center[1],0);o.rotation_euler.z=rot
    # Upper spandrel surfaces accurately follow arch extrados, not a blocking box.
    for side in [-1,1]:
        xs=[rout*i/12 for i in range(13)];points=[(side*x,zbase+spring+sqrt(max(0,rout*rout-x*x))) for x in xs]
        points += [(side*bay/2,zbase+spring),(side*bay/2,zbase+height),(0,zbase+height)]
        vs=[(x,y,z) for y in [-depth/2,depth/2] for x,z in points];l=len(points)
        fs=[tuple(range(l-1,-1,-1)),tuple(range(l,2*l))]+[(i,(i+1)%l,(i+1)%l+l,i+l) for i in range(l)]
        o=mesh(name+f'/spandrel_{side}',vs,fs,mat,collection,collision);o.location=(center[0],center[1],0);o.rotation_euler.z=rot

def column(name,x,y,z,height,radius=.45,mat='light',collection='Facade'):
    box(name+'/plinth',(x,y,z+.18),(radius*2.65,radius*2.65,.36),mat,collection=collection)
    cylinder(name+'/base',(x,y,z+.52),radius*1.2,.32,mat,16,collection=collection)
    cylinder(name+'/shaft',(x,y,z+height/2),radius,height-1.15,mat,16,r2=radius*.89,collection=collection)
    cylinder(name+'/neck',(x,y,z+height-.53),radius*1.14,.25,mat,16,collection=collection)
    box(name+'/capital',(x,y,z+height-.20),(radius*2.65,radius*2.65,.40),mat,collection=collection)

def setup():
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats();s=bpy.context.scene;s.unit_settings.system='METRIC';s.render.engine='CYCLES';s.cycles.samples=24
    s.cycles.use_denoising=True
    try:
        p=bpy.context.preferences.addons['cycles'].preferences;p.compute_device_type='OPTIX';p.get_devices()
        for d in p.devices:d.use=d.type!='CPU'
        s.cycles.device='GPU'
    except Exception:pass
    s.render.resolution_x=1456;s.render.resolution_y=1088;s.render.resolution_percentage=70
    s.world.color=(.23,.28,.36);s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.60,.70,.86,1);s.world.node_tree.nodes['Background'].inputs['Strength'].default_value=.55
    ld=bpy.data.lights.new('Afternoon sun','SUN');lo=bpy.data.objects.new('Afternoon sun',ld);coll('Lighting').objects.link(lo);ld.energy=3.2;ld.angle=.12;lo.rotation_euler=(math.radians(28),math.radians(-28),math.radians(-28))
    s.view_settings.view_transform='AgX';s.view_settings.look='AgX - Medium High Contrast';s.view_settings.exposure=.1
    for name,cs in SPEC['cameras'].items():camera(name,cs['position'],cs['target'],cs.get('lens',38))
    camera('floor',[31,-25,2.12],[0,58,17],30);camera('facade',[39,-89,1.72],[15,-80,14],24)
    camera('seating',[65,-44,17.5],[0,30,10],26);camera('hypogeum',[23,-19,-3.88],[0,9,-4],24)
    camera('market',[27,-112,1.72],[10,-83,17],29);camera('reverse',[0,133,85],[0,0,10],36)
    camera('vip',[0,46,8],[0,60,19],28)

def camera(name,pos,target,lens=40):
    data=bpy.data.cameras.new(name);o=bpy.data.objects.new('CAM_'+name,data);coll('Cameras').objects.link(o);o.location=pos;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler();data.lens=lens;data.clip_end=3000
    return o

def stage1():
    # The central surface owner excludes the full sand opening and underground space.
    arc('PLAZA/Foundation',148,126,69.9,46.9,-.7,0,mat='paving',collection='Ground',n=256)
    for rx,ry in [(114,91),(132,109)]:arc('PLAZA/Paving border',rx+.22,ry+.22,rx-.22,ry-.22,.004,.018,mat='light',collection='Ground',collision='none')
    # Individual paving courses at foreground approach give close scale without noisy scatter.
    for j in range(20):
        for i in range(-8,9):
            x=i*2.1+(j%2)*1.05;y=-87-j*2.0
            if (x/108)**2+(y/85)**2>1:box(f'PLAZA/Slab_{j}_{i}',(x,y,.006),(2.04,1.94,.012),'paving',collection='Ground',collision='none')

def stage2():
    arc('ARENA/Foundation ring',108,85,70,47,-.6,-.025,mat='stone',collection='Foundations')
    arc('ARENA/Facade stylobate',107.3,84.3,103.1,80.1,0,.20,mat='light',collection='Foundations')
    arc('ARENA/Podium footprint',73.5,50.5,70,47,0,.22,mat='light',collection='Foundations')

def stage3():
    N=64
    for floor,z0 in [(0,.20),(1,12.0)]:
        for i in range(N):
            a=TAU*i/N;x,y=ellipse_pos(a,104.5,81.5);rot=angle_frame(a,104.5,81.5)
            tang=sqrt((104.5*sin(a))**2+(81.5*cos(a))**2);bay=tang*TAU/N+.08
            opening=bay*.64
            arch(f'FACADE/L{floor}/B{i:02}',(x,y,z0),rot,opening,5.65 if floor==0 else 5.35,11.25,3.2,bay,segments=14)
            # Proud pilaster/column stack at the inter-bay pier.
            a2=a+pi/N;px,py=ellipse_pos(a2,106.35,83.35)
            column(f'FACADE/L{floor}/Column{i:02}',px,py,z0+.3,10.6,.42 if floor==0 else .35)
            # Coherent block joints on the outer pier faces.
            for j in range(1,9):
                p=localpos((px,py),angle_frame(a2),(0,-.19,z0+j*1.12))
                box(f'FACADE/L{floor}/Joint{i}_{j}',p,(1.38,.023,.025),'mortar',angle_frame(a2),collision='none',collection='Masonry')
    for z,extra,th in [(11.55,.35,.24),(11.88,.7,.22),(23.4,.35,.26),(23.78,.85,.34),(24.3,.45,.28)]:
        arc('FACADE/Continuous cornice',106+extra,83+extra,102,79,z,z+th,mat='light',collection='Facade')
    for z in [0,11.7,24.08]:arc('CONCOURSE/Annular floor',103.1,80.1,97.6,74.6,z-.22,z,mat='stone',collection='Circulation')
    arc('FACADE/Attic parapet',106,83,104.9,81.9,24.58,26.1,mat='light',collection='Facade')
    arc('FACADE/Parapet coping',106.3,83.3,104.6,81.6,26.1,26.38,mat='light',collection='Facade')
    for i in range(64):
        a=TAU*(i+.5)/64;x,y=ellipse_pos(a,105.5,82.5)
        box(f'FACADE/Attic pedestal_{i}',(x,y,26.35),(1.2,1.2,1.05),'light',rot=a,collection='Facade')
    # Inner ground arcade reveals real lower ambulatory behind the outer arch openings.
    for i in range(32):
        a=TAU*i/32;x,y=ellipse_pos(a,96,73);rot=angle_frame(a,96,73);tang=sqrt((96*sin(a))**2+(73*cos(a))**2);bay=tang*TAU/32
        arch(f'AMBULATORY/Inner arch{i}',(x,y,0),rot,5.2,3.3,8.2,1.0,bay,'darkstone','Circulation',segments=12)

def stage4():
    # Twenty-four actual tread/riser solids separated by sixteen stair aisles.
    for row in range(24):
        radius=73.3+row*.86+(1.8 if row>=8 else 0)+(1.8 if row>=16 else 0)
        z=5.15+row*.74
        for sec in range(16):
            a0=TAU*sec/16+.020;a1=TAU*(sec+1)/16-.020
            arc(f'CAVEA/Sector{sec:02}/Row{row:02}',radius+.86,radius-23+.86,radius,radius-23,z-.62,z, a0,a1,'stone','Seating',n=9)
            # Front coping is thin, physical, walkable at the matching step level.
            arc(f'CAVEA/Sector{sec:02}/Nosing{row:02}',radius+.16,radius-23+.16,radius,radius-23,z,z+.06,a0,a1,'light','Seating',n=9)
    for row in [8,16,24]:
        radius=73.3+row*.86+(1.8 if row>=8 else 0)+(1.8 if row>=16 else 0)
        z=5.15+(row-1)*.74
        arc('CAVEA/Cross aisle',radius,radius-23,radius-1.8,radius-24.8,z-.28,z,mat='stone',collection='Seating')
        # Balustrades follow tiers but leave gaps at radial aisles.
        for sec in range(16):
            a0=TAU*sec/16+.024;a1=TAU*(sec+1)/16-.024
            arc(f'CAVEA/Terrace parapet{row}_{sec}',radius-.05,radius-23.05,radius-.30,radius-23.30,z,z+.65,a0,a1,'light','Seating',n=10)
    # Raker supports leave generous interior corridors below the seating.
    for sec in range(16):
        a=TAU*(sec+.5)/16
        v=[]
        for da in [-.008,.008]:
            for r,z in [(73.5,.2),(73.5,4.5),(99,23.0),(99,.2)]:v.append((r*cos(a+da),(r-23)*sin(a+da),z))
        mesh(f'CAVEA/Raker wall{sec}',v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],'darkstone','Seating')
    # Imperial box replaces the central north seat region with a complete supported loggia.
    box('VIP/Foundation',(0,60,6.9),(17,13,13.8),'warm',collection='Imperial')
    arch('VIP/Arena triumphal gate',(0,52.95,.4),0,5.8,5.6,12.6,2.0,16,'stone','Imperial')
    box('VIP/Viewing balcony',(0,52.4,13.5),(19,4,.6),'light',collection='Imperial')
    box('VIP/Loggia floor',(0,60,14.0),(19,15,.8),'light',collection='Imperial')
    for x in [-8.2,8.2]:
        for y in [53.5,66.0]:column(f'VIP/Corinthian{x}_{y}',x,y,14.4,9.0,.58,'light','Imperial')
    box('VIP/Back wall',(0,66.9,18.7),(18,1.0,8.6),'warm',collection='Imperial')
    box('VIP/Entablature',(0,60,23.65),(20,15,.75),'light',collection='Imperial')
    for x in [-8.3,8.3]:box('VIP/Side balustrade',(x,58,15.2),(.6,10,1.6),'light',collection='Imperial')

def stage5():
    # Sand deck tiled into real polygons, omitting the open service ramp and grate.
    # Polar triangulation is clipped around the rectangular service cutout by grid cells.
    step=2
    for ix in range(-35,35):
        for iy in range(-24,24):
            x0,x1=ix*step,(ix+1)*step;y0,y1=iy*step,(iy+1)*step
            if x0>=46 and x1<=64 and y0>=-4 and y1<=4:continue
            if x0>=-6 and x1<=6 and y0>=-4 and y1<=4:continue
            poly=[(x0,y0),(x1,y0),(x1,y1),(x0,y1)]
            # Sutherland-Hodgman clip each square to 128-sided elliptical arena.
            if (min(abs(x0),abs(x1))/70)**2+(min(abs(y0),abs(y1))/47)**2>1.06:continue
            for k in range(128):
                a=TAU*k/128;b=TAU*(k+1)/128;p=(70*cos(a),47*sin(a));q=(70*cos(b),47*sin(b));out=[]
                for j,s in enumerate(poly):
                    e=poly[(j+1)%len(poly)];ds=(q[0]-p[0])*(s[1]-p[1])-(q[1]-p[1])*(s[0]-p[0]);de=(q[0]-p[0])*(e[1]-p[1])-(q[1]-p[1])*(e[0]-p[0])
                    if ds>=0:out.append(s)
                    if (ds>=0)!=(de>=0):t=ds/(ds-de);out.append((s[0]+t*(e[0]-s[0]),s[1]+t*(e[1]-s[1])))
                poly=out
                if not poly:break
            if len(poly)>=3:mesh(f'SANDS/Deck_{ix}_{iy}',[(x,y,.4) for x,y in poly],[tuple(range(len(poly)))],'sand','Sand',collision='walkable')
    for i in range(-6,7):box('SANDS/Hypogeum iron grate',(i,0,.38),(.12,8,.20),'iron',collection='ArenaFloor')
    for j in range(-4,5):box('SANDS/Hypogeum crossbar',(0,j,.37),(12,.11,.22),'iron',collection='ArenaFloor')
    for sec in range(16):
        a=TAU*sec/16;x,y=ellipse_pos(a,71.7,48.7);rot=angle_frame(a,71.7,48.7);tang=sqrt((71.7*sin(a))**2+(48.7*cos(a))**2);bay=tang*TAU/16
        arch(f'PODIUM/Gate{sec}',(x,y,.4),rot,4.0,2.25,4.7,2.6,bay,'stone','Podium',segments=12)
        # Vertical stone pilasters align to the gate corners.
        for off in [-2.5,2.5]:
            p=localpos((x,y),rot,(off,-1.45,.4));column(f'PODIUM/Pilaster{sec}_{off}',*p,4.4,.27,'light','Podium')
    arc('PODIUM/Inner coping',73.3,50.3,70.2,47.2,5.05,5.3,mat='light',collection='Podium')

def stage6():
    # Real staircase treads connect the floor gates to the cavea and the upper concourse.
    for sec in range(16):
        a=TAU*sec/16
        # inner short flight rises along the clear aisle from arena level to row one.
        for j in range(20) if sec in [0,8] else []:
            r=62.6+j*.535;z=.4+(j+1)*.2375
            arc(f'STAIRS/Lower{sec}/{j}',r+.535,r-23+.535,r,r-23,z-.25,z,a-.018,a+.018,'light','Circulation',n=2)
        # 72 modest risers rather than the tall seat risers.
        for j in range(72):
            t=j/72;r=73.3+t*24.2;z=5.15+(j+1)*(17.25/72)
            arc(f'STAIRS/Cavea{sec}/{j}',r+.36,r-23+.36,r,r-23,z-.28,z,a-.018,a+.018,'light','Circulation',n=2)
        # An annular outer landing bridges into upper promenade at z24.08.
        for j in range(7):
            r=97.5+j*.65;z=22.4+(j+1)*.24
            arc(f'STAIRS/Upper{sec}/{j}',r+.65,r-23+.65,r,r-23,z-.27,z,a-.018,a+.018,'light','Circulation',n=2)
    # Clear radial tunnels at ground beneath raised seating. Vault rings are actual geometry.
    for sec in [0,4,8,12]:
        a=TAU*sec/16
        for j in range(7):
            r=75+j*3.7;x,y=ellipse_pos(a,r,r-23);rot=angle_frame(a,r,r-23)
            arch(f'TUNNEL/{sec}/Rib{j}',(x,y,0),rot,5.6,3.5,7.0,.55,7.0,'darkstone','Circulation',segments=12)
        # Clear wall signs/rosettes above accessible passage.
    # Tangential lower-to-middle stairs inside four covered corridors, real switchback.
    for side in [-1,1]:
        x=side*86
        for j in range(48):
            y=-18+j*.63;z=(j+1)*.245
            box(f'STAIRS/Ambulatory_{side}_{j}',(x,y,z-.16),(3.2,.66,.32),'stone',collection='Circulation')
        box('STAIRS/Middle landing',(x,12.8,11.62),(4,4,.3),'stone',collection='Circulation')
    # VIP has connected stairs from the middle north terrace.
    for side in [-1,1]:
        for j in range(13):
            x=side*(10.8+j*.39);z=14.4-j*.25
            box(f'VIP/Access stair{side}_{j}',(x,59,z-.15),(.42,3.0,.3),'light',collection='Imperial')

def stage7():
    floor=-5.6
    box('HYPOGEUM/Continuous foundation',(4,0,floor-.3),(94,66,.6),'darkstone',collection='Hypogeum')
    # Four peripheral walls retain earth; generous central aisles connect all rooms.
    for y in [-31,31]:box('HYPOGEUM/Retaining wall',(4,y,-2.8),(94,1.2,5.6),'darkstone',collection='Hypogeum')
    box('HYPOGEUM/West retaining wall',(-43,0,-2.8),(1.2,62,5.6),'darkstone',collection='Hypogeum')
    for y in [-19,19]:
        for x in [-32,-19,-6,7,20,33]:
            arch(f'HYPOGEUM/Room portal{x}_{y}',(x,y,floor),0,3.2,2.3,5.1,1.0,12.9,'darkstone','Hypogeum',segments=10)
            box(f'HYPOGEUM/Room partition{x}_{y}',(x-6.45,y+(5 if y>0 else -5),-3),(1.0,10,5.2),'darkstone',collection='Hypogeum')
    for x in [-35,-21,-7,7,21,35]:
        # Open service cross vault sequence.
        arch(f'HYPOGEUM/Cross rib{x}',(x,0,floor),pi/2,11,1.5,5.4,.7,14,'darkstone','Hypogeum',segments=16)
    # East ramp enters a clearly visible arena opening, slope 6/18, body-safe headroom.
    v=[(46,-3.4,-5.6),(46,3.4,-5.6),(64,-3.4,.4),(64,3.4,.4),(46,-3.4,-6.1),(46,3.4,-6.1),(64,-3.4,-.1),(64,3.4,-.1)]
    mesh('HYPOGEUM/Gladiator ramp',v,[(0,2,3,1),(4,5,7,6),(0,4,6,2),(1,3,7,5),(0,1,5,4),(2,6,7,3)],'stone','Hypogeum')
    for side in [-1,1]:
        v=[(46,side*3.7,-5.6),(64,side*3.7,.4),(64,side*3.7,1.3),(46,side*3.7,-4.7)]
        mesh('HYPOGEUM/Ramp guard',v,[(0,1,2,3)],'light','Hypogeum')
    # Cell gates and prep furnishings retain open entries and a wide circulation spine.
    for x in [-32,-19,-6]:
        for j in range(9):box('HYPOGEUM/Holding cell bars',(x-1.4+j*.35,19.1,-3.55),(.06,.06,3.4),'iron',collection='HypogeumProps',collision='none')
    for x in [7,20,33]:
        box('HYPOGEUM/Preparation bench',(x,24,-4.7),(7,1.2,.32),'wood',collection='HypogeumProps')
        for s in [-2.6,2.6]:box('HYPOGEUM/Bench support',(x+s,24,-5.13),(.3,1.1,.9),'wood',collection='HypogeumProps')
    for x in [-32,-19,7,20]:
        box('HYPOGEUM/Supply crate',(x,-25,-4.9),(1.5,1.3,1.4),'woodlight',collection='HypogeumProps')
    for x in [-25,0,25]:
        cylinder('HYPOGEUM/Machinery drum',(x,9,-4.1),.8,2.5,'wood',12,collection='HypogeumProps')
        for dx in [-1.3,1.3]:box('HYPOGEUM/Hoist post',(x+dx,9,-2.8),(.3,.3,5.4),'wood',collection='HypogeumProps')
        beam('HYPOGEUM/Hoist header',(x-1.7,9,-.5),(x+1.7,9,-.5),.3,'wood','HypogeumProps')

def stage8():
    # Correct underground vault extrados: every rib stays below the sand deck.
    for o in list(bpy.data.objects):
        if o.name.startswith('HYPOGEUM/Cross rib'):bpy.data.objects.remove(o,do_unlink=True)
    for x in [-35,-21,-7,7,21,35]:arch(f'HYPOGEUM/Cross rib{x}',(x,0,-5.6),pi/2,8.4,.5,5.1,.7,14,'darkstone','Hypogeum',segments=16)
    o=bpy.data.objects['CAM_hypogeum'];o.location=(20,-11,-3.88);o.rotation_euler=(Vector((0,4,-3.7))-o.location).to_track_quat('-Z','Y').to_euler()
    # Broad public approaches, monument bases and market courts remain unobstructed.
    for side in [-1,1]:
        for y in [-111,-124]:
            box('DISTRICT/Market court',(side*43,y,.035),(40,10,.07),'paving',collection='District')
        box('DISTRICT/Ceremonial statue plinth',(side*13,-90,1.0),(5,5,2),'warm',collection='Monuments')
        box('DISTRICT/Statue die',(side*13,-90,3.35),(3.2,3.2,2.7),'light',collection='Monuments')
        box('DISTRICT/Statue coping',(side*13,-90,5.0),(4,4,.7),'light',collection='Monuments')
        box('DISTRICT/Inscribed panel',(side*13,-92,3.45),(2.2,.10,1.4),'darkstone',collection='Monuments',collision='none')
    arch('MAIN/Projected triumphal entry',(0,-85.0,.26),0,7.4,8.7,14.4,4.2,12,'light','Monuments',segments=20)
    for x in [-6.6,6.6]:column('MAIN/Paired entry order',x,-87.0,.0,14.75,.68,'light','Monuments')
    box('MAIN/Entablature',(0,-85.4,15.05),(16.2,5.4,.85),'light',collection='Monuments')
    for side in [-1,1]:
        # Four shared surfaces connect the circular plaza to adjacent city streets.
        box('DISTRICT/Side street',(side*134,0,-.07),(22,12,.14),'paving',collection='District')
    box('DISTRICT/North temple street',(0,116,-.08),(18,24,.16),'paving',collection='District')
    # Low surface thresholds preserve the .38m controller step contract.
    for sec in [2,10]:
        a=TAU*sec/16
        arc('STAIRS/Lower approach threshold',62.65,39.65,61.9,38.9,.35,.59,a-.025,a+.025,'stone','Circulation',n=3)
    # Portable subtle sand map; broad repeated noise would create a checkerboard at aerial scale.
    m=M['sand'];p=m.node_tree.nodes.get('Principled BSDF')
    for link in list(m.node_tree.links):
        if link.to_node==p and link.to_socket.name=='Base Color':m.node_tree.links.remove(link)
    p.inputs['Base Color'].default_value=(.63,.46,.28,1)
    if 'map' in m:del m['map']

def stage10():
    sys.path.insert(0,str(ROOT/'scripts'))
    from market_dressing import build_market
    from dressing import build_dressing
    market=build_market(sys.modules[__name__],SPEC)
    (ROOT/'market_registry.json').write_text(json.dumps(market,indent=2))
    dressing=build_dressing(sys.modules[__name__],SPEC)
    (ROOT/'dressing_registry.json').write_text(json.dumps(dressing,indent=2))

def stage11():
    sys.path.insert(0,str(ROOT/'scripts'));from character_population import build_population
    meta=build_population(sys.modules[__name__],SPEC)
    (ROOT/'population_registry.json').write_text(json.dumps(meta,indent=2))

def render(name,filename=None,pct=None):
    s=bpy.context.scene;s.camera=bpy.data.objects['CAM_'+name]
    if pct:s.render.resolution_percentage=pct
    s.render.filepath=str(ROOT/'renders'/(filename or name+'.png'));bpy.ops.render.render(write_still=True)

def main():
    p=argparse.ArgumentParser();p.add_argument('--stage',type=int,required=True);p.add_argument('--render',default='reference');p.add_argument('--no-render',action='store_true');p.add_argument('--start',type=int);args=p.parse_args(sys.argv[sys.argv.index('--')+1:])
    current=ROOT/'checkpoints/current.blend'
    if args.stage==1:setup();start=1
    else:
        bpy.ops.wm.open_mainfile(filepath=str(current));mats();start=bpy.context.scene.get('stage',0)+1
    if args.start:start=args.start
    for s in range(start,args.stage+1):
        if s<=7:globals()['stage'+str(s)]()
        elif s==8:stage8()
        elif s==9:
            sys.path.insert(0,str(ROOT/'scripts'));from city import build_city;meta=build_city(sys.modules[__name__],SPEC);(ROOT/'city_registry.json').write_text(json.dumps(meta,indent=2))
        elif s==10:stage10()
        elif s==11:stage11()
        bpy.context.scene['stage']=s
    bpy.context.scene.render.resolution_percentage=70
    bpy.ops.wm.save_as_mainfile(filepath=str(current))
    if args.stage in [3,4,7,9,11]:bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'checkpoints'/f'{args.stage:02}_construction.blend'))
    if not args.no_render:render(args.render,f'checkpoint_{args.stage:02}_{args.render}.png')
    print('ARENA_STAGE_COMPLETE',args.stage,len(bpy.data.objects),flush=True)

if __name__=='__main__':main()
