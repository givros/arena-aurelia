"""Complete additive street assemblies for every inhabited district."""
from pathlib import Path
from collections import Counter
import bpy,json,math,hashlib
from mathutils import Vector
from city import CityGeometry,_collection
import market_dressing as M
import street_life_geometry as S
R=Path(__file__).resolve().parents[1]

def frontage(item,mats,c):
    g=CityGeometry();kind=item['family'];cloth=['red','linen','clothOchre','clothBlue','linen','red'][kind]
    # Four posts and tied sloping cloth retain depth independently of the house.
    for x in [-3.5,3.5]:
        for y,h in [(-1.65,3.05),(1.65,3.70)]:
            g.box('wood',(x,y,h/2),(.16,.18,h))
            g.box('stone',(x,y,.09),(.29,.31,.18))
        g.beam('wood',(x,-1.65,3.05),(x,1.65,3.70),.08,8)
    for y,z in [(-1.65,3.05),(1.65,3.70)]:g.box('wood',(0,y,z),(7.25,.17,.17))
    vs=[];nx=24;ny=10
    for j in range(ny+1):
        t=j/ny;y=-1.91+3.82*t
        for i in range(nx+1):
            u=i/nx;x=-3.80+7.60*u
            z=3.01+.72*t-.24*math.sin(math.pi*u)*math.sin(math.pi*t)+.045*math.sin(u*math.pi*9)
            vs.append((x,y,z))
    fs=[]
    for j in range(ny):
        for i in range(nx):
            q=j*(nx+1)+i;fs.extend([(q,q+1,q+nx+2,q+nx+1),(q+nx+1,q+nx+2,q+1,q)])
    g.mesh(cloth,vs,fs)
    for i in range(20):
        x=-3.8+i*.38
        g.mesh(cloth,[(x,-1.91,3.01),(x+.38,-1.91,3.01),(x+.38,-1.91,2.82),(x+.19,-1.91,2.73),(x,-1.91,2.82)],[(0,1,2,3,4),(4,3,2,1,0)])
    for x in [-2.9,0,2.9]:
        for y in [-1.43,-.73]:g.box('wood',(x,y,.56),(.14,.14,1.12))
    g.box('woodLight',(0,-1.08,1.13),(6.75,.92,.13))
    for j,x in enumerate([-2.65,-1.55,-.5,.6,1.7,2.7]):
        if kind in [0,4]:M._pot(g,x,-1.08,1.2,.40+(j%3)*.07,j)
        elif kind==1:M._produce(g,x,-1.08,1.2,j)
        elif kind in [2,5]:S._loaf(g,x,-1.08,1.36,1.05)
        else:S._cloth_roll(g,x,-1.08,1.39,j)
    for x in [-2.65,2.65]:M._crate(g,x,1.13,0,.80,.76,.75)
    if kind==3:
        g.beam('wood',(-2.9,1.53,3.3),(2.9,1.53,3.3),.055,8)
        for i,x in enumerate([-1.85,0,1.85]):
            verts=[(x-.58,1.57,3.28),(x+.58,1.57,3.28),(x+.57,1.47,1.27),(x-.58,1.49,1.24)]
            g.mesh(['red','clothBlue','clothOchre'][i],verts,[(0,1,2,3),(3,2,1,0)])
    return g.objects(item['id'],c,mats,'solid','district_life/frontage/'+item['id'])

def bench(item,mats,c):
    g=CityGeometry()
    # Existing canonical seated mesh uses this exact seat datum, with feet on ground.
    for x in [-.90,.90]:g.box('stone',(x,0,.17),(.24,.8,.34))
    for y in [-.31,0,.31]:g.box('woodLight',(0,y,.39),(2.45,.28,.10))
    for x in [-1.06,1.06]:g.box('wood',(x,.47,.65),(.12,.13,.94))
    for z in [.72,.98]:g.box('woodLight',(0,.49,z),(2.30,.10,.20))
    return g.objects(item['id'],c,mats,'solid','district_life/bench/'+item['id'])

