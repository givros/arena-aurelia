"""Root-authorized targeted repair and save; no architecture or placement edits."""
import bpy,sys,json,hashlib,shutil,array
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
from street_life_population import repair_empty_variants,append_entry_gatherings
source=R/'Aurelia_Arena.blend';before=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
def architecture():
    h=hashlib.sha256();count=0
    for o in sorted(bpy.context.scene.objects,key=lambda o:o.name):
        if o.get('runtime_skip'):continue
        h.update(o.name.encode());h.update(str(tuple(v for row in o.matrix_world for v in row)).encode())
        if o.type=='MESH':
            v=array.array('f',[0])*(len(o.data.vertices)*3);o.data.vertices.foreach_get('co',v);h.update(v.tobytes())
            t=array.array('i',[0])*len(o.data.loops);o.data.loops.foreach_get('vertex_index',t);h.update(t.tobytes());count+=1
    return {'sha256':h.hexdigest(),'meshObjects':count}
def placements():return {o.name:(tuple(v for row in o.matrix_world for v in row),o.instance_collection.name) for o in bpy.data.collections['Population'].objects}
original=architecture();positions=placements();report=repair_empty_variants(R)
report['entryGatherings']=append_entry_gatherings(R)
report['repairOnlyTriangleInstances']=report['sourceTriangleInstances']
report['sourceTriangleInstances']=report['entryGatherings']['characterTriangleInstances']
report['runtimeTriangleInstances']=report['entryGatherings']['characterTriangleInstances']
report['crowdManifestSHA256']=report['entryGatherings']['crowdManifestSHA256']
assert architecture()==original,'Architecture changed during character-only repair'
current=placements();assert all(current[k]==v for k,v in positions.items()),'Existing population transforms changed during variant repair'
bpy.ops.wm.save_as_mainfile(filepath=str(source),check_existing=False)
shutil.copy2(source,R/'checkpoints/current.blend')
after=hashlib.sha256(source.read_bytes()).hexdigest()
report.update(sourceSHA256Before=before,sourceSHA256=after,architectureSignature=original,architectureUnchanged=True,
    originalPlacementCount=len(positions),placementCount=len(current),allExistingPlacementsUnchanged=True,currentCheckpointIdentical=hashlib.sha256((R/'checkpoints/current.blend').read_bytes()).hexdigest()==after)
(R/'characters/street_empty_variant_repair.json').write_text(json.dumps(report,indent=2))
print('STREET_REPAIR_SAVED',json.dumps(report),flush=True)
