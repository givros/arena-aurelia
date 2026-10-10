"""Local overhead market grouping; no parcel or population-anchor changes."""
import bpy,json,math
from pathlib import Path
from mathutils import Vector
from city import CityGeometry,_collection,_material
from street_life_geometry import _materials
from street_life_layout import world
from street_life_layout import rectangle,inside,poly_distance
from market_dressing import _cart

ROOT=Path(__file__).resolve().parents[1]

def _anchor(item,dx,dy,z):
    choices=[world(item,x,y,z) for x in [-3.29975,3.29975] for y in [-2.45,2.45]]
    return max(choices,key=lambda p:(p[0]-item['center'][0])*dx+(p[1]-item['center'][1])*dy)

def _sail(g,points,material,seed):
    center=[sum(p[i] for p in points)/len(points) for i in range(3)]
    center[2]=4.95+.12*(seed%3)
    minimum=99
    # Triangular patches share the low center and bowed, tensioned boundaries.
    for face,(a,b) in enumerate(zip(points,points[1:]+points[:1])):
        n=20;vs=[];indices={}
        for i in range(n+1):
            for j in range(n+1-i):
                u=i/n;v=j/n;t=1-u-v
                p=[u*a[k]+v*b[k]+t*center[k] for k in range(3)]
                p[2]-=.22*math.sin(math.pi*u)*math.sin(math.pi*v)
                indices[(i,j)]=len(vs);vs.append(p);minimum=min(minimum,p[2])
        fs=[]
        for i in range(n):
            for j in range(n-i):
                tri=(indices[(i,j)],indices[(i+1,j)],indices[(i,j+1)])
                fs.extend([tri,tuple(reversed(tri))])
                if j<n-i-1:
                    tri=(indices[(i+1,j)],indices[(i+1,j+1)],indices[(i,j+1)])
                    fs.extend([tri,tuple(reversed(tri))])
        g.mesh(material,vs,fs)
        # Visible doubled edge seams and ropes follow each sagging fabric edge.
        previous=None
        for i in range(25):
            t=i/24;p=[a[k]*(1-t)+b[k]*t for k in range(3)];p[2]-=.055*math.sin(math.pi*t)
            if previous:g.beam('rope',previous,p,.038,6)
            previous=p
        g.beam('rope',a,center,.022,6)
    return minimum