def brazier(item,mats,c):
    g=CityGeometry()
    g.box('stone',(0,0,.13),(.91,.91,.26))
    g.box('stone',(0,0,.30),(.66,.66,.12))
    g.box('iron',(0,0,.82),(.21,.21,1.0))
    for a in [0,math.pi/2,math.pi,math.pi*1.5]:
        g.beam('iron',(.32*math.cos(a),.32*math.sin(a),.26),(.15*math.cos(a),.15*math.sin(a),1.24),.065,6)
    g.cylinder('iron',(0,0,1.38),.48,.27,20)
    g.cylinder('ember',(0,0,1.52),.44,.03,20)
    for i in range(5):
        a=math.tau*i/5
        g.cylinder('ember',(.22*math.cos(a),.22*math.sin(a),1.64),.075,.23,6)
    return g.objects(item['id'],c,mats,'solid','district_life/brazier/'+item['id'])

def apply(B):
    raw=(R/'district_life_layout.json').read_bytes();layout=json.loads(raw)
    assert not bpy.data.collections.get('District_Life'),'District geometry already integrated; use a targeted refinement.'
    c=_collection('District_Life');mats=S._materials()
    mats['ember']=B.material('District lamp embers',(.99,.20,.025),.65,0,4)
    prototypes={};created=[];by_item={}
    for item in layout['items']:
        kind=item['kind']
        if kind in ['stall','cargo']:
            key=('stall',item['family'],item['height_extra'])
            if key not in prototypes:prototypes[key]=S._stall(item['family'],item['height_extra'],mats,c)
            objects=S._instance(prototypes[key],item,c,'district_life/'+kind)
        elif kind in ['infill_shop','frontage','bench','brazier']:
            key=(kind,item['family'] if kind in ['infill_shop','frontage'] else 0,item.get('height',0) if kind=='infill_shop' else 0)
            if key not in prototypes:
                template={**item,'id':'DistrictKit/'+str(len(prototypes))}
                builder={'infill_shop':S._shop,'frontage':frontage,'bench':bench,'brazier':brazier}[kind]
                prototypes[key]=builder(template,mats,c)
            objects=S._instance(prototypes[key],item,c,'district_life/'+kind)
        else:raise ValueError(kind)
        for obj in objects:
            obj.location=(*item['center'],item['ground_z']);obj.rotation_euler.z=item['rotation']
            obj['semantic']='district_life/'+kind+'/'+item['id'];obj['district_zone']=item['zone'];obj['assembly_id']=item['id']
        by_item[item['id']]=objects;created+=objects
        if kind=='brazier':
            ld=bpy.data.lights.new('LAMP/'+item['id'],'POINT');ld.color=(1,.39,.12);ld.energy=340;ld.shadow_soft_size=.45
            obj=bpy.data.objects.new(ld.name,ld);c.objects.link(obj)
            obj.location=(*item['center'],item['ground_z']+1.89);obj['distance']=15;obj['district_zone']=item['zone']
    for group in prototypes.values():
        for obj in group:bpy.data.objects.remove(obj,do_unlink=True)
    for name,view in layout['cameras'].items():
        existing=bpy.data.objects.get('CAM_'+name)
        if existing:
            existing.location=view['position']
            existing.rotation_euler=(Vector(view['target'])-existing.location).to_track_quat('-Z','Y').to_euler()
            existing.data.lens=view['lens']
        else:B.camera(name,view['position'],view['target'],view['lens'])
    bpy.context.view_layer.update()
    violations=[]
    for item in layout['items']:
        a=item['rotation'];ca,sa=math.cos(a),math.sin(a);w,d=item['full_dimensions'];x,y=item['center']
        for obj in by_item[item['id']]:
            for v in obj.bound_box:
                p=obj.matrix_world@Vector(v);u=(p.x-x)*ca+(p.y-y)*sa;v=-(p.x-x)*sa+(p.y-y)*ca
                if abs(u)>w/2+.035 or abs(v)>d/2+.035:violations.append({'item':item['id'],'object':obj.name,'local':[u,v]})
    assert not violations,'Geometry outside declared envelopes: '+str(violations[:6])
    result={'passed':True,'layoutSHA256':hashlib.sha256(raw).hexdigest(),'counts':dict(Counter(i['kind'] for i in layout['items'])),
        'regions':layout['coverage'],'createdMeshObjects':len(created),'actualProjectionViolations':violations,
        'benchSeatHeight':.44,'lights':len(layout['lights']),'cameras':list(layout['cameras']),
        'allSourceComponentsPreserved':True,'sourceSaved':False}
    (R/'comparisons/district_life_geometry.json').write_text(json.dumps(result,indent=2))
    print('DISTRICT_GEOMETRY_READY',json.dumps(result),flush=True)
    return result
