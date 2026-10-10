from pathlib import Path
import json,math,hashlib
from PIL import Image,ImageDraw,ImageFont
from semantic_metadata import current_semantic_fields
R=Path(__file__).resolve().parents[1];s=json.loads((R/'scene_spec.json').read_text())
derived=current_semantic_fields(R,s)
master=json.loads((R/'master_world_layout.json').read_text())
boundary=json.loads((R/'master_world_boundary.json').read_text())
district=json.loads((R/'district_life_layout.json').read_text())
quarter_life=json.loads((R/'master_spine_life_layout.json').read_text())
interior_life=json.loads((R/'arena_interior_life_layout.json').read_text())
W,H=1800,1300;im=Image.new('RGB',(W,H),'#f5efe2');d=ImageDraw.Draw(im)
try:font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22);title=ImageFont.truetype('C:/Windows/Fonts/georgia.ttf',38)
except:font=ImageFont.load_default();title=font
def xy(x,y):return (int(630+x*1.4),int(860-y*1.4))
def rect(b,color):
    x0,y0,x1,y1=b;d.rectangle([xy(x0,y1),xy(x1,y0)],fill=color)
def ellipse(rx,ry,color):d.ellipse([xy(-rx,ry),xy(rx,-ry)],fill=color)
d.polygon([xy(*p) for p in boundary['wall']['centerline']],fill='#c7bca1')
rect([-197,-240,-160,440],'#517c89')
for spine in master['quarterSpines']:d.line([xy(*p) for p in spine['points']],fill='#efe2c5',width=6)
city=json.loads((R/'city_registry.json').read_text())
for parcel in city['parcels']:
    x,y=parcel['center'][:2];w,h=parcel.get('full_dimensions',parcel.get('full_projection',[15,18]))[:2]
    a=parcel.get('rotation',0);ca,sa=math.cos(a),math.sin(a)
    corners=[xy(x+u*ca-v*sa,y+u*sa+v*ca) for u,v in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]
    d.polygon(corners,fill='#b99170',outline='#92775b')
ellipse(148,126,'#ddcdb0');ellipse(106,83,'#92724e');ellipse(100,77,'#a77853');ellipse(70,47,'#d8b379')
rect([-10,52,10,68],'#9d2530');rect([-43,-31,51,31],'#5c6178')
# Dashed ground plan indicates the service level lies below the sand, not an open excavation.
ellipse(70,47,'#d8b379')
for i in range(12):
    xx=-42+i*8;d.line([xy(xx,-31),xy(xx+4,-31)],fill='#5c6178',width=3);d.line([xy(xx,31),xy(xx+4,31)],fill='#5c6178',width=3)
rect([46,-4,64,4],'#5c6178')
market=json.loads((R/'market_registry.json').read_text())
street=json.loads((R/'street_life_layout.json').read_text()) if (R/'street_life_layout.json').exists() else None
if street:
    for assembly in street['stalls']+street['shops']:
        d.polygon([xy(*p) for p in assembly['polygon']],fill='#9d2530' if assembly['kind']=='shop_house' else '#be7644',outline='#785639')
    for route in street['clear_routes']:
        d.line([xy(*p[:2]) for p in route['points']],fill='#f5e9ca',width=2)
else:
    for stall in market['stalls']:
        x,y=stall['center'];a=stall['rotation'];ca,sa=math.cos(a),math.sin(a)
        d.polygon([xy(x+u*ca-v*sa,y+u*sa+v*ca) for u,v in [(-4.3,-3.25),(4.3,-3.25),(4.3,3.25),(-4.3,3.25)]],fill='#be7644')
for shop in json.loads((R/'foreground_registry.json').read_text())['workshops']:
    x,y=shop['center'];rect([x-9,y-4,x+9,y+4],'#9d2530')
colors={'infill_shop':'#a66d46','frontage':'#d3a16c','stall':'#ae5940','cargo':'#80683e','bench':'#62795b','brazier':'#d4993b'}
for item in district['items']:d.polygon([xy(*p) for p in item['polygon']],fill=colors[item['kind']],outline='#796044')
civic=json.loads((R/'civic_court_layout.json').read_text()) if (R/'civic_court_layout.json').exists() else None
if civic:
    for part in civic['parts']:
        if part['kind'] in ['roof','basin','bed']:
            d.polygon([xy(*p) for p in part['polygon']],fill={'roof':'#be885e','basin':'#517c89','bed':'#64754c'}[part['kind']],outline='#796044')
    for route in civic['clear_routes']:d.line([xy(*p[:2]) for p in route['points']],fill='#47786c',width=2)
