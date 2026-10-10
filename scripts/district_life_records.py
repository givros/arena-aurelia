"""Publish current citywide scene records only when final source/runtime checks agree."""
from pathlib import Path
from collections import Counter
import json,hashlib
from semantic_metadata import current_semantic_fields
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf8'))
def write(p,d):(R/p).write_text(json.dumps(d,indent=2),encoding='utf8')
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
source=read('source_reopen_validation.json');transfer=read('source_transfer_validation.json');runtime=read('viewer/runtime_validation.json')
performance=read('viewer/performance_optimization.json')
stable_grid=read('viewer/stable_grid_validation.json')
profile=read('viewer/render_profile.json')
district=read('district_life_layout.json');street=read('street_life_layout.json');manifest=read('characters/runtime/crowd_manifest.json')
population=read('characters/district_life_population_validation.json')
geometry=read('comparisons/district_life_geometry_integration.json')
master=read('master_world_layout.json');boundary=read('master_world_boundary.json')
master_integration=read('comparisons/master_world_integration.json');edge=read('comparisons/world_boundary_geometry.json')
civic=read('civic_court_layout.json');civic_integration=read('comparisons/civic_court_integration.json')
assert master_integration['passed'] and not master_integration['unexpectedChanges']
assert civic_integration['passed'] and not civic_integration['changedExistingComponents']
saved_geometry=read('comparisons/district_life_saved_geometry.json')
assert saved_geometry['passed'] and saved_geometry['sourceSHA256']==sha('Aurelia_Arena.blend')
assert saved_geometry['layoutSHA256']==sha('district_life_layout.json')
assert saved_geometry['reviewCameraAuthoritySHA256']==sha('district_review_views.json')
camera_revision=read('comparisons/district_review_camera_integration.json')
assert camera_revision['passed'] and not camera_revision['changedNonCameraObjects']
bank_revision=read('comparisons/watergate_boundary_integration.json')
assert bank_revision['passed'] and not bank_revision['changedExistingComponents']
assert bank_revision['cameraUnchanged'] and bank_revision['populationUnchanged']
assert bank_revision['beforeSourceSHA256']==camera_revision['sourceSHA256']
assert bank_revision['sourceSHA256']==sha('Aurelia_Arena.blend')
assert bank_revision['authoritySHA256']==sha('watergate_boundary_revision.json')
assert source['sourceSHA256']==sha('Aurelia_Arena.blend')==transfer['sourceHash']==runtime['source']['blendSHA256']
assert performance['status']=='passed' and performance['sourceSHA256']==source['sourceSHA256']
assert stable_grid['status']=='passed' and stable_grid['sourceSHA256']==source['sourceSHA256']
assert stable_grid['finalBuild']==performance['finalBuild']
assert stable_grid['moduleSHA256']==sha('viewer/src/stable-clustered-lighting.js')
assert profile['lighting']['fog']['nearMeters']==1200 and profile['lighting']['fog']['farMeters']==4500
for measured_file in ['viewer/performance/baseline_final.json','viewer/performance/final.json']:
    measured=read(measured_file)
    assert measured['quality']['fog']==[1200,4500]
    assert measured['sourceSHA256']==source['sourceSHA256']
assert performance['qualityPreserved']
assert population['crowdManifestSHA256']==sha('characters/runtime/crowd_manifest.json')==runtime['source']['characterManifestSHA256']
for authority in manifest['districtLife']['layouts']:
    assert authority['sha256']==sha(authority['path']),authority['path']
