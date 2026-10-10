"""Root-callable market-court construction. apply(B) does not save or export."""
import bpy, json, math
from pathlib import Path
from mathutils import Vector
from city import CityGeometry,_collection,_material,_roof
import market_dressing as M

ROOT=Path(__file__).resolve().parents[1]

def _materials():
    colors={
      'wood':((.19,.09,.038),.94,0),'woodLight':((.38,.215,.09),.91,0),
      'iron':((.065,.06,.052),.55,.55),'rope':((.47,.35,.20),.98,0),'wicker':((.36,.24,.12),.94,0),
      'linen':((.62,.50,.33),.98,0),'linenEdge':((.39,.28,.15),.96,0),
      'red':((.31,.052,.029),.96,0),'goldCloth':((.59,.34,.105),.94,0),
      'pot':((.43,.18,.075),.93,0),'potDark':((.25,.105,.044),.96,0),'potRim':((.57,.28,.11),.88,0),
      'fruit':((.68,.29,.056),.85,0),'olive':((.20,.28,.055),.87,0),
      'bread':((.60,.34,.115),.95,0),'breadCut':((.30,.135,.038),.98,0),
      'clothBlue':((.135,.205,.225),.96,0),'clothOchre':((.62,.35,.095),.97,0),
      'coal':((.26,.035,.009),.93,0),'stone':((.55,.47,.35),.94,0),
      'plaster':((.61,.50,.35),.97,0),'plasterLight':((.72,.62,.46),.95,0),
      'tile':((.39,.15,.064),.94,0),'tileLight':((.55,.25,.11),.91,0),
      'dark':((.11,.085,.060),.98,0)}
    mats={k:_material('Event_'+k,*v) for k,v in colors.items()}
    for key in ['plaster','plasterLight']:
        m=mats[key];socket=m.node_tree.nodes.get('Principled BSDF').inputs['Base Color']
        for link in list(m.node_tree.links):
            if link.to_socket==socket:m.node_tree.links.remove(link)
        for field in ['map','texture_repeat_meters']:
            if field in m:del m[field]
    # Original physical-scale maps remain portable through the existing exporter.
    for key in ['stone']:
        m=mats[key];p=m.node_tree.nodes.get('Principled BSDF');n=m.node_tree.nodes.get('SurfaceTexture') or m.node_tree.nodes.new('ShaderNodeTexImage')
        n.name='SurfaceTexture';n.image=bpy.data.images.load(str(ROOT/'textures/travertine.png'),check_existing=True)
        m.node_tree.links.new(n.outputs['Color'],p.inputs['Base Color'])
        m['map']='travertine.png';m['texture_repeat_meters']=4.0
    return mats

def _loaf(g,x,y,z,scale=1):
    vs=[];rings=7;sides=16
    for j in range(rings+1):
        p=-math.pi/2+math.pi*j/rings
        for i in range(sides):
            a=math.tau*i/sides
            vs.append((x+.35*scale*math.cos(p)*math.cos(a),y+.18*scale*math.cos(p)*math.sin(a),z+.12*scale*math.sin(p)))
    fs=[(j*sides+i,j*sides+(i+1)%sides,(j+1)*sides+(i+1)%sides,(j+1)*sides+i) for j in range(rings) for i in range(sides)]
    g.mesh('bread',vs,fs)
    for dx in [-.16,0,.16]:g.beam('breadCut',(x+dx*scale,y-.09*scale,z+.105*scale),(x+(dx+.04)*scale,y+.09*scale,z+.105*scale),.012*scale,4)

def _cloth_roll(g,x,y,z,kind):
    mat=['linen','red','clothBlue','clothOchre'][kind%4]
    g.beam(mat,(x-.5,y,z),(x+.5,y,z),.20,16)
    for xx in [x-.4,x+.4]:
        # Tied roll's bindings are sculpted as separate cord rings.
        M._ring(g,'rope',(xx,y,z),.203,.018,16,5,'x')

