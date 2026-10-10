"""Reopen the delivered source and inventory its actual editable contents."""
import bpy,json,sys,hashlib,collections,math
from pathlib import Path
R=Path(__file__).resolve().parents[1]
path=R/'Aurelia_Arena.blend';digest=hashlib.sha256(path.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(path));s=bpy.context.scene;s.frame_set(1)
collections_info=[]
for c in sorted(bpy.data.collections,key=lambda c:c.name):
    objects=list(c.objects)
    if not objects:continue
    collections_info.append({'name':c.name,'objects':len(objects),'meshObjects':sum(o.type=='MESH' for o in objects),'collectionInstances':sum(o.instance_type=='COLLECTION' for o in objects),'components':[o.name for o in objects]})
images=[{'name':i.name,'size':list(i.size),'packed':bool(i.packed_file),'file':i.filepath} for i in bpy.data.images if i.source=='FILE']
missing=[i['name'] for i in images if not i['packed'] and not Path(bpy.path.abspath(i['file'])).exists()]
bad=[]
for o in s.objects:
    if not all(math.isfinite(v) for row in o.matrix_world for v in row):bad.append(o.name)
cameras={o.name.replace('CAM_',''):{'position':list(o.location),'rotationEuler':list(o.rotation_euler),'lens':o.data.lens} for o in s.objects if o.type=='CAMERA'}
source_counts={'sceneObjects':len(s.objects),'meshObjects':sum(o.type=='MESH' for o in s.objects),'materials':len(bpy.data.materials),'cameras':len(cameras),'pointLights':sum(o.type=='LIGHT' and o.data.type=='POINT' for o in s.objects),'characterInstances':s.get('population_instances',0),'characterTriangleInstances':s.get('population_triangle_instances',0),'actions':len(bpy.data.actions)}
population_manifest=json.loads((R/'characters/runtime/crowd_manifest.json').read_text())
expected_population=len(population_manifest['instances'])+len(population_manifest['npcs'])
assert len(cameras)>=10 and source_counts['characterInstances']==expected_population
assert sum(i['role']=='seated-spectator' for i in population_manifest['instances'])==12000
assert not missing and not bad
assert bpy.data.objects.get('HYPOGEUM/Ramp retaining side-1') and bpy.data.objects.get('HYPOGEUM/Ramp retaining side1')
audit={'passed':True,'source':path.name,'sourceSHA256':digest,'reopenedFreshProcess':True,'counts':source_counts,'missingDependencies':missing,'nonfiniteTransforms':bad,'images':images,'cameras':cameras,'renderEvidence':[f'renders/pass3_{n}.png' for n in cameras if (R/f'renders/pass3_{n}.png').exists()],'sourceUnchangedDuringAudit':hashlib.sha256(path.read_bytes()).hexdigest()==digest}
audit['currentRevisionRenderEvidence']=[str(p.relative_to(R)).replace('\\','/') for p in sorted((R/'renders').glob('street_life_*.png'))]
audit['districtRevisionRenderEvidence']=[str(p.relative_to(R)).replace('\\','/') for p in sorted((R/'renders').glob('district_life_*.png'))]
(R/'source_reopen_validation.json').write_text(json.dumps(audit,indent=2))
assets={'scene':'Aurelia Arena District','source':path.name,'sourceSHA256':digest,'provenance':'Original locally modeled architecture, terrain, props and textures. All humans and human statues derive from the required canonical blender-lowpoly-character skill. User-provided image is the composition reference; no external model packs or paid assets.','heroAssets':['Arena elliptical masonry and deep open arcades','Stepped cavea and actual radial stairs','Imperial loggia and canopy','Sand deck over connected hypogeum','River bridge and temple precinct'],'repeatedFamilies':['64 facade bays on two levels','24 seating rows across 16 sectors','Linked Roman city modules','Market stalls and workshops','Canonical character role/palette collections'],'counts':source_counts,'collections':collections_info,'relatedRegistries':['city_registry.json','market_registry.json','market_refinement_registry.json','dressing_registry.json','population_registry.json','characters/asset_registry.json'],'textures':images,'editability':'Named independent architectural components; shared mesh data for repeated modules and collection instances for the population.'}
(R/'asset_registry.json').write_text(json.dumps(assets,indent=2))
for registry in ['street_life_layout.json','street_life_geometry_registry.json','street_life_population_registry.json','district_life_layout.json','district_life_geometry_registry.json','district_life_population_registry.json','arena_interior_life_layout.json','master_world_layout.json','master_world_boundary.json','master_spine_life_layout.json','civic_court_layout.json']:
    if (R/registry).exists():assets['relatedRegistries'].append(registry)
(R/'asset_registry.json').write_text(json.dumps(assets,indent=2))
sp=json.loads((R/'scene_spec.json').read_text());sp['verifiedCounts']=source_counts;sp['finalCameras']=cameras
(R/'scene_spec.json').write_text(json.dumps(sp,indent=2))
print('SOURCE_REOPEN_PASS',json.dumps(source_counts),flush=True)
