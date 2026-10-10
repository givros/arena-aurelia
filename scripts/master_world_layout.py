"""Author the irregular city envelope and reusable house assembly placements."""
import json, math, random, hashlib
from pathlib import Path
from collections import Counter
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import unary_union
from street_life_layout import rectangle

R=Path(__file__).resolve().parents[1]
WALL=[[-311,-145],[-297,-199],[-253,-222],[-202,-227],[-157,-229],[-107,-230],[-40,-227],[0,-229],[64,-226],[126,-228],[181,-218],[241,-202],[291,-160],[326,-111],[341,-40],[341,45],[332,113],[342,174],[340,251],[321,315],[286,370],[220,414],[141,428],[56,422],[-25,427],[-109,419],[-165,424],[-201,425],[-247,411],[-290,371],[-306,306],[-303,241],[-315,181],[-310,116],[-307,57],[-314,-18]]

def boundary():
    data={'revision':'organic-city-envelope-1','coordinateSystem':'blender_xyz_z_up',
      'wall':{'id':'Aurelia_city_enclosure','closed':True,'centerline':WALL,'thickness':3.0,'height':8.5,'interiorWalkReservation':5.0,'housingInset':8.0},
      'gates':[
        {'id':'Porta_Spectaculorum','label':'Southern arena gate','center':[0,-229,0],'width':9,'height':9,'approach':[[0,-174,0],[0,-198,0],[0,-217,0]],'closed':True},
        {'id':'Porta_Orientalis','label':'Eastern trade gate','center':[341,-10,0],'width':8,'height':8,'approach':[[289,12,0],[310,8,0],[329,-10,0]],'closed':True},
        {'id':'Porta_Pontis','label':'Western bridge gate','center':[-310,116,0],'width':8,'height':8,'approach':[[-238.5,105,0],[-268,97,0],[-292,112,0]],'closed':True},
        {'id':'Porta_Collina','label':'Northern hill gate','center':[56,422,0],'width':8,'height':8,'approach':[[91,370,0],[75,393,0],[57,411,0]],'closed':True}],
      'watergates':[
        {'id':'Southern_river_gate','center':[-179.5,-228,0],'waterRangeX':[-197,-160],'bankRangeX':[-202,-157],'archClearance':8,'riverContinuation':[[-179.5,-228,-3.5],[-184,-300,-3.5],[-213,-390,-3.5],[-280,-500,-3.5]]},
        {'id':'Northern_river_gate','center':[-179.5,424.4,0],'waterRangeX':[-197,-160],'bankRangeX':[-201,-158],'archClearance':8,'riverContinuation':[[-179.5,424.4,-3.5],[-171,496,-3.5],[-139,570,-3.5],[-95,680,-3.5]]}],
      'landformBands':[
        {'id':'South_olive_terraces','polyline':[[-320,-247],[-228,-255],[-109,-252],[7,-252],[141,-255],[246,-229],[320,-192]],'width':125,'heightRange':[4,22],'theme':'layered stone terraces, groves and distant rooftops'},
        {'id':'East_cypress_ridge','polyline':[[357,-170],[370,-70],[370,58],[366,174],[365,292],[321,377]],'width':150,'heightRange':[12,58],'theme':'rolling cypress ridge with terraced villas'},
        {'id':'North_urban_hills','polyline':[[-296,433],[-145,459],[-3,452],[146,453],[275,437],[355,390]],'width':210,'heightRange':[22,105],'theme':'layered urban roofs, olives and varied hills'},
        {'id':'West_river_hills','polyline':[[-334,-222],[-348,-69],[-345,85],[-348,249],[-334,398]],'width':135,'heightRange':[10,48],'theme':'river terraces and wooded shoulder'}],
      'protectedLandmarks':['arena','current street markets and all current people','Pons_Caelius','Temple_of_Concordia','Aqua_Aurelia','Basilica_Aemilia','Basilica_Mercatoria','Tower_of_the_Watch','Civic_Archive_Tower'],
      'notes':['The wall replaces the exposed rectangular pavement edge; gatehouse doors close the walkable world physically.','Water continues under dedicated arched river gates and beyond the ground cutoffs.','Housing envelopes stay at least8m inside the wall centerline. Existing arena and street layout coordinates remain fixed.']}
    (R/'master_world_boundary.json').write_text(json.dumps(data,indent=2))
    return data

