"""Shared deterministic event-market parcels, foot anchors and clear alley loops."""
import json, math, random
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SEED=74129

def rectangle(x,y,w,d,a=0):
    ca,sa=math.cos(a),math.sin(a)
    return [[x+u*ca-v*sa,y+u*sa+v*ca] for u,v in [(-w/2,-d/2),(w/2,-d/2),(w/2,d/2),(-w/2,d/2)]]

def overlap(a,b,margin=0):
    for p in (a,b):
        for q,r in zip(p,p[1:]+p[:1]):
            nx,ny=-(r[1]-q[1]),r[0]-q[0];s=math.hypot(nx,ny)
            av=[x*nx+y*ny for x,y in a];bv=[x*nx+y*ny for x,y in b]
            if max(av)+margin*s<=min(bv) or max(bv)+margin*s<=min(av):return False
    return True

def segment_distance(p,a,b):
    dx,dy=b[0]-a[0],b[1]-a[1]
    t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/(dx*dx+dy*dy or 1)))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)

def inside(p,poly):
    signs=[]
    for a,b in zip(poly,poly[1:]+poly[:1]):signs.append((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
    return all(s>=-1e-7 for s in signs) or all(s<=1e-7 for s in signs)

def poly_distance(p,poly):
    return 0 if inside(p,poly) else min(segment_distance(p,a,b) for a,b in zip(poly,poly[1:]+poly[:1]))

def ellipse_clear(poly,rx=110,ry=87):
    scaled=[[p[0]/rx,p[1]/ry] for p in poly]
    return poly_distance((0,0),scaled)>=1

def world(item,u,v,z=0):
    x,y=item['center'];a=item['rotation'];ca,sa=math.cos(a),math.sin(a)
    return [round(x+u*ca-v*sa,5),round(y+u*sa+v*ca,5),z]

def segment_samples(a,b,spacing=.45):
    n=max(1,math.ceil(math.dist(a[:2],b[:2])/spacing))
    return [[a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n] for i in range(n+1)]

def facade_ambulatory_points():
    """Facade circuit with a real forecourt detour around entry monuments."""
    ellipse=[[round(108*math.cos(i*math.tau/128),5),round(85*math.sin(i*math.tau/128),5),.02] for i in range(129)]
    return ellipse[:92]+[[-22.5,-84.3,.02],[-22.5,-94.3,.02],[22.5,-94.3,.02],[22.5,-84.3,.02]]+ellipse[101:]

def append_entry_gathering(layout):
    """Unroofed waiting/conversation groups beside the protected ceremonial axis."""
    if any(a['id'].startswith('EntryGathering_') for a in layout['anchors']):return layout
    rng=random.Random(SEED+173)
    human=[a['position'] for a in layout['anchors']+layout['vendors']]
    guard_polys=[q['polygon'] for q in layout['footprint_obstacles'] if q['kind']=='protected_guard']
    solids=[q['polygon'] for q in layout['footprint_obstacles'] if q['kind']!='protected_guard']
    loops=[(a,b) for r in layout['routes'] for a,b in zip(r['points'],r['points'][1:])]
    protected=[(a,b,r['width']/2+.38) for r in layout['clear_routes'] for a,b in zip(r['points'],r['points'][1:])]
    east=[(5.8,-120.0,5),(9.5,-119.0,7),(6.2,-115.5,6),(9.8,-114.8,4),
          (5.8,-111.0,8),(9.6,-110.8,5),(5.8,-102.4,7),(9.7,-103.0,6),
          (5.6,-98.0,4),(9.4,-97.6,8)]
    west=[(5.7,-119.0,6),(9.5,-120.2,4),(5.8,-114.6,7),(9.7,-115.9,5),
          (5.7,-110.2,5),(9.5,-111.6,8),(5.7,-102.8,6),(9.6,-101.8,7),
          (5.8,-97.9,8),(9.5,-97.3,4),(5.8,-106.3,7),(9.4,-106.8,7)]
    groups=[]
    for side,definitions in [(1,east),(-1,west)]:
        for j,(cx,cy,count) in enumerate(definitions):
            center=[side*cx,cy];group=f'EntryCourt_{"east" if side>0 else "west"}_{j:02}'
            accepted=[]
            # One varied ring makes every group a legible social unit. Small
            # rotations/elliptical proportions avoid rows or bilateral symmetry.
            for trial in range(220):
                angle=rng.uniform(0,math.tau);radius=max(.86,.56/math.sin(math.pi/count))
                squash=rng.uniform(.84,1.04);shift=[rng.uniform(-.25,.25),rng.uniform(-.25,.25)]
                points=[]
                for k in range(count):
                    a=angle+k*math.tau/count
                    p=[round(center[0]+shift[0]+radius*squash*math.cos(a),4),round(center[1]+shift[1]+radius/squash*math.sin(a),4),.02]
                    if not 4.5<=abs(p[0])<=11 or not -122<=p[1]<=-96:break
                    if any(math.dist(p[:2],q[:2])<1.0 for q in human+points):break
                    if any(poly_distance(p,q)<.45 for q in solids+guard_polys):break
                    if any(segment_distance(p,a,b)<.86 for a,b in loops):break
                    if any(segment_distance(p,a,b)<w for a,b,w in protected):break
                    points.append(p)
                if len(points)==count:accepted=points;break
            if not accepted:continue
            for k,p in enumerate(accepted):
                facing=math.atan2(center[1]-p[1],center[0]-p[0])-math.pi/2
                layout['anchors'].append({'id':f'EntryGathering_{len(groups):02}_{k:02}',
                    'position':p,'facing':facing,'activity':'conversation' if j%3 else 'queue',
                    'role':'citizen','groupId':group})
                human.append(p)
            groups.append({'id':group,'center':center,'count':len(accepted),'activity':'waiting for admission' if j%3==0 else 'conversation'})
    layout['entry_gathering_groups']=groups
    layout['counts']['entry_gathering_patrons']=sum(g['count'] for g in groups)
    layout['counts']['static_patrons']=len(layout['anchors'])
    return layout

def build_layout():
    rng=random.Random(SEED)
    city=json.loads((ROOT/'city_registry.json').read_text())
    old=json.loads((ROOT/'market_registry.json').read_text())
    occupied=[]
    for p in city['parcels']:
        if p['center'][1]>110:continue
        w,d=p['projection_envelope'];a=p.get('rotation',0)
        if p['id'].startswith('ForegroundHouse'):a=0
        occupied.append({'id':p['id'],'kind':'existing_house','polygon':rectangle(*p['center'],w,d,a)})
    for i,x in enumerate([-62,62]):occupied.append({'id':f'Workshop_{i}','kind':'workshop','polygon':rectangle(x,-117,18.6,9.8,math.pi)})
    manifest=json.loads((ROOT/'characters/runtime/crowd_manifest.json').read_text())
    guards=[o for o in manifest.get('instances',[])+manifest.get('npcs',[]) if o.get('zone')=='gate_guard']
    for g in guards:
        x,y,z=g['sourcePosition'];occupied.append({'id':g['id'],'kind':'protected_guard','polygon':rectangle(x,y,1.2,1.2)})
    for x in [-13,13]:occupied.append({'id':f'Ceremonial_statue_{x}','kind':'monument','polygon':rectangle(x,-90,6,6)})
    # Entrance thresholds and existing monumental braziers get their own room.
    reserved=[{'id':'ceremonial_axis','polygon':rectangle(0,-128,6,92),'width':6},
              {'id':'ceremonial_threshold','polygon':rectangle(0,-90,42,17),'width':6},
              {'id':'east_gate','polygon':rectangle(132,0,59,6),'width':6},
              {'id':'west_gate','polygon':rectangle(-132,0,59,6),'width':6},
              {'id':'north_gate','polygon':rectangle(0,106,6,47),'width':6}]
    def accept(item):
        p=item['polygon']
        if not ellipse_clear(p):return False
        if any(overlap(p,q['polygon'],.20) for q in occupied):return False
        if any(overlap(p,q['polygon']) for q in reserved):return False
        occupied.append(item);return True
    shops=[]
    placements=[]
    for side in [-1,1]:
        for y in [-147,-130]:placements.append((side*14,y,math.pi/2 if side<0 else -math.pi/2,'Avenue'))
        for x,y in [(35,-129),(49,-134),(83,-126),(98,-112)]:placements.append((side*x,y,math.pi,'Southern'))
        for y in [-61,-31,24,55]:placements.append((side*138,y,-math.pi/2 if side>0 else math.pi/2,'Side'))
    for i,(x,y,a,zone) in enumerate(placements):
        item={'id':f'ShopHouse_{i:02}','kind':'shop_house','zone':zone,'center':[x,y],'rotation':a,
              'full_dimensions':[13,16],'height':10.8+(i%3)*1.65,'family':i%5,'polygon':rectangle(x,y,13,16,a)}
        if accept(item):shops.append(item)
    stalls=[];candidates=[]
    # Closely set opposite-facing rows form southern courts rather than rings.
    for row,y in enumerate([-91,-102,-113]):
        for side in [-1,1]:
            for x in [17,28.4,39.8,51.2,75,86.4,97.8]:
                candidates.append((side*x,y,0 if row%2==0 else math.pi,'SouthWest' if side<0 else 'SouthEast'))
    # Stepped corner courts adapt to the oval while keeping their own alley rhythm.
    for side in [-1,1]:
        for y in [-78,-66.5,-55,55,66.5,78]:
            for x in [76,87.4,98.8]:candidates.append((side*x,y,0 if y<0 else math.pi,'CornerWest' if side<0 else 'CornerEast'))
    for row,x in enumerate([114,125]):
        for y in [-67,-55.6,-44.2,-32.8,-21.4,-10,10,21.4,32.8,44.2,55.6,67]:
            for side in [-1,1]:
                a=(math.pi/2 if side<0 else -math.pi/2)+(math.pi if row else 0)
                candidates.append((side*x,y,a,'WestSouk' if side<0 else 'EastSouk'))
    for x,y,a,zone in candidates:
        # Small authored height/canopy differences retain full-size tables and goods.
        i=len(stalls);variation=(i%5-2)*.004
        item={'id':f'EventStall_{i:03}','kind':'stall','zone':zone,'center':[x,y],
              'rotation':a+variation,'full_dimensions':[8.6,6.5],'height_extra':[0,.22,.48,-.15,.32][i%5],
              'family':i%6,'activity':['pottery','produce','bread','cloth','cookshop','loading'][i%6],
              'polygon':rectangle(x,y,8.6,6.5,a+variation)}
        if accept(item):stalls.append(item)
        if len(stalls)>=84:break
    # Locally closed porter/customer loops use actual free corridors. Their entire
    # sampled centerline is kept at least 1.25m from full occupied projections.
    solid=[o for o in occupied if o['kind']!='protected_guard']
    routes=[]
    for item in stalls:
        points=[world(item,u,v) for u,v in [(-5.75,-4.70),(5.75,-4.70),(5.75,4.70),(-5.75,4.70),(-5.75,-4.70)]]
        safe=True;minimum=99
        for a,b in zip(points,points[1:]):
            for p in segment_samples(a,b):
                if (p[0]/107.7)**2+(p[1]/84.7)**2<1:safe=False;break
                d=min(poly_distance(p,q['polygon']) for q in solid)
                minimum=min(minimum,d)
                if d<1.25:safe=False;break
            if not safe:break
        if safe:routes.append({'id':f"MarketLoop_{len(routes):02}",'points':points,'width':round(minimum*2,3),'zone':item['zone'],'serves':item['id']})
        if len(routes)>=40:break
    all_route_segments=[(a,b) for route in routes for a,b in zip(route['points'],route['points'][1:])]
    vendors=[];anchors=[];human_positions=[g['sourcePosition'] for g in guards]
    def anchor(position,facing,activity,group,role='citizen',special=False):
        if any(math.dist(position[:2],p[:2])<.83 for p in human_positions):return
        if not special:
            if any(poly_distance(position,q['polygon'])<.37 for q in solid):return
            if any(segment_distance(position,a,b)<.86 for a,b in all_route_segments):return
            if (position[0]/110)**2+(position[1]/87)**2<1:return
        rec={'id':f'StreetPatron_{len(anchors):04}','position':position,'facing':facing,
             'activity':activity,'role':role,'groupId':group}
        anchors.append(rec);human_positions.append(position)
    for item in stalls:
        p=world(item,0,.45,.02)
        vendors.append({'id':'Vendor_'+item['id'],'position':p,'facing':item['rotation'],'stallId':item['id'],'activity':item['activity']})
        human_positions.append(p)
        for u in [-2.35,-1.42,-.48,.48,1.42,2.35]:
            anchor(world(item,u,-3.72,.02),item['rotation']+math.pi,'customer',item['id'])
        for u in [-1.85,-.9,.9,1.85]:
            anchor(world(item,u,3.72,.02),item['rotation'],'porter' if item['family']==5 else 'conversation',item['id'],'worker' if item['family']==5 else 'citizen')
    for item in shops:
        vendors.append({'id':'Vendor_'+item['id'],'position':world(item,-3.25,-4.15,.18),'facing':item['rotation'],'stallId':item['id'],'activity':'shopkeeper'})
        for u in [-4.4,-3.4,-2.4,2.4,3.4,4.4]:anchor(world(item,u,-8.65,.02),item['rotation']+math.pi,'customer',item['id'])
    # Conversation groups and queues occupy the remaining court edges. Deliberate
    # zone masks prevent these anchors becoming arbitrary city-wide scatter.
    zones=[('PottersCourt',[-101,-22,-121,-89]),('FoodCourt',[22,101,-121,-89]),
           ('WestLoading',[-145,-111,-72,75]),('EastLoading',[111,145,-72,75])]
    for name,(xmin,xmax,ymin,ymax) in zones:
        for i in range(2000):
            if len(anchors)>=680:break
            x=rng.uniform(xmin,xmax);y=rng.uniform(ymin,ymax)
            if not ellipse_clear(rectangle(x,y,.8,.8)):continue
            if any(inside((x,y),q['polygon']) for q in reserved):continue
            if min((math.dist([x,y],s['center']) for s in stalls if s['zone'].startswith(('South','Corner','West','East'))),default=999)>8:continue
            anchor([round(x,4),round(y,4),.02],rng.uniform(-math.pi,math.pi),['conversation','queue','porter'][i%3],name,'worker' if i%7==0 else 'citizen')
    facade=[[round(108*math.cos(i*math.tau/128),5),round(85*math.sin(i*math.tau/128),5),.02] for i in range(129)]
    clear_routes=[{'id':'FacadeAmbulatory','points':facade,'width':3.0,'closed':True},
                  {'id':'CeremonialApproach','points':[[0,-162,.02],[0,-83,.02]],'width':6},
                  {'id':'EastEntrance','points':[[147,0,.02],[106,0,.02]],'width':6},
                  {'id':'WestEntrance','points':[[-147,0,.02],[-106,0,.02]],'width':6},
                  {'id':'NorthEntrance','points':[[0,83,.02],[0,116,.02]],'width':6},
                  {'id':'CityToMarketToFacade','points':[[0,-154,.02],[0,-107.5,.02],[34.1,-107.5,.02],[34.1,-80.65,.02]],'width':2.7}]
    layout={'revision':'street-life-1','seed':SEED,'axes':'Blender X east, Y north, Z up; runtime [X,Z,-Y]',
            'units':'meters','stalls':stalls,'shops':shops,'preserved_workshops':['Workshop_0','Workshop_1'],
            'removed_semantics':['market/Stall_*','market/Cart_*','market/basin','market/Rack_*','market/ForegroundCypress*'],
            'preserved_guard_ids':[g['id'] for g in guards],'footprint_obstacles':occupied,'protected_polygons':reserved,
            'vendors':vendors,'anchors':anchors,'routes':routes,'clear_routes':clear_routes,
            'counts':{'stalls':len(stalls),'shop_houses':len(shops),'vendors':len(vendors),'static_patrons':len(anchors),'roaming_routes':len(routes)},
            'clearance':{'facade_walkway_width':3,'main_axis_width':6,'minimum_roaming_width':2.5,'static_center_spacing':.83,'static_to_roaming_centerline':.86},
            'coordinateSystem':'blender_xyz_z_up',
            'views':[{'id':'street_market_lane','position':[34,-107.6,1.72],'target':[34,-91,2.0]},
                     {'id':'street_west_souk','position':[-119.5,-61,1.72],'target':[-119.5,-27,2.1]},
                     {'id':'street_shop_approach','position':[0,-154,1.72],'target':[0,-90,5]}]}
    selected={0,2,3,5,6,8,9,11,12,14,16,17,19,21,22,24,25,27,28,30,31,33,34,35,37,39}
    layout['routes']=[r for r in routes if int(r['id'].rsplit('_',1)[-1]) in selected]
    layout['counts']['roaming_routes']=len(layout['routes'])
    layout['clearance']['independent_route_segment_spacing']=1.4
    layout['cameras']={v['id']:{'position':v['position'],'target':v['target'],'lens':28} for v in layout['views']}
    layout['destinations']=[{'id':v['id'],'label':{'street_market_lane':'Market alleys','street_west_souk':'West souk','street_shop_approach':'Shop-lined approach'}[v['id']],
                             'position':v['position'],'lookAt':v['target']} for v in layout['views']]
    for route in routes:route['clearWidth']=route['width'];route['label']=route['zone']+' '+route['serves']
    # Keep the established population generation stable; the route correction
    # changes navigation metadata only, after all authored feet are generated.
    layout=append_entry_gathering(layout)
    facade_route=next(r for r in layout['clear_routes'] if r['id']=='FacadeAmbulatory')
    facade_route['points']=facade_ambulatory_points()
    facade_route['label']='Facade circuit via ceremonial forecourt'
    facade_route['shape']='oval arcs connected by a south monument detour'
    return layout

def main():
    layout=build_layout();(ROOT/'street_life_layout.json').write_text(json.dumps(layout,indent=2))
    print(json.dumps(layout['counts']))

if __name__=='__main__':main()
