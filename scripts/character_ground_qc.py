"""Read-only actual support audit for all statues and important standing characters."""
import bpy,json,hashlib,math
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'Aurelia_Arena.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source));bpy.context.scene.frame_set(1)
manifest=json.loads((ROOT/'characters/runtime/crowd_manifest.json').read_text())
population=bpy.data.collections['Population'];lookup={o.get('runtime_id'):o for o in population.objects}
architecture=[];cache={};prototypes={}
for o in bpy.context.scene.objects:
    if o.type!='MESH' or o.get('runtime_skip') or o.hide_render:continue
    if o.get('collision') not in ['solid','walkable'] and not o.name.startswith('STATUARY/Pedestal_'):continue
    points=[o.matrix_world@Vector(v) for v in o.bound_box]
    architecture.append((o,[min(v[k] for v in points) for k in range(3)],[max(v[k] for v in points) for k in range(3)]))
def bvh(o):
    if o.name not in cache:cache[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
    return cache[o.name]
def feet(collection):
    if collection.name not in prototypes:
        shoe=next(o for o in collection.objects if o.type=='MESH' and 'romansandals' in o.name.lower())
        coords=[shoe.matrix_world@v.co for v in shoe.data.vertices];result=[]
        for sign in [-1,1]:
            side=[v for v in coords if sign*v.x>0];z=min(v.z for v in side);bottom=[v for v in side if v.z<z+.002]
            result.append(sum(bottom,Vector())/len(bottom))
        prototypes[collection.name]=result
    return prototypes[collection.name]
records=[]
for item in manifest['instances']:
    if item['role']=='seated-spectator':continue
    obj=lookup[item['id']];results=[]
    for local in feet(obj.instance_collection):
        p=obj.matrix_world@local;hits=[]
        for architecture_obj,lo,hi in architecture:
            if not(lo[0]-.001<=p.x<=hi[0]+.001 and lo[1]-.001<=p.y<=hi[1]+.001 and lo[2]<=p.z+.08 and hi[2]>=p.z-1.5):continue
            hit,normal,_,_=bvh(architecture_obj).ray_cast(p+Vector((0,0,.08)),Vector((0,0,-1)),1.58)
            if hit is not None and normal.z>.25:hits.append((p.z-hit.z,architecture_obj.name,hit.z))
        closest=min(hits,key=lambda q:abs(q[0])) if hits else None
        results.append({'footWorld':list(p),'gap':closest[0] if closest else None,'support':closest[1] if closest else None,'supportZ':closest[2] if closest else None})
    records.append({'id':item['id'],'zone':item['zone'],'sourcePosition':item['sourcePosition'],'feet':results})
bad=[r for r in records if any(f['gap'] is None or abs(f['gap'])>.025 for f in r['feet'])]
report={'source':str(source),'sourceSHA256':before,'sourceUnchanged':hashlib.sha256(source.read_bytes()).hexdigest()==before,'tested':len(records),'statuesTested':sum(r['zone'] in ['facade_statue','ceremonial_statue'] for r in records),'tolerance':.025,'passed':not bad,'issues':bad,'records':records}
(ROOT/'characters/standing-ground-qc.json').write_text(json.dumps(report,indent=2))
assert report['sourceUnchanged']
print('STANDING_GROUND_QC',json.dumps({k:v for k,v in report.items() if k!='records'}),flush=True)