SPINES=[
 ('southern_west','Southern potters street',5.0,[[-7,-165],[-38,-169],[-70,-176],[-98,-186],[-127,-197]]),
 ('southern_east','Southern lodging street',5.0,[[8,-169],[36,-174],[65,-181],[99,-186],[133,-200],[173,-197],[200,-178]]),
 ('southern_courts','Southern courtyard lane',3.8,[[-122,-195],[-88,-192],[-49,-191],[-10,-193],[34,-191],[73,-195],[115,-196],[148,-190]]),
 ('western_quay','West bank merchants',5.0,[[-235,-180],[-243,-142],[-252,-97],[-247,-49],[-239,-8],[-242,35],[-255,73],[-260,114],[-248,157],[-244,198],[-253,241],[-257,289],[-244,338],[-225,378]]),
 ('eastern_trades','Eastern craftsmen street',5.6,[[150,-127],[175,-106],[189,-74],[199,-36],[218,5],[240,41],[250,80],[241,120],[222,147]]),
 ('eastern_lanes','Eastern upper lanes',4.4,[[207,-162],[242,-138],[269,-101],[283,-53],[293,-6],[299,41],[286,87],[275,130]]),
 ('aqueduct_courts','Aqueduct service courts',4.8,[[162,199],[195,214],[220,240],[255,256],[286,239],[304,211],[312,186]]),
 ('western_civic','Civic bakers street',4.8,[[-119,194],[-99,221],[-74,245],[-62,281],[-77,317],[-94,350],[-99,389]]),
 ('temple_residential','Temple residential lanes',4.8,[[-23,207],[-12,241],[13,264],[31,293],[28,327],[12,360],[-18,389]]),
 ('archive_quarter','Archive quarter street',5.0,[[72,248],[86,274],[115,291],[141,321],[173,346],[211,360],[252,348],[279,323]]),
 ('upper_courts','Upper garden streets',4.2,[[-118,299],[-120,333],[-115,373],[-82,396],[-38,402],[6,397],[49,382],[88,359]]),
 ('northern_hillside','Northern hillside lane',4.6,[[91,388],[137,397],[179,393],[213,389],[248,372]])]

def curve(points):
    """Centripetal-looking smooth polyline, with stable endpoints and tangents."""
    p=[points[0]]+points+[points[-1]];out=[]
    for i in range(1,len(p)-2):
        a,b,c,d=p[i-1:i+3]
        steps=max(8,int(math.dist(b,c)/2))
        for j in range(steps):
            t=j/steps;t2=t*t;t3=t2*t
            out.append([.5*((2*b[k])+(-a[k]+c[k])*t+(2*a[k]-5*b[k]+4*c[k]-d[k])*t2+(-a[k]+3*b[k]-3*c[k]+d[k])*t3) for k in range(2)])
    out.append(points[-1]);return out

