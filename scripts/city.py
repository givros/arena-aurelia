"""Deterministic Roman urban framing, river and monumental infrastructure.

Blender coordinates: X east/right, Y north/background, Z up. Meters.
The arena and its protected ellipse are owned by the arena generator.
"""
import bpy
import math
import random
from collections import defaultdict
from mathutils import Vector
from pathlib import Path


TAU = math.tau


class CityGeometry:
    def __init__(self):
        self.buffers = defaultdict(lambda: [[], []])

    def mesh(self, material, vertices, faces):
        v, f = self.buffers[material]
        k = len(v)
        v.extend(vertices)
        f.extend(tuple(k + i for i in face) for face in faces)

    def box(self, material, center, size, angle=0):
        x, y, z = center
        sx, sy, sz = [a / 2 for a in size]
        ca, sa = math.cos(angle), math.sin(angle)
        vertices = []
        for a, b, c in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),
                        (-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]:
            vertices.append((x + a * ca - b * sa, y + a * sa + b * ca, z + c))
        self.mesh(material, vertices, [(0,3,2,1),(0,1,5,4),(1,2,6,5),
                                       (2,3,7,6),(3,0,4,7),(4,5,6,7)])

    def cylinder(self, material, center, radius, depth, vertices=16, top_radius=None):
        x, y, z = center
        rt = radius if top_radius is None else top_radius
        vs = [(x + r*math.cos(i*TAU/vertices), y + r*math.sin(i*TAU/vertices), z+dz)
              for dz, r in [(-depth/2, radius),(depth/2, rt)] for i in range(vertices)]
        faces = [tuple(range(vertices-1,-1,-1)), tuple(range(vertices,vertices*2))]
        faces += [(i,(i+1)%vertices,(i+1)%vertices+vertices,i+vertices) for i in range(vertices)]
        self.mesh(material, vs, faces)

    def beam(self, material, start, end, radius, sides=8):
        a, b = Vector(start), Vector(end)
        d = (b-a).normalized()
        side = d.cross(Vector((0,0,1)))
        if side.length < .01:
            side = d.cross(Vector((0,1,0)))
        side.normalize()
        up = d.cross(side).normalized()
        vs = [tuple(p + radius*(math.cos(i*TAU/sides)*side + math.sin(i*TAU/sides)*up))
              for p in [a,b] for i in range(sides)]
        fs = [tuple(range(sides-1,-1,-1)),tuple(range(sides,sides*2))]
        fs += [(i,(i+1)%sides,(i+1)%sides+sides,i+sides) for i in range(sides)]
        self.mesh(material, vs, fs)

    def arch(self, material, center, width, rise, thickness, depth, angle=0, segments=20):
        """Elliptical voussoir ring; center gives spring-line center."""
        cx,cy,cz=center
        ca,sa=math.cos(angle),math.sin(angle)
        for j in range(segments):
            lo=j*math.pi/segments+.007
            hi=(j+1)*math.pi/segments-.007
            vertices=[]
            for yy in [-depth/2,depth/2]:
                for r,h,t in [(width/2,rise,lo),(width/2,rise,hi),
                              (width/2+thickness,rise+thickness,hi),
                              (width/2+thickness,rise+thickness,lo)]:
                    xx=r*math.cos(t)
                    vertices.append((cx+ca*xx-sa*yy,cy+sa*xx+ca*yy,cz+h*math.sin(t)))
            self.mesh(material,vertices,[(0,3,2,1),(4,5,6,7),(0,1,5,4),
                                        (1,2,6,5),(2,3,7,6),(3,0,4,7)])

    def objects(self, name, collection, materials, collision='solid', semantic=None):
        out=[]
        for key,(vertices,faces) in self.buffers.items():
            if not vertices:
                continue
            mesh=bpy.data.meshes.new(f'{name}/{key}/geometry')
            mesh.from_pydata(vertices,[],faces)
            mesh.materials.append(materials[key])
            mesh.update()
            # Dominant-face projection keeps the source texture at a four-meter repeat.
            uv=mesh.uv_layers.new(name='SurfaceUV')
            for poly in mesh.polygons:
                axis=max(range(3),key=lambda i:abs(poly.normal[i]))
                axes=([1,2] if axis==0 else [0,2] if axis==1 else [0,1])
                for li in poly.loop_indices:
                    co=mesh.vertices[mesh.loops[li].vertex_index].co
                    uv.data[li].uv=(co[axes[0]]/4,co[axes[1]]/4)
            obj=bpy.data.objects.new(f'{name}/{key}',mesh)
            collection.objects.link(obj)
            obj['semantic']=semantic or f'city/{name}/{key}'
            obj['collision']=collision
            obj['source_component']=name
            out.append(obj)
        return out


