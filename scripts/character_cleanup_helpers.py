"""Remove importer-only rig display geometry from the already loaded arena scene.

Root calls cleanup_imported_rig_helpers() during its final source refinement.
The helper does not save either .blend file or change any authored character mesh.
"""
from pathlib import Path
import json,hashlib

ROOT=Path(__file__).resolve().parents[1]
def cleanup_imported_rig_helpers(root=ROOT):
    import bpy
    root=Path(root);collection=bpy.data.collections.get('CharacterLibrary/animated-citizen')
    if collection is None:raise RuntimeError('Expected animated citizen library is absent')
    rigs=[o for o in collection.objects if o.type=='ARMATURE']
    helpers={p.custom_shape for rig in rigs for p in rig.pose.bones if p.custom_shape}
    removed=[]
    for obj in helpers:
        if obj.type!='MESH' or obj not in list(collection.objects):continue
        obj.data.calc_loop_triangles()
        if not obj.name.startswith('Icosphere') or len(obj.data.loop_triangles)!=80:
            raise RuntimeError(f'Unexpected rig display object {obj.name}; do not remove without inspection')
        removed.append({'name':obj.name,'triangles':80,'reason':'Blender GLB importer bone display shape; absent from authored glTF nodes'})
        for rig in rigs:
            for bone in rig.pose.bones:
                if bone.custom_shape==obj:bone.custom_shape=None
        data=obj.data;bpy.data.objects.remove(obj,do_unlink=True)
        if data.users==0:bpy.data.meshes.remove(data)
    population=bpy.data.collections['Population'];cache={}
    for instance in population.objects:
        c=instance.instance_collection
        if c and c.name not in cache:
            total=0
            for o in c.objects:
                if o.type=='MESH':o.data.calc_loop_triangles();total+=len(o.data.loop_triangles)
            cache[c.name]=total
    actual=sum(cache[o.instance_collection.name] for o in population.objects if o.instance_collection)
    expected=61689244
    assert actual==expected,f'Authored source triangles {actual} differ from GLB expected {expected}'
    bpy.context.scene['population_triangle_instances']=actual
    manifest_path=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(manifest_path.read_text())
    previous=manifest['sourcePopulation']['evaluatedTriangleInstances']
    manifest['sourcePopulation']['evaluatedTriangleInstances']=actual
    manifest['sourcePopulation']['triangleCounting']='Authored character meshes only; importer-only bone display helpers excluded'
    manifest['sourcePopulation']['importerDisplayHelperTriangleInstancesRemoved']=previous-actual
    manifest_path.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    for path in [root/'characters/population-validation.json',root/'population_registry.json']:
        data=json.loads(path.read_text());data['sourcePopulation']=manifest['sourcePopulation'];path.write_text(json.dumps(data,indent=2))
    report={'passed':True,'removedHelpers':removed,'sourceInstanceCount':len(population.objects),
            'previousCountIncludingImporterHelpers':previous,'authoredCharacterTriangleInstances':actual,
            'runtimeCharacterTriangleInstances':expected,'identical':actual==expected,
            'removedTriangleInstances':previous-actual,'crowdManifestSHA256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'authoredBodyGarmentAndRigRestGeometryUnchanged':True,'sourceSaveResponsibility':'Caller'}
    (root/'characters/import-helper-cleanup.json').write_text(json.dumps(report,indent=2))
    print('CHARACTER_IMPORT_HELPERS_CLEANED',json.dumps(report),flush=True)
    return report

def ground_verified_instances(root=ROOT):
    """Apply the six measured standing-foot corrections to source and runtime."""
    import bpy
    root=Path(root);audit=json.loads((root/'characters/standing-ground-qc.json').read_text())
    expected={'merchant_014','merchant_020','merchant_021','merchant_027','statue_hero_-1','statue_hero_1'}
    manifest_path=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(manifest_path.read_text())
    entries={i['id']:i for i in manifest['instances']}
    population=bpy.data.collections['Population'];objects={o.get('runtime_id'):o for o in population.objects}
    market_path=root/'market_registry.json';market=json.loads(market_path.read_text());vendors={s['id']:s for s in market['vendor_spawns']}
    changes=[]
    for record in audit['issues']:
        ident=record['id']
        if ident not in expected:raise RuntimeError(f'Ground correction for {ident} has not been reviewed')
        gaps=[f['gap'] for f in record['feet']]
        if any(g is None for g in gaps) or max(gaps)-min(gaps)>.001:raise RuntimeError(f'Uneven or absent support for {ident}')
        delta=-sum(gaps)/len(gaps);entry=entries[ident];obj=objects[ident]
        assert abs(obj.location.z-record['sourcePosition'][2])<1e-4,'Source moved after ground audit'
        for foot in record['feet']:
            support=bpy.data.objects.get(foot['support'])
            assert support is not None,'Audited support was removed'
        old=list(entry['sourcePosition']);new_z=round(old[2]+delta,5)
        obj.location.z=new_z;entry['sourcePosition'][2]=new_z;entry['position'][1]=new_z
        entry['groundContactAdjustment']=round(delta,7)
        if entry['zone']=='market_vendor':vendors[entry['stallId']]['position'][2]=new_z
        changes.append({'id':ident,'oldZ':old[2],'newZ':new_z,'measuredGapBefore':-delta,'sourceAndRuntimeUpdated':True})
    assert {c['id'] for c in changes}==expected,'Expected six measured corrections'
    bpy.context.view_layer.update()
    manifest_path.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    market_path.write_text(json.dumps(market,indent=2))
    report={'passed':True,'changes':changes,'sourceAndRuntimePositionsIdentical':True,
            'crowdManifestSHA256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),'sourceSaveResponsibility':'Caller'}
    (root/'characters/ground-contact-corrections.json').write_text(json.dumps(report,indent=2))
    print('CHARACTER_GROUND_CONTACT_CORRECTIONS',json.dumps(report),flush=True)
    return report

def normalize_animated_library(root=ROOT):
    """Match the corrected unanimated GLB normalization parent in the source library."""
    import bpy
    root=Path(root);collection=bpy.data.collections['CharacterLibrary/animated-citizen']
    scale=1.8/1.0514808893203735
    if not collection.get('human_scale_normalized'):
        roots=[o for o in collection.objects if o.parent is None]
        wrapper=bpy.data.objects.new('CanonicalHumanScale',None);collection.objects.link(wrapper)
        wrapper.scale=(scale,)*3;wrapper['runtime_skip']=True;wrapper['collision']='none';wrapper['source_role']='animated-citizen'
        for obj in roots:obj.parent=wrapper
        collection['human_scale_normalized']=True
    asset_hash=hashlib.sha256((root/'characters/runtime/animated-citizen.glb').read_bytes()).hexdigest()
    manifest_path=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(manifest_path.read_text())
    manifest['assetHashes']['animated-citizen']=asset_hash
    manifest['sourcePopulation']['animatedNormalizationScale']=scale
    for instance in bpy.data.collections['Population'].objects:
        if instance.instance_collection==collection:instance['source_asset_sha256']=asset_hash
    manifest_path.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    for path in [root/'characters/population-validation.json',root/'population_registry.json']:
        data=json.loads(path.read_text());data['assetHashes']['animated-citizen']=asset_hash;data['sourcePopulation']=manifest['sourcePopulation'];path.write_text(json.dumps(data,indent=2))
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    report={'passed':True,'unanimatedParent':'CanonicalHumanScale','scale':scale,'animatedAssetSHA256':asset_hash,
      'clipChannelsAndMeshDataUnchanged':True,'sourceSaveResponsibility':'Caller'}
    (root/'characters/source-animation-normalization.json').write_text(json.dumps(report,indent=2))
    print('SOURCE_ANIMATION_NORMALIZED',json.dumps(report),flush=True)
    return report
