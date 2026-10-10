"""Serial integration of approved organic city reflow and real landscape edge."""
from pathlib import Path
import bpy,sys,json,hashlib,struct,shutil
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
import master_world_geometry as G
import world_boundary_geometry as W
source=R/'Aurelia_Arena.blend'
backup=R/'checkpoints/13_before_master_world.blend'
if not backup.exists():
    shutil.copy2(source,backup)
    for rel in ['city_registry.json','scene_spec.json','characters/runtime/crowd_manifest.json']:
        shutil.copy2(R/rel,R/'checkpoints'/('13_before_master_world_'+Path(rel).name))
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.scene.frame_set(1)
B.mats()
mesh_cache={}
def signature(o):
    h=hashlib.sha256(o.name.encode())
    h.update(struct.pack('<16f',*[v for row in o.matrix_world for v in row]))
    if o.type=='MESH':
        key=o.data.as_pointer()
        if key not in mesh_cache:
            mh=hashlib.sha256()
            for v in o.data.vertices:mh.update(struct.pack('<3f',*v.co))
            for p in o.data.polygons:mh.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
            mesh_cache[key]=mh.digest()
        h.update(mesh_cache[key])
    if o.instance_type=='COLLECTION' and o.instance_collection:h.update(o.instance_collection.name.encode())
    return h.hexdigest()
before={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
approved=set(G.eligible_object_names())|{o.name for o in bpy.data.objects if o.name.startswith('Roman_hills/') or o.get('semantic')=='landscape/hills'}
registry=(R/'city_registry.json').read_bytes()
try:
    city=G.apply(B)
    edge=W.apply(B)
    # This camera reproduces the user-reported southern blank ward.
    B.camera('district_feedback_southern_ward',[240,150,165],[25,-5,10],39.2)
    B.camera('district_entire_world',[460,-510,520],[0,100,8],36)
    B.camera('district_south_gate',[0,-207,1.685],[0,-229,5.5],25)
    bpy.context.view_layer.update()
    mesh_cache.clear()
    after={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
    changed=[n for n,h in before.items() if after.get(n)!=h]
    unexpected=[n for n in changed if n not in approved]
    assert not unexpected,'Protected source changed: '+str(unexpected[:20])
    bpy.context.scene['master_world_boundary']=json.loads((R/'master_world_boundary.json').read_text())['revision']
    bpy.context.preferences.filepaths.save_version=0
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
except Exception:
    (R/'city_registry.json').write_bytes(registry)
    raise
report={'passed':True,'protectedComponents':len(before)-len(approved),'changedExistingComponents':changed,
 'unexpectedChanges':unexpected,'approvedCityChanges':len(approved),'newComponents':len(set(after)-set(before)),
 'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'city':city,'boundary':edge}
(R/'comparisons/master_world_integration.json').write_text(json.dumps(report,indent=2,default=str))
print('MASTER_WORLD_INTEGRATED',report['protectedComponents'],report['newComponents'],flush=True)
