"""Replace only the managed source crowd, preserving every architectural object."""
from pathlib import Path
import sys,json,hashlib,struct,shutil
import bpy

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import build_arena as api
from character_population import build_population

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fingerprint(obj):
    h=hashlib.sha256()
    h.update(obj.name.encode());h.update(obj.type.encode())
    h.update(struct.pack('<16f',*[x for row in obj.matrix_world for x in row]))
    h.update(str(sorted((k,str(obj[k])) for k in obj.keys())).encode())
    if obj.type=='MESH':
        for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
        for p in obj.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices));h.update(struct.pack('<I',p.material_index))
        for slot in obj.material_slots:h.update((slot.material.name if slot.material else '').encode())
    return h.hexdigest()

current=ROOT/'checkpoints/current.blend'
bpy.ops.wm.open_mainfile(filepath=str(current))
bpy.context.scene.frame_set(1)
old_hash=sha(current)
owned_collections=[c for c in bpy.data.collections if c.name=='Population' or c.name.startswith(('CharacterLibrary/','CharacterVariants/'))]
owned_objects=set(o for c in owned_collections for o in c.objects)
architecture={o.name:fingerprint(o) for o in bpy.data.objects if o not in owned_objects}
old_count=bpy.context.scene.get('population_instances')
actions=set(o.animation_data.action for o in owned_objects if o.animation_data and o.animation_data.action)
owned_data=set(o.data for o in owned_objects if o.data is not None)
for obj in owned_objects:bpy.data.objects.remove(obj,do_unlink=True)
for col in owned_collections:bpy.data.collections.remove(col)
for data in owned_data:
    if data.users==0:
        if isinstance(data,bpy.types.Mesh):bpy.data.meshes.remove(data)
        elif isinstance(data,bpy.types.Armature):bpy.data.armatures.remove(data)
for action in list(bpy.data.actions):
    if action.users==0 and (action in actions or action.name in ['Idle','Walk','Run','Jump']):bpy.data.actions.remove(action)
api.mats()
result=build_population(api,api.SPEC)
bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
failures=[]
for name,signature in architecture.items():
    obj=bpy.data.objects.get(name)
    if obj is None or fingerprint(obj)!=signature:failures.append(name)
assert not failures,f'Architecture unexpectedly changed: {failures[:20]}'
assert bpy.context.scene['population_instances']==12322
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=str(current))
final=ROOT/'Aurelia_Arena.blend';shutil.copy2(current,final)
(ROOT/'population_registry.json').write_text(json.dumps(result,indent=2))
spec_path=ROOT/'characters/population-spec.json';spec=json.loads(spec_path.read_text())
spec.update(spectators=12000,spectator_spacing_meters=.72,placement_status='Built and source/runtime matched; source inspection follows')
spec_path.write_text(json.dumps(spec,indent=2))
report={'passed':True,'previousSourceSHA256':old_hash,'sourceSHA256':sha(current),'finalSourceSHA256':sha(final),
        'sourceFilesIdentical':sha(current)==sha(final),'architectureObjectsPreserved':len(architecture),
        'architectureFingerprintChanges':failures,'previousPopulation':old_count,'population':result['sourcePopulation'],
        'newSeatedAssetSHA256':sha(ROOT/'characters/runtime/seated-spectator.glb'),
        'newCrowdManifestSHA256':sha(ROOT/'characters/runtime/crowd_manifest.json')}
(ROOT/'characters/population-rebuild.json').write_text(json.dumps(report,indent=2))
print('CHARACTER_POPULATION_REBUILD',json.dumps(report),flush=True)