def apply(B=None):
    layout=json.loads((ROOT/'street_life_layout.json').read_text());items={int(s['id'].split('_')[-1]):s for s in layout['stalls']}
    c=_collection('Street_Life_Overhead');mats=_materials()
    mats['sailRusset']=_material('Sail_worn_russet',(.37,.105,.06),.96)
    mats['sailFlax']=_material('Sail_warm_flax',(.64,.49,.30),.97)
    mats['sailOchre']=_material('Sail_dull_ochre',(.47,.275,.11),.97)
    # Six unequal group silhouettes bridge selected courts at generous headroom.
    groups=[
      [(0,1,1,6.40),(2,-1,1,6.95),(14,-1,-1,6.10)],
      [(3,1,1,6.15),(5,-1,1,7.05),(17,-1,-1,6.40),(16,1,-1,5.90)],
      [(6,-1,1,6.30),(8,1,1,6.90),(20,1,-1,6.00)],
      [(9,-1,1,6.75),(11,1,1,6.20),(31,1,-1,7.10),(22,-1,-1,6.20)],
      [(56,1,-1,6.50),(78,-1,0,6.10),(60,1,1,7.00)],
      [(45,-1,-1,6.15),(46,1,-1,6.95),(57,1,1,6.30),(48,-1,1,6.45)]]
    evidence=[]
    for i,group in enumerate(groups):
        name=f'CourtShade_{i:02}'
        if any(o.get('semantic')=='event_market/shade/'+name for o in c.objects):continue
        g=CityGeometry();points=[];supports=[]
        for idx,dx,dy,z in group:
            p=_anchor(items[idx],dx,dy,z);points.append(p);supports.append({'stall':items[idx]['id'],'position':p})
            # Sister masts are attached exactly to existing canopy corner posts.
            g.beam('wood',(p[0],p[1],3.00),(p[0],p[1],p[2]+.20),.095,10)
            for zz in [3.12,3.40]:g.cylinder('iron',(p[0],p[1],zz),.117,.075,10)
            g.cylinder('goldCloth',(p[0],p[1],p[2]+.23),.12,.16,8,.05)
        center=[sum(p[k] for p in points)/len(points) for k in [0,1]]
        points.sort(key=lambda p:math.atan2(p[1]-center[1],p[0]-center[0]))
        low=_sail(g,points,['sailRusset','sailFlax','sailOchre','sailRusset','sailFlax','sailRusset'][i],i)
        objects=g.objects(name,c,mats,'none','event_market/shade/'+name)
        evidence.append({'id':name,'anchors':supports,'minimum_cloth_z':round(low,4),'collision':'none','objects':len(objects)})
    folded=[]
    for idx in [1,7,12,17,26,31,44,55,59,64,78,83]:
        item=items[idx];prefix='event_market/stall/'+item['id']
        for obj in bpy.context.scene.objects:
            if obj.type!='MESH' or obj.get('semantic')!=prefix:continue
            mat=obj.data.materials[0]
            if mat.name not in ['City/Event_red','City/Event_linen']:continue
            if obj.get('folded_back_roof'):continue
            obj.data=obj.data.copy()
            for v in obj.data.vertices:
                if v.co.y>0 and v.co.z>2.7:
                    y=v.co.y;v.co.y*=.23;v.co.z+=.55*y/2.75
            obj['folded_back_roof']=True;folded.append(obj.name)
        g=CityGeometry();x,y=item['center']
        # A folded cloth ridge is inside the prevalidated stall envelope.
        for dx in [-2.8,2.8]:
            a=world(item,dx,.62,4.13+item['height_extra']);b=world(item,dx,.62,4.32+item['height_extra'])
            g.beam('rope',a,b,.028,6)
        g.objects('FoldedRidge_'+item['id'],c,mats,'none','event_market/overhead-detail')
    recolored=[]
    palette=[(.43,.19,.08),(.56,.405,.235),(.28,.045,.025),(.51,.28,.095),(.40,.34,.24)]
    for idx in [3,4,8,13,15,19,21,23,27,29,32,34,39,42,47,51,56,62,66,70,76,81]:
        for obj in bpy.context.scene.objects:
            if obj.type!='MESH' or obj.get('semantic')!='event_market/stall/'+items[idx]['id']:continue
            mat=obj.data.materials[0]
            if mat.name not in ['City/Event_red','City/Event_linen']:continue
            color=palette[(idx*3)%len(palette)];new=_material('Court_cloth_'+str((idx*3)%len(palette)),color,.97)
            obj.data=obj.data.copy();obj.data.materials[0]=new;recolored.append(obj.name)
    # Goods remain within occupied parcels. Higher hanging rugs supply visual layers.
    for idx in [0,5,8,16,21,27,34,40,48,55,61,73]:
        item=items[idx];g=CityGeometry()
        for x in [-2.7,2.7]:g.box('wood',(x,2.48,1.42),(.12,.13,2.84))
        g.beam('rope',(-2.7,2.48,2.72),(2.7,2.48,2.72),.026,6)
        for j,x in enumerate([-1.72,0,1.72]):
            vs=[]
            for k in range(13):
                xx=x-.65+1.3*k/12;yy=2.48+.07*math.sin(k*math.pi/3)
                vs.extend([(xx,yy,2.69),(xx,yy,.77+.07*math.cos(k*math.pi/3))])
            fs=[]
            for k in range(12):fs.extend([(2*k,2*k+2,2*k+3,2*k+1),(2*k+1,2*k+3,2*k+2,2*k)])
            g.mesh(['red','clothOchre','clothBlue'][(j+idx)%3],vs,fs)
        objects=g.objects('HangingRugs_'+item['id'],c,mats,'solid','event_market/within-parcel')
        for obj in objects:obj.location=(*item['center'],0);obj.rotation_euler.z=item['rotation']
    # Full wheeled loading carts occupy existing workshop aisles and two shop
    # inventory rooms; their shafts stay inside already occupied parcels.
    cart_prototype=_cart(mats,c);cart_records=[]
    placements=[('WorkshopCart_W',{'center':[-62,-117],'rotation':math.pi},0,.75,.58),
                ('WorkshopCart_E',{'center':[62,-117],'rotation':math.pi},0,.75,.58)]
    shop_lookup={s['id']:s for s in layout['shops']}
    for sid in ['ShopHouse_03','ShopHouse_12']:
        placements.append(('InventoryCart_'+sid,shop_lookup[sid],0,3.1,.24))
    for name,owner,u,v,z in placements:
        position=world(owner,u,v,z);a=owner['rotation'];cx,cy=world(owner,u,v-1.1)[:2]
        polygon=rectangle(cx,cy,3.0,6.1,a)
        conflicts=[p['id'] for p in layout['anchors']+layout['vendors'] if poly_distance(p['position'],polygon)<.38]
        if conflicts:raise RuntimeError('Loading cart collides with foot anchors: '+name+' '+str(conflicts))
        for source in cart_prototype:
            obj=bpy.data.objects.new(name+'/'+source.data.materials[0].name,source.data);c.objects.link(obj)
            obj.location=position;obj.rotation_euler.z=a;obj['semantic']='event_market/loading-cart/'+name;obj['collision']='solid'
        cart_records.append({'id':name,'position':position,'rotation':a,'source':'complete existing HandcartFamily','anchor_conflicts':[]})
    for obj in cart_prototype:bpy.data.objects.remove(obj,do_unlink=True)
    result={'shade_groups':evidence,'folded_roof_components':len(folded),'recolored_components':len(recolored),
            'hanging_rug_assemblies':12,'footprints_changed':False,'population_anchors_changed':False,'minimum_requested_headroom':3.3,'source_saved':False}
    result['loading_carts']=cart_records
    (ROOT/'comparisons/street_life_canopy_refinement.json').write_text(json.dumps(result,indent=2))
    print('STREET_LIFE_CANOPIES',json.dumps({k:v for k,v in result.items() if k!='shade_groups'}),flush=True)
    return result
