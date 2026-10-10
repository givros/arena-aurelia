import json,hashlib,sys
from pathlib import Path
import matplotlib;matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as DrawPoly,Patch
from shapely.geometry import Polygon,LineString,Point,box
R=Path.cwd();c=json.loads((R/'civic_court_layout.json').read_text());d=json.loads((R/'district_life_layout.json').read_text());o=json.loads((R/'comparisons/district_source_obstacles.json').read_text());m=json.loads((R/'master_spine_life_layout.json').read_text());t=json.loads((R/'comparisons/civic_court_tree_bounds.json').read_text())
fig,ax=plt.subplots(figsize=(13,13),dpi=155);ax.set_facecolor('#ece7d9')
for item in o['obstacles']:
 p=Polygon(item['polygon'])
 if p.intersects(box(135,104,201,159)):ax.add_patch(DrawPoly(item['polygon'],fc='#b8b4a7',ec='#898674',lw=.4))
for item in d['items']:
 p=Polygon(item['polygon'])
 if p.intersects(box(135,104,201,159)):ax.add_patch(DrawPoly(item['polygon'],fc='#b9724d',ec='#79563d',lw=.6))
for tree in t:
 if '/leaf' not in tree['id']:continue
 x,y=(tree['lo'][0]+tree['hi'][0])/2,(tree['lo'][1]+tree['hi'][1])/2;w,h=tree['hi'][0]-tree['lo'][0],tree['hi'][1]-tree['lo'][1]
 from matplotlib.patches import Ellipse
 ax.add_patch(Ellipse((x,y),w,h,fc='#829160',ec='#5a6a49',alpha=.30,lw=.6))
colors={'roof':'#d79c78','paving':'#d6caaa','column':'#6f5b43','wall':'#88785b','basin':'#4b8e9d','bed':'#6e8548','bench':'#614c34','lamp':'#bf942f'}
for p in sorted(c['parts'],key=lambda p:0 if p['kind']=='roof' else 1 if p['kind']=='paving' else 2):ax.add_patch(DrawPoly(p['polygon'],fc=colors[p['kind']],ec='#796955',alpha=.37 if p['kind']=='roof' else .95,lw=.6))
for r in d['clear_routes']+d['routes']+m['routes']:
 ps=r['points'];ax.plot([p[0] for p in ps],[p[1] for p in ps],c='#858f98',lw=.8)
for r in c['clear_routes']:
 ps=r['points'];ax.plot([p[0] for p in ps],[p[1] for p in ps],c='#237768',lw=2.6,label='3m public tour')
for r in c['routes']:
 ps=r['points'];ax.plot([p[0] for p in ps],[p[1] for p in ps],c='#4462a0',lw=1.7,label='Fountain walking loop')
for a in c['anchors']:ax.scatter(*a['position'][:2],s=35,c='#282a2c',zorder=10,marker='s' if a['role']=='seated-citizen' else 'o')
ax.text(151.5,125.5,'COVERED\nPERISTYLE',ha='center',va='center',rotation=90,fontsize=9)
ax.text(169.4,141.75,'NORTH COLONNADE',ha='center',va='center',fontsize=9)
ax.text(159.7,128.75,'FOUNTAIN',ha='center',va='center',rotation=90,fontsize=8,c='white')
ax.text(170,128,'Existing cypress\nand pine grove',ha='center',va='center',fontsize=9,c='#45543a')
ax.text(168,152.5,'AURELIA  /  EASTERN FOUNTAIN GARDEN',ha='center',fontsize=14)
ax.set_xlim(137,199);ax.set_ylim(106,155);ax.set_aspect('equal');ax.set_xlabel('East / west — metres');ax.set_ylabel('North / south — metres');ax.grid(ls=':',alpha=.25)
ax.legend(loc='lower right');fig.tight_layout();fig.savefig(R/'comparisons/civic_court_layout_map.png');plt.close(fig)
obstacles=[(p['id'],Polygon(p['polygon'])) for p in o['obstacles']]+[(p['id'],Polygon(p['polygon'])) for p in d['items']]
low=[(p['id'],Polygon(p['polygon'])) for p in c['parts'] if p['kind'] not in ['roof','paving']]
report={'layoutSHA256':hashlib.sha256((R/'civic_court_layout.json').read_bytes()).hexdigest(),'districtLayoutSHA256':hashlib.sha256((R/'district_life_layout.json').read_bytes()).hexdigest(),'plannedComponentConflicts':c['audit']['failures'],'routes':[],'roofProjectionConflicts':[],'scope':'Full new component footprints against preserved source pedestrian hulls, current district full parcels, all district actors, master-spine and public paths; full nearby crown bounds separately checked. Actual geometry integration verified in civic_court_geometry_audit.json.'}
for r in c['routes']+c['clear_routes']:
 l=LineString([v[:2] for v in r['points']]);gap=min((l.distance(p),id) for id,p in obstacles+low);report['routes'].append({'id':r['id'],'minimumProjectionGap':gap,'declaredWidth':r['width'],'passed':gap[0]>=r['width']/2})
for p in c['parts']:
 if p['kind']=='roof':
  q=Polygon(p['polygon'])
  for id,o in obstacles:
   if q.intersects(o):report['roofProjectionConflicts'].append([p['id'],id])
(R/'comparisons/civic_court_layout_audit.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
