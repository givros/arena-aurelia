"""Add the eastern fountain garden; caller owns the source save/export."""
import bpy,json,math,hashlib,random
from pathlib import Path
from mathutils import Vector
from city import CityGeometry,_collection,_roof
import market_dressing as M
R=Path(__file__).resolve().parents[1]

def _column(mats,c):
 g=CityGeometry()
 for z,r,h in [(.075,.47,.15),(.19,.38,.08),(.285,.34,.11),(4.63,.34,.13),(4.76,.39,.12)]:g.cylinder('stone',(0,0,z),r,h,24)
 g.box('stone',(0,0,4.88),(.88,.88,.12))
 rings=[(.34,.31),(1.1,.30),(3.7,.265),(4.57,.26)];n=48;verts=[]
 for z,r in rings:
  for i in range(n):
   a=i*math.tau/n;rr=r-.017*(1+math.cos(12*a));verts.append((rr*math.cos(a),rr*math.sin(a),z))
 faces=[tuple(range(n-1,-1,-1)),tuple(range((len(rings)-1)*n,len(rings)*n))]
 for j in range(len(rings)-1):
  for i in range(n):faces.append((j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i))
 g.mesh('stone',verts,faces)
 return g.objects('CivicColumnKit',c,mats,'solid','civic_court/column')

def _ring_rect(g,material,x,y,z,w,d,t,h):
 g.box(material,(x-w/2+t/2,y,z),(t,d,h));g.box(material,(x+w/2-t/2,y,z),(t,d,h))
 g.box(material,(x,y-d/2+t/2,z),(w-2*t,t,h));g.box(material,(x,y+d/2-t/2,z),(w-2*t,t,h))

