"""Additional event-market depth, with conservative clearance checks."""
import bpy
import json
import math
from pathlib import Path
from city import CityGeometry,_collection,_material,_cypress_proto
from market_dressing import _crate,_barrel,_pot,_ring

ROOT=Path(__file__).resolve().parents[1]


def _rectangle(x,y,w,d,a=0,margin=0):
    ca,sa=math.cos(a),math.sin(a)
    return [(x+u*ca-v*sa,y+u*sa+v*ca) for u,v in
            [(-w/2-margin,-d/2-margin),(w/2+margin,-d/2-margin),
             (w/2+margin,d/2+margin),(-w/2-margin,d/2+margin)]]


def _overlap(a,b):
    for poly in [a,b]:
        for p,q in zip(poly,poly[1:]+poly[:1]):
            nx,ny=-(q[1]-p[1]),q[0]-p[0]
            av=[x*nx+y*ny for x,y in a]
            bv=[x*nx+y*ny for x,y in b]
            if max(av)<min(bv) or max(bv)<min(av):return False
    return True


def _world(x,y,a,u,v):
    return (x+u*math.cos(a)-v*math.sin(a),y+u*math.sin(a)+v*math.cos(a))


def _constraints():
    registry=json.loads((ROOT/'market_registry.json').read_text())
    occupied=[]
    for p in registry['stalls']:
        occupied.append((p['id'],_rectangle(*p['center'],8.6,6.5,p['rotation'],.30)))
    for i,(x,y,a) in enumerate([(-45,-126,.8),(49,-128,-.8),(-138,-79,.4),(140,-50,math.pi/2),
                               (-137,34,math.pi/2),(138,61,-math.pi/2)]):
        xx,yy=_world(x,y,a,0,-1.1)
        occupied.append((f'Cart_{i:02}',_rectangle(xx,yy,3.2,6.0,a,.25)))
    for i,(x,y) in enumerate([(-72,-125),(73,-125),(-137,80),(137,80)]):
        occupied.append((f'Basin_{i:02}',_rectangle(x,y,3.3,3.3,0,.2)))
    humans=[]
    path=ROOT/'characters/runtime/crowd_manifest.json'
    if path.exists():
        population=json.loads(path.read_text())
        for item in population.get('instances',[])+population.get('npcs',[]):
            p=item.get('sourcePosition')
            if p and p[2]<2:humans.append((item['id'],p[0],p[1]))
    return registry,occupied,humans


def _clear(poly,occupied,humans):
    collisions=[name for name,q in occupied if _overlap(poly,q)]
    collisions += [name for name,x,y in humans if _overlap(poly,_rectangle(x,y,1.1,1.1))]
    for x,y in poly:
        if (x/119)**2+(y/96)**2<1:collisions.append('circumferential-route')
        if -8<x<8 and -145<y<-83:collisions.append('central-avenue')
    return sorted(set(collisions))