assert source['passed'] and population['passed'] and runtime['status']=='passed'
assert not geometry['changedExistingComponents']
assert not read('comparisons/district_life_population_integration.json')['changedExistingComponents']
assert len(manifest['instances'])+len(manifest['npcs'])==source['counts']['characterInstances']
assert all(v['assemblies'] and v['loops'] for v in district['coverage'].values())
live=manifest['districtLife'];counts=source['counts'];regions=district['regions']
statues=sum(p.get('zone') in ('facade_statue','ceremonial_statue') for p in manifest['instances'])
spec=read('scene_spec.json')
spec.update(current_semantic_fields(R,spec))
spec['streetLife']={'revision':street['revision'],'layout':'street_life_layout.json','counts':street['counts'],'population':manifest['streetLife'],'clearance':street['clearance']}
spec['plaza']['streetWidth']=3
spec['plaza']['clearCircumferentialRouteRadii']=[108,85]
spec['plaza']['circulationNote']='Nominal ellipse with the authored southern forecourt detour around projecting entry piers and statues.'
spec['plaza']['clearCircumferentialRoute']=next(r for r in street['clear_routes'] if r['id']=='FacadeAmbulatory')
spec['districtLife']={'revision':district['revision'],'layout':'district_life_layout.json','layoutSHA256':sha('district_life_layout.json'),
    'regions':regions,'counts':district['counts'],'coverage':district['coverage'],'population':live,
    'feedbackReference':'references/empty_outer_ward_feedback.png','sourceSHA256':source['sourceSHA256']}
spec['city']['originalResidentialAssemblies']=159
spec['city']['layout']='master_world_layout.json'
spec['city']['cityGridRetired']=True
spec['city']['organicStreetSpines']=len(master['quarterSpines'])
spec['city']['courtyardCount']=len(master['courtyards'])
spec['city'].pop('protected_arena_plaza',None)
spec['city']['protectedCirculation']={'facadeAmbulatory':spec['plaza']['clearCircumferentialRoute'],
    'ceremonialAxisWidth':6,'quarterConnections':'district_life_layout.json and master_world_layout.json'}
spec['worldBoundary']={'layout':'master_world_boundary.json','layoutSHA256':sha('master_world_boundary.json'),
    'wallHeight':boundary['wall']['height'],'closedGates':list(edge['closedGates']),
    'watergates':edge['riverGates'],'continuousOuterTerrain':True,'groveTrees':len(edge['groveTrees']),
    'outerVillas':len(edge['completeOuterVillas']),'scope':edge['caveat']}
spec['worldBoundary']['quayPedestrianGates']={'authority':'watergate_boundary_revision.json',
    'authoritySHA256':bank_revision['authoritySHA256'],'count':4,
    'purpose':'Supported visible iron gates close pedestrian quay-cap passages beside both river arches while retaining the central water corridor.'}
spec['referenceContinuation']={'concept':'references/expanded_city_concept.png','provenance':'references/expanded_city_concept.json','role':'Layout aid for the unseen city; the primary user image still governs the arena.'}
spec['sceneryBeyondBounds']={'layout':'master_world_boundary.json','geometryAudit':'comparisons/world_boundary_geometry.json',
    'scope':edge['caveat'],'playableBoundary':'Physical irregular walls and four closed city gates inside the rectangular safety envelope.'}
spec['civicCourt']={'layout':'civic_court_layout.json','layoutSHA256':sha('civic_court_layout.json'),'parts':len(civic['parts']),
    'role':'Fountain garden, planted beds, resting benches and complete L-shaped roofed porticoes enclose the eastern civic void.'}
spec['streetReviewCameras']={'authority':'district_review_views.json','sha256':sha('district_review_views.json')}
spec['city']['addedCommercialAssemblies']=len(street['shops'])+sum(i['kind']=='infill_shop' for i in district['items'])
spec['city']['building_count']=159+spec['city']['addedCommercialAssemblies']
write('scene_spec.json',spec)
write('district_life_geometry_registry.json',{'savedSource':saved_geometry,'integration':geometry,'civicCourtIntegration':civic_integration})
write('district_life_population_registry.json',{k:v for k,v in population.items() if k not in ['groundContacts','routeChecks']})
population_history=R/'checkpoints/12_original_population_registry.json'
if not population_history.exists():
    population_history.write_bytes((R/'population_registry.json').read_bytes())