def _goods(g,kind,table_z=1.11):
    if kind==0:
        for i,x in enumerate([-2,-1.2,-.4,.4,1.2,2]):M._pot(g,x,-1.5,table_z,.50+(i%3)*.12,i)
        for i in range(4):M._pot(g,1.4+(i%2)*.65,.75+(i//2)*.65,0,.67+(i%3)*.10,i)
    elif kind==1:
        for i,x in enumerate([-2,-1,0,1,2]):M._produce(g,x,-1.5,table_z,i)
        for i in range(3):M._basket(g,1.7+i*.38,.8,0,.32)
    elif kind==2:
        for j in range(3):
            for i in range(6):_loaf(g,-2.1+i*.80,-1.78+j*.28,table_z+.13,.9)
        for x in [-2,2]:M._basket(g,x,1.1,0,.52)
    elif kind==3:
        for i in range(5):_cloth_roll(g,-1.9+i*.92,-1.5,table_z+.24,i)
        for x in [-2.8,2.8]:g.box('wood',(x,1.4,1.75),(.12,.13,3.5))
        g.beam('rope',(-2.8,1.4,3.3),(2.8,1.4,3.3),.026,6)
        for i,x in enumerate([-1.85,0,1.85]):
            vs=[(x-.65,1.43,3.27),(x+.65,1.43,3.27),(x+.62,1.35,.55),(x-.63,1.36,.55)]
            g.mesh(['red','clothBlue','clothOchre'][i],vs,[(0,1,2,3),(3,2,1,0)])
            for xx in [x-.60,x+.60]:g.box('goldCloth',(xx,1.33,1.9),(.04,.03,2.6))
    elif kind==4:
        # A masonry firebox, real arched mouth and metal cooking grate.
        g.box('stone',(1.7,1.1,.45),(1.5,1.4,.90))
        g.box('stone',(1.1,1.1,1.25),(.28,1.4,.8));g.box('stone',(2.3,1.1,1.25),(.28,1.4,.8))
        g.arch('stone',(1.7,.41,1.35),.94,.58,.22,.22,0,14)
        g.box('dark',(1.7,1.65,1.25),(1.1,.20,.8))
        for i in range(6):g.beam('iron',(1.17+i*.21,.55,1.03),(1.17+i*.21,1.60,1.03),.025,6)
        for i in range(5):g.cylinder('coal',(1.3+(i%3)*.30,.75+(i//3)*.35,.97),.14,.14,8)
        for i in range(5):_loaf(g,-1.9+i*.8,-1.5,table_z+.14,1.0)
    else:
        for x,y,z in [(-2.1,.3,0),(1.8,.9,0),(1.8,.9,.85),(-2.1,1.3,0)]:M._crate(g,x,y,z,1.1,.9,.85)
        M._barrel(g,2.2,1.9,0,.72)
        for i in range(4):M._basket(g,-1.6+i*1.0,-1.5,table_z,.32)
    if kind!=3:
        M._barrel(g,-2.65,1.50,0,.78)
        M._crate(g,-2.2,.22,0,.8,.75,.72)
    g.box('woodLight',(0,2.05,.50),(2.25,.48,.13))
    for x in [-.8,.8]:g.box('wood',(x,2.05,.25),(.16,.32,.5))

def _stall(kind,height,mats,c):
    g=CityGeometry();M._canopy(g,1 if kind in [1,2,5] else 0)
    # Roof differences affect the complete supported canopy, not the tabletop height.
    for key,(vs,fs) in g.buffers.items():
        for i,(x,y,z) in enumerate(vs):
            z=z*(4.11+height)/4.11
            if z>2.6:
                blend=min(1,(z-2.6)/.8)
                if kind==1:z+=.22*math.cos(x*.8)*blend
                elif kind==3:z+=.30*(x/3.65)*blend
                elif kind==5:z-=.35*(y/2.75)*blend
            vs[i]=(x*.985,y,z)
    M._table(g);_goods(g,kind)
    return g.objects(f'EventStallPrototype_{kind}_{height}',c,mats,'solid','event_market/prototype')

def _window_wall(g,w,front,walltop,mat):
    y=front;z0=5.18;sill=5.92;head=7.66
    g.box(mat,(0,y,(z0+sill)/2),(w,.48,sill-z0))
    g.box(mat,(0,y,(head+walltop)/2),(w,.48,walltop-head))
    centers=[-3.8,0,3.8];edges=[-w/2]
    cursor=-w/2
    for x in centers:
        left=x-.82;right=x+.82
        if left>cursor:g.box(mat,((cursor+left)/2,y,(sill+head)/2),(left-cursor,.48,head-sill))
        g.box('stone',(x,y-.04,sill),(1.95,.72,.17))
        for side in [-1,1]:g.box('wood',(x+side*.70,y-.04,(sill+head)/2),(.12,.24,head-sill))
        # Inset closed upper shutters retain their depth and real masonry reveal.
        for j in range(6):g.box('woodLight',(x-.66+(j+.5)*1.32/6,y+.17,(sill+head)/2),(1.32/6-.018,.07,head-sill-.12))
        for zz in [sill+.35,head-.30]:g.box('wood',(x,y+.11,zz),(1.4,.08,.10))
        cursor=right
    if cursor<w/2:g.box(mat,((cursor+w/2)/2,y,(sill+head)/2),(w/2-cursor,.48,head-sill))

def _shop(item,mats,c):
    g=CityGeometry();kind=item['family'];h=item['height'];w=[11.8,11.1,11.6,11.3,11.7][kind];d=9.3;cy=2.0;front=cy-d/2;back=cy+d/2;top=h-2.1
    plaster='plasterLight' if kind%2 else 'plaster'
    # Low continuous paved threshold supports both the shop interior and its portico.
    g.box('stone',(0,-.35,.09),(12.7,15.3,.18))
    for x in [-w/2,w/2]:g.box(plaster,(x,cy,(top+.18)/2),(.48,d,top-.18))
    g.box(plaster,(0,back,(top+.18)/2),(w,.48,top-.18))
    # Full open ground shop frontage: wide central entrance and two trading bays.
    for x in [-w/2,-1.45,1.45,w/2]:
        g.box('stone',(x,front,2.6),(.50,.64,5.2))
        g.box('stone',(x,front,.29),(.73,.85,.22))
    g.box('stone',(0,front,4.75),(w+.4,.70,.72))
    _window_wall(g,w,front,top,plaster)
    # Upper floor has a real stair aperture, landing and guardrail.
    g.box('woodLight',((-w/2+3.22)/2,cy,5.08),(w/2+3.22,d-.48,.2))
    g.box('woodLight',((3.22+w/2)/2,5.9,5.08),(w/2-3.22,1.5,.2))
    for i in range(20):
        z=.18+(i+1)*.25;y=-1.65+i*.35
        g.box('woodLight',(4.25,y,(z+.18)/2),(1.7,.35,z-.18))
    for y in [-1.8,.6,3.0,5.25]:g.box('wood',(3.25,y,5.66),(.12,.12,1.15))
    g.beam('wood',(3.25,-1.8,6.2),(3.25,5.25,6.2),.07,8)
    roof=CityGeometry();_roof(roof,w,d,top,2.1)
    for key,(vs,fs) in roof.buffers.items():g.mesh(key,[(x,y+cy,z) for x,y,z in vs],fs)
    for z in [5.06,top-.17]:g.box('stone',(0,front-.09,z),(w+.55,.65,.22))
    # Layered shop canopy, real posts, valance and tied stays within its parcel.
    vs=[];nx=20;ny=10
    for j in range(ny+1):
        y=front-.32+(-7.45-front+.32)*j/ny
        for i in range(nx+1):
            x=-5.75+11.5*i/nx;t=j/ny
            z=(4.25+(kind%3)*.17)*(1-t)+3.15*t-.18*math.sin(i*math.pi*3/nx)*math.sin(math.pi*t)
            vs.append((x,y,z))
    cloth=['red','linen','clothOchre','red','linen'][kind]
    fs=[]
    for j in range(ny):
        for i in range(nx):
            q=j*(nx+1)+i;fs.extend([(q,q+1,q+nx+2,q+nx+1),(q+nx+1,q+nx+2,q+1,q)])
    g.mesh(cloth,vs,fs)
    for x in [-5.6,5.6]:
        g.box('wood',(x,-7.15,1.58),(.19,.20,3.16))
        g.beam('rope',(x,-7.15,3.15),(x*1.08,-7.85,.20),.024,6)
        g.box('wood',(x*1.08,-7.85,.18),(.12,.12,.36))
    g.box('wood',(0,-7.15,3.14),(11.5,.16,.16))
    for i in range(20):
        x=-5.75+i*11.5/20
        g.mesh(cloth,[(x,-7.45,3.15),(x+.575,-7.45,3.15),(x+.575,-7.45,2.86),(x+.2875,-7.45,2.76),(x,-7.45,2.86)],[(0,1,2,3,4),(4,3,2,1,0)])
    for x in [-3.25,3.25]:
        for xx in [x-1.22,x+1.22]:
            for yy in [-5.98,-5.08]:g.box('wood',(xx,yy,.72),(.15,.15,1.08))
        g.box('woodLight',(x,-5.5,1.27),(3.15,1.12,.15))
        for j in range(4):
            if kind in [0,3]:M._pot(g,x-1.12+j*.74,-5.5,1.35,.48+(j%2)*.12,j)
            elif kind==1:M._produce(g,x-1.05+j*.70,-5.5,1.35,j)
            elif kind==2:_loaf(g,x-1.05+j*.70,-5.5,1.5,1.1)
            else:_cloth_roll(g,x-1.05+j*.70,-5.5,1.57,j)
    # Interior inventory sits along walls, leaving the entrance and stair route clear.
    for x in [-4.65,-3.25]:
        for y in [1.7,3.25,4.8]:M._crate(g,x,y,.18,1.05,.95,.9)
    for x in [-1.8,0,1.8]:M._barrel(g,x,5.7,.18,.83)
    g.box('wood',(0,front-.65,4.05),(3.0,.14,.58))
    g.box('goldCloth',(0,front-.74,4.05),(2.72,.03,.06))
    return g.objects(item['id'],c,mats,'solid','event_market/shop/'+item['id'])

def _instance(proto,item,c,semantic):
    out=[]
    for source in proto:
        obj=bpy.data.objects.new(item['id']+'/'+source.data.materials[0].name,source.data)
        c.objects.link(obj);obj.location=(*item['center'],0);obj.rotation_euler.z=item['rotation']
        obj['semantic']=semantic+'/'+item['id'];obj['collision']='solid';obj['prototype']=source['source_component'];out.append(obj)
    return out

def apply(B=None):
    layout=json.loads((ROOT/'street_life_layout.json').read_text())
    removed=[]
    for obj in list(bpy.data.objects):
        s=str(obj.get('semantic',''))
        retire=s.startswith(('market/Stall_','market/Cart_','market/Rack_','market/ForegroundCypress')) or s=='market/basin'
        # The formal white outer ring no longer defines the pedestrian market.
        retire=retire or obj.name.startswith(('DISTRICT/Plaza border','PLAZA/Outer border','PLAZA/Paving border'))
        if retire:removed.append(obj.name);bpy.data.objects.remove(obj,do_unlink=True)
    old=bpy.data.collections.get('Street_Life')
    if old:
        for obj in list(old.objects):bpy.data.objects.remove(obj,do_unlink=True)
    c=_collection('Street_Life');mats=_materials();cache={};created=[]
    for item in layout['stalls']:
        key=(item['family'],item['height_extra'])
        if key not in cache:cache[key]=_stall(*key,mats,c)
        created.extend(_instance(cache[key],item,c,'event_market/stall'))
    for item in layout['shops']:
        prototype=_shop(item,mats,c)
        # Each shop is already a complete editable assembly, then placed once.
        for obj in prototype:obj.location=(*item['center'],0);obj.rotation_euler.z=item['rotation'];created.append(obj)
    for prototype in cache.values():
        for obj in prototype:bpy.data.objects.remove(obj,do_unlink=True)
    for name,config in layout['cameras'].items():
        obj=bpy.data.objects.get('CAM_'+name)
        if obj is None:
            data=bpy.data.cameras.new('CAM_'+name);obj=bpy.data.objects.new('CAM_'+name,data);bpy.context.scene.collection.objects.link(obj)
        obj.location=config['position'];obj.rotation_euler=(Vector(config['target'])-obj.location).to_track_quat('-Z','Y').to_euler();obj.data.lens=config['lens']
    market=bpy.data.objects.get('CAM_market')
    if market:
        config=layout['cameras']['street_market_lane'];market.location=config['position']
        market.rotation_euler=(Vector(config['target'])-market.location).to_track_quat('-Z','Y').to_euler();market.data.lens=config['lens']
    bpy.context.view_layer.update()
    # Actual generated projection validation catches kit pieces that exceed a parcel.
    groups={}
    for obj in created:groups.setdefault(str(obj.get('semantic','')),[]).append(obj)
    violations=[]
    for item in layout['stalls']+layout['shops']:
        key=('event_market/stall/' if item['kind']=='stall' else 'event_market/shop/')+item['id']
        objects=groups[key];w,d=item['full_dimensions'];a=item['rotation'];ca,sa=math.cos(a),math.sin(a);x,y=item['center']
        for obj in objects:
            for co in obj.bound_box:
                p=obj.matrix_world@Vector(co);u=(p.x-x)*ca+(p.y-y)*sa;v=-(p.x-x)*sa+(p.y-y)*ca
                if abs(u)>w/2+.035 or abs(v)>d/2+.035:violations.append({'id':item['id'],'object':obj.name,'local':[u,v]})
    if violations:raise RuntimeError('Street-life geometry escaped parcels: '+str(violations[:5]))
    result={'counts':layout['counts'],'created_mesh_objects':len(created),'retired_objects':len(removed),'actual_projection_violations':violations,'source_saved':False}
    report_name='street_life_geometry.json' if bpy.data.filepath else 'street_life_geometry_isolated.json'
    (ROOT/'comparisons'/report_name).write_text(json.dumps(result,indent=2))
    print('STREET_LIFE_GEOMETRY',json.dumps(result),flush=True)
    return result