def build_houses():
    env=boundary();rng=random.Random(27031)
    city=json.loads((R/'city_registry.json').read_text());street=json.loads((R/'street_life_layout.json').read_text())
    actual=json.loads((R/'comparisons/district_source_obstacles.json').read_text())
    houses=city['parcels'];ids={p['id'] for p in houses}
    source_groups=json.loads((R/'comparisons/master_world_source_groups.json').read_text())
    for h in houses:
        a=0 if h['id'].startswith('ForegroundHouse') else h['rotation'];ca,sa=math.cos(a),math.sin(a);cx,cy=h['center'];local=[]
        for o in source_groups[h['id']]:
            for x in [o['lo'][0],o['hi'][0]]:
                for y in [o['lo'][1],o['hi'][1]]:local.append(((x-cx)*ca+(y-cy)*sa,-(x-cx)*sa+(y-cy)*ca))
        # Actual complete meshes include eaves, front stoops and protruding beams.
        h['projection_envelope']=[2*max(abs(p[i]) for p in local)+.1 for i in range(2)]
    protected=[]
    for o in actual['obstacles']:
        if o['id'].split('/')[0] in ids or o['id'].startswith('Block_courtyard_boundaries/'):continue
        protected.append(Polygon(o['polygon']).buffer(.25))
    for o in street['footprint_obstacles']:
        if o['kind']!='existing_house':protected.append(Polygon(o['polygon']).buffer(.25))
    for r in street['clear_routes']+street['routes']:
        protected.append(LineString([p[:2] for p in r['points']]).buffer(r.get('width',3)/2+.25))
    for o in street['protected_polygons']:protected.append(Polygon(o['polygon']).buffer(.2))
    manifest=json.loads((R/'characters/runtime/crowd_manifest.json').read_text())
    for h in manifest['instances']:
        p=h.get('sourcePosition')
        if p and (p[0]/109)**2+(p[1]/86)**2>1 and p[2]<2:protected.append(Point(p[:2]).buffer(.85))
    protected += [Polygon(rectangle(-179.5,100,44,700)), Polygon(rectangle(-180,105,112,16)), Polygon(rectangle(10,129,23,39)), Polygon(rectangle(10,166,57,46))]
    for b in city['civic_landmarks']:protected.append(Polygon(rectangle(*b['center'],*b['footprint'])).buffer(1))
    protected.append(Point(0,0).buffer(1).buffer(0))
    # Ellipse excludes the full landmark core even when low-geometry sampling
    # cannot see the upper seating or a high facade cornice.
    protected.append(Polygon([(110*math.cos(i*math.tau/128),87*math.sin(i*math.tau/128)) for i in range(128)]))
    fixed=unary_union(protected);inside_wall=Polygon(WALL).buffer(-8)
    spines=[]
    for sid,label,w,pts in SPINES:
        line=LineString(curve(pts));spines.append({'id':sid,'label':label,'width':w,'points':list(map(list,line.coords)),'length':line.length,'_line':line})
    gate_routes=[LineString([p[:2] for p in g['approach']]+[g['center'][:2]]).buffer(g['width']/2+.3) for g in env['gates']]
    street_union=unary_union([s['_line'].buffer(s['width']/2+.45) for s in spines]+gate_routes)
    # Families are mixed intentionally along each street; no newly authored mesh
    # copies are needed to replace the original orthogonal house grid.
    pool=sorted(houses,key=lambda h:(h['family'],h['id']));rng.shuffle(pool)
    placements=[];polys=[];rejections=Counter();cursor=0
    # Revisit all street banks in successive small batches so no quarter can
    # consume the whole reusable city kit before the other regions are framed.
    states=[]
    for s in spines:
        for side in [1,-1]:states.append({'s':s,'side':side,'at':7.0+(3.7 if side<0 else 0),'finished':False})
    while pool and any(not q['finished'] for q in states):
        progressed=False
        for q in states:
            if q['finished'] or not pool:continue
            s=q['s'];line=s['_line'];at=q['at'];side=q['side']
            if at>line.length-7:q['finished']=True;continue
            accepted=None
            candidates=sorted(pool,key=lambda h:h['projection_envelope'][1]) if s['id']=='southern_courts' else pool
            for candidate in candidates[:min(len(pool),24)]:
                w,d=candidate['projection_envelope'];w+=.9;d+=.9
                if at+w/2>line.length-2:continue
                pt=line.interpolate(at);before=line.interpolate(max(0,at-1));after=line.interpolate(min(line.length,at+1))
                angle=math.atan2(after.y-before.y,after.x-before.x)
                # Street-aligned local fronts follow each bend; setbacks vary
                # within 0.6m but never compromise the public walking strip.
                offset=d/2+s['width']/2+.7+(candidate['family']%3)*.17
                x=pt.x-side*math.sin(angle)*offset;y=pt.y+side*math.cos(angle)*offset
                rotation=angle+(math.pi if side<0 else 0)
                poly=Polygon(rectangle(x,y,w,d,rotation))
                if not inside_wall.covers(poly):rejections['wall_inset']+=1;continue
                if fixed.intersects(poly):rejections['protected_source']+=1;continue
                if street_union.intersects(poly):rejections['street_corridor']+=1;continue
                if any(poly.distance(p)<1.0 for p in polys):rejections['house_gap']+=1;continue
                accepted=(candidate,x,y,rotation,poly,w);break
            if accepted:
                h,x,y,rotation,poly,w=accepted
                oldrot=0 if h['id'].startswith('ForegroundHouse') else h['rotation']
                placements.append({'id':h['id'],'family':h['family'],'sourceCenter':h['center'],'sourceRotation':oldrot,
                    'center':[round(x,5),round(y,5)],'rotation':round(rotation,7),'rotationDelta':round(rotation-oldrot,7),
                    'quarter':s['id'],'street':s['label'],'side':side,'streetDistance':round(at,3),
                    'full_dimensions':h['full_dimensions'],'projection_envelope':[round(v+.9,4) for v in h['projection_envelope']],
                    'polygon':[[round(x,5),round(y,5)] for x,y in list(poly.exterior.coords)[:-1]],'preserveScale':True,
                    'frontApproach':[round(pt.x,5),round(pt.y,5),-.035]})
                pool.remove(h);polys.append(poly);q['at']+=w+1.4;progressed=True
            else:q['at']+=3.3
        if not progressed and all(q['finished'] for q in states):break
    output={'revision':'master-organic-quarters-1','coordinateSystem':'blender_xyz_z_up','sourceHouseCount':len(houses),
       'boundaryFile':'master_world_boundary.json','housePlacements':placements,'unplacedHouseIds':[p['id'] for p in pool],
       'quarterSpines':[{k:v for k,v in s.items() if not k.startswith('_')} for s in spines],
       'counts':{'movedHouses':len(placements),'unplacedHouses':len(pool),'quarters':len(spines)},'quarterCoverage':dict(Counter(p['quarter'] for p in placements)),
       'rejections':dict(rejections),'preservedStreetLayoutSHA256':hashlib.sha256((R/'street_life_layout.json').read_bytes()).hexdigest(),
       'retiredSourceComponents':['Block_courtyard_boundaries'],
       'contract':['Move complete semantic house assemblies rigidly with preserved mesh data and object scales.','Current arena, street shops, workshops, all existing people and all proven street routes remain fixed.','Quarter spines are master layout reservations; final connected runtime routes will be derived from actual post-move collision geometry.','Courtyard enclosure is rebuilt locally at the moved houses; merged former grid garden boundaries must be retired.']}
    yards=[];yard_polys=[]
    for h in placements:
        w,d=h['projection_envelope'];a=h['rotation'];cx,cy=h['center'];depth=4.2
        x=cx-math.sin(a)*(d/2+depth/2+.25);y=cy+math.cos(a)*(d/2+depth/2+.25)
        poly=Polygon(rectangle(x,y,max(7,w-1.1),depth,a))
        if inside_wall.covers(poly) and not fixed.intersects(poly) and not street_union.intersects(poly) and all(poly.distance(p)>.14 for p in polys+yard_polys):
            yards.append({'id':'Courtyard_'+h['id'],'houseId':h['id'],'center':[x,y],'rotation':a,'width':max(7,w-1.1),'depth':depth,'polygon':list(map(list,list(poly.exterior.coords)[:-1]))});yard_polys.append(poly)
    output['courtyards']=yards
    # Cohesive small groves, close to the new courtyard backs and edge gardens.
    # Existing first-market foreground cypress assemblies are outside Tree_* and
    # remain fixed; this list relocates the original city tree kit only.
    groves=[[-239,288],[-227,345],[-278,230],[-227,-203],[-276,-179],[-107,-207],[120,-207],[-127,123],[50,204],[-123,281],[-36,315],[58,337],[56,238],[171,290],[213,305],[294,298],[314,151],[311,18],[273,-176],[179,117],[137,-72]]
    trees=[]
    for trial in range(18000):
        c=groves[trial%len(groves)];a=rng.uniform(0,math.tau);rad=math.sqrt(rng.random())*(17 if trial<12000 else 27)
        p=Point(c[0]+math.cos(a)*rad,c[1]+math.sin(a)*rad)
        if not Polygon(WALL).buffer(-10).covers(p.buffer(1.35)):continue
        if fixed.distance(p)<1.35 or street_union.distance(p)<1.25:continue
        if any(q.distance(p)<1.6 for q in polys+yard_polys):continue
        if any(math.dist((p.x,p.y),q['position'][:2])<3.8 for q in trees):continue
        trees.append({'id':f'CityGroveTree_{len(trees):03}','position':[round(p.x,4),round(p.y,4),0],'grove':trial%len(groves)})
        if len(trees)>=180:break
    output['treePlantings']=trees;output['counts'].update({'courtyards':len(yards),'cityTreePlantings':len(trees)})
    (R/'master_world_layout.json').write_text(json.dumps(output,indent=2));print(json.dumps(output['counts']));print(output['quarterCoverage'])
    draw(output,street,city)
    return output

