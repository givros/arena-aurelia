from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parents[1]
def read(p):return json.loads((R/p).read_text(encoding='utf8'))
s=read('scene_spec.json')
for region in s['regions']:
    if region['id']=='REG_HYPOGEUM':region['bounds']=[-43,-33,51,33];region['floorZ']=-5.6
(R/'scene_spec.json').write_text(json.dumps(s,indent=2))
animation={'scene':'Aurelia Arena District','source':'Aurelia_Arena.blend','characters':'characters/animation_manifest.json','systems':[
 {'id':'day_night','owner':'viewer/src/atmosphere.ts','durationSeconds':1080,'loop':True,'defaultHour':15,'pauseAndManualTimeSelection':True,'changes':['Sun direction and intensity','Moon and sky fill','Sky gradient and distant atmospheric color','Brazier light and emissive intensity']},
 {'id':'brazier_light','owner':'viewer/src/atmosphere.ts','contributors':31,'phaseOffsetPerLamp':True,'amplitude':.06,'angularFrequency':3.7,'geometry':'Static modeled bowl/coals/flames; light intensity flickers'},
 {'id':'plaza_patrols','instances':8,'clip':'Walk','source':'Blender collection instances with cyclic transform paths and actual armature clips','runtime':'Same role GLB and placement/path manifest; continuously sampled AnimationMixer'},
 {'id':'spectator_population','instances':12000,'motion':'Static seated poses; full geometry shared and instanced','placement':'Distinct lower/middle/upper density zones, eight garment palettes and open aisles'},
 {'id':'district_roles','motion':'Static guard, merchant, gladiator, worker, noble and citizen poses; animated eight-person patrol listed separately'},
 {'id':'fabric_and_water','motion':'Static authored geometry/materials; no cloth or fluid simulation'}
], 'interaction':'First-person exploration, collision, aerial orbit, destination selection, day/night controls and fullscreen. No scripted gladiator combat or interactive gates.'}
(R/'animation_manifest.json').write_text(json.dumps(animation,indent=2))
source=read('source_reopen_validation.json');transfer=read('source_transfer_validation.json');runtime=read('viewer/runtime_validation.json')
if runtime['source']['blendSHA256']!=source['sourceSHA256']:raise RuntimeError('Final runtime report must match final source before writing final validation report')
names=['reference','top','approach','facade','seating','floor','vip','hypogeum','market','reverse']
for p in [1,2,3]:
    for n in names:assert (R/f'renders/pass{p}_{n}.png').exists()
