import bpy,json,math,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena/characters')
reports=[]
for path in sorted((ROOT/'runtime').glob('*.glb')):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    helpers={p.custom_shape for o in bpy.data.objects if o.type=='ARMATURE' for p in o.pose.bones if p.custom_shape}
    helper_triangles=0
    for helper in helpers:helper.data.calc_loop_triangles();helper_triangles+=len(helper.data.loop_triangles)
    objects=[o for o in bpy.data.objects if o.type=='MESH' and o not in helpers]
    deps=bpy.context.evaluated_depsgraph_get()
    evaluated=[o.evaluated_get(deps) for o in objects]
    verts=[o.matrix_world@v.co for o in evaluated for v in o.data.vertices]
    finite=all(math.isfinite(c) for v in verts for c in v)
    triangles=0
    for o in objects:o.data.calc_loop_triangles();triangles+=len(o.data.loop_triangles)
    payload=path.read_bytes();length,kind=struct.unpack_from('<II',payload,12);gltf=json.loads(payload[20:20+length])
    clips=sorted(a.get('name','') for a in gltf.get('animations',[]));bones=sum(len(o.data.bones) for o in bpy.data.objects if o.type=='ARMATURE')
    animated=path.stem.startswith('animated-')
    assert finite and len(objects)>=5 and triangles>=3134
    assert (set(clips)=={'Idle','Walk','Run','Jump'} and bones>=49) if animated else not clips
    authored_triangles=sum(gltf['accessors'][p.get('indices',p['attributes']['POSITION'])]['count']//3 for m in gltf['meshes'] for p in m['primitives'])
    assert triangles==authored_triangles
    reports.append({'asset':str(path),'sha256':hashlib.sha256(payload).hexdigest(),'passed':True,'mesh_count':len(objects),'triangles':triangles,'authoredGltfTriangles':authored_triangles,'importerOnlyDisplayHelperTrianglesExcluded':helper_triangles,'clips':clips,'bones':bones,'finite_vertices':finite,'bounds_blender':[[min(v[a] for v in verts) for a in range(3)],[max(v[a] for v in verts) for a in range(3)]]})
result={'passed':True,'reimports':reports,'source_sha256':hashlib.sha256((ROOT/'CharacterBase.blend').read_bytes()).hexdigest()}
(ROOT/'runtime-validation.json').write_text(json.dumps(result,indent=2))
print('RUNTIME_VALIDATION',json.dumps(result))