all_people=manifest['instances']+manifest['npcs']
write('population_registry.json',{
    'revision':'citywide-life','passed':population['passed'],
    'source':'Aurelia_Arena.blend','sourceSHA256':source['sourceSHA256'],
    'manifest':'characters/runtime/crowd_manifest.json','manifestSHA256':sha('characters/runtime/crowd_manifest.json'),
    'counts':dict(Counter(p['zone'] for p in all_people)),
    'sourcePopulation':{'instanceCount':len(all_people),'staticInstances':len(manifest['instances']),
        'animatedActors':len(manifest['npcs']),'evaluatedTriangleInstances':counts['characterTriangleInstances'],
        'allCharactersFullBase':True,'runtimeManifestRequired':True},
    'clips':dict(Counter(n['clip'] for n in manifest['npcs'])),
    'canonicalCharacterSHA256':manifest['canonicalCharacterSHA256'],
    'assetHashes':manifest['assetHashes'],'placement_contract':manifest['placement_contract'],
    'validationReports':'characters/asset_registry.json',
    'historicalOriginalBuild':'checkpoints/12_original_population_registry.json',
    'scope':'Static human groups are visual occupants; 164 individually animated actors provide ambient activity.'})
write('market_registry.json',{'revision':'citywide-life','streetLayout':'street_life_layout.json','districtLayout':'district_life_layout.json',
    'stalls':street['stalls'],'shops':street['shops'],'districtAssemblies':district['items'],
    'vendor_spawns':street['vendors']+district['vendors'],'workshops_preserved':street['preserved_workshops'],
    'counts':{'arenaMarketStalls':len(street['stalls']),'arenaShopHouses':len(street['shops']),
        'vendorSpawns':len(street['vendors'])+len(district['vendors'])},
    'streetCounts':street['counts'],'districtCounts':district['counts']})
animation=read('animation_manifest.json')
for system in animation['systems']:
    if system['id']=='brazier_light':system['contributors']=counts['pointLights']
animation['systems']=[s for s in animation['systems'] if s['id'] not in ['plaza_patrols','district_roles','street_life','district_life']]
animation['systems'].append({'id':'district_life','animatedActors':len(manifest['npcs']),
    'clips':dict(Counter(n['clip'] for n in manifest['npcs'])),'regions':live['zoneCounts'],
    'source':'Full canonical role geometry, real skeletal actions, cyclic authored walking paths and varied frozen Idle poses',
    'runtime':'The same complete assets and placements with individual phases, constant walking speed and player/actor yielding',
    'limits':'Ambient social, working and commercial activity; no simulated transactions or dialogue economy'})
write('animation_manifest.json',animation)
asset=read('asset_registry.json')
for name in ['district_life_layout.json','district_life_geometry_registry.json','district_life_population_registry.json','arena_interior_life_layout.json','master_world_layout.json','master_world_boundary.json','master_spine_life_layout.json','civic_court_layout.json','district_review_views.json','watergate_boundary_revision.json']:
    if name not in asset['relatedRegistries']:asset['relatedRegistries'].append(name)
write('asset_registry.json',asset)
frames=runtime['performance']['frameIntervalMs'];vp=runtime['viewport'];walking=sum(n['clip']=='Walk' for n in manifest['npcs'])
idle=sum(n['clip']=='Idle' for n in manifest['npcs'])
region_rows='\n'.join(f"| {regions[k]['label']} | {v['assemblies']} | {live['zoneCounts'].get('district_'+k,0)} | {v['loops']} |" for k,v in district['coverage'].items())
performance_rows='\n'.join(
    f"| {s['name'].replace('_',' ')} | {s['before']['frameIntervalMs']['p95']:.1f} / {s['after']['frameIntervalMs']['p95']:.1f} | "
    f"{s['before']['frameIntervalMs']['max']:.1f} / {s['after']['frameIntervalMs']['max']:.1f} |"
    for s in performance['scenarios'])