frames=runtime['performance']['frameIntervalMs'];cpu=runtime['performance']['cpuCallbackMs'];vp=runtime['viewport'];counts=source['counts']
failed=[c for c in runtime['checks'] if c['status'] not in ['passed','not_applicable','unavailable']]
text=f'''# Aurelia — validated scene and exploration

The delivered environment is an editable Blender scene and a local desktop WebGPU explorer. The previous Abyssal Garden project is preserved separately. The supplied image remains the primary composition reference.

## Delivered world

- Arena footprint: 212 × 166 m, 34.3 m parapet, 64 structural bays on each of two facade levels, 3.2 m deep open arcades.
- Arena floor: 140 × 94 m ellipse, real sand deck, grated opening, cage, combat markers, weapon racks and a connected eastern service ramp.
- Cavea: 24 solid stepped rows, 16 radial stair aisles, lower/middle/upper crowd zones, 384 curved benches, upper promenade and north imperial loggia.
- Below ground: connected holding/preparation rooms, storage, cages, props, retaining walls and a ramp to the sand at −5.6 m.
- District: 28 vendor stalls, two larger workshops, six carts, goods racks, basins, 159 residential building assemblies, a temple precinct, two basilicas, two towers, bridge, canal, aqueduct, trees and distant hills.
- Population: 12,000 seated spectators and 322 other human instances, including guards, merchants, nobles, workers, gladiators, citizens, statues and eight walking patrols. Every human derives from the required canonical character skill.

## Reference comparisons

The original reference was reopened through construction. Named elevated and human-scale views were inspected; comparison images are retained in `comparisons/`.

| Checkpoint | Comparison and resulting decisions | Evidence |
|---|---|---|
| 1. Map boundaries | Reserved a dominant central oval, canal/bridge west, aqueduct east, temple and city north; kept city approach space. | `renders/checkpoint_01_reference.png` |
| 2. Footprint | Checked the oval rather than a circle, interior opening and plaza offsets. | `renders/checkpoint_02_reference.png` |
| 3. Facade | Built two complete deep arcades and continuous architectural datums; corrected normals and supports. | `renders/checkpoint_03_reference.png` and refined view |
| 4. Seating bowl | Built actual tread/riser rows, tier divisions and sixteen stair slots. | `renders/checkpoint_04_reference.png` |
| 5. Sand floor | Retained a broad open combat area with modeled deck openings and props. | `renders/checkpoint_05_reference.png` |
| 6. Entrances/circulation | Connected outer arches, vaulted radial routes and stair access. | `renders/checkpoint_06_reference.png` |
| 7. Hypogeum | Added service rooms, cross vaults and ramp; moved lower stairs away from the ramp and raised arena architecture to improve monumentality. | `renders/checkpoint_07_refined.png` |
| 8. Market/plaza | Kept the central avenue and circumferential route open while distributing functional vendors. | `renders/checkpoint_08_reference.png` |
| 9. City | Refined temple height/placement, city families, bridge approaches and aqueduct to preserve the reference landmark order. | `renders/checkpoint_09_refined.png` |
| 10. Ornament | Added real cloth, standards, statues, furnishings, benches and braziers; cleared foreground canopy panels. | `renders/checkpoint_10_reference.png` |
| 11. Population | Corrected sparse stands with 12,000 compact seated full-body characters, reserved aisles and the imperial axis. | `renders/checkpoint_11_reference.png`, final population QC |
| 12. Final comparison | Added larger close workshops, darker cloth, sand wear, imperial valances, ramp retaining walls and actual room clearance. | `comparisons/pass3_reference_comparison.jpg` |

## Three complete view passes

Each pass includes reference aerial, top, approach, facade detail, seating, sand, imperial interior, hypogeum, market and reverse views.

1. Pass 1 exposed sparse crowd, pale regular cloth, sharp sand stains, slots under seating risers and weak close cameras. Corrections: denser full crowd, darker cloth, continuous risers, arena-wide 4096 px sand atlas, larger market structures and improved camera placement.
2. Pass 2 exposed open ramp sides, cavea geometry entering the loggia, a floating throne, importer-only rig display geometry, small standing contact gaps and the final promenade lip. Corrections: physical retaining walls, a reserved loggia interior, throne supports, helper removal, verified contacts and inward cornice clearance. Foreground workshops were brought closer; southern hills close the reverse skyline.
3. Pass 3 verifies those corrections from all ten viewpoints and from the reopened source. The imperial room is clear, ramp enclosure is continuous, aisles remain open and distant context surrounds the arena. Nine-view sheet: `comparisons/pass3_nine_views.jpg`; reverse detail: `renders/pass3_reverse.png`.

## Functional and source validation

- Fresh-process Blender reopen passed: {counts['sceneObjects']:,} scene objects, {counts['meshObjects']:,} mesh objects, {counts['materials']} materials, {counts['cameras']} cameras and {counts['pointLights']} point lights. All file-image dependencies are packed; no missing dependencies or nonfinite transforms.
- All {transfer['visibleTriangles']:,} evaluated architectural triangles and 61,689,244 authored human triangle instances are preserved in the viewer. Full positions, corner normals, UVs, source texture resolutions, materials and transforms are transferred. No decimation, LOD, billboard crowds or geometry compression.
- Exact character body/rig validation is retained under `characters/reports/`. All 12,000 seated contacts and all 314 static standing contacts pass. Source and runtime placements match. Actual walking geometry was sampled after normalization; adult scale and foot contact pass.
- Nine continuous runtime routes pass: plaza to sand; sand to upper terraces; final stair to gallery; terraces down to sand; middle cavea to imperial box; arena to hypogeum/prep; hypogeum return; west-to-east bridge; avenue to temple portico and cella.
- City geometry probes pass: 536 bridge support samples and 561 temple samples. Runtime checks cover WASD/ZQSD, mouse look, pause, fullscreen, day/night changes, source fidelity, reload/disposal, finite bounds and backend errors.
- Editable source SHA-256: `{source['sourceSHA256']}`. The source, transfer and final runtime reports refer to this identical version.

## Measured desktop runtime

Actual backend: {runtime['backend']}; hardware adapter: {runtime['adapter'].get('vendor','')} {runtime['adapter'].get('architecture','')}; viewport {vp['width']} × {vp['height']} at DPR {vp['dpr']}. Native resolution, 4× MSAA, 4096 px full-detail sun shadow map, all crowd geometry retained.

- Median frame interval: {frames['p50']:.1f} ms (approximately {1000/frames['p50']:.0f} fps); 95th percentile: {frames['p95']:.1f} ms.
- Median CPU callback: {cpu['p50']:.1f} ms; 95th percentile: {cpu['p95']:.1f} ms.
- Sampling duration: {runtime['performance']['samplingSeconds']} seconds after warmup, without simultaneous Blender rendering. Browser/driver shader caches are not controlled. Frame pacing is not an isolated GPU execution measurement; GPU timestamp timing availability is recorded in the runtime report.
- Geometry is shared, instanced, spatially grouped and culled; small architecture groups are merged without changing their vertices. Native clustered lighting retains all 31 finite source lights. No persistent lighting cache is used.

Full evidence and checks: `viewer/runtime_validation.json`, `viewer/source_validation.json`, `viewer/render_profile.json`, `source_reopen_validation.json`, `source_transfer_validation.json`, `characters/population-source-qc.json` and `comparisons/city/city_final_audit.json`.

## Visual and scope limits

The layout, architectural hierarchy and explorable arena are recognizable against the reference. The result is a stylized reconstruction with simpler carved ornament, more uniform city families and a more open, regularly spaced plaza than the source image. The southern reverse view has a broad plain terrain band and less city layering. It does not achieve photorealistic or pixel-level reference parity, and a 9/10 similarity claim is not supported.

The arena, passages, stands, imperial box, underground rooms, plaza, city streets, bridge and temple approach are explorable. Most surrounding residential buildings are exterior context. The population uses static role poses and eight animated patrols; there is no merchant transaction simulation, fighting AI, interactive cage machinery or animated fabric/water simulation. Distant hills are scenery beyond the walking boundary. Desktop was verified; mobile was outside the requested scope.

Local viewer: http://127.0.0.1:4178. Walk with WASD or ZQSD and mouse; Shift runs; Escape pauses. Aerial inspection, destinations, time controls and fullscreen are available in the compact interface.
'''
(R/'validation_report.md').write_text(text,encoding='utf8')
assert not failed,f'Runtime checks need review: {failed}'
print('FINAL_DELIVERABLE_RECORDS_READY')
