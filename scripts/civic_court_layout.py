import json,math,hashlib
from pathlib import Path
from shapely.geometry import Polygon,LineString,Point,box
from shapely.ops import unary_union
R=Path(__file__).resolve().parents[1]
G=-.035

def rect(cx,cy,w,d):return [[cx-w/2,cy-d/2],[cx+w/2,cy-d/2],[cx+w/2,cy+d/2],[cx-w/2,cy+d/2]]
def build():
 d=json.loads((R/'district_life_layout.json').read_text());source=json.loads((R/'comparisons/district_source_obstacles.json').read_text());master=json.loads((R/'master_spine_life_layout.json').read_text())
 obstacles=[(o['id'],Polygon(o['polygon'])) for o in source['obstacles']]+[(o['id'],Polygon(o['polygon'])) for o in d['items']]
 actors=[a for a in d['anchors']+d['vendors']]
 trees=json.loads((R/'comparisons/civic_court_tree_bounds.json').read_text())
 parts=[]
 def part(id,kind,cx,cy,w,dep,**kw):
  p={'id':id,'kind':kind,'center':[cx,cy],'dimensions':[w,dep],'polygon':rect(cx,cy,w,dep),'groundZ':G,**kw};parts.append(p);return p
 # Deep roofed aisles are supported on two fully modeled rows of columns.
 part('CivicWestRoof','roof',151.5,127.85,6.5,31.3,axis='y')
 part('CivicNorthRoof','roof',169.8,141.75,30.1,6.5,axis='x')
 part('CivicSouthRoof','roof',157.1,115.35,4.7,6.3,axis='x')
 # Peristyle floors are level with the street; separate shallow paving edges have no inaccessible steps.
 part('CivicWestPaving','paving',151.5,127.85,6,30.8)
 part('CivicNorthPaving','paving',169.8,141.75,29.6,6)
 part('CivicSouthPaving','paving',157.1,115.35,4.2,5.8)
 for x in [149.05,153.95]:
  for y in ([112.85,118.6,124.35,130.1,135.85,141.6] if x<150 else [112.85,118.6,124.35,130.1,135.85]):part(f'CivicColumn_{len(parts):02}','column',x,y,1.0,1.0)
 for y in [139.3,144.2]:
  for x in [158.65,164.45,170.25,176.05,181.85]:part(f'CivicColumn_{len(parts):02}','column',x,y,1.0,1.0)
 part('CivicSouthColumn_A','column',158.65,112.85,1,1)
 part('CivicSouthColumn_B','column',158.65,117.85,1,1)
 # Low enclosing walls preserve an open western entrance opposite an established public trunk.
 part('CivicWestWall_A','wall',148.48,121.1,.32,18.0)
 part('CivicWestWall_B','wall',148.48,139.95,.32,7.9)
 part('CivicNorthWall_A','wall',164.5,145.02,24,.32)
 part('CivicNorthWall_B','wall',183.3,145.02,3,.32)
 part('CivicReflectingBasin','basin',159.7,128.75,4.8,8.0)
 part('CivicHerbBed_A','bed',171.7,136.45,8.0,1.7)
 part('CivicHerbBed_B','bed',180.1,136.45,2.8,1.7)
 for i,(x,y) in enumerate([(167.15,138.0),(176.65,138.0)]):part('CivicBench_'+str(i),'bench',x,y,2.6,1.0)
 for i,(x,y) in enumerate([(155.6,114.5),(181.1,139.9)]):part('CivicLamp_'+str(i),'lamp',x,y,.65,.65)
 # Tour enters through a 4.5m opening in the western garden wall.
 access={'id':'CivicCourtPublicTour','label':'Eastern garden and covered peristyle','width':3.0,'clearWidth':3.0,'zone':'civic_court','points':[[143.65,132.975,G],[151.5,132.975,G],[151.5,141.75,G],[179.0,141.75,G],[179.0,149.0,G]],'closed':False}
 loop={'id':'CivicCourtGardenLoop','label':'Fountain garden circuit','zone':'civic_court','width':1.2,'clearWidth':1.2,'closed':True,'points':[[155.8,122,G],[163.6,122,G],[163.6,135.1,G],[155.8,135.1,G],[155.8,122,G]]}
 low=[p for p in parts if p['kind'] not in ['roof','paving']]
 fails=[]
 for p in low:
  poly=Polygon(p['polygon'])
  for name,q in obstacles:
   if poly.intersects(q):fails.append([p['id'],'existing',name])
  for a in actors:
   if poly.distance(Point(a['position'][:2]))<.6:fails.append([p['id'],'actor',a['id']])
  for r in d['routes']+d['clear_routes']+master['routes']:
   gap=poly.distance(LineString([v[:2] for v in r['points']]))
   if gap<r.get('width',1.2)/2+.25:fails.append([p['id'],'old route',r['id'],gap])
 for p in [p for p in parts if p['kind']=='roof']:
  poly=Polygon(p['polygon'])
  for t in trees:
   if t['lo'][2]<6.8 and poly.intersects(box(t['lo'][0],t['lo'][1],t['hi'][0],t['hi'][1])):fails.append([p['id'],'tree crown',t['id']])
 for r in [access,loop]:
  line=LineString([v[:2] for v in r['points']]);width=r['width']/2
  for name,q in obstacles+[(p['id'],Polygon(p['polygon'])) for p in low]:
   gap=line.distance(q)
   if gap<width:fails.append([r['id'],'route clearance',name,gap])
 anchors=[]
 for bench in [p for p in parts if p['kind']=='bench']:
  for dx in [-.60,.60]:anchors.append({'id':bench['id']+str(dx),'position':[bench['center'][0]+dx,bench['center'][1]-.08,G],'facing':0,'activity':'resting','role':'seated-citizen','zone':'civic_court','groupId':bench['id'],'seatTop':G+.44,'feetZ':G,'benchId':bench['id']})
 for i,(x,y,f,role) in enumerate([(155.8,119.6,-.7,'worker'),(157.1,119.7,.7,'citizen'),(157.0,116.0,2.4,'worker'),(178.8,137.8,-.8,'citizen'),(179.9,138.15,2.1,'citizen'),(164.7,136.8,-.6,'citizen'),(165.6,137.6,2.4,'citizen'),(180.0,147.0,2.4,'guard')]):
  q=Point(x,y)
  if any(q.distance(poly)<.45 for name,poly in obstacles+[(p['id'],Polygon(p['polygon'])) for p in low]):continue
  if any(q.distance(LineString([v[:2] for v in r['points']]))<r.get('width',1.2)/2+.38 for r in [access,loop]+d['routes']+d['clear_routes']+master['routes']):continue
  anchors.append({'id':'CivicGardenResident_'+str(i),'position':[x,y,0 if 154.5<=x<=159.2 and 112.45<=y<=118.25 else G],'facing':f,'activity':'gardening' if role=='worker' else 'watch' if role=='guard' else 'conversation','role':role,'zone':'civic_court','groupId':'CivicGardenGroup_'+str(i//2)})
 print(json.dumps(fails,indent=2));print('ANCHORS',len(anchors));
 return {'revision':'civic-court-1','coordinateSystem':'blender_xyz_z_up','districtLayoutSHA256':hashlib.sha256((R/'district_life_layout.json').read_bytes()).hexdigest(),'parts':parts,'anchors':anchors,'routes':[loop],'clear_routes':[access],'animatedActorCount':4,'cameras':{'street_district_civic_court':{'position':[151.5,120,1.72],'target':[161,134,2.1],'lens':28},'district_civic_court_aerial':{'position':[207,73,61],'target':[163,130,2.5],'lens':44}},'destinations':[{'id':'street_district_civic_court','label':'Eastern fountain garden','position':[151.5,120,1.72],'lookAt':[161,134,2.1]}],'audit':{'failures':fails,'sourceObstacleSHA256':source['source_sha256']}}
if __name__=='__main__':
 d=build();(R/'civic_court_layout.json').write_text(json.dumps(d,indent=2));print('PARTS',len(d['parts']))