def apply(B):
 assert not bpy.data.collections.get('Civic_Court'),'Civic court already exists.'
 raw=(R/'civic_court_layout.json').read_bytes();layout=json.loads(raw)
 assert not layout['audit']['failures'],layout['audit']['failures']
 c=_collection('Civic_Court');mats={}
 for key in ['wood','woodLight','iron','stone','tile','tileLight','goldCloth','red']:
  mats[key]=bpy.data.materials.get('City/Event_'+key) or bpy.data.materials.get('City/'+key)
  assert mats[key],key
 mats['paving']=bpy.data.materials.get('City/road') or mats['stone']
 mats['water']=B.material('Civic garden water',(.10,.23,.215),.23,.17)
 mats['soil']=B.material('Civic garden dark earth',(.13,.09,.048),.97)
 mats['herb']=B.material('Civic sage and rosemary',(.19,.26,.11),.97)
 mats['herbLight']=B.material('Civic clipped olive foliage',(.31,.35,.15),.97)
 mats['flower']=B.material('Civic herb blossoms',(.41,.20,.30),.95)
 mats['ember']=B.material('Civic garden embers',(.94,.19,.026),.6,0,4)
 proto=_column(mats,c);created=[];by_part={};rng=random.Random(7183)
 for p in layout['parts']:
  kind=p['kind'];x,y=p['center'];w,d=p['dimensions'];z=p['groundZ'];g=CityGeometry();water=CityGeometry();objects=[]
  if kind=='column':
   for src in proto:
    obj=src.copy();obj.data=src.data;obj.name=p['id']+'/'+src.name.rsplit('/',1)[-1];c.objects.link(obj);obj.location=(x,y,z);objects.append(obj)
  elif kind=='roof':
   # Roof thickness, ribs, ridge caps, entablature and exposed rafters all use geometry.
   ww,dd=(w,d) if p['axis']=='y' else (d,w)
   _roof(g,ww-1.2,dd-1.2,5.48,.88)
   for side in [-1,1]:
    g.box('stone',(side*(ww/2-.66),0,5.04),(.72,dd-.6,.28))
    g.box('stone',(side*(ww/2-.64),0,5.23),(.93,dd-.42,.12))
    for j in range(int((dd-.5)/.60)):
     yy=-dd/2+.45+j*.60;g.box('stone',(side*(ww/2-.36),yy,5.15),(.25,.25,.12))
   for j in range(int((dd-.7)/1.12)+1):
    yy=-dd/2+.4+j*1.12;g.box('wood',(0,yy,5.24),(ww-.8,.13,.17))
   objects=g.objects(p['id'],c,mats,'solid','civic_court/portico_roof')
   for obj in objects:obj.location=(x,y,z);obj.rotation_euler.z=0 if p['axis']=='y' else math.pi/2
  elif kind=='paving':
   g.box('paving',(x,y,-.065),(w,d,.13))
   # Small contrasting inlay bands articulate the walk without raised trip edges.
   for sx in [-1,1]:g.box('stone',(x+sx*(w/2-.18),y,.006),(.12,d-.3,.012))
   objects=g.objects(p['id'],c,mats,'walkable','civic_court/level_paving')
  elif kind=='wall':
   g.box('stone',(x,y,z+.64),(w,d,1.28));g.box('stone',(x,y,z+1.31),(w,d,.08))
   objects=g.objects(p['id'],c,mats,'solid','civic_court/garden_enclosure')
  elif kind=='basin':
   g.box('stone',(x,y,z+.055),(w,d,.11));_ring_rect(g,'stone',x,y,z+.36,w,d,.28,.58)
   _ring_rect(g,'stone',x,y,z+.69,w,d,.34,.08)
   g.box('stone',(x,y,z+.17),(w-.56,d-.56,.12))
   water.box('water',(x,y,z+.51),(w-.60,d-.60,.035))
   # A supported fluted fountain stalk and shallow bowl give a readable focal point.
   g.cylinder('stone',(x,y,z+.68),.38,.86,20)
   g.cylinder('stone',(x,y,z+1.16),.75,.18,28,top_radius=.92)
   M._ring(g,'stone',(x,y,z+1.27),.84,.085,28,8)
   water.cylinder('water',(x,y,z+1.258),.77,.02,28)
   for a in [0,math.pi/2,math.pi,math.pi*1.5]:g.beam('water',(x+.72*math.cos(a),y+.72*math.sin(a),z+1.23),(x+.81*math.cos(a),y+.81*math.sin(a),z+.54),.018,6)
   objects=g.objects(p['id'],c,mats,'solid','civic_court/reflecting_basin')+water.objects(p['id']+'/water',c,mats,'none','civic_court/water')
  elif kind=='bed':
   _ring_rect(g,'stone',x,y,z+.12,w,d,.18,.24);g.box('soil',(x,y,z+.12),(w-.36,d-.36,.18))
   for i in range(int(w*4)):
    xx=x-w/2+.32+rng.random()*(w-.64);yy=y-d/2+.28+rng.random()*(d-.56);h=.18+rng.random()*.28
    for j in range(4):
     a=math.tau*j/4+rng.random();g.beam('herb',(xx,yy,z+.17),(xx+.11*math.cos(a),yy+.11*math.sin(a),z+.17+h),.07,6)
    if i%3==0:g.cylinder('flower',(xx,yy,z+.2+h),.065,.05,6)
   objects=g.objects(p['id'],c,mats,'solid','civic_court/raised_herb_bed')
  elif kind=='bench':
   for xx in [-.9,.9]:g.box('stone',(x+xx,y,z+.17),(.24,.8,.34))
   for yy in [-.31,0,.31]:g.box('woodLight',(x,y+yy,z+.39),(2.45,.28,.10))
   for xx in [-1.06,1.06]:g.box('wood',(x+xx,y+.43,z+.65),(.12,.12,.94))
   for zz in [.72,.98]:g.box('woodLight',(x,y+.44,z+zz),(2.3,.10,.20))
   objects=g.objects(p['id'],c,mats,'solid','civic_court/bench')
  elif kind=='lamp':
   g.box('stone',(x,y,z+.14),(.6,.6,.28));g.box('iron',(x,y,z+.85),(.15,.15,1.3))
   g.cylinder('iron',(x,y,z+1.55),.27,.2,16);g.cylinder('ember',(x,y,z+1.66),.24,.04,16)
   for a in [0,math.pi/2,math.pi,math.pi*1.5]:g.beam('iron',(x+.23*math.cos(a),y+.23*math.sin(a),z+.2),(x+.08*math.cos(a),y+.08*math.sin(a),z+1.45),.036,6)
   objects=g.objects(p['id'],c,mats,'solid','civic_court/brazier')
   light=bpy.data.lights.new('LAMP/'+p['id'],'POINT');light.energy=420;light.color=(1,.40,.15);light.shadow_soft_size=.5
   ob=bpy.data.objects.new(light.name,light);c.objects.link(ob);ob.location=(x,y,z+1.83);ob['distance']=17
  for obj in objects:obj['assembly_id']=p['id'];obj['semantic']='civic_court/'+kind+'/'+p['id']
  created+=objects;by_part[p['id']]=objects
 for obj in proto:bpy.data.objects.remove(obj,do_unlink=True)
 for name,v in layout['cameras'].items():B.camera(name,v['position'],v['target'],v['lens'])
 bpy.context.view_layer.update();violations=[]
 for p in layout['parts']:
  x,y=p['center'];w,d=p['dimensions']
  for o in by_part[p['id']]:
   for v in o.bound_box:
    q=o.matrix_world@Vector(v)
    if abs(q.x-x)>w/2+.03 or abs(q.y-y)>d/2+.03:violations.append([p['id'],o.name,list(q)])
 assert not violations,violations[:5]
 bpy.context.scene['civic_court_revision']=layout['revision']
 result={'passed':True,'layoutSHA256':hashlib.sha256(raw).hexdigest(),'createdMeshObjects':len(created),'parts':len(layout['parts']),'sharedColumnMeshUsers':sum(p['kind']=='column' for p in layout['parts']),'actualProjectionViolations':violations,'existingGeometryModified':False,'sourceSaved':False,'seatedAnchors':4,'lights':2}
 (R/'comparisons/civic_court_geometry_audit.json').write_text(json.dumps(result,indent=2));print('CIVIC_COURT_READY',json.dumps(result),flush=True)
 return result