before_load=performance['startupTradeoff']['before']['freshContextMs']/1000
after_load=runtime['loads']['freshTemporaryContextMs']/1000
report=f'''# Aurelia — living arena district

The editable Blender environment and local WebGPU explorer extend the reference arena into a coherent inhabited city. The original reference remains the architectural and atmospheric anchor. A generated continuation concept supports the unseen districts; it is not a render of the delivered model.

## Built changes

All 159 existing residential assemblies are reused in {len(master['quarterSpines'])} curved street systems with {len(master['courtyards'])} fitted courtyards. Complete houses move as rigid assemblies, preserving their geometry. The old common street grid and courtyard walls are replaced. Arena architecture, established market shops, original crowds and monumental infrastructure are preserved.

The arena edge has {len(street['stalls'])} detailed market stalls and {len(street['shops'])} shop houses. Beyond it, {district['counts']['commercial_assemblies']} commercial assemblies include {district['counts']['complete_infill_shops']} complete infill shops and {district['counts']['shopfronts']} supported shopfront awnings, with loading areas, goods, benches and warm lamps.

A complete L-shaped peristyle gives the eastern civic space a purpose: a fountain garden around retained cypresses, with planted herb beds, shaded resting benches and connected open circulation. Its {len(civic['parts'])} declared parts include structural columns, tiled roofs, rafters, level paving and supported lamps.

An irregular physical enclosure has four closed city gates, {edge['riverGates']} arched watergates and complete watchtowers. The river continues into rolling outer terrain, with {len(edge['groveTrees'])} grounded trees and {len(edge['completeOuterVillas'])} complete hillside villas. This landscape covers the former rectangular platform edge; closed gates define the playable boundary.

Four supported iron pedestrian gates close the narrow quay-cap passages beside the river arches. They prevent walking beyond the city to the technical safety clamp while preserving the central waterway. This local revision adds {bank_revision['newMeshObjects']} meshes without changing any existing geometry, cameras, people or materials.

New activity extends through {len(regions)} regional areas. Full bodies, clothing and carried goods are retained for every human. The character-derived inventory has {counts['characterInstances']:,} instances, including {statues} sculptural figures, the existing 12,000 seated spectators, {walking} walking actors and {idle} fixed animated staff. The latest citywide addition contributes {live['staticAdded']:,} static residents and {live['animatedAdded']} animated actors, including arena galleries, backstage passages and arrival flow.

| Region | Commercial assemblies | Accepted new people | Moving routes |
| --- | ---: | ---: | ---: |
{region_rows}

The six-metre ceremonial axis remains clear. Narrow market passages and city connections use the shared authored routes; the complete facade circuit detours around the projecting entrance monument. Actual controller traversal is recorded against the final exported geometry.

## Visual and movement evidence

- Regional views: `comparisons/district_life_final_regional_sheet.jpg` and full-resolution `renders/district_life_final_*`.
- Whole-project before/after: `comparisons/district_life_final_world_comparison.jpg`.
- User-reported empty area: `comparisons/district_life_final_southern_ward_comparison.jpg`.
- Layout and dimensional checks: `comparisons/district_life_layout_map.png` and `comparisons/district_life_layout_audit.json`.
- Organic city reflow and physical edge: `comparisons/master_world_layout_map.png`, `comparisons/master_world_integration.json` and `comparisons/world_boundary_geometry.json`.
- Quay passage closure and preservation: `watergate_boundary_revision.json`, `comparisons/watergate_boundary_integration.json` and the final runtime boundary checks.
- Eastern fountain court: `comparisons/civic_court_layout_map.png` and its source render views.
- Actual source contacts, preserved actors and full triangle counts: `characters/district_life_population_validation.json` and the fresh character QC reports.
- Runtime views, continuous traversal, actor circulation/yielding and day/night: `viewer/runtime_validation.json` and its related route/activity reports.
- Final reference comparison and remaining visual limits: `comparisons/street_life_review.json`.

The first street revision remains documented by its own renders and comparison files. The original arena build validation remains in `checkpoints/12_before_street_life_validation.md`; its older exterior density/counts are historical.

## Source and performance verification

The saved scene was reopened in a fresh Blender process: {counts['sceneObjects']:,} scene objects, {counts['materials']} materials, {counts['cameras']} cameras and no missing packed dependencies or invalid transforms. The explorer transfers {transfer['visibleTriangles']:,} complete architectural triangle instances and {counts['characterTriangleInstances']:,} human triangle instances without geometry compression, simplification, crowd billboards or LOD replacement.

Source SHA-256: `{source['sourceSHA256']}`. Source, transfer and runtime checks refer to this identical version; the runtime also binds the layout and character manifest hashes.

Tested backend: {runtime['backend']}, {vp['width']} × {vp['height']} at DPR {vp['dpr']}. Median reference-view frame interval: {frames['p50']:.1f} ms (approximately {1000/frames['p50']:.0f} fps), 95th percentile {frames['p95']:.1f} ms. Native resolution, full assets, 4× MSAA and full-detail shadows remain enabled. Per-view measurements are in the runtime report. The dedicated WebGPU optimization evidence in `viewer/performance_optimization.json` separates frame pacing, CPU work and available GPU timestamp measurements, with matching before/after quality and source. Frame interval is not presented as isolated GPU execution time. Its reference ledger is `viewer/performance_reference_ledger.json`.

| Fixed desktop scenario | 95th-percentile frame interval, before / after (ms) | Largest sampled frame interval, before / after (ms) |
| --- | ---: | ---: |
{performance_rows}

Fresh isolated-context preparation took {before_load:.1f} seconds before and {after_load:.1f} seconds after optimization. Preparing the scene's main and shadow pipelines moves work into loading to reduce pauses during exploration. Browser/driver shader-cache state is not controlled; these are measured context loads, not guaranteed first-install times. Other applications were using the GPU during verification, so this is a shared-GPU measurement rather than an exclusive hardware benchmark; small throughput differences are not treated as conclusive. This full-detail scene remains demanding and does not promise a locked 60 fps. All raw samples, actual travel distances and the shared corrected movement code are recorded with the paired measurements.

The requested lighter fog now begins at 1,200 metres and ends at 4,500 metres, keeping the city clear and a light haze over the distant landscape. Both measured implementations use these same settings.

Clustered lighting now keeps its shader nodes and storage stable during ordinary window resizing. The reserved grid covers a native 3,840 × 2,160 framebuffer and uses 50,135,040 bytes, about 40.7 MB more than the original 1,440 × 1,080 allocation. Every light, depth slice and active cluster remains evaluated. The CPU, actual GPU light-list, pixel and production resize evidence is recorded in `viewer/stable_grid_validation.json`. Larger grids can grow geometrically within the device buffer limit and may recompile; outgoing storage remains allocated until renderer teardown. Resize stability is therefore bounded to the current allocation, without silently lowering resolution or removing lights.

## Scope and limits

This is ambient district life with walking, waiting, resting, carrying and staff animations; it does not simulate commerce or conversations. Static crowd groups are visual occupants rather than player collision barriers; moving actors yield along authored routes. Background residences remain largely exterior scenery, and the outer hills and villas continue the view beyond the enclosed playable city. Architecture, ornament and material variation are simplified relative to the supplied illustration; building modules, clothing and seated crowd patterns repeat more regularly, and the lighting is stylized. Visual comparisons record those differences without claiming photographic parity.

Local explorer: http://127.0.0.1:4178/. Walk with WASD or ZQSD and mouse, run with Shift, pause with Escape. Places, aerial views and time controls are available in the interface.
'''
(R/'validation_report.md').write_text(report,encoding='utf8')
print('CITYWIDE_RECORDS_UPDATED',counts['characterInstances'],len(regions),walking,idle)