def _material(name,color,roughness=.8,metallic=0):
    m=bpy.data.materials.get('City/'+name) or bpy.data.materials.new('City/'+name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value=(*color,1)
    p.inputs['Roughness'].default_value=roughness
    p.inputs['Metallic'].default_value=metallic
    texture='travertine.png' if name in {'stone','bank','marble'} else ('paving.png' if name in {'ground','road'} else None)
    texture_path=Path(__file__).resolve().parents[1]/'textures'/texture if texture else None
    if texture_path and texture_path.exists():
        n=m.node_tree.nodes.get('CitySurfaceTexture') or m.node_tree.nodes.new('ShaderNodeTexImage')
        n.name='CitySurfaceTexture'
        n.image=bpy.data.images.load(str(texture_path),check_existing=True)
        m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
        m['map']=texture
        m['texture_repeat_meters']=4.0
    return m


def _collection(name):
    c=bpy.data.collections.get(name)
    if c is None:
        c=bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def _roof(g,w,d,z,pitch=2.6):
    # Roof skins include deep eaves and visibly curved imbrex ribs.
    W=w/2+.48
    D=d/2+.5
    vs=[(-W,-D,z),(-W,D,z),(0,D,z+pitch),(0,-D,z+pitch),
        (W,-D,z),(W,D,z),(-W,-D,z-.2),(-W,D,z-.2),(W,-D,z-.2),(W,D,z-.2)]
    g.mesh('tile',vs,[(0,1,2,3),(3,2,5,4),(6,0,3,4,8),(7,9,5,2,1),
                          (6,7,1,0),(8,4,5,9)])
    for y in [(-D+.2)+i*.58 for i in range(int((D*2-.2)/.58)+1)]:
        for side in [-1,1]:
            g.beam('tileLight',(side*.05,y,z+pitch+.08),(side*(W+.01),y,z+.08),.10,6)
    g.beam('tileLight',(0,-D-.12,z+pitch+.08),(0,D+.12,z+pitch+.08),.23,10)
    for side in [-1,1]:
        g.box('wood',(side*(W-.13),0,z-.19),(.21,d+.9,.25))


def _facade(g,width,depth,stories,plaster,side):
    # Each face is constructed around actual recessed apertures.
    if side in ['front','back']:
        span=width
        sign=-1 if side=='front' else 1
        origin=(0,sign*depth/2)
        angle=0 if side=='front' else math.pi
    else:
        span=depth
        sign=1 if side=='right' else -1
        origin=(sign*width/2,0)
        angle=math.pi/2 if side=='right' else -math.pi/2
    ca,sa=math.cos(angle),math.sin(angle)
    def part(mat,x,y,z,sx,sy,sz):
        g.box(mat,(origin[0]+x*ca-y*sa,origin[1]+x*sa+y*ca,z),(sx,sy,sz),angle)
    bays=max(2,int(span/3.6))
    bay=span/bays
    storyh=3.7
    for floor in range(stories):
        base=.45+floor*storyh
        winbottom=base+1.15
        wintop=base+2.65
        for b in range(bays):
            x=-span/2+(b+.5)*bay
            door=(floor==0 and side=='front' and b==bays//2)
            ww=1.4 if door else 1.16
            low=base if door else winbottom
            high=base+2.7 if door else wintop
            part(plaster,x,-.05,base+(low-base)/2,bay,.55,max(.015,low-base))
            part(plaster,x,-.05,(high+base+storyh)/2,bay,.55,base+storyh-high)
            for dx in [-1,1]:
                part(plaster,x+dx*(ww/2+(bay-ww)/4),-.05,(low+high)/2,(bay-ww)/2,.55,high-low)
            part('shadow',x,.20,(low+high)/2,ww,.15,high-low)
            if door:
                for i in range(6):
                    part('wood',x-ww/2+(i+.5)*ww/6,.11,(low+high)/2,ww/6-.027,.16,high-low-.05)
                part('stone',x,-.07,low+.08,ww+.4,.85,.16)
                for zz in [low+.6,high-.5]:
                    part('iron',x,.01,zz,ww-.1,.08,.08)
                part('iron',x+.30,-.07,low+1.3,.1,.08,.15)
            else:
                # Shutter cheeks are set within the masonry reveal, not painted holes.
                for dx in [-1,1]:
                    part('wood',x+dx*(ww/2-.22),.10,(low+high)/2,.38,.13,high-low-.12)
                part('stone',x,-.14,low-.09,ww+.34,.84,.19)
            part('stone',x,-.1,high+.1,ww+.42,.68,.22)
        part('stone',0,-.12,base+storyh-.05,span+.18,.72,.21)
    for x in [-span/2+.23,span/2-.23]:
        for z in [.85+i*.64 for i in range(int(stories*storyh/.64))]:
            part('stone',x,-.1,z,.47,.67,.31)


def _house_proto(index,width,depth,stories,materials,collection):
    g=CityGeometry()
    h=.45+3.7*stories
    plaster=['plaster','plasterWarm','plasterPale'][index%3]
    g.box('stone',(0,0,.22),(width+.35,depth+.35,.44))
    # Closed supporting houses have a structural core. Apertures have 0.35m reveals.
    g.box('shadow',(0,0,h/2),(width-.95,depth-.95,h))
    for side in ['front','back','left','right']:
        _facade(g,width,depth,stories,plaster,side)
    g.box('stone',(0,0,h+.05),(width+.45,depth+.45,.3))
    if index==3:
        # Broad hipped villa roof breaks the repeated gable cadence.
        W,D=width/2+.48,depth/2+.5
        z=h+.22
        g.mesh('tile',[(-W,-D,z),(W,-D,z),(W,D,z),(-W,D,z),
                       (0,-D*.44,z+3.1),(0,D*.44,z+3.1)],
                      [(0,1,4),(1,2,5,4),(2,3,5),(3,0,4,5)])
        for i in range(24):
            y=-D+(i+.5)*(2*D/24)
            ridgey=max(-D*.44,min(D*.44,y))
            for side in [-1,1]:
                g.beam('tileLight',(side*W,y,z+.06),(0,ridgey,z+3.16),.095,6)
        g.beam('tileLight',(0,-D*.44,z+3.14),(0,D*.44,z+3.14),.2,8)
    elif index==4:
        # A usable-looking flat terrace and pergola make the low courtyard family distinct.
        for dx in [-width/2,width/2]:g.box('plasterPale',(dx,0,h+.7),(.38,depth,1.05))
        for yy in [-depth/2,depth/2]:g.box('plasterPale',(0,yy,h+.7),(width,.38,1.05))
        g.box('stone',(0,0,h+.21),(width,depth,.14))
        for xx in [-3,3]:
            for yy in [-4,4]:g.box('wood',(xx,yy,h+1.55),(.16,.16,2.65))
        for yy in [-4,4]:g.box('woodLight',(0,yy,h+2.82),(6.5,.18,.18))
        for xx in range(-3,4):g.box('woodLight',(xx,0,h+2.95),(.12,8.6,.15))
    else:
        _roof(g,width,depth,h+.22,pitch=2.15+index*.16)
    if index==5:
        # A proper projecting upper loggia links the facade's lower supports to its balcony.
        g.box('stone',(0,-depth/2-1.03,3.75),(width+.30,2.05,.36))
        for xx in [-width/2+.4,-width/4,0,width/4,width/2-.4]:
            _column(g,xx,-depth/2-1.45,.2,3.4,.18)
        for yy in [-depth/2-1.95]:
            g.box('stone',(0,yy,4.57),(width+.2,.18,.95))
            g.box('marble',(0,yy,5.1),(width+.4,.34,.18))
    # Ground-level threshold, lintel and entrance canopy with attached brackets.
    entrance_bays=max(2,int(width/3.6))
    entrance_x=-width/2+(entrance_bays//2+.5)*(width/entrance_bays)
    g.box('stone',(entrance_x,-depth/2-.6,.10),(2.8,1.4,.20))
    if index%2==0:
        g.box('wood',(entrance_x,-depth/2-1.0,3.35),(3.1,2.0,.18))
        for x in [-1.25,1.25]:
            g.beam('wood',(x+entrance_x,-depth/2-.15,2.5),(x+entrance_x,-depth/2-1.7,3.25),.11,6)
    objs=g.objects(f'HouseFamily{index}',collection,materials)
    for o in objs:
        o['closed_background_building']=True
    return objs


def _copy_assembly(proto,name,x,y,rotation,collection):
    out=[]
    for p in proto:
        q=bpy.data.objects.new(f'{name}/{p.data.materials[0].name.split("/")[-1]}',p.data)
        collection.objects.link(q)
        q.location=(x,y,0)
        q.rotation_euler.z=rotation
        q['semantic']=f'city/building/{name}'
        q['collision']='solid'
        q['prototype']=p['source_component']
        q['closed_background_building']=True
        out.append(q)
    return out


def _column(g,x,y,base,height,radius=.95):
    g.box('stone',(x,y,base+.18),(radius*2.8,radius*2.8,.36))
    g.cylinder('stone',(x,y,base+.51),radius*1.22,.3,20)
    shaft=height-1.55
    g.cylinder('marble',(x,y,base+.72+shaft/2),radius,shaft,20,top_radius=radius*.86)
    for j in range(16):
        a=j*TAU/16
        g.beam('marbleLight',(x+radius*.97*math.cos(a),y+radius*.97*math.sin(a),base+.85),
               (x+radius*.84*math.cos(a),y+radius*.84*math.sin(a),base+.65+shaft),.07,6)
    g.cylinder('stone',(x,y,base+height-.62),radius*1.06,.24,20)
    g.cylinder('stone',(x,y,base+height-.35),radius*1.32,.34,16)
    g.box('marble',(x,y,base+height-.10),(radius*2.75,radius*2.75,.20))


def _temple(materials,collection):
    g=CityGeometry()
    X,Y=10,140
    for k in range(4):
        g.box('stone',(X,Y,.5+k),(48-k*.75,40-k*.75,1))
    for i in range(16):
        top=(i+1)*.25
        g.box('stone',(X,107+i*.8+.4,top/2),(27,.8,top))
    g.box('marble',(X,Y,4.13),(46,38,.26))
    for ix in range(8):
        _column(g,X-20+ix*(40/7),Y-15,4.26,19.7,1.01)
        _column(g,X-20+ix*(40/7),Y+15,4.26,19.7,1.01)
    for iy in range(1,6):
        for dx in [-20,20]:
            _column(g,X+dx,Y-15+iy*5,4.26,19.7,1.01)
    # Cella has actual door opening and wall thickness; the portico is fully accessible.
    g.box('marble',(X,Y+3.2,4.45),(29,25,.42))
    for dx in [-14,14]:
        g.box('plasterPale',(X+dx,Y+3,13),(1.2,24,17.5))
    g.box('plasterPale',(X,Y+14.4,13),(29,1.2,17.5))
    for dx in [-9.5,9.5]:
        g.box('plasterPale',(X+dx,Y-9,13),(9,1.2,17.5))
    g.box('plasterPale',(X,Y-9,20.7),(10,1.2,2.7))
    for dx in [-5.0,5.0]:
        g.box('marble',(X+dx,Y-9.7,12.4),(.65,.50,16.3))
    g.box('marble',(X,Y-9.7,20.4),(10.7,.55,.62))
    g.box('red',(X-7.3,Y-9.72,15),(2.7,.12,10))
    g.box('red',(X+7.3,Y-9.72,15),(2.7,.12,10))
    g.box('stone',(X,Y,24.35),(45,36,1.0))
    g.box('marble',(X,Y,25.0),(47,38,.32))
    for y in [Y-18.5,Y+18.5]:
        for ix in range(32):
            g.box('stone',(X-22.5+ix*1.45,y,25.5),(.7,.9,.68))
    for side in [-1,1]:
        y=Y+side*18.7
        g.mesh('marble',[(X-23.3,y,25.5),(X+23.3,y,25.5),(X,y,31.6),
                         (X-23.3,y+side*.7,25.5),(X+23.3,y+side*.7,25.5),(X,y+side*.7,31.6)],
                        [(0,1,2),(5,4,3),(0,3,4,1),(1,4,5,2),(2,5,3,0)])
        for dx in [-1,1]:
            g.beam('marbleLight',(X,y+side*.8,31.65),(X+dx*23.7,y+side*.8,25.3),.25,8)
        g.beam('gold',(X,y+side*.82,27.5),(X,y+side*1.03,27.5),1.0,16)
    # Tiled temple roof shares the gable datum.
    roof=CityGeometry()
    _roof(roof,46.6,37.4,25.5,6.1)
    for mat,(vs,fs) in roof.buffers.items():
        temple_roof_material={'tile':'marble','tileLight':'marbleLight'}.get(mat,mat)
        g.mesh(temple_roof_material,[(x+X,y+Y,z) for x,y,z in vs],fs)
    for dx in [-17,17]:
        g.box('stone',(X+dx,Y-24,1.8),(3.5,3.5,3.6))
        g.box('marble',(X+dx,Y-24,3.75),(4.2,4.2,.3))
    # Raise the sacred precinct coherently to retain the reference's visible rear temple.
    for vertices,faces in g.buffers.values():
        for i,(x,y,z) in enumerate(vertices):vertices[i]=(x,y+26,z+8)
    g.box('bank',(10,166,4),(55,44,8))
    g.box('marble',(10,166,8.12),(56,45,.24))
    g.box('bank',(10,139.5,4),(29,13,8))
    for i in range(32):
        top=(i+1)*.25
        g.box('stone',(10,112.2+i*.65+.325,top/2),(29,.65,top))
    # Side stairs provide alternate approaches to the elevated precinct.
    for side in [-1,1]:
        for i in range(32):
            top=(i+1)*.25
            g.box('stone',(10+side*(28+20.8-(i+.5)*.65),171,top/2),(.65,6,top))
    return g.objects('Temple_of_Concordia',collection,materials)


def _clip(poly,xlimit,less):
    out=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):
        ia=a[0]<=xlimit if less else a[0]>=xlimit
        ib=b[0]<=xlimit if less else b[0]>=xlimit
        if ia:
            out.append(a)
        if ia!=ib:
            f=(xlimit-a[0])/(b[0]-a[0])
            out.append((xlimit,a[1]+f*(b[1]-a[1]),a[2]+f*(b[2]-a[2])))
    return out


def _terrain(materials,collection):
    g=CityGeometry()
    inner=[]
    outer=[]
    for i in range(256):
        t=TAU*i/256
        ca,sa=math.cos(t),math.sin(t)
        inner.append((128*ca,105*sa,-.035))
        ex=360 if ca>0 else 320
        ey=440 if sa>0 else 240
        dist=min(ex/max(abs(ca),1e-7),ey/max(abs(sa),1e-7))
        outer.append((dist*ca,dist*sa,-.035))
    for i in range(256):
        poly=[inner[i],outer[i],outer[(i+1)%256],inner[(i+1)%256]]
        for limit,less in [(-200,True),(-158,False)]:
            p=_clip(poly,limit,less)
            if len(p)>2:
                g.mesh('ground',p,[tuple(range(len(p)))])
    g.objects('District_ground',collection,materials,'walkable','city/terrain/ground')
    water=CityGeometry()
    water.box('water',(-179,100,-3.50),(42,680,.10))
    water.objects('River_Tiber',collection,materials,'none','water/river')
    banks=CityGeometry()
    for x in [-159,-199]:
        banks.box('bank',(x,100,-2.7),(2.0,680,5.4))
        banks.box('stone',(x,100,.10),(2.5,680,.20))
        for y in range(-238,440,8):
            # Retaining piers and alternating masonry courses reach below water level.
            banks.box('stone',(x,y,-2.5),(2.4,.6,5.0))
    banks.objects('River_quay_walls',collection,materials,'solid','city/infrastructure/quay')
    # The foreground central avenue stays open at the player spawn.
    roads=CityGeometry()
    for center,size in [((0,-180,.004),(20,119,.07)),((0,193,.004),(315,13,.07)),
                         ((0,232,.004),(316,11,.07)),((0,271,.004),(316,11,.07)),
                         ((0,310,.004),(316,11,.07)),((160,20,.004),(12,338,.07)),
                         ((207,145,.004),(12,350,.07)),((253,145,.004),(12,350,.07)),
                         ((-225,70,.004),(13,600,.07)),((10,105,.004),(27,24,.07))]:
        roads.box('road',center,size)
    roads.objects('District_routes',collection,materials,'walkable','city/routes')


def _bridge(materials,collection):
    g=CityGeometry()
    Y=105
    # Three flattened Roman masonry arches connect both quays at the common street datum.
    for x in [-194,-180,-166]:
        g.arch('stone',(x,Y,-6.1),12.0,5.0,1.05,13.0,segments=22)
        for side in [-1,1]:
            g.arch('marble',(x,Y+side*6.65,-6.1),12.0,5.0,.8,.50,segments=22)
    for x in [-201,-187,-173,-159]:
        g.box('bank',(x,Y,-4.1),(2.2,14,8.2))
        # Prow-shaped cutwaters interrupt the flow at the masonry piers.
        for side in [-1,1]:
            g.mesh('bank',[(x-1.5,Y+side*6.8,-7),(x+1.5,Y+side*6.8,-7),(x,Y+side*9.0,-7),
                           (x-1.5,Y+side*6.8,-1.0),(x+1.5,Y+side*6.8,-1.0),(x,Y+side*9,-1.0)],
                          [(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)])
    # Explicit spandrels above the curved arch soffits, with no filled openings.
    for x in [-194,-180,-166]:
        for i in range(24):
            xx=-7+(i+.5)*14/24
            outertop=-6.1+6.05*math.sqrt(max(0,1-(xx/7.05)**2))
            if outertop < -.38:
                g.box('stone',(x+xx,Y,(outertop-.30)/2),(14/24,13,-.30-outertop))
    g.box('road',(-180,Y,-.13),(65,13,.36))
    for side in [-1,1]:
        g.box('stone',(-180,Y+side*6.0,.85),(65,.8,1.7))
        g.box('marble',(-180,Y+side*6.0,1.78),(65,1,.22))
        for x in range(-210,-147,7):
            g.box('stone',(x,Y+side*6,1.15),(1.3,1.3,2.3))
            g.box('marble',(x,Y+side*6,2.36),(1.6,1.6,.22))
    for vertices,faces in g.buffers.values():
        for i,(x,y,z) in enumerate(vertices):vertices[i]=(x,y,z+6)
    # Grounded ramp abutments connect the raised bridge to the street network.
    for x0,x1,lefttop,righttop in [(-232.5,-212.5,0,6.05),(-147.5,-127.5,6.05,0)]:
        vs=[(x0,Y-6.5,-.2),(x1,Y-6.5,-.2),(x1,Y+6.5,-.2),(x0,Y+6.5,-.2),
            (x0,Y-6.5,lefttop),(x1,Y-6.5,righttop),(x1,Y+6.5,righttop),(x0,Y+6.5,lefttop)]
        g.mesh('stone',vs,[(0,3,2,1),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)])
        for sign in [-1,1]:
            g.beam('marble',(x0,Y+sign*6.0,lefttop+.75),(x1,Y+sign*6,righttop+.75),.30,6)
    g.objects('Pons_Caelius',collection,materials,'solid','city/infrastructure/bridge')


def _aqueduct(materials,collection):
    g=CityGeometry()
    Y=170
    xs=[66+i*17 for i in range(17)]
    for x in xs:
        for z in [0,9,18]:
            g.box('stone',(x,Y,z+.28),(4.8,6.6,.56))
        g.box('bank',(x,Y,12.4),(3.0,5.8,24.8))
        g.box('stone',(x,Y,2.1),(4.2,6.2,4.2))
    for x in xs[:-1]:
        g.arch('stone',(x+8.5,Y,17.0),14,6.2,1.5,5.8,segments=24)
        for side in [-1,1]:
            g.arch('marble',(x+8.5,Y+side*3.00,17),14,6.2,.70,.28,segments=24)
        for j in range(17):
            xx=-8.5+(j+.5)
            top=17+7.7*math.sqrt(max(0,1-(xx/8.5)**2))
            g.box('bank',(x+8.5+xx,Y,(top+25.25)/2),(1.0,5.7,25.25-top))
    g.box('stone',((xs[0]+xs[-1])/2,Y,25.9),(xs[-1]-xs[0]+5,6.4,1.3))
    # Open trough and two raised retaining sides make the crown readable from above.
    for side in [-1,1]:
        g.box('bank',((xs[0]+xs[-1])/2,Y+side*2.5,27.4),(xs[-1]-xs[0]+5,.9,1.8))
        g.box('stone',((xs[0]+xs[-1])/2,Y+side*2.5,28.45),(xs[-1]-xs[0]+5,1.2,.3))
    for vertices,faces in g.buffers.values():
        for i,(x,y,z) in enumerate(vertices):vertices[i]=(x,y,z*1.3)
    g.objects('Aqua_Aurelia',collection,materials,'solid','city/infrastructure/aqueduct')


def _cypress_proto(materials,collection):
    g=CityGeometry()
    g.cylinder('bark',(0,0,3.1),.32,6.2,10,.16)
    rng=random.Random(819)
    # Layered branched needle sprays, with gaps and fine silhouette breakup.
    for level in range(15):
        z=1.8+level*.75
        radius=1.45*(math.sin((level+1)/17*math.pi)**.6)*(1-level*.035)
        for j in range(7):
            a=(j/7+level*.113)*TAU
            reach=radius*rng.uniform(.83,1.20)
            p=(reach*math.cos(a),reach*math.sin(a),z+.55)
            g.beam('bark',(0,0,z),p,.055,5)
            for sprig in range(5):
                az=a+(sprig-2)*.28
                rr=reach*(.45+sprig*.11)
                cz=z+.15+sprig*.17
                cx,cy=rr*math.cos(az),rr*math.sin(az)
                for k in range(3):
                    t=az+k*math.pi/3
                    # Crossed tapered needle fans are sculpted geometry, not blob crowns.
                    dx,dy=math.cos(t)*.38,math.sin(t)*.38
                    g.mesh('leafDark' if (j+level)%3 else 'leaf',
                           [(cx-dx,cy-dy,cz),(cx+dx,cy+dy,cz),(cx+.18*dx,cy+.18*dy,cz+1.35)],[(0,1,2),(2,1,0)])
    return g.objects('CypressFamily',collection,materials,'none','vegetation/cypress')


def _pine_proto(materials,collection):
    g=CityGeometry()
    rng=random.Random(126)
    g.cylinder('bark',(0,0,4.3),.50,8.6,12,.27)
    for j in range(14):
        a=j*2.399
        r=2.2+(j%4)*.56
        z=8.5+(j%3)*.60
        p=(r*math.cos(a),r*math.sin(a),z)
        g.beam('bark',(0,0,5.8+(j%4)*.6),p,.17,7)
        for k in range(13):
            aa=k*2.399+j
            rr=math.sqrt((k+.5)/13)*1.75
            x,y=p[0]+rr*math.cos(aa),p[1]+rr*math.sin(aa)
            zz=z+rng.uniform(-.35,.5)
            for kk in range(3):
                t=aa+kk*math.pi/3
                dx,dy=math.cos(t)*.70,math.sin(t)*.70
                g.mesh('leaf' if k%3 else 'leafDark',
                       [(x-dx,y-dy,zz),(x+dx,y+dy,zz),(x+.2,y,zz+1.0),(x-.2,y,zz+1.0)],
                       [(0,1,2,3),(3,2,1,0)])
    return g.objects('UmbrellaPineFamily',collection,materials,'none','vegetation/umbrella-pine')


def _boat(g,x,y,angle=0):
    ca,sa=math.cos(angle),math.sin(angle)
    def tr(p):
        return (x+p[0]*ca-p[1]*sa,y+p[0]*sa+p[1]*ca,p[2])
    vs=[(-1.4,-3,-3.15),(1.4,-3,-3.15),(1.5,2,-3.15),(0,4,-3.15),(-1.5,2,-3.15),
        (-.7,-2.5,-4),(.7,-2.5,-4),(.8,2,-4),(0,3,-4),(-.8,2,-4)]
    g.mesh('wood',[tr(p) for p in vs],[(0,5,6,1),(1,6,7,2),(2,7,8,3),(3,8,9,4),(4,9,5,0),(5,9,8,7,6)])
    for yy in [-1.8,-.4,1]:
        a,b=tr((-1.35,yy,-3.12)),tr((1.35,yy,-3.12))
        g.beam('woodLight',a,b,.18,6)
    for yy in [-1.7,.4]:
        for xx in [-.55,.55]:
            p=tr((xx,yy,-2.85))
            g.cylinder('pot',p,.34,.58,10,.21)


def _hills(materials,collection):
    g=CityGeometry()
    rng=random.Random(529)
    # Backdrop terrain uses connected irregular ridges beyond the modeled city.
    nx,ny=48,12
    vs=[]
    for iy in range(ny):
        y=430+iy*18
        for ix in range(nx):
            x=-490+ix*22
            z=max(-.035,(iy/11)**.6*(16+18*math.sin(ix*.29+.4)**2+14*math.sin(ix*.7+iy*.23)**2)+rng.uniform(-.6,.6))
            vs.append((x,y,z))
    for iy in range(ny-1):
        for ix in range(nx-1):
            i=iy*nx+ix
            g.mesh('hill', [vs[i],vs[i+1],vs[i+nx+1],vs[i+nx]],[(0,1,2),(0,2,3)])
    g.objects('Roman_hills',collection,materials,'solid','landscape/hills')


def _basilica(materials,collection,name,x,y,w=60,d=20):
    g=CityGeometry()
    g.box('stone',(x,y,.35),(w+1.2,d+1.2,.7))
    # Deep public arcade in front of the raised clerestory hall.
    n=int(w/6.2)
    bay=w/n
    for i in range(n+1):
        xx=x-w/2+i*bay
        _column(g,xx,y-d/2+.4,.7,7.2,.40)
    for i in range(n):
        xx=x-w/2+(i+.5)*bay
        g.arch('stone',(xx,y-d/2+.4,5.5),bay-.9,2.4,.48,.95,segments=16)
    g.box('marble',(x,y-d/2+.4,8.45),(w+1,1.6,.55))
    # The lower arcade has its own supported lean-to roof below the clerestory.
    fy,by=y-d/2-.3,y-d/2+5.6
    g.mesh('tile',[(x-w/2-.5,fy,8.83),(x+w/2+.5,fy,8.83),
                   (x+w/2+.5,by,11.55),(x-w/2-.5,by,11.55),
                   (x-w/2-.5,fy,8.66),(x+w/2+.5,fy,8.66),
                   (x+w/2+.5,by,11.38),(x-w/2-.5,by,11.38)],
                  [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)])
    for i in range(int(w/.6)+1):
        xx=x-w/2+i*.6
        g.beam('tileLight',(xx,fy,8.91),(xx,by,11.63),.085,6)
    for dx in [-w/2,w/2]:g.box('plasterPale',(x+dx,y+1,5.6),(1,d-2,9.8))
    g.box('plasterWarm',(x,y+d/2-.5,5.6),(w,1,9.8))
    g.box('plaster',(x,y+1,9.65),(w,d-3,2.0))
    # Clerestory walls are divided around upper recessed windows.
    for xx in [x-w/2+(i+.5)*bay for i in range(n)]:
        g.box('plasterPale',(xx,y-d/2+5.5,12.1),(bay-.3,.8,1.0))
        for side in [-1,1]:g.box('stone',(xx+side*(bay/2-.5),y-d/2+5.5,14),(.8,.8,3.1))
        g.box('shadow',(xx,y-d/2+5.7,13.65),(bay-1.2,.30,2.1))
        g.box('marble',(xx,y-d/2+5.30,14.95),(bay+.2,1,.35))
    g.box('marble',(x,y+1,15.5),(w+1,d-4,.5))
    roof=CityGeometry()
    # Ridge along its long dimension: a broad civic silhouette unlike the houses.
    _roof(roof,d-4,w,15.8,4.1)
    for mat,(vs,fs) in roof.buffers.items():g.mesh(mat,[(x-vy,y+vx+1,vz) for vx,vy,vz in vs],fs)
    g.objects(name,collection,materials,'solid','city/civic-basilica')