for p in master['treePlantings']:
    x,y=xy(*p['position'][:2]);d.ellipse((x-2,y-2,x+2,y+2),fill='#64754c')
bridge=city['bridge'];bx,by=bridge['center'];half=bridge['width']/2
rect([bx-bridge['length']/2,by-half,bx+bridge['length']/2,by+half],'#eee5d2')
for start,end in bridge['approach_ramps']:rect([start,by-half,end,by+half],'#d8d0b9')
aqueduct=city['aqueduct'];rect([aqueduct['x_range'][0],aqueduct['y']-4,aqueduct['x_range'][1],aqueduct['y']+4],'#9b9686')
temple=city['temple'];tx,ty=temple['center'];tw,th=temple['footprint']
rect([tx-tw/2,ty-th/2,tx+tw/2,ty+th/2],'#eee5d2')
rect([temple['stair_start'][0]-8,temple['stair_start'][1],temple['stair_end'][0]+8,temple['stair_end'][1]],'#e3d8c0')
for angle in range(0,360,22):
    a=math.radians(angle);d.line([xy(74*math.cos(a),51*math.sin(a)),xy(101*math.cos(a),78*math.sin(a))],fill='#eadbbd',width=3)
for pts in [[(0,-180),(0,-85),(0,-40)],[(65,0),(46,0),(22,0)],[(0,108),(10,132)]]:
    d.line([xy(*p) for p in pts],fill='#903e36',width=4)
for route in district['clear_routes']:d.line([xy(*p[:2]) for p in route['points']],fill='#47786c',width=2)
for route in district['routes']+quarter_life['routes']+(street['routes'] if street else [])+(civic['routes'] if civic else []):
    d.line([xy(*p[:2]) for p in route['points']],fill='#577fa2',width=1)
for route in interior_life['routes']:
    d.line([xy(*p[:2]) for p in route['points']],fill='#79678e',width=1)
d.line([xy(*p) for p in boundary['wall']['centerline']+[boundary['wall']['centerline'][0]]],fill='#584c3c',width=5)
for gate in boundary['gates']:
    x,y=xy(*gate['center'][:2]);d.rectangle((x-5,y-5,x+5,y+5),fill='#795237')
for i,region in enumerate(district['regions'].values(),1):
    x,y=xy(*region['center']);d.ellipse((x-12,y-12,x+12,y+12),fill='#f8edda',outline='#715c43');d.text((x-7,y-15),str(i),font=font,fill='#554632')
if civic:
    cc=next(n for n in derived['regions'] if n['id']=='REG_CIVIC_COURT');x,y=xy(*cc['center'])
    d.ellipse((x-14,y-14,x+14,y+14),fill='#f8edda',outline='#715c43');d.text((x-13,y-15),'11',font=font,fill='#554632')
d.text((48,38),'AURELIA  /  ARENA DISTRICT',font=title,fill='#402c25')
d.text((48,89),'Curved city quarters · connected routes · north up',font=font,fill='#675948')
labels=[('REG_ARENA  The Sands','#d8b379'),('REG_CAVEA  Spectator terraces','#a77853'),('REG_VIP  Imperial loggia','#9d2530'),('REG_HYPOGEUM  Service level below','#5c6178'),('REG_MARKET  Festival market','#be7644'),('REG_CITY  Roman city','#c7bca1'),('REG_RIVER  River and quay','#517c89'),('REG_AQUEDUCT  Monumental arches','#9b9686')]
for i,(name,col) in enumerate(labels):
    y=170+i*43;d.rectangle((1200,y,1227,y+24),fill=col);d.text((1237,y-3),name,font=font,fill='#402c25')
