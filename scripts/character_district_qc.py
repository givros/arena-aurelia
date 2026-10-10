"""Read-only saved-source audit of district additions and their protected baseline."""
from pathlib import Path
from collections import Counter
import sys,json,math,bpy
from mathutils import Vector
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from district_life_population import sha,digest,GeometrySupport,source,role_of

path=R/'Aurelia_Arena.blend';before=sha(path);bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(1)
manifest=json.loads((R/'characters/runtime/crowd_manifest.json').read_text());population=bpy.data.collections['Population']
by_id={o.get('runtime_id'):o for o in population.objects};support=GeometrySupport();records=[];failures=[];prototype_cache={}
baseline=[e for e in manifest['instances']+manifest['npcs'] if not e.get('districtLife')]
if digest(baseline)!=manifest['districtLife']['previousPopulationFingerprint']:failures.append({'kind':'previous_population_changed'})
def probes(collection):
    if collection.name not in prototype_cache:
        shoe=next(o for o in collection.objects if o.type=='MESH' and 'romansandals' in o.name.lower())
        points=[shoe.matrix_world@v.co for v in shoe.data.vertices];feet=[]
        for sign in [-1,1]:
            side=[v for v in points if v.x*sign>0];z=min(v.z for v in side);bottom=[v for v in side if v.z<z+.002]
            feet.append(sum(bottom,Vector())/len(bottom))
        butt=None
        if 'seated-spectator' in collection.name:
            body=next(o for o in collection.objects if o.type=='MESH' and 'characterbase' in o.name.lower())
            points=[body.matrix_world@v.co for v in body.data.vertices];candidates=[v for v in points if abs(v.x)<.2 and -.06<v.y<.17 and .2<v.z<.53]
            z=min(v.z for v in candidates);bottom=[v for v in candidates if v.z<z+.001];butt=sum(bottom,Vector())/len(bottom)
        prototype_cache[collection.name]=(feet,butt)
    return prototype_cache[collection.name]
for e in manifest['instances']:
    if not e.get('districtLife'):continue
    obj=by_id[e['id']];feet,butt=probes(obj.instance_collection);gaps=[];objects=[]
    for p in feet:
        world=obj.matrix_world@p;hit=support.ground(world)
        gaps.append(None if hit is None else world.z-hit[1]);objects.append(None if hit is None else hit[2])
    seat_gap=None
    if butt is not None:
        world=obj.matrix_world@butt;seat=bpy.data.objects.get(e.get('seatObject',''))
        hit=None if seat is None else support.bvh(seat).ray_cast(world+Vector((0,0,.1)),Vector((0,0,-1)),.3)[0]
        seat_gap=None if hit is None else world.z-hit.z
        if seat_gap is None or abs(seat_gap)>.03:failures.append({'kind':'district_butt_seat_contact','id':e['id'],'gap':seat_gap})
    if any(v is None or abs(v)>.025 for v in gaps):failures.append({'kind':'district_feet_contact','id':e['id'],'gaps':gaps})
    meshes=[o for o in obj.instance_collection.objects if o.type=='MESH']
    if obj.hide_render or obj.instance_collection.hide_render or not meshes or any(o.hide_render for o in meshes):failures.append({'kind':'source_visibility','id':e['id']})
    records.append({'id':e['id'],'role':e['role'],'zone':e['zone'],'footGaps':gaps,'footSupport':objects,'buttSeatGap':seat_gap})
routes=[]
for e in manifest['npcs']:
    if not e.get('districtLife') or not e.get('path'):continue
    checked=0;radius=.53 if role_of(e)!='animated-citizen' else .35
    for p in source(e['path']):
        hit=support.ground(p);obstacle=support.blocked(p,radius)
        if hit is None or abs(p[2]-hit[1]-.015)>.025 or obstacle:
            failures.append({'kind':'saved_walking_path_geometry','id':e['id'],'point':p,'support':hit,'obstacle':obstacle});break
        checked+=1
    routes.append({'id':e['id'],'routeId':e['routeId'],'samples':checked,'actualGroundAndClearance':checked==len(e['path'])})
report={'passed':not failures,'sourceSHA256':before,'sourceUnchanged':sha(path)==before,
    'crowdManifestSHA256':sha(R/'characters/runtime/crowd_manifest.json'),'districtLife':manifest['districtLife'],
    'protectedPopulationUnchanged':not any(f['kind']=='previous_population_changed' for f in failures),'protectedCount':len(baseline),
    'staticTested':len(records),'seatedTested':sum(r['role']=='seated-citizen' for r in records),'routeActorsTested':len(routes),
    'zoneCounts':dict(Counter(r['zone'] for r in records)),'failures':failures,'contacts':records,'routes':routes}
(R/'characters/district_life_source_qc.json').write_text(json.dumps(report,indent=2))
print('DISTRICT_SOURCE_QC',json.dumps({k:v for k,v in report.items() if k not in ['contacts','routes']}),flush=True)
assert report['passed'] and report['sourceUnchanged']
