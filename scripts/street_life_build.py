"""Serial integration of the street-life revision into the editable arena source."""
from pathlib import Path
import bpy, sys, json, hashlib, struct

R = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(R/'scripts'))
import build_arena as B

def signature(obj):
    h=hashlib.sha256()
    h.update(obj.name.encode())
    h.update(struct.pack('<16f',*[v for row in obj.matrix_world for v in row]))
    if obj.type=='MESH':
        for v in obj.data.vertices:h.update(struct.pack('<3f',*v.co))
        for p in obj.data.polygons:h.update(struct.pack('<'+str(len(p.vertices))+'I',*p.vertices))
    return h.hexdigest()

def protected_snapshot():
    prefixes=('ARENA/','FACADE/','VIP/','CAVEA/','STAIRS/','HYPOGEUM/','CONCOURSE/','AMBULATORY/','SAND/')
    return {o.name:signature(o) for o in bpy.context.scene.objects if o.name.startswith(prefixes)}

args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['geometry']
stage=args[0]
source=R/'Aurelia_Arena.blend'
bpy.ops.wm.open_mainfile(filepath=str(source))
bpy.context.scene.frame_set(1)
B.mats()
before=protected_snapshot()
population=bpy.data.collections.get('Population')
if population:population.hide_viewport=True

if stage=='geometry':
    from street_life_geometry import apply
    result=apply(B)
elif stage=='population':
    # This real one-sided city plane was authored with its normals facing down.
    # Correct the source winding rather than accepting invalid floor normals.
    import bmesh
    ground=bpy.data.objects['District_ground/ground']
    bm=bmesh.new();bm.from_mesh(ground.data)
    down=[face for face in bm.faces if face.normal.z<-.55]
    bmesh.ops.reverse_faces(bm,faces=down)
    bm.to_mesh(ground.data);bm.free()
    (R/'comparisons/street_life_ground_repair.json').write_text(json.dumps({
        'object':ground.name,'downwardFacesReversed':len(down),
        'positionsAndTopologyCountsPreserved':True,
        'reason':'Actual city ground was present but its one-sided floor normals faced down; strict upward support tests retained.'},indent=2))
    if len(args)>1:
        import importlib
        refinement=importlib.import_module(args[1]).apply(B)
        (R/'comparisons/street_life_silhouette_integration.json').write_text(json.dumps(refinement,indent=2,default=str))
    from street_life_population import apply_population
    result=apply_population(R)
else:raise ValueError(stage)

if population:population.hide_viewport=False
bpy.context.scene.frame_set(1)
bpy.context.view_layer.update()
after=protected_snapshot()
changes=[name for name,h in before.items() if after.get(name)!=h]
assert not changes, f'Protected arena architecture changed: {changes[:12]}'
bpy.context.scene['street_life_revision']=stage
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(source))
report={'stage':stage,'protectedArenaComponents':len(before),'protectedArenaChanges':changes,
        'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'result':result}
(R/'comparisons'/f'street_life_{stage}_integration.json').write_text(json.dumps(report,indent=2,default=str))
print('STREET_LIFE_INTEGRATED',stage,len(before),flush=True)
