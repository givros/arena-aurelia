"""Refresh current scene records only after source and runtime evidence agree."""
from pathlib import Path
from collections import Counter
import json,hashlib
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf8'))
def sha(p):return hashlib.sha256((R/p).read_bytes()).hexdigest()
source=read('source_reopen_validation.json')
transfer=read('source_transfer_validation.json')
runtime=read('viewer/runtime_validation.json')
layout=read('street_life_layout.json')
population=read('characters/street_life_population_validation.json')
crowd=read('characters/runtime/crowd_manifest.json')
assert source['sourceSHA256']==sha('Aurelia_Arena.blend')==transfer['sourceHash']==runtime['source']['blendSHA256']
assert source['passed'] and population['passed'] and runtime['status']=='passed'
assert len(crowd['instances'])+len(crowd['npcs'])==source['counts']['characterInstances']
for stage in ['geometry','population']:
    assert not read(f'comparisons/street_life_{stage}_integration.json')['protectedArenaChanges']
spec=read('scene_spec.json')
spec['streetLife']={'revision':layout['revision'],'layout':'street_life_layout.json',
    'counts':layout['counts'],'population':{k:crowd['streetLife'][k] for k in ['staticAdded','animatedAdded','activityCounts','fullCharacterGeometry']},
    'clearance':layout['clearance'],'sourceSHA256':source['sourceSHA256']}
spec['plaza']['streetWidth']=3.0
spec['plaza']['clearCircumferentialRouteRadii']=[108,85]
spec['city']['building_count']=159+len(layout['shops'])
spec['city']['originalResidentialAssemblies']=159
spec['city']['addedCommercialAssemblies']=len(layout['shops'])
spec['city']['protected_arena_plaza']={'rx':110,'ry':87,'purpose':'Footprint exclusion beyond continuous facade walking space; previous broad empty belt replaced by compact markets.'}
(R/'scene_spec.json').write_text(json.dumps(spec,indent=2))
(R/'street_life_population_registry.json').write_text(json.dumps({k:v for k,v in population.items() if k not in ['groundSupports','routes']},indent=2))
old_market=R/'checkpoints/12_before_street_life_market.json'
if not old_market.exists():old_market.write_bytes((R/'market_registry.json').read_bytes())
(R/'market_registry.json').write_text(json.dumps({'revision':layout['revision'],'layout':'street_life_layout.json',
    'stall_count':len(layout['stalls']),'shop_house_count':len(layout['shops']),
    'stalls':layout['stalls'],'shops':layout['shops'],'vendor_spawns':layout['vendors'],
    'workshops_preserved':layout['preserved_workshops'],'clearance':layout['clearance'],
    'details':'street_life_geometry_registry.json','previousRegistry':str(old_market.relative_to(R))},indent=2))
geometry=read('comparisons/street_life_geometry_integration.json')['result']
geometry['layout']='street_life_layout.json'
geometry['currentSourceSHA256']=source['sourceSHA256']
if (R/'comparisons/street_life_canopy_refinement.json').exists():geometry['canopyRefinement']=read('comparisons/street_life_canopy_refinement.json')
(R/'street_life_geometry_registry.json').write_text(json.dumps(geometry,indent=2))
animation=read('animation_manifest.json')
animation['systems']=[s for s in animation['systems'] if s['id'] not in ['plaza_patrols','district_roles','street_life']]
animation['systems'].append({'id':'street_life','staticActors':crowd['streetLife']['staticAdded'],
    'animatedActors':len(crowd['npcs']),'clips':dict(Counter(n['clip'] for n in crowd['npcs'])),
    'source':'Full canonical role geometry, cyclic Blender paths and skeletal actions',
    'runtime':'Same full assets and routes with individual phases and player/actor yielding',
    'placement':'Customers, conversations, queues and workers beside compact market passages',
    'limits':'Ambient activity; no transaction economy or dialogue simulation'})
