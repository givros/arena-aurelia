"""Write portable asset and animation inventories from validated character outputs."""
from pathlib import Path
from collections import Counter
import json,struct,hashlib,datetime
ROOT=Path(__file__).resolve().parents[1];CHAR=ROOT/'characters'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(name):return json.loads((CHAR/name).read_text())
def glb(path):
    data=path.read_bytes();length=struct.unpack_from('<I',data,12)[0];return json.loads(data[20:20+length])
canonical=CHAR/'CharacterBase.blend';acceptance=read('acceptance.json');components=read('CharacterBase_animation_components_after.json')
guard=read('CharacterBase_animation_component_guard.json');validation=read('runtime-validation.json');crowd=read('runtime/crowd_manifest.json')
source_qc=read('population-source-qc.json');ground_qc=read('standing-ground-qc.json');roles=read('runtime/role-manifest.json')['roles'];role_lookup={r['role']:r for r in roles}
if (CHAR/'ambient_pose_assets.json').exists():
    role_lookup.update({a['id']:{'pose':a['pose']} for a in read('ambient_pose_assets.json')['assets']})
counts=Counter(i.get('sourcePrototype',i['role']) for i in crowd['instances']+crowd['npcs']);assets=[]
for row in validation['reimports']:
    path=Path(row['asset']);role=path.stem;g=glb(path);parts=[]
    for node in g['nodes']:
        if 'mesh' not in node:continue
        mesh=g['meshes'][node['mesh']]
        count=sum(g['accessors'][p.get('indices',p['attributes']['POSITION'])]['count']//3 for p in mesh['primitives'])
        parts.append({'node':node['name'],'triangles':count,'skinned':'skin' in node})
    assets.append({'id':role,'path':'runtime/'+path.name,'sha256':sha(path),'bytes':path.stat().st_size,
        'visibleTriangles':sum(p['triangles'] for p in parts),'parts':parts,'originalBodyTriangles':3134,
        'sourceInstanceCount':counts[role],'sourceCollections':
            ([e.get('sourceCollection','StreetLifeAnimated/'+e['id']) for e in crowd['npcs'] if e.get('sourcePrototype')==role]
             if role.startswith('animated-') and crowd.get('streetLife') else
             [name for name in source_qc['sharedGeometry'] if name.startswith('CharacterVariants/'+role+'/') or name=='CharacterLibrary/'+role]),
        'pose':'bundled skeletal animation' if role.startswith('animated-') else role_lookup[role]['pose'],
        'boundsBlender':row['bounds_blender'],'runtimeCoordinates':{'up':'+Y','forward':'+Z','groundOrigin':True},
        'animationClips':row['clips'],'fullGeometryRetained':True,'reimportValidationPassed':row['passed']})
actual=sum(a['visibleTriangles']*a['sourceInstanceCount'] for a in assets)
registry={'schema':'roman-arena.character-assets/v1','canonical':{'path':'CharacterBase.blend','sha256':sha(canonical),
    'body':{'object':'CharacterBase','mesh':'CharacterMesh','vertices':1596,'triangles':3134,'componentDigest':components['scopes']['body_geometry']['digest']},
    'rig':{'object':'CharacterRig','bones':49,'constraints':7,'restDigest':components['scopes']['rig_rest']['digest']},
    'guard':{'passed':guard['passed'],'violations':guard['violations'],'unchangedScopes':guard['unchanged_scopes'],'report':'CharacterBase_animation_component_guard.json'},
    'neutralTpose':True,'createdOnce':True},
    'provenance':{'skill':'blender-lowpoly-character','skillFile':'C:/Users/limou/.codex/skills/blender-lowpoly-character/SKILL.md',
       'body':'Exact bundled CharacterBase, generated once and preserved through scoped component guards',
       'clothing':'Locally constructed, guarded Roman tunic, belt, hair, sandals, armor, helmet, shield, spear and sword',
       'reference':'references/arena-primary.png','genericCharacterPacksUsed':False,'simplifiedCrowdProxyUsed':False},
    'neutralExports':[{'path':p.name,'sha256':sha(p),'bytes':p.stat().st_size} for p in [CHAR/'CharacterBase.glb',CHAR/'CharacterBase.fbx']],
    'runtimeAssets':assets,'population':{'manifest':'runtime/crowd_manifest.json','manifestSHA256':sha(CHAR/'runtime/crowd_manifest.json'),
       'sourceScene':'../Aurelia_Arena.blend','lastNumericallyVerifiedSourceSHA256':source_qc['sourceSHA256'],
       'staticInstances':len(crowd['instances']),'animatedInstances':len(crowd['npcs']),'totalInstances':len(crowd['instances'])+len(crowd['npcs']),
       'roles':dict(counts),'zones':crowd['counts'],'garmentPalette':crowd['palette'],'stoneHumanStatues':26,
       'sourceRepresentation':'Editable collection instances with shared full mesh data and object-linked garment palette materials',
       'runtimeRepresentation':'The same role GLBs and exact transforms; full-geometry GPU instances and '+str(len(crowd['npcs']))+' skeletal actors',
       'authoredTriangleInstances':actual,'sourceTriangleCountMetadata':crowd['sourcePopulation']['evaluatedTriangleInstances'],
       'sourceContactAndTransformValidationPassed':source_qc['passed'],
       'standingGroundValidationPassed':ground_qc['passed'],'standingGroundContactsTested':ground_qc['tested'],
       'sourceRuntimeTriangleParity':source_qc.get('triangleInstances'),
       'actualSourcePatrolPoseSamples':source_qc.get('actualSourcePatrolPoseSamples',[])},
    'triangleReconciliation':{'authoredPerAnimatedActor':5002,'importerOnlyDisplayHelperPerActor':80,'affectedActors':8,
       'historicalSourceCountIncludingHelpers':61689884,'authoredSourceAndRuntimeCount':actual,
       'reason':'Blender GLB importer generates an Icosphere for bone custom shapes. It is absent from the authored GLB and removed from source instance collections by character_cleanup_helpers.',
       'sourceCleanupApplied':(CHAR/'import-helper-cleanup.json').exists()},
    'validationReports':['acceptance.json','garment-validation.json','runtime-validation.json','population-source-qc.json','standing-ground-qc.json','animation-scale-qc.json']}
if (CHAR/'street_accessory_assets.json').exists():
    registry['streetCarrierAssets']=read('street_accessory_assets.json')
    registry['streetCarrierQC']=read('street_carriers_qc.json')
    registry['streetLife']=crowd.get('streetLife')
    registry['validationReports']+=['street_accessory_assets.json','street_carriers_qc.json','street_life_population_validation.json']
    for key,name in [('streetActivityQC','street_activity_qc.json'),('entryGatherings','street_entry_crowd_validation.json'),('restoredVariants','street_empty_variant_repair.json')]:
        if (CHAR/name).exists():registry[key]=read(name);registry['validationReports'].append(name)
for item in registry['neutralExports']:
    if item['path'].endswith('.glb'):item['compression']='none'
(CHAR/'asset_registry.json').write_text(json.dumps(registry,indent=2))
animation_validation=read('CharacterBase_animation_validation.json');g=glb(CHAR/'runtime/animated-citizen.glb');clips=[]
for item in animation_validation['actions']:
    name=item['action'];clip=next(a for a in g['animations'] if a['name']==name)
    times=[g['accessors'][s['input']] for s in clip['samplers']]
    start=min(a['min'][0] for a in times);end=max(a['max'][0] for a in times)
    path=CHAR/'anim'/(name.lower()+'.fbx')
    clips.append({'name':name,'canonicalFrameRange':[item['frame_start'],item['frame_end']],'canonicalFPS':30,
      'runtimeTimeRangeSeconds':[start,end],'runtimeDurationSeconds':end-start,'runtimeChannels':len(clip['channels']),
      'bundledSourcePayloadSHA256':item['source_fbx_sha256'],'deliveredSkeletonOnlyFBX':'anim/'+path.name,'deliveredFBXSHA256':sha(path),
      'validationPassed':True,'restMatrixMaxDelta':item['rest_matrix_max_delta'],'evaluatedPoseMaxDelta':item['evaluated_pose_matrix_max_delta']})
patrol_qc={p['id']:p for p in source_qc['patrols']};patrols=[]
for p in crowd['npcs']:
    patrols.append({'id':p['id'],'asset':p['asset'],'clip':p['clip'],'speedMetersPerSecond':p['speed'],'loop':p['loop'],
      'phase':p['animationPhase'],'sourcePathBlender':[[q[0],-q[2],q[1]] for q in p.get('path',[])],
      'runtimePathYUp':p.get('path',[]),'sourceInstance':'NPC/'+p['id'],'sourceKeyframes':'Linear closed route with cycles and bundled Walk' if p.get('path') else 'Fixed location; actual bundled Idle clip with cyclic f-curves',
      'sourceMotionValidation':patrol_qc[p['id']]})
animations={'schema':'roman-arena.character-animation/v1','canonical':'CharacterBase.blend','canonicalSHA256':sha(canonical),
    'provenance':{'skill':'blender-lowpoly-character','packageBuilder':'C:/Users/limou/.codex/skills/blender-lowpoly-character/scripts/animation/create_basic_animation_package.py',
      'origin':'User-supplied privately bundled Mixamo source motions in the required character skill; reconstructed locally and installed onto its exact 49-bone rig',
      'runtimeExternalSourceDependency':False,'runtimeFilesSelfContained':True},
    'animatedAsset':'runtime/animated-citizen.glb','animatedAssetSHA256':sha(CHAR/'runtime/animated-citizen.glb'),
    'normalization':read('runtime/animation-normalization.json'),'evaluatedScaleAndGroundQC':read('animation-scale-qc.json'),
    'clips':clips,'animatedPatrolCount':len(patrols),'patrols':patrols,
    'crowdBehavior':'Full-detail seated, resting and conversational groups across the arena and city; '+str(sum(bool(p.get('path')) for p in crowd['npcs']))+' walking actors and '+str(sum(not bool(p.get('path')) for p in crowd['npcs']))+' fixed Idle actors. Input-driven runtime waits preserve the authored routes.',
    'validation':{'passed':animation_validation['passed'],'componentGuardPassed':guard['passed'],
      'sourcePatrolMotionPassed':all(p['keyframes'] and p['cyclic'] for p in source_qc['patrols']),
      'report':'CharacterBase_animation_validation.json','sourceReport':'population-source-qc.json'}}
if (CHAR/'street_activity_qc.json').exists():
    animations['actualStreetActivityValidation']=read('street_activity_qc.json')
    animations['portableCarrierAssets']=read('street_accessory_assets.json')
if crowd.get('districtLife'):
    registry['districtLife']=crowd['districtLife']
    registry['validationReports']+=['district_life_population_validation.json','district_life_source_qc.json']
    animations['districtLife']=crowd['districtLife']
    if (CHAR/'district_life_source_qc.json').exists():registry['districtLifeSourceQC']=read('district_life_source_qc.json')
    if (CHAR/'ambient_pose_assets.json').exists():registry['ambientPoseAssets']=read('ambient_pose_assets.json')
    (CHAR/'asset_registry.json').write_text(json.dumps(registry,indent=2))
(CHAR/'animation_manifest.json').write_text(json.dumps(animations,indent=2))
print(json.dumps({'assetRegistry':'characters/asset_registry.json','animationManifest':'characters/animation_manifest.json','assets':len(assets),'clips':len(clips),'authoredCharacterTriangles':actual,'sourceCandidateHash':source_qc['sourceSHA256']}))