def draw(data,street,city):
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as Patch
    fig,ax=plt.subplots(figsize=(15,15));fig.patch.set_facecolor('#e7dfcb');ax.set_facecolor('#ece4d1')
    ax.fill([-201,-157,-157,-201],[-240,-240,440,440],color='#6d9a9f',alpha=.85)
    ax.add_patch(Patch(WALL,closed=True,fill=False,edgecolor='#594b38',linewidth=5))
    colors=plt.cm.tab20.colors
    for o in street['footprint_obstacles']:
        if o['kind']!='existing_house':ax.add_patch(Patch(o['polygon'],closed=True,facecolor='#a38468',edgecolor='#5c4c3b',linewidth=.25))
    ax.add_patch(Patch([(106*math.cos(t*math.tau/128),83*math.sin(t*math.tau/128)) for t in range(128)],facecolor='#cfbb95',edgecolor='#7e6850'))
    for i,s in enumerate(data['quarterSpines']):
        xx,yy=zip(*s['points']);ax.plot(xx,yy,color=colors[i%20],linewidth=2.1)
        mid=s['points'][len(s['points'])//2];ax.text(*mid,s['label'],fontsize=8,rotation=0,color='#30302c',bbox={'facecolor':'white','alpha':.6,'edgecolor':'none'})
    mapping={s['id']:i for i,s in enumerate(data['quarterSpines'])}
    for h in data['housePlacements']:ax.add_patch(Patch(h['polygon'],facecolor=colors[mapping[h['quarter']]%20],edgecolor='#453c2e',linewidth=.5,alpha=.8))
    for b in city['civic_landmarks']+[city['temple']]:ax.add_patch(Patch(rectangle(*b['center'],*b['footprint']),facecolor='#b39a74',edgecolor='#544430',linewidth=1))
    for g in boundary()['gates']:ax.scatter(*g['center'][:2],s=75,marker='s',color='#714f3a');ax.text(g['center'][0]+5,g['center'][1],g['label'],fontsize=8)
    ax.set(xlim=(-335,365),ylim=(-250,445),aspect='equal',title=f"Organic Aurelia master plan — {len(data['housePlacements'])} reused complete houses")
    ax.grid(alpha=.14);fig.tight_layout();fig.savefig(R/'comparisons/master_world_layout_map.png',dpi=155);plt.close(fig)

if __name__=='__main__':
    build_houses()
