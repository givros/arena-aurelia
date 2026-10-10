"""Author separated two-lane resident traffic inside the reserved quarter streets.

This is a placement plan only. Source mesh preflight must pass before integration.
"""
from pathlib import Path
import json,math,hashlib
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.geometry.polygon import orient

R=Path(__file__).resolve().parents[1]

def build(root=R):
    root=Path(root);path=root/'master_world_layout.json';master=json.loads(path.read_text())
    routes=[];reserved=[];coverage={};traffic=[];traffic_evidence=[]
    city_path=root/'district_life_layout.json'
    if city_path.exists():
        city=json.loads(city_path.read_text())
        traffic.extend(LineString([p[:2] for p in route['points']]) for route in city.get('routes',[]))
        traffic_evidence.append({'path':city_path.name,'sha256':hashlib.sha256(city_path.read_bytes()).hexdigest()})
    crowd_path=root/'characters/runtime/crowd_manifest.json'
    if crowd_path.exists():
        crowd=json.loads(crowd_path.read_text());seen=set()
        for npc in crowd.get('npcs',[]):
            if not npc.get('path') or npc.get('districtLife'):continue
            ident=npc.get('routeId',npc['id'])
            if ident in seen:continue
            seen.add(ident);traffic.append(LineString([[p[0],-p[2]] for p in npc['path']]))
        traffic_evidence.append({'path':'characters/runtime/crowd_manifest.json','sha256':hashlib.sha256(crowd_path.read_bytes()).hexdigest(),
            'meaning':'Protected population when quarter traffic was authored'})
    traffic_mask=unary_union([g.buffer(2.45,cap_style=1) for g in traffic]) if traffic else None
    for spine in master['quarterSpines']:
        line=LineString(spine['points']);allowed=line
        # Split later streets around earlier crossing loops; this leaves the
        # crossing itself open for the player and prevents two NPC loops fighting.
        if reserved:allowed=allowed.difference(unary_union([g.buffer(3.4,cap_style=1) for g in reserved]))
        if traffic_mask is not None:allowed=allowed.difference(traffic_mask)
        pieces=[allowed] if allowed.geom_type=='LineString' else list(allowed.geoms)
        pieces=sorted((g for g in pieces if g.geom_type=='LineString' and g.length>=15),key=lambda g:line.project(g.interpolate(.5,normalized=True)))
        for j,segment in enumerate(pieces):
            loop=orient(segment.buffer(.9,cap_style=2,join_style=1,quad_segs=4),sign=1)
            if loop.geom_type!='Polygon':raise RuntimeError('Non-simple street '+spine['id'])
            points=[[round(x,5),round(y,5),-.035] for x,y in loop.exterior.coords]
            actors=max(2,math.ceil(segment.length/100))
            route={'id':'QuarterWalk_'+spine['id']+'_'+str(j),'label':spine['label']+' resident circulation',
                'zone':'quarter_'+spine['id'],'masterSpine':spine['id'],'points':points,'actors':actors,
                'roles':['citizen','merchant','citizen','worker'] if spine['id']=='western_quay' else ['citizen','citizen','merchant'],
                'speed':.88,'closed':True,'width':3.0,'laneSeparation':1.8,'purpose':'Residents and small deliveries moving through the '+spine['label'].lower()}
            routes.append(route)
        if not pieces:raise RuntimeError('No independent walking section on '+spine['id'])
        coverage[spine['id']]={'streetLength':line.length,'walkingStreetLength':sum(g.length for g in pieces),
            'loops':len(pieces),'actors':sum(r['actors'] for r in routes if r['masterSpine']==spine['id'])}
        reserved.append(line)
    # Check disjoint authored loops, including separate sections of one street.
    loops=[LineString(r['points']) for r in routes];minimum=float('inf')
    for i,a in enumerate(loops):
        for b in loops[:i]:minimum=min(minimum,a.distance(b))
        for b in traffic:minimum=min(minimum,a.distance(b))
    if minimum<1.39:raise RuntimeError('Quarter loops too close: '+str(minimum))
    result={'revision':'quarter-resident-traffic-v1','coordinateSystem':'blender_xyz_z_up','masterLayoutSHA256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'anchors':[],'routes':routes,'animatedActorCount':sum(r['actors'] for r in routes),'coverage':coverage,
        'minimumIndependentLoopSeparation':minimum,'trafficReservationEvidence':traffic_evidence,
        'sourceMeshPreflightRequired':True,'fullCanonicalCharacters':True}
    (root/'master_spine_life_layout.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({'loops':len(routes),'actors':result['animatedActorCount'],'minimumSeparation':minimum,'coverage':coverage},indent=2))
    return result

if __name__=='__main__':build()
