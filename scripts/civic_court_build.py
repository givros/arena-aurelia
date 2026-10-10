"""Integrate the final additive civic court while retaining every existing component."""
from pathlib import Path
import bpy,sys,json,hashlib,struct,shutil
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
import civic_court_geometry as C
source=R/'Aurelia_Arena.blend'
backup=R/'checkpoints/14_before_civic_court.blend'
if not backup.exists():shutil.copy2(source,backup)
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.scene.frame_set(1);B.mats()
cache={}
def signature(o):
    h=hashlib.sha256(o.name.encode());h.update(struct.pack('<16f',*[v for row in o.matrix_world for v in row]))
    if o.type=='MESH':
        key=o.data.as_pointer()
        if key not in cache:
            m=hashlib.sha256()
            for v in o.data.vertices:m.update(struct.pack('<3f',*v.co))
            for p in o.data.polygons:m.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
            cache[key]=m.digest()
        h.update(cache[key])
    if o.instance_type=='COLLECTION' and o.instance_collection:h.update(o.instance_collection.name.encode())
    return h.hexdigest()
before={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
result=C.apply(B)
bpy.context.view_layer.update();cache.clear()
after={o.name:signature(o) for o in bpy.context.scene.objects if o.type=='MESH' or o.instance_type=='COLLECTION'}
changed=[n for n,h in before.items() if after.get(n)!=h]
assert not changed,'Existing source changed: '+str(changed[:10])
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'passed':True,'preservedComponents':len(before),'changedExistingComponents':changed,'newComponents':len(set(after)-set(before)),
 'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'result':result}
(R/'comparisons/civic_court_integration.json').write_text(json.dumps(report,indent=2,default=str))
print('CIVIC_COURT_INTEGRATED',report['newComponents'],flush=True)