def _workshop(mats,collection):
    g=CityGeometry()
    # Plank platform, three shallow approach treads, and a central aisle.
    for x in [-8,-4,0,4,8]:g.box('wood',(x,0,.19),(.22,7.8,.38))
    for i in range(40):g.box('woodLight',(-8.9+(i+.5)*17.8/40,0,.44),(17.8/40-.02,7.8,.16))
    for i in range(3):
        top=(i+1)*.15
        g.box('woodLight',(0,-4.7+i*.30,top/2),(4.0,.30,top))
    for x in [-8.45,-2.9,2.9,8.45]:
        for y in [-3.5,3.5]:
            g.box('wood',(x,y,2.39),(.24,.24,4.5))
            g.box('iron',(x,y,.61),(.28,.28,.12))
            g.beam('woodLight',(x,y,3.9),(x+(.8 if x<0 else -.8),y,4.5),.09,6)
    for y in [-3.5,3.5]:g.box('woodLight',(0,y,4.56),(17.6,.24,.24))
    for x in [-8.45,-2.9,2.9,8.45]:
        g.box('wood',(x,0,4.48),(.22,7.6,.22))
        g.box('wood',(x,0,4.97),(.20,.20,1.0))
    g.box('woodLight',(0,0,5.42),(17.8,.20,.20))
    # Tensioned cloth follows its structural ridge and softened lower edges.
    nx,ny=36,16
    vertices=[]
    for j in range(ny+1):
        y=-4+8*j/ny
        for i in range(nx+1):
            x=-9+18*i/nx
            edge=4.55-.22*(math.sin((x+9)/18*math.pi*3)**2)
            z=edge+(5.53-edge)*(1-abs(y)/4)
            vertices.append((x,y,z))
    for j in range(ny):
        for i in range(nx):
            q=j*(nx+1)+i
            g.mesh('cloth',[vertices[q],vertices[q+1],vertices[q+nx+2],vertices[q+nx+1]],[(0,1,2,3),(3,2,1,0)])
    for yy in [-4,4]:
        for i in range(36):
            x=-9+i*.5
            z=4.55-.22*(math.sin((x+9)/18*math.pi*3)**2)
            g.mesh('clothEdge',[(x,yy,z),(x+.5,yy,z),(x+.5,yy,z-.23),(x+.25,yy,z-.35),(x,yy,z-.23)],[(0,1,2,3,4),(4,3,2,1,0)])
    for x in [-5.5,5.5]:
        for yy in [-2.25,1.8]:
            g.box('woodLight',(x,yy,1.46),(4.6,1.3,.15))
            for dx in [-1.9,1.9]:
                for dy in [-.46,.46]:g.box('wood',(x+dx,yy+dy,.97),(.17,.17,.90))
            for i in range(5):_pot(g,x-1.8+i*.85,yy,1.55,.75+(i%2)*.16,i)
    for x in [-7.8,-6.5,6.5,7.8]:_barrel(g,x,.15,.52,.88)
    for x in [-4.4,4.4]:
        _crate(g,x,2.8,.52,1.2,1.1,.95)
        _crate(g,x,2.8,1.47,1.0,.9,.8)
    # Back storage shelving has legs, boards and grouped goods rather than loose clutter.
    for x in [-2.4,2.4]:g.box('wood',(x,3.1,1.85),(.18,.18,2.65))
    for z in [.75,1.6,2.5]:
        g.box('woodLight',(0,3.1,z),(5.0,.8,.12))
        for x in [-1.8,-.6,.6,1.8]:_pot(g,x,3.1,z+.065,.57)
    return g.objects('WorkshopPrototype',collection,mats,'solid','market/workshop')


def _goods_rack(mats,collection):
    g=CityGeometry()
    for x in [-1.4,1.4]:g.box('wood',(x,0,1.05),(.12,.13,2.1))
    for z in [.23,1.05,1.9]:
        g.box('woodLight',(0,0,z),(3.0,.8,.11))
        for x in [-1.1,0,1.1]:_pot(g,x,0,z+.06,.50)
    _crate(g,-1.0,.65,0,.7,.65,.75)
    _barrel(g,1.03,.6,0,.62)
    return g.objects('GoodsRackPrototype',collection,mats,'solid','market/stacked-goods')


def _copy(assembly,name,x,y,a,collection,scale=1):
    for p in assembly:
        obj=bpy.data.objects.new(name+'/'+p.data.materials[0].name,p.data)
        collection.objects.link(obj)
        obj.location=(x,y,0)
        obj.rotation_euler.z=a
        obj.scale=(scale,scale,scale)
        obj['semantic']='market/'+name
        obj['collision']='none' if name.startswith('ForegroundCypress') else 'solid'
        obj['prototype']=p['source_component']


