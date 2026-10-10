"""Citywide commercial courts and residential street life, in Blender meters."""
import json,math,random,heapq,hashlib
from collections import defaultdict,Counter
from pathlib import Path
from street_life_layout import rectangle,overlap,inside,poly_distance,segment_distance,world,segment_samples
from shapely.geometry import Polygon as ShapePolygon,Point as ShapePoint,LineString as ShapeLine
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1]
SEED=49183
REGIONS={
 'rear_precinct':{'label':'Rear arena precinct','center':[-58,112],'role':'event refreshments'},
 'temple_civic':{'label':'Temple and civic courts','center':[-80,145],'role':'offerings, scribes and civic trade'},
 'east_quay':{'label':'Arena river quay','center':[-146,35],'role':'river cargo and food'},
 'west_quay':{'label':'West bridge ward','center':[-221,65],'role':'boat cargo, fish and repair'},
 'eastern_trades':{'label':'Eastern trade streets','center':[208,10],'role':'neighborhood workshops'},
 'eastern_backstreets':{'label':'Eastern lodging lanes','center':[232,-66],'role':'close shops, lodging and neighborhood courts'},
 'aqueduct_ward':{'label':'Aqueduct ward','center':[235,151],'role':'provisioning and cloth'},
 'north_insulae':{'label':'Northern residential streets','center':[-30,262],'role':'domestic trade and neighbors'},
 'upper_city':{'label':'Upper city courts','center':[80,344],'role':'bread, pottery and textiles'},
 'south_residential':{'label':'Southern residential approaches','center':[62,-178],'role':'arrival services and loading'}}

def bounds(poly):return (min(p[0] for p in poly),max(p[0] for p in poly),min(p[1] for p in poly),max(p[1] for p in poly))
class Index:
    def __init__(self):self.cells=defaultdict(list);self.records=[]
    def add(self,o):
        o=dict(o);o['_bounds']=bounds(o['polygon']);i=len(self.records);self.records.append(o)
        x0,x1,y0,y1=o['_bounds']
        for x in range(math.floor(x0/20),math.floor(x1/20)+1):
            for y in range(math.floor(y0/20),math.floor(y1/20)+1):self.cells[x,y].append(i)
    def nearby(self,p,r=0):
        ids=set()
        for x in range(math.floor((p[0]-r)/20),math.floor((p[0]+r)/20)+1):
            for y in range(math.floor((p[1]-r)/20),math.floor((p[1]+r)/20)+1):ids.update(self.cells[x,y])
        return [self.records[i] for i in ids]
    def clear_poly(self,poly,margin=.18):
        b=bounds(poly);c=((b[0]+b[1])/2,(b[2]+b[3])/2);r=max(b[1]-b[0],b[3]-b[2])/2+margin
        return not any(overlap(poly,o['polygon'],margin) for o in self.nearby(c,r))
    def clear_point(self,p,d):return all(poly_distance(p,o['polygon'])>=d for o in self.nearby(p,d+1))
    def distance(self,p):return min((poly_distance(p,o['polygon']) for o in self.nearby(p,10)),default=20)

def ground(x,y):return 0 if (x/148)**2+(y/126)**2<1 else -.035
def route_safe(points,index,margin=1.25):
    return all(index.clear_point(p,margin) for a,b in zip(points,points[1:]) for p in segment_samples(a,b,.45))
def segment_gap(a,b,c,d):
    def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if cross(a,b,c)*cross(a,b,d)<=0 and cross(c,d,a)*cross(c,d,b)<=0:
        if max(min(a[0],b[0]),min(c[0],d[0]))<=min(max(a[0],b[0]),max(c[0],d[0])) and max(min(a[1],b[1]),min(c[1],d[1]))<=min(max(a[1],b[1]),max(c[1],d[1])):return 0
    return min(segment_distance(a,c,d),segment_distance(b,c,d),segment_distance(c,a,b),segment_distance(d,a,b))