d.text((1200,595),'Living city quarters',font=font,fill='#903e36')
for i,region in enumerate(district['regions'].values(),1):d.text((1200,632+(i-1)*34),str(i)+'. '+region['label'],font=font,fill='#675948')
d.text((1200,972),'11. Fountain garden and peristyle',font=font,fill='#675948')
d.text((1200,1030),'Green: public connections',font=font,fill='#47786c')
d.text((1200,1064),'Blue: market and quarter walkers',font=font,fill='#577fa2')
d.text((1200,1098),'Purple: gallery / service circulation',font=font,fill='#79678e')
d.text((58,1218),'Schematic overview. Region markers may overlap; the service level is shown beneath the arena.',font=font,fill='#675948')
d.text((58,1252),'Closed city gates bound exploration. Hills and river continue beyond the map as scenery.',font=font,fill='#675948')
im.save(R/'semantic_layout.png')
graph={'coordinateSystem':'Blender X east,Y north,Z up','regions':derived['regions'],'regionMetadata':derived['regionMetadata'],'edges':[
 {'from':'REG_CITY','to':'REG_MARKET','via':'Ceremonial avenue','clearWidth':6},
 {'from':'REG_MARKET','to':'REG_ARENA','via':'South outer arcade and vaulted radial tunnel','clearWidth':5.6},
 {'from':'REG_ARENA','to':'REG_CAVEA','via':'NE/SW stepped aisles','clearWidth':2.6},
 {'from':'REG_CAVEA','to':'REG_VIP','via':'North middle terrace and side stair'},
 {'from':'REG_ARENA','to':'REG_HYPOGEUM','via':'East service ramp','clearWidth':6.8,'slope':1/3},
 {'from':'REG_MARKET','to':'REG_RIVER','via':'West quay street'},
 {'from':'REG_CITY','to':'REG_AQUEDUCT','via':'Eastern city streets'}]}
if street:
    graph['localMarketConnections']=[{'id':route['id'],'width':route['width'],'points':route['points']} for route in street['clear_routes']]
    graph['streetLifeLayout']='street_life_layout.json'
graph['districtRegions']=district['regions'];graph['districtConnections']=district['clear_routes'];graph['residentLoops']=district['routes']
graph['residentLoopsScope']='District commercial loops only; other circulation is listed in the named loop collections.'
graph['quarterResidentLoops']=quarter_life['routes'];graph['quarterLifeLayout']='master_spine_life_layout.json'
graph['interiorResidentLoops']=interior_life['routes'];graph['interiorLifeLayout']='arena_interior_life_layout.json'
graph['marketResidentLoops']=street['routes'] if street else []
graph['districtLifeLayout']='district_life_layout.json';graph['masterWorldLayout']='master_world_layout.json';graph['worldBoundary']='master_world_boundary.json'
graph['quarterStreets']=master['quarterSpines'];graph['gates']=boundary['gates'];graph['watergates']=boundary['watergates']
if civic:
    graph['civicCourtLayout']='civic_court_layout.json';graph['civicCourtConnections']=civic['clear_routes']
    graph['civicResidentLoops']=civic['routes']
    graph['edges'].append({'from':'REG_CITY','to':'REG_CIVIC_COURT','via':'Eastern fountain garden and covered peristyle','clearWidth':3.0})
for key,region in district['regions'].items():graph['edges'].append({'from':'REG_CITY','to':'REG_DISTRICT_'+key.upper(),'via':region['label'],'clearWidth':2.5})
authorities=['master_world_layout.json','master_world_boundary.json','district_life_layout.json','street_life_layout.json','civic_court_layout.json','master_spine_life_layout.json','arena_interior_life_layout.json']
if (R/'watergate_boundary_revision.json').exists():
    gate_revision=json.loads((R/'watergate_boundary_revision.json').read_text())
    authorities.append('watergate_boundary_revision.json')
    graph['watergateBoundaryRevision']='watergate_boundary_revision.json'
    graph['quayPedestrianGates']=[{'id':gate['id'],'center':gate['center'],'xExtent':gate['xExtent'],
                                   'physicalState':gate['physicalState'],'testPath':gate['testPath']}
                                  for gate in gate_revision['gates']]
graph['authorityHashes']={name:hashlib.sha256((R/name).read_bytes()).hexdigest() for name in authorities}
source=json.loads((R/'source_reopen_validation.json').read_text());graph['sourceSHA256']=source['sourceSHA256']
graph['mapEvidence']={'file':'semantic_layout.png','sha256':hashlib.sha256((R/'semantic_layout.png').read_bytes()).hexdigest(),'scope':'Derived schematic footprint and circulation overview; not a navigation mesh or collision proof.'}
graph['boundaryScope']='Closed physical city gates and local quay pedestrian barriers delimit playable streets; exterior hills, villas and river continuation are scenery.'
node_ids={node['id'] for node in graph['regions']}
assert all(edge['from'] in node_ids and edge['to'] in node_ids for edge in graph['edges'])
(R/'region_graph.json').write_text(json.dumps(graph,indent=2))
print('Saved semantic layout and connected route records')