def add_temple_threshold(api=None,spec=None):
    name='TEMPLE/Cella intermediate threshold'
    if bpy.data.objects.get(name):return {'already_present':True,'name':name}
    if api is not None:
        api.box(name,(10,156.45,12.36),(9,.7,.20),'light',collection='City_Architecture')
    else:
        mat=_material('stone',(.63,.56,.43))
        g=CityGeometry()
        g.box('stone',(10,156.45,12.36),(9,.7,.20))
        g.objects(name,_collection('City_Architecture'),{'stone':mat},'solid','city/temple/threshold')
    return {'name':name,'center':[10,156.45,12.36],'full_dimensions':[9,.7,.20],'top':12.46}


def refine_market(api=None,spec=None):
    registry,occupied,humans=_constraints()
    collection=_collection('Market_Refinement')
    colors={'wood':((.22,.12,.052),.91,0),'woodLight':((.42,.26,.12),.90,0),
            'iron':((.085,.08,.067),.50,.5),'cloth':((.32,.067,.037),.94,0),
            'clothEdge':((.55,.32,.10),.93,0),'pot':((.49,.22,.10),.90,0),
            'potDark':((.30,.13,.07),.93,0),'potRim':((.62,.31,.14),.88,0),
            'bark':((.21,.15,.09),.95,0),'leaf':((.14,.205,.075),.93,0),
            'leafDark':((.075,.13,.055),.96,0)}
    mats={k:_material('Refinement_'+k,*v) for k,v in colors.items()}
    workshop=_workshop(mats,collection)
    rack=_goods_rack(mats,collection)
    tree=_cypress_proto(mats,collection)
    placed=[]
    for i,x in enumerate([-64,64]):
        poly=_rectangle(x,-134,18.6,9.8,math.pi,.25)
        conflicts=_clear(poly,occupied,humans)
        if conflicts:raise RuntimeError(f'Workshop {i} clearance conflict: {conflicts}')
        _copy(workshop,f'Workshop_{i}',x,-134,math.pi,collection)
        occupied.append((f'Workshop_{i}',poly))
        placed.append({'id':f'Workshop_{i}','center':[x,-134],'rotation':math.pi,'full_projection':[18.6,9.8]})
    racks=[]
    for p in registry['stalls']:
        if int(p['id'].split('_')[-1])%2:continue
        x,y=p['center'];a=p['rotation']
        rx,ry=_world(x,y,a,0,5.0)
        poly=_rectangle(rx,ry,3.3,2.0,a,.20)
        if _clear(poly,occupied,humans):continue
        _copy(rack,'Rack_'+p['id'],rx,ry,a,collection)
        occupied.append(('Rack_'+p['id'],poly))
        racks.append({'parent':p['id'],'center':[rx,ry],'rotation':a})
    tree_positions=[]
    for i,(x,y) in enumerate([(-85,-115),(85,-115),(-100,-100),(100,-100)]):
        # Trunk clearance, plus a conservative low crown envelope.
        poly=_rectangle(x,y,3.6,3.6,0,.2)
        if _clear(poly,occupied,humans):
            found=False
            for dx,dy in [(0,-4),(-4,0),(4,0),(0,4)]:
                q=_rectangle(x+dx,y+dy,3.6,3.6,0,.2)
                if not _clear(q,occupied,humans):x,y,poly,found=x+dx,y+dy,q,True;break
            if not found:raise RuntimeError(f'Foreground cypress {i} has no clear placement')
        _copy(tree,f'ForegroundCypress_{i}',x,y,i*.81,collection,1.7)
        occupied.append((f'ForegroundCypress_{i}',poly))
        tree_positions.append([x,y,0])
    for assembly in [workshop,rack,tree]:
        for obj in assembly:bpy.data.objects.remove(obj,do_unlink=True)
    threshold=add_temple_threshold(api,spec)
    return {'workshops':placed,'goods_racks':racks,'foreground_cypresses':tree_positions,
            'existing_human_anchors_checked':len(humans),'full_projection_conflicts':[],
            'protected_route_ellipse':[119,96],'temple_threshold':threshold}