def region_of(p):
    q=p.get('quarter')
    if q:
        if q.startswith('southern'):return 'south_residential'
        return {'western_quay':'west_quay','eastern_trades':'eastern_trades','eastern_lanes':'eastern_backstreets','aqueduct_courts':'aqueduct_ward','western_civic':'north_insulae','temple_residential':'north_insulae','archive_quarter':'upper_city','upper_courts':'upper_city','northern_hillside':'upper_city'}[q]
    x,y=p['center']
    if x<-200:return 'west_quay'
    if y>305:return 'upper_city'
    if y>193:return 'north_insulae'
    if x>157 and y>145:return 'aqueduct_ward'
    if x>157 and y>-178:return 'eastern_trades'
    if y<-128:return 'south_residential'
    if x<-130:return 'east_quay'
    if y>135:return 'temple_civic'
    return 'rear_precinct'

def astar(start,end,index):
    step=.85
    def node(p):return (round(p[0]/step),round(p[1]/step))
    def point(n):return [n[0]*step,n[1]*step]
    tag=(len(index.records),step)
    if getattr(index,'_astar_tag',None)!=tag:index._astar_tag=tag;index._astar_cache={}
    cache=index._astar_cache
    def valid(n):
        if n not in cache:
            p=point(n);cache[n]=(-305<p[0]<348 and -223<p[1]<419 and not -201<p[0]<-157 and index.clear_point(p,1.28))
        return cache[n]
    def nearest(p):
        n=node(p)
        for ring in range(9):
            ns=[(n[0]+x,n[1]+y) for x in range(-ring,ring+1) for y in range(-ring,ring+1) if max(abs(x),abs(y))==ring]
            ns.sort(key=lambda a:math.dist(point(a),p[:2]))
            for a in ns:
                if valid(a):return a
    a=nearest(start);b=nearest(end)
    if not a or not b:return []
    queue=[(0,a)];cost={a:0};prev={};seen=set()
    while queue and len(seen)<220000:
        _,p=heapq.heappop(queue)
        if p in seen:continue
        seen.add(p)
        if p==b:
            ns=[p]
            while p in prev:p=prev[p];ns.append(p)
            ns.reverse();raw=[point(n) for n in ns];out=[raw[0]];i=0
            while i<len(raw)-1:
                j=min(len(raw)-1,i+28)
                while j>i+1 and not route_safe([raw[i],raw[j]],index,1.25):j-=1
                out.append(raw[j]);i=j
            result=[[x,y,ground(x,y)] for x,y in out]
            if math.dist(result[0][:2],start[:2])>.01:
                # The first short transition starts on a previously tested
                # facade route, before reaching the broader city corridor.
                result.insert(0,[start[0],start[1],ground(*start[:2])])
            return result
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            q=(p[0]+dx,p[1]+dy)
            if not valid(q):continue
            if dx and dy and (not valid((p[0]+dx,p[1])) or not valid((p[0],p[1]+dy))):continue
            c=cost[p]+math.hypot(dx,dy)
            if c<cost.get(q,1e30):cost[q]=c;prev[q]=p;heapq.heappush(queue,(c+math.dist(q,b),q))
    return []