def _tower(materials,collection,name,x,y,height=31):
    g=CityGeometry()
    g.box('stone',(x,y,.5),(15,15,1))
    g.box('shadow',(x,y,height/2),(10.8,10.8,height))
    facade=CityGeometry()
    for side in ['front','back','left','right']:_facade(facade,12,12,8,'plasterWarm',side)
    for mat,(vs,fs) in facade.buffers.items():g.mesh(mat,[(x+vx,y+vy,vz) for vx,vy,vz in vs],fs)
    g.box('plasterWarm',(x,y,height-.6),(12,12,1.2))
    for z in [7,14,21,height]:
        g.box('stone',(x,y,z),(13.5,13.5,.5))
    for dx in [-5.75,5.75]:
        for dy in [-5.75,5.75]:g.box('marble',(x+dx,y+dy,height/2),(.8,.8,height))
    roof=CityGeometry()
    _roof(roof,13.2,13.2,height+.35,3.3)
    for mat,(vs,fs) in roof.buffers.items():g.mesh(mat,[(x+vx,y+vy,vz) for vx,vy,vz in vs],fs)
    g.objects(name,collection,materials,'solid','city/landmark-tower')


def build_city(api=None,spec=None):
    """Build urban framing. Independent of arena API; returns spatial evidence."""
    city=_collection('City_Architecture')
    infra=_collection('City_Infrastructure')
    landscape=_collection('City_Landscape')
    palette={
        'stone':((.64,.56,.43),.87,0),'marble':((.81,.75,.63),.73,0),
        'marbleLight':((.91,.84,.70),.72,0),'bank':((.43,.40,.32),.94,0),
        'plaster':((.72,.62,.44),.88,0),'plasterWarm':((.65,.44,.29),.87,0),
        'plasterPale':((.84,.76,.58),.84,0),'tile':((.43,.20,.105),.85,0),
        'tileLight':((.61,.31,.16),.83,0),'wood':((.24,.14,.075),.88,0),
        'woodLight':((.44,.28,.14),.86,0),'shadow':((.075,.066,.052),.99,0),
        'iron':((.16,.14,.115),.5,.4),'red':((.36,.055,.035),.78,0),
        'gold':((.55,.38,.12),.35,.55),'water':((.17,.29,.28),.21,.28),
        'ground':((.45,.405,.325),.93,0),'road':((.53,.48,.39),.94,0),
        'leaf':((.19,.24,.105),.92,0),'leafDark':((.09,.145,.070),.94,0),
        'bark':((.23,.17,.11),.93,0),'pot':((.51,.24,.12),.88,0),
        'hill':((.38,.385,.28),.98,0)}
    mats={k:_material(k,*v) for k,v in palette.items()}
    _terrain(mats,infra)
    _bridge(mats,infra)
    _aqueduct(mats,infra)
    _temple(mats,city)
    families=[(12,15,2),(15,13,2),(10,12,3),(17,17,2),(13,18,1),(18,12,2)]
    prototypes=[_house_proto(i,*f,mats,city) for i,f in enumerate(families)]
    parcels=[]
    # Deliberate blocks: entrances face east-west streets; north-facing blocks have
    # their counterpart across an eleven-meter street, never arbitrary rotations.
    for row,y in enumerate([208,247,286,325,362,399]):
        for col,x in enumerate([-135,-111,-86,-61,-36,-11,14,39,64,89,114,139,183,229,278,311]):
            # Keep the central temple precinct and high aqueduct legibility.
            family=(row*3+col)%len(families)
            rotation=0 if row%2==0 else math.pi
            parcels.append((f'North_{row:02}_{col:02}',x,y,family,rotation))
    # Outer east quarter: constrained frontage and four-meter minimum side passages.
    for row,y in enumerate([-157,-119,-75,-34,8,50,95,130]):
        for col,x in enumerate([183,230,278,313]):
            family=(row+col*2)%len(families)
            parcels.append((f'East_{row:02}_{col:02}',x,y,family,math.pi/2))
    # River's far bank is divided by the broad west-bank road.
    for row,y in enumerate([-165,-122,-77,-34,11,54,151,198,244,287,329]):
        for col,x in enumerate([-249,-284]):
            family=(row+col*3)%len(families)
            parcels.append((f'West_{row:02}_{col:02}',x,y,family,-math.pi/2))
    # Oblique close framing is deliberately restricted to the image's corners.
    parcels += [('SouthEast_01',169,-185,3,0),('SouthEast_02',205,-190,1,0),
                ('SouthWest_01',-137,-160,1,-math.pi/2),('SouthWest_02',-135,-199,3,0)]
    parcels += [('Precinct_01',-113,120,1,0),('Precinct_02',-134,156,2,math.pi/2),
                ('Precinct_06',57,189,4,0),
                ('Precinct_07',123,128,1,math.pi/2),('Precinct_08',148,144,2,math.pi/2),
                ('Precinct_09',146,109,0,math.pi/2)]
    # Civic masses occupy resolved parcels, replacing the affected residential plots.
    parcels=[p for p in parcels if not (p[0].startswith('North_00') and p[1] in [89,114,139])
             and not (p[0].startswith('North_01') and p[1]==-135)
             and not (p[0].startswith('North_03') and p[1]==114)]
    gardens=CityGeometry()
    for name,x,y,family,rotation in parcels:
        copies=_copy_assembly(prototypes[family],name,x,y,rotation,city)
        if name.startswith('North'):
            for obj in copies:
                obj.scale=(1.18,1.36,1.0+(family%3)*.065)
            # Contained rear gardens join the built blocks without obstructing streets.
            for dx in [-6.65,6.65]:
                gardens.box('bank',(x+dx,y+15.6,.8),(9.2,.40,1.6))
            for dx in [-11.05,11.05]:
                gardens.box('stone',(x+dx,y+11.8,.70),(.35,7.5,1.4))
            gardens.box('ground',(x,y+12,.04),(21.8,7.0,.1))
        elif name.startswith(('East','West')):
            for obj in copies:
                obj.scale=(1.35,1.45,1.0+(family%2)*.12)
            gardens.box('bank',(x,y+17,.8),(27,.40,1.6))
            for dx in [-13.3,13.3]:
                gardens.box('stone',(x+dx,y+7,.7),(.40,20,1.4))
    gardens.objects('Block_courtyard_boundaries',city,mats,'solid','city/courtyard-walls')
    _basilica(mats,city,'Basilica_Aemilia',-86,169,60,20)
    _basilica(mats,city,'Basilica_Mercatoria',112,215,60,21)
    _tower(mats,city,'Tower_of_the_Watch',-135,247,31)
    _tower(mats,city,'Civic_Archive_Tower',114,325,32)
    # Hide prototype-only originals from final scene without hiding mesh instances.
    for assembly in prototypes:
        for p in assembly:
            bpy.data.objects.remove(p,do_unlink=True)
    # Colonnaded public side court, aligned with the approach to the temple.
    court=CityGeometry()
    for cx in [-76,81]:
        cy=142
        court.box('stone',(cx,cy,.24),(29,31,.48))
        for yy in [cy-12,cy+12]:
            for xx in range(-11,12,5):
                _column(court,cx+xx,yy,.48,6.2,.43)
            court.box('stone',(cx,yy,7.0),(28,2,1.0))
        for dx in [-13,13]:
            court.box('plaster',(cx+dx,cy,3.4),(1.0,23,6.2))
        court.box('stone',(cx,cy,1.0),(5.4,5.4,2.0))
        court.box('marble',(cx,cy,2.2),(6.1,6.1,.4))
    court.objects('Sacred_courtyards',city,mats,'solid','city/courtyard')
    # Modeled waterfront docks and utility boats occupy water, not the road.
    docks=CityGeometry()
    for y in [-64,4,170]:
        for x in [-162.4,-165.6,-168.8]:
            docks.box('woodLight',(x,y,-.38),(3.0,8.0,.30))
        for x in [-161,-169]:
            for yy in [y-3.4,y+3.4]:
                docks.cylinder('wood',(x,yy,-2),.20,5.6,8)
        _boat(docks,-173,y+.6,.12)
    _boat(docks,-184,-92,-.3)
    _boat(docks,-182,228,.45)
    docks.objects('River_trade',infra,mats,'solid','city/river-trade')
    # Trees planted in courtyards, quays and blocks; no random plaza scatter.
    cyp=_cypress_proto(mats,landscape)
    pine=_pine_proto(mats,landscape)
    plants=[]
    for x,y in [(-144,-145),(-146,-183),(151,-162),(151,-128),(155,111),
                (-145,119),(-143,156),(-48,131),(46,129),(-48,157),(47,158),
                (112,139),(-105,147),(-209,142),(-210,68),(-209,-15),(-209,-100),
                (167,181),(207,186),(255,186),(300,186)]:
        plants.append((x,y,'cypress'))
    for row,y in enumerate([187,225,265,304,344,381,418]):
        for col,x in enumerate([-146,-64,30,111,174,218,264,321]):
            plants.append((x,y,'pine' if (row+col)%3==0 else 'cypress'))
    for i,(name,x,y,family,rotation) in enumerate(parcels):
        if name.startswith(('North','West','East')) and i%2==0:
            plants.append((x+7.4,y+13.8,'pine' if i%6==0 else 'cypress'))
    # Composed groves give the background layered density instead of isolated markers.
    for x,y in [(-142,-170),(155,-159),(-144,141),(-42,190),(48,197),
                (-215,151),(-211,36),(165,122),(164,218),(211,274)]:
        plants += [(x,y,'pine'),(x-4.5,y+5.5,'cypress'),(x+5.5,y+3.0,'cypress')]
    for i,(x,y,kind) in enumerate(plants):
        assembly=cyp if kind=='cypress' else pine
        out=_copy_assembly(assembly,f'Tree_{i:03}',x,y,i*2.399,landscape)
        s=1.0+(i%5)*.12
        if i<21:s*=1.28
        for obj in out:
            obj.scale=(s,s,s)
            obj['semantic']=f'vegetation/{kind}'
            obj['collision']='none'
            obj['planting_datum']=0.0
            if 'closed_background_building' in obj:
                del obj['closed_background_building']
    for p in cyp+pine:
        bpy.data.objects.remove(p,do_unlink=True)
    _hills(mats,landscape)
    result={
        'building_count':len(parcels),'tree_count':len(plants),
        'temple':{'center':[10,166],'footprint':[56,45],'height':39.6,
                  'portico_walkable':True,'stair_start':[10,112.2,0],'stair_end':[10,145.8,12.0],
                  'stair_rise':.25,'stair_run':.65,'upper_stair_run':.80,'raised_precinct':8},
        'bridge':{'center':[-180,105],'deck_z':6.05,'width':13,'length':65,'open_arches':3,
                  'approach_ramps':[[-232.5,-212.5],[-147.5,-127.5]],'approach_run':20,'approach_rise':6.05},
        'aqueduct':{'y':170,'x_range':[66,338],'height':37.18,'open_arches':16},
        'civic_landmarks':[{'id':'Basilica_Aemilia','center':[-86,169],'footprint':[61.2,21.2],'height':19.9},
                           {'id':'Basilica_Mercatoria','center':[112,215],'footprint':[61.2,22.2],'height':19.9},
                           {'id':'Tower_of_the_Watch','center':[-135,247],'footprint':[15,15],'height':34.7},
                           {'id':'Civic_Archive_Tower','center':[114,325],'footprint':[15,15],'height':35.7}],
        'protected_arena_plaza':{'rx':128,'ry':105},
        'parcels':[],
        'collections':['City_Architecture','City_Infrastructure','City_Landscape']}
    for name,x,y,family,rotation in parcels:
        scale=(1.18,1.36) if name.startswith('North') else ((1.35,1.45) if name.startswith(('East','West')) else (1,1))
        w,d= families[family][:2]
        footprint=[w*scale[0],d*scale[1]]
        envelope=[(w+1)*scale[0],(d+2.4)*scale[1]]
        result['parcels'].append({'id':name,'center':[x,y],'family':family,'rotation':rotation,
                                  'full_dimensions':footprint,'projection_envelope':envelope,
                                  'enterable':False,'frontage':'south' if rotation==0 else 'rotated-south'})
    return result