(R/'animation_manifest.json').write_text(json.dumps(animation,indent=2))
counts=source['counts'];frames=runtime['performance']['frameIntervalMs'];vp=runtime['viewport']
walkers=sum(n.get('clip')=='Walk' for n in crowd['npcs']);idle=sum(n.get('clip')=='Idle' for n in crowd['npcs'])
report=f'''# Aurelia — arena district with crowded market streets

The revised editable Blender scene and local WebGPU explorer replace the sparse exterior market with compact retail courts and enclosed pedestrian streets. The supplied image remains the primary layout and atmosphere reference.

## Current revision

- {len(layout['stalls'])} detailed market stalls in compact groups, {len(layout['shops'])} complete shop-house assemblies, and the two larger workshops retained as market anchors.
- Pottery, food, produce, cloth and loading activities; varied canopies and goods occupy the market edges while actual passages remain connected.
- {crowd['streetLife']['staticAdded']:,} static street actors, {walkers} walking actors and {idle} animated vendors. Every human retains the required canonical low-poly character body and coherent Roman role assets. The 12,000 seated spectators remain in place.
- Main entry axis: 6 m. The shared layout records the facade ambulatory and individual narrow market route widths; the actual runtime route report records controller traversal against the final geometry.
- Arena footprint, facade, seating, imperial box and underground circulation are preserved. Component signatures were compared before and after both geometry and population integration.

## Evidence

Corresponding before/reference/after views: `comparisons/street_life_final_reference_comparison.jpg`. Saved-source renders are under `renders/street_life_final_*`; runtime street views are under `renders/viewer_street_*`. The reference was reopened for the layout and final visual checks. The final visual assessment is recorded in `comparisons/street_life_review.json`.

The original full-build validation remains as historical evidence in `checkpoints/12_before_street_life_validation.md`. Its earlier exterior population and market-density claims are superseded by this revision.

## Source and transfer checks

- Fresh-process Blender reopen passed: {counts['sceneObjects']:,} objects, {counts['materials']} materials and {counts['cameras']} cameras, with packed dependencies and finite transforms.
- {transfer['visibleTriangles']:,} full architectural triangle instances and {counts['characterTriangleInstances']:,} full human triangle instances are transferred without compression, decimation, LOD or billboard substitutions.
- Actual ground support and source/runtime placement checks: `characters/street_life_population_validation.json`. Canonical body and pre-existing role assets remain unchanged; carrier accessories are recorded separately.
- Current source SHA-256: `{source['sourceSHA256']}`. The source, transfer and runtime reports refer to this identical source version.
- Controller traversal, actor yielding/progress, day/night views and resource/backend errors: `viewer/runtime_validation.json` and the related current route reports.

## Measured desktop runtime

Actual backend: {runtime['backend']}. Viewport: {vp['width']} × {vp['height']} at DPR {vp['dpr']}. Median reference-view frame interval: {frames['p50']:.1f} ms (approximately {1000/frames['p50']:.0f} fps); 95th percentile: {frames['p95']:.1f} ms. Full geometry, native resolution, 4× MSAA and full-detail shadows are retained. Measurements and other view results are in the runtime report. GPU execution timestamps are unavailable on the tested configuration; frame pacing is not an isolated GPU measurement.

## Scope

The crowd presents authored social and commercial activity with walking, idle animation and yielding; it is not a simulated merchant economy. Many background residences remain exterior scenery. Ornament, background-city variety and irregularity remain simpler than the supplied illustration. The revised market addresses the requested close-set street life, without claiming photographic or pixel-level parity.

Local explorer: http://127.0.0.1:4178/. WASD or ZQSD and mouse to walk; Shift to run; Escape to pause. Destination, aerial-view and time controls are available in the interface.
'''
(R/'validation_report.md').write_text(report,encoding='utf8')
print('STREET_LIFE_RECORDS_UPDATED',counts['characterInstances'],walkers,idle)