def build():
    rng=random.Random(SEED);city=json.loads((R/'city_registry.json').read_text());street=json.loads((R/'street_life_layout.json').read_text())
    actual=json.loads((R/'comparisons/district_source_obstacles.json').read_text());index=Index()
    for o in actual['obstacles']:index.add(o)
    for p in city['parcels']:
        a=p['rotation'];w,d=p['projection_envelope']
        index.add({'id':p['id'],'kind':'house_full_projection','polygon':rectangle(*p['center'],w,d,a)})
    for o in street['footprint_obstacles']:
        if o['kind']!='existing_house':index.add(o)
    wall=ShapePolygon(json.loads((R/'master_world_boundary.json').read_text())['wall']['centerline']).buffer(-7.5)
    # Landmark approach reservations protect ramps/stairs at their actual extents.
    for name,x,y,w,d in [('Bridge_route',-180,105,111,15),('Temple_steps',10,129,22,38),('River',-179.5,70,43,700)]:
        index.add({'id':name,'kind':'protected_landmark','polygon':rectangle(x,y,w,d)})
    protected=street['clear_routes']+street['routes']
    protected_segments=[(a,b,r['width']/2) for r in protected for a,b in zip(r['points'],r['points'][1:])]
    for g in city['civic_landmarks']:
        index.add({'id':g['id'],'kind':'civic_full_projection','polygon':rectangle(*g['center'],*g['footprint'])})
    index.add({'id':'Temple_precinct','kind':'temple_full_projection','polygon':rectangle(10,166,56,45)})
    items=[];door_landings=[]
    def accept(kind,x,y,a,zone,family=0,parent=None):
        w,d={'stall':(8.7,6.6),'frontage':(7.8,4.0),'cargo':(8.7,6.6),'infill_shop':(13,16),'bench':(2.6,1.45),'brazier':(1.5,1.5)}[kind]
        polygon=rectangle(x,y,w,d,a)
        if not wall.covers(ShapePolygon(polygon)):return None
        if (x/113)**2+(y/90)**2<1:return None
        if not index.clear_poly(polygon,.17):return None
        if any(overlap(polygon,p,.17) for p in door_landings):return None
        door=None
        if kind=='infill_shop':
            doorpos=world({'center':[x,y],'rotation':a},0,-9.5)
            door=rectangle(*doorpos[:2],3.0,3.0,a)
            if not index.clear_poly(door,.08):return None
        if any(poly_distance(p,polygon)<r+.22 for pa,pb,r in protected_segments for p in segment_samples(pa,pb,2.2) if abs(p[0]-x)<12 and abs(p[1]-y)<12):return None
        item={'id':f'District_{kind}_{len(items):03}','kind':kind,'center':[round(x,4),round(y,4)],'rotation':a,'zone':zone,'family':family%6,
              'height_extra':[.25,0,.52,-.1,.35][len(items)%5],'full_dimensions':[w,d],'polygon':polygon,'ground_z':ground(x,y),'parent':parent,
              'activity':['pottery','produce','bread','cloth','cookshop','cargo'][family%6],'height':10.3+(len(items)%3)*.7}
        index.add(item);items.append(item)
        if door:door_landings.append(door)
        return item
    master=json.loads((R/'master_world_layout.json').read_text())
    from organic_district_candidates import streets,infill_candidates,market_candidates
    inner=streets()
    link_records=[];seen_links=set()
    review=json.loads((R/'characters/master_pedestrian_review.json').read_text())
    for link in review['shortestMissingLinksPerComponent']:
        pair=tuple(sorted([link['a'],link['b']]))
        if pair in seen_links or link['centerlineGap']>90:continue
        seen_links.add(pair);path=astar(*link['ends'],index)
        if path:
            link_records.append({'id':'DistrictLink_'+str(len(link_records)),'label':link['a'].replace('_',' ').title()+' connection','points':path,'width':2.5,'clearWidth':2.5,'zone':'connections'})
            protected_segments += [(a,b,1.25) for a,b in zip(path,path[1:])]
    for spine in master['quarterSpines']:
        dest=spine['points'][len(spine['points'])//2];x,y=dest
        start=([-238.5,105] if x<-200 else [0,-119] if y<-120 else [108,0] if x>145 else [0,106])
        path=astar(start,dest,index)
        if path:
            link_records.append({'id':'DistrictQuarter_'+spine['id'],'label':spine['label']+' connection','points':path,'width':2.5,'clearWidth':2.5,'existingRouteEntryTransitionWidth':.8,'zone':'connections'})
            protected_segments += [(a,b,1.25) for a,b in zip(path,path[1:])]
    # Author the linked narrow passage network first. Full assembly envelopes
    # preserve its public walking strip before any commercial detail is accepted.
    # Inner lines are candidate frontage guides. The verified master corridors
    # and source-derived connections, below, are the protected public network.
    protected_segments += [(a,b,1.5) for r in master['quarterSpines'] for a,b in zip(r['points'],r['points'][1:])]
    protected_segments += [([0,-174],[0,-221],3.0)]
    for i,(x,y,a,zone,parent) in enumerate(infill_candidates(master)):
        accept('infill_shop',x,y,a,zone,i%5,parent)
    # Trading fronts attach only where a full depth of merchandise and posts
    # fits beside the protected passage; no facade-width proxy is used.
    quotas={z:9 for z in REGIONS};quotas.update({'eastern_trades':14,'north_insulae':15,'upper_city':16,'south_residential':16,'west_quay':15})
    counts=Counter()
    ordered=sorted(city['parcels'],key=lambda p:(region_of(p),int(hashlib.sha256(p['id'].encode()).hexdigest()[:8],16)))
    for p in ordered:
        zone=region_of(p)
        if counts[zone]>=quotas[zone]:continue
        a=p['rotation'];w,d=p['projection_envelope'];temp={'center':p['center'],'rotation':a}
        for u,v,rot in [(0,-d/2-o,a) for o in [2.2,2.6,3.2]]+[(side*(w/2+2.5),-d*.22,a+side*math.pi/2) for side in [-1,1]]:
            pos=world(temp,u,v)
            if accept('frontage',*pos[:2],rot,zone,p['family'],p['id']):counts[zone]+=1;break
    placed=Counter();quotas={z:14 for z in REGIONS};quotas.update({'rear_precinct':18,'south_residential':18,'west_quay':18,'upper_city':16})
    candidates=market_candidates(master,city['parcels'])
    for x,y,a,parent,family in candidates:
        zone=parent.get('forced_zone') or region_of(parent)
        if placed[zone]>=quotas[zone]:continue
        if accept('cargo' if family%6==5 else 'stall',x,y,a,zone,family):placed[zone]+=1
    commercial=[p for p in items if p['kind'] in ['stall','cargo','frontage','infill_shop']]
    # Closed loops use streets around selected complete market assemblies.
    loops=[];loop_segments=[]
    for zone in REGIONS:
        local=[p for p in commercial if p['zone']==zone and p['kind'] in ['stall','cargo']]
        for p in local:
            path=[world(p,u,v,p['ground_z']) for u,v in [(-5.9,-4.8),(5.9,-4.8),(5.9,4.8),(-5.9,4.8),(-5.9,-4.8)]]
            if not route_safe(path,index,1.23):continue
            segs=list(zip(path,path[1:]))
            if any(segment_gap(a,b,c,d)<1.45 for a,b in segs for c,d in loop_segments):continue
            loops.append({'id':f'DistrictLoop_{len(loops):02}','label':REGIONS[zone]['label']+' circulation','zone':zone,'points':path,'width':2.45,'clearWidth':2.45,'closed':True,'serves':p['id']});loop_segments+=segs
            if sum(l['zone']==zone for l in loops)>=4:break
    # Routes connect the actual market courts to established city approaches.
    starts={'rear_precinct':[0,106],'temple_civic':[0,106],'east_quay':[-108,0],'west_quay':[-238.5,105],'eastern_trades':[108,0],'eastern_backstreets':[108,0],
            'aqueduct_ward':[108,0],'north_insulae':[0,106],'upper_city':[0,106],'south_residential':[0,-119]}
    clear_routes=list(link_records);views={}
    for zone in REGIONS:
        local=[p for p in commercial if p['zone']==zone]
        if not local:continue
        center=REGIONS[zone]['center'];chosen=min(local,key=lambda p:math.dist(p['center'],center))
        destination=world(chosen,0,-(chosen['full_dimensions'][1]/2+2.1),chosen['ground_z'])
        path=astar(starts[zone],destination,index)
        if path:
            clear_routes.append({'id':'DistrictAccess_'+zone,'label':REGIONS[zone]['label']+' approach','points':path,'width':2.5,'clearWidth':2.5,'existingRouteEntryTransitionWidth':.8,'zone':zone})
            eye=[path[-1][0],path[-1][1],path[-1][2]+1.72];views['street_district_'+zone]={'position':eye,'target':[chosen['center'][0],chosen['center'][1],2.0],'lens':28}
    bridge=astar([-108,0],[-121.5,105],index)
    if bridge:
        bridge += [[-123,105,0],[-127.5,105,0],[-147.5,105,6.05],[-212.5,105,6.05],[-232.5,105,0],[-238.5,105,-.035]]
        clear_routes.append({'id':'DistrictBridgeTrunk','label':'Arena to both riverbanks','points':bridge,'width':2.5,'clearWidth':2.5,'existingRouteEntryTransitionWidth':.8,'zone':'west_quay','known_bridge_route':True})
    for gate in json.loads((R/'master_world_boundary.json').read_text())['gates']:
        zone={'Porta_Spectaculorum':'south_residential','Porta_Orientalis':'eastern_backstreets','Porta_Pontis':'west_quay','Porta_Collina':'upper_city'}[gate['id']]
        path=astar(starts[zone],gate['approach'][-1],index)
        if path:clear_routes.append({'id':'DistrictGate_'+gate['id'],'label':gate['label']+' approach','points':path,'width':2.5,'clearWidth':2.5,'existingRouteEntryTransitionWidth':.8,'zone':zone,'closed_world_gate':True})
    # Compact two-lane resident circuits fill regions whose complete-parcel loop
    # would cross neighboring architecture. Opposing centerlines stay1.7m apart.
    for zone in REGIONS:
        if sum(l['zone']==zone for l in loops)>=2:continue
        route=next((r for r in clear_routes if r['zone']==zone and r['id']!='DistrictBridgeTrunk'),None)
        if not route:continue
        candidates=[]
        for a,b in zip(route['points'],route['points'][1:]):
            length=math.dist(a[:2],b[:2])
            if length<10:continue
            angle=math.atan2(b[1]-a[1],b[0]-a[0]);ca,sa=math.cos(angle),math.sin(angle)
            for t in [.75,.5,.25]:
                cx=a[0]+t*(b[0]-a[0]);cy=a[1]+t*(b[1]-a[1]);half=min(7,length*.2)
                points=[[cx+u*ca-v*sa,cy+u*sa+v*ca,ground(cx,cy)] for u,v in [(-half,-.85),(half,-.85),(half,.85),(-half,.85),(-half,-.85)]]
                candidates.append(points)
        candidates.sort(key=lambda ps:math.dist(ps[0][:2],REGIONS[zone]['center']))
        for points in candidates:
            segs=list(zip(points,points[1:]))
            if not route_safe(points,index,.61):continue
            if any(segment_gap(a,b,c,d)<1.45 for a,b in segs for c,d in loop_segments):continue
            loops.append({'id':f'DistrictLoop_{len(loops):02}','label':REGIONS[zone]['label']+' resident circuit','zone':zone,'points':points,'width':1.2,'clearWidth':1.2,'publicCorridorWidth':2.9,'closed':True,'type':'separated walking lanes'})
            loop_segments+=segs
            if sum(l['zone']==zone for l in loops)>=2:break
    # Real seats and supported light sources occupy clear social-court edges.
    benches=[];lights=[]
    allroute=[(a,b) for r in loops+clear_routes for a,b in zip(r['points'],r['points'][1:])]
    def route_clear(poly,margin):return all(poly_distance(p,poly)>margin for a,b in allroute for p in segment_samples(a,b,1.0) if poly_distance(p,poly)<margin+1)
    for zone in REGIONS:
        local=[p for p in commercial if p['zone']==zone]
        for p in local:
            bench_offsets=[(-6.2,0),(6.2,0),(0,6.0),(-7.5,3.8),(7.5,3.8)] if p['kind']!='infill_shop' else [(-8.1,0),(8.1,0),(-8.1,3.8),(8.1,3.8),(0,-10.3)]
            for u,v in bench_offsets:
                if sum(b['zone']==zone for b in benches)>=2:break
                q=world(p,u,v);poly=rectangle(q[0],q[1],2.6,1.45,p['rotation'])
                if not route_clear(poly,1.30):continue
                item=accept('bench',*q[:2],p['rotation'],zone)
                if item:benches.append(item)
            lamp_offsets=[(-5.4,-5.8),(5.4,-5.8),(-6.5,5),(6.5,5)] if p['kind']!='infill_shop' else [(-7.8,0),(7.8,0),(-7.8,4.5),(7.8,4.5),(-4,-10.1),(4,-10.1)]
            for u,v in lamp_offsets:
                if sum(l['zone']==zone for l in lights)>=2:break
                q=world(p,u,v);poly=rectangle(q[0],q[1],1.5,1.5)
                if not route_clear(poly,1.30):continue
                item=accept('brazier',*q[:2],0,zone)
                if item:lights.append(item)
    manifest=json.loads((R/'characters/runtime/crowd_manifest.json').read_text());human=[a['sourcePosition'] for a in manifest['instances']+manifest['npcs']]
    # Spatial hash keeps the large full-world foot clearance check inexpensive.
    hgrid=defaultdict(list)
    for p in human:hgrid[math.floor(p[0]/2),math.floor(p[1]/2)].append(p)
    anchors=[];vendors=[]
    public_lanes=unary_union([ShapeLine([a[:2],b[:2]]).buffer(w+.38) for a,b,w in protected_segments]+[ShapePolygon(p).buffer(.3) for p in door_landings])
    def foot(p,facing,activity,zone,group,role='citizen',special=False,seat=None):
        x,y=p[:2];key=(math.floor(x/2),math.floor(y/2))
        for u in range(key[0]-1,key[0]+2):
            for v in range(key[1]-1,key[1]+2):
                if any(math.dist(p[:2],q[:2])<.92 for q in hgrid[u,v]):return
        if not special and not index.clear_point(p,.42):return
        if not special and public_lanes.covers(ShapePoint(p[:2])):return
        if any(segment_distance(p,a,b)<1.03 for a,b in allroute):return
        if any(segment_distance(p,a,b)<r['width']/2+.36 for r in clear_routes for a,b in zip(r['points'],r['points'][1:])):return
        rec={'id':f'DistrictPatron_{len(anchors):04}','position':p,'facing':facing,'activity':activity,'role':role,'zone':zone,'groupId':group}
        if seat:rec.update(seat)
        anchors.append(rec);hgrid[key].append(p);return rec
    for item in commercial:
        vendor=world(item,-3.25,-4.15,item['ground_z']+.18) if item['kind']=='infill_shop' else world(item,0,.35,item['ground_z'])
        vendors.append({'id':'Vendor_'+item['id'],'position':vendor,'facing':item['rotation'],'stallId':item['id'],'activity':item['activity'],'zone':item['zone']});hgrid[math.floor(vendor[0]/2),math.floor(vendor[1]/2)].append(vendor)
        # Broken customer rows and angled small groups respond to each storefront.
        depth=item['full_dimensions'][1]/2;goal=9 if item['kind']!='frontage' else 5;made=0
        for trial in range(220):
            u=rng.uniform(-4.0,4.0);v=-depth-rng.uniform(.55,3.6)
            p=world(item,u,v,item['ground_z']);f=item['rotation']+rng.uniform(-.65,.65)
            if foot(p,f,'customer' if trial%3 else 'conversation',item['zone'],item['id']):made+=1
            if made>=goal:break
        if item['kind']!='frontage':
            for u in [-1.1,1.1]:foot(world(item,u,depth+.6,item['ground_z']),item['rotation']+math.pi,'porter' if item['kind']=='cargo' else 'conversation',item['zone'],item['id'],'worker' if item['kind']=='cargo' else 'citizen')
    for item in benches:
        for u in [-.60,.60]:
            foot(world(item,u,-.08,item['ground_z']),item['rotation'],'resting',item['zone'],item['id'],'seated-citizen',True,{'seatTop':item['ground_z']+.44,'feetZ':item['ground_z'],'benchId':item['id']})
    # Small front-door groups distribute life across every reused quarter.
    for h in city['parcels']:
        w,d=h['projection_envelope'];zone=region_of(h);made=0
        for trial in range(100):
            u=rng.uniform(-w*.45,w*.45);v=-d/2-rng.uniform(.55,1.7);p=world(h,u,v,ground(*h['center']))
            if foot(p,h['rotation']+rng.uniform(-.8,.8),'resident',zone,'Household_'+h['id']):made+=1
            if made>=3:break
    guards=[(-11,109,0,'temple_civic'),(31,109,0,'temple_civic'),(-146,97,0,'east_quay'),(-238,96,0,'west_quay')]
    for x,y,a,zone in guards:foot([x,y,ground(x,y)],a,'watch',zone,'WardGuard_'+zone,'guard')
    views['district_aerial_north']={'position':[-135,400,230],'target':[0,100,0],'lens':43}
    if 'street_district_west_quay' not in views:
        views['street_district_west_quay']={'position':[-255,102.17,1.685],'target':[-256,86,2.1],'lens':28}
    views['district_aerial_reverse']={'position':[315,280,225],'target':[-40,95,0],'lens':42}
    views['district_feedback_southern_ward']={'position':[240,150,165],'target':[25,-5,10],'lens':39.2}
    layout={'revision':'district-life-organic-2','coordinateSystem':'blender_xyz_z_up','seed':SEED,'animatedActorCount':48,'regions':REGIONS,'items':items,'vendors':vendors,'anchors':anchors,'routes':loops,
            'clear_routes':clear_routes,'benches':benches,'lights':lights,'cameras':views,'destinations':[{'id':k,'label':REGIONS[k.removeprefix('street_district_')]['label'],'position':v['position'],'lookAt':v['target']} for k,v in views.items() if k.startswith('street_')],
            'source_obstacle_evidence':'comparisons/district_source_obstacles.json','source_obstacle_hash':actual['source_sha256'],'preserved_street_layout_sha256':hashlib.sha256((R/'street_life_layout.json').read_bytes()).hexdigest(),
            'master_world_layout':'master_world_layout.json','frontage_guides':inner,'door_landings':door_landings,
            'counts':{'commercial_assemblies':len(commercial),'stalls_and_cargo':sum(p['kind'] in ['stall','cargo'] for p in commercial),'shopfronts':sum(p['kind']=='frontage' for p in commercial),'complete_infill_shops':sum(p['kind']=='infill_shop' for p in commercial),'vendors':len(vendors),'static_patrons':len(anchors),'seated':sum(a['role']=='seated-citizen' for a in anchors),'routes':len(loops),'access_routes':len(clear_routes),'benches':len(benches),'supported_lights':len(lights)},
            'coverage':{zone:{'assemblies':sum(p['zone']==zone for p in commercial),'patrons':sum(p['zone']==zone for p in anchors),'loops':sum(p['zone']==zone for p in loops)} for zone in REGIONS}}
    support_fixes={'Vendor_District_frontage_125':-10.45,'DistrictPatron_1746':10.55,'DistrictPatron_1981':-10.45}
    for anchor in layout['vendors']+layout['anchors']:
        if anchor['id'] in support_fixes:anchor['position'][0]=support_fixes[anchor['id']]
    layout['sourceSupportCorrections']={'reason':'Exact two-foot support at original central avenue slab edge','anchorX':support_fixes}
    return layout
if __name__=='__main__':
    layout=build();(R/'district_life_layout.json').write_text(json.dumps(layout,indent=2));print(json.dumps({'counts':layout['counts'],'coverage':layout['coverage']}),flush=True)
