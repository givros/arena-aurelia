"""Read-only source population/contact verification and close source renders.

Run only after stage 11 is saved. This tool never saves or modifies the .blend.
"""
from pathlib import Path
import sys,json,math,hashlib,argparse,statistics
from collections import defaultdict
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[1]
def args():
    p=argparse.ArgumentParser();p.add_argument('--source',default=str(ROOT/'checkpoints/current.blend'))
    p.add_argument('--no-render',action='store_true');p.add_argument('--samples',type=int,default=16)
    return p.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def curves(action):
    if hasattr(action,'fcurves'):yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:yield from bag.fcurves
def main():
    a=args();source=Path(a.source);source_hash=sha(source)
    bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;scene.frame_set(1)
    if scene.get('stage',0)<11:raise RuntimeError('Stage 11 must be saved before population QC')
    manifest=json.loads((ROOT/'characters/runtime/crowd_manifest.json').read_text())
    population=bpy.data.collections.get('Population')
    if population is None:raise RuntimeError('Source Population collection is absent')
    source_by_id={o.get('runtime_id'):o for o in population.objects if o.get('runtime_id')}
    items=manifest['instances']+manifest['npcs'];failures=[];support=[];geometry={};bvh_cache={}
    if len(source_by_id)!=len(items):failures.append({'kind':'population_count','source':len(source_by_id),'runtime':len(items)})
    def bvh(obj):
        if obj.name not in bvh_cache:
            verts=[obj.matrix_world@v.co for v in obj.data.vertices]
            bvh_cache[obj.name]=BVHTree.FromPolygons(verts,[list(p.vertices) for p in obj.data.polygons])
        return bvh_cache[obj.name]
    def surface(obj,p):
        hit,normal,index,distance=bvh(obj).ray_cast(Vector((p.x,p.y,p.z+1)),Vector((0,0,-1)),3)
        return None if hit is None else hit.z
    def probes(collection):
        if collection.name in geometry:return geometry[collection.name]
        meshes=[o for o in collection.objects if o.type=='MESH']
        helpers={p.custom_shape for obj in collection.objects if obj.type=='ARMATURE' for p in obj.pose.bones if p.custom_shape}
        for helper in helpers:
            if helper in meshes:failures.append({'kind':'importer_display_helper_in_instance','prototype':collection.name,'helper':helper.name})
        bodies=[o for o in meshes if 'characterbase' in o.name.lower()]
        base_triangles=0
        for body in bodies:body.data.calc_loop_triangles();base_triangles+=len(body.data.loop_triangles)
        if base_triangles!=3134:failures.append({'kind':'full_base_geometry','prototype':collection.name,'base_triangles':base_triangles})
        total=0
        for obj in meshes:obj.data.calc_loop_triangles();total+=len(obj.data.loop_triangles)
        record={'bodyTriangles':base_triangles,'totalTriangles':total,'meshCount':len(meshes)}
        if 'seated-spectator' in collection.name:
            body=bodies[0];coords=[body.matrix_world@v.co for v in body.data.vertices]
            all_coords=[obj.matrix_world@v.co for obj in meshes for v in obj.data.vertices]
            record['widthMeters']=max(v.x for v in all_coords)-min(v.x for v in all_coords)
            record['heightMeters']=max(v.z for v in all_coords)-min(v.z for v in all_coords)
            butt=[v for v in coords if abs(v.x)<.20 and -.06<v.y<.17 and .20<v.z<.53]
            minimum=min(v.z for v in butt)
            contact=[v for v in butt if v.z<minimum+.001]
            record['butt']=sum(contact,Vector())/len(contact)
            shoe=next(o for o in meshes if 'romansandals' in o.name.lower())
            coords=[shoe.matrix_world@v.co for v in shoe.data.vertices]
            feet=[]
            for sign in [-1,1]:
                side=[v for v in coords if sign*v.x>0];minimum=min(v.z for v in side)
                bottom=[v for v in side if v.z<minimum+.002]
                feet.append(sum(bottom,Vector())/len(bottom))
            record['feet']=feet
        geometry[collection.name]=record;return record
    for item in items:
        obj=source_by_id.get(item['id'])
        if obj is None:failures.append({'kind':'missing_source_instance','id':item['id']});continue
        delta=(obj.location-Vector(item['sourcePosition'])).length
        rot=abs((obj.rotation_euler.z-item['rotationY']+math.pi)%math.tau-math.pi)
        scale=max(abs(v-item['scale']) for v in obj.scale)
        if delta>1e-4 or rot>1e-4 or scale>1e-5:failures.append({'kind':'transform_mismatch','id':item['id'],'positionDelta':delta,'rotationDelta':rot,'scaleDelta':scale})
        if not obj.get('runtime_skip'):failures.append({'kind':'double_export_risk','id':item['id']})
        if obj.instance_type!='COLLECTION' or obj.instance_collection is None:
            failures.append({'kind':'missing_full_character_collection','id':item['id']});continue
        geo=probes(obj.instance_collection)
        if item['role']=='seated-spectator':
            row=item['row'];sector=item['sector']
            tread=bpy.data.objects.get(f'CAVEA/Sector{sector:02}/Row{row:02}')
            bench=bpy.data.objects.get(f'CAVEA/Seat bench{row}_{sector}')
            if tread is None or bench is None:
                failures.append({'kind':'seat_surface_missing','id':item['id']});continue
            butt=obj.matrix_world@geo['butt'];seat_z=surface(bench,butt)
            foot_gaps=[]
            for p in geo['feet']:
                wp=obj.matrix_world@p;floor_z=surface(tread,wp)
                foot_gaps.append(None if floor_z is None else wp.z-floor_z)
            seat_gap=None if seat_z is None else butt.z-seat_z
            support.append({'id':item['id'],'buttSeatGap':seat_gap,'footTreadGaps':foot_gaps})
            if seat_gap is None or abs(seat_gap)>.04 or any(v is None or abs(v)>.025 for v in foot_gaps):
                failures.append({'kind':'seat_contact','id':item['id'],'buttSeatGap':seat_gap,'footTreadGaps':foot_gaps})
    # Inspect actual keyframes at a second source time, with the same manifest route.
    patrol_checks=[]
    starts={item['id']:source_by_id[item['id']].matrix_world.translation.copy() for item in manifest['npcs']}
    scene.frame_set(91)
    later={item['id']:source_by_id[item['id']].matrix_world.translation.copy() for item in manifest['npcs']}
    scene.frame_set(1)
    for item in manifest['npcs']:
        obj=source_by_id[item['id']]
        moving=bool(item.get('path'))
        rigs=[o for o in obj.instance_collection.objects if o.type=='ARMATURE']
        rig_keys=bool(rigs and rigs[0].animation_data and rigs[0].animation_data.action)
        has_keys=bool(obj.animation_data and obj.animation_data.action) if moving else rig_keys
        action=obj.animation_data.action if moving and has_keys else (rigs[0].animation_data.action if rig_keys else None)
        cyclic=bool(action) and all(any(m.type=='CYCLES' for m in c.modifiers) for c in curves(action))
        start=starts[item['id']];movement=(later[item['id']]-start).length
        expected_travel=item['speed']*90/(scene.render.fps/scene.render.fps_base) if moving else 0
        expected_point=Vector(item['sourcePosition'])
        if moving:
            points=[Vector((p[0],-p[2],p[1])) for p in item['path']]
            segments=[(b-a).length for a,b in zip(points,points[1:])];remaining=expected_travel%sum(segments)
            for j,distance in enumerate(segments):
                if remaining<=distance:
                    expected_point=points[j].lerp(points[j+1],remaining/distance if distance else 0);break
                remaining-=distance
        expected=(expected_point-start).length
        patrol_checks.append({'id':item['id'],'keyframes':has_keys,'cyclic':cyclic,'clip':item['clip'],'moving':moving,
            'movementOver90Frames':movement,'expectedTravelDistance':expected_travel,'expectedDisplacement':expected})
        if not has_keys or not cyclic or abs(movement-expected)>.05:failures.append({'kind':'patrol_motion','id':item['id'],'movement':movement,'expected':expected})
    patrol_pose_samples=[]
    if manifest['npcs']:
        first=source_by_id[manifest['npcs'][0]['id']]
        for frame in [1,7,13,19,25]:
            scene.frame_set(frame);deps=bpy.context.evaluated_depsgraph_get();points=[]
            for mesh in first.instance_collection.objects:
                if mesh.type!='MESH':continue
                ev=mesh.evaluated_get(deps)
                points.extend(first.matrix_world@(ev.matrix_world@v.co) for v in ev.data.vertices)
            bottom=min(v.z for v in points);top=max(v.z for v in points)
            relative=bottom-first.matrix_world.translation.z
            sample={'frame':frame,'height':top-bottom,'lowestPointRelativePlaza':relative,'normalizationApplied':bool(first.instance_collection.get('human_scale_normalized'))}
            patrol_pose_samples.append(sample)
            if not(1.65<sample['height']<1.95) or abs(relative)>.05:
                failures.append({'kind':'patrol_character_scale_or_ground','sample':sample})
        scene.frame_set(1)
    market=json.loads((ROOT/'market_registry.json').read_text())
    spawn={s['id']:s for s in market.get('vendor_spawns',[])}
    for item in manifest['instances']:
        if item['zone']=='market_vendor':
            expected=spawn[item['stallId']]['position'];gap=(Vector(item['sourcePosition'])-Vector(expected)).length
            if gap>1e-4:failures.append({'kind':'merchant_slot','id':item['id'],'gap':gap})
    contact_numbers=[x['buttSeatGap'] for x in support if x['buttSeatGap'] is not None]
    foot_numbers=[g for x in support for g in x['footTreadGaps'] if g is not None]
    rows=defaultdict(list)
    for item in manifest['instances']:
        if item['role']=='seated-spectator':rows[item['row']].append(Vector(item['sourcePosition']))
    neighbor_distances=[]
    for row in rows.values():
        row.sort(key=lambda p:math.atan2(p.y,p.x))
        neighbor_distances.extend((p-row[(i+1)%len(row)]).length for i,p in enumerate(row))
    minimum_neighbor=min(neighbor_distances) if neighbor_distances else None
    maximum_width=max((g.get('widthMeters',0) for g in geometry.values()),default=0)
    if minimum_neighbor is not None and minimum_neighbor<maximum_width:
        failures.append({'kind':'crowd_neighbor_overlap','minimumCenterDistance':minimum_neighbor,'posedWidth':maximum_width})
    source_triangle_instances=sum(probes(obj.instance_collection)['totalTriangles'] for obj in source_by_id.values())
    runtime_inventory=json.loads((ROOT/'characters/runtime-validation.json').read_text())
    triangles_by_role={Path(r['asset']).stem:r['triangles'] for r in runtime_inventory['reimports']}
    runtime_triangle_instances=sum(triangles_by_role[i.get('sourcePrototype',i['role'])] for i in items)
    if source_triangle_instances!=runtime_triangle_instances:
        failures.append({'kind':'source_runtime_triangle_mismatch','source':source_triangle_instances,'runtime':runtime_triangle_instances})
    out=ROOT/'characters/population-qc';out.mkdir(exist_ok=True)
    images=[]
    if not a.no_render:
        camera_data=bpy.data.cameras.new('Population QC camera');camera=bpy.data.objects.new('Population QC camera',camera_data);scene.collection.objects.link(camera);scene.camera=camera
        scene.render.resolution_x=1024;scene.render.resolution_y=768;scene.render.resolution_percentage=100
        scene.cycles.samples=a.samples;scene.cycles.use_denoising=True
        def render(name,position,target,lens=45):
            camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera_data.lens=lens
            scene.render.filepath=str(out/(name+'.png'));bpy.ops.render.render(write_still=True);images.append(scene.render.filepath)
        seated=next(i for i in items if i.get('row')==4 and i.get('sector')==10)
        p=Vector(seated['sourcePosition']);toward=Vector((-p.x,-p.y,0)).normalized();side=Vector((-toward.y,toward.x,0))
        render('stands',p+toward*5+side*2+Vector((0,0,2.5)),p+Vector((0,0,.75)),48)
        merchant=next(i for i in items if i['zone']=='market_vendor');p=Vector(merchant['sourcePosition']);angle=merchant['rotationY'];forward=Vector((math.sin(angle),-math.cos(angle),0))
        render('merchant',p+forward*5+Vector((0,0,1.8)),p+Vector((0,0,.9)),40)
        guard=next(i for i in items if i['id']=='guard_gate3_0_1');p=Vector(guard['sourcePosition']);forward=Vector((p.x,p.y,0)).normalized()
        render('guard',p+forward*5+Vector((2,0,1.8)),p+Vector((0,0,1.0)),38)
        render('statue',(21,-104,10),(13,-90,7.5),48)
    unchanged=sha(source)==source_hash
    report={'passed':not failures,'source':str(source),'sourceSHA256':source_hash,'sourceUnchanged':unchanged,
      'populationSourceInstances':len(source_by_id),'populationManifestInstances':len(items),'sourceRuntimeTransformsIdentical':not any(f['kind']=='transform_mismatch' for f in failures),
      'spectatorsContactTested':len(support),'seatContact':{'minimumGap':min(contact_numbers) if contact_numbers else None,'maximumGap':max(contact_numbers) if contact_numbers else None,'meanGap':statistics.mean(contact_numbers) if contact_numbers else None},
      'footTreadContact':{'minimumGap':min(foot_numbers) if foot_numbers else None,'maximumGap':max(foot_numbers) if foot_numbers else None},
      'crowdSpacing':{'minimumAdjacentCenterDistance':minimum_neighbor,'maximumSeatedCharacterWidth':maximum_width,'clearanceMinimum':minimum_neighbor-maximum_width if minimum_neighbor is not None else None},
      'triangleInstances':{'source':source_triangle_instances,'runtimeAuthoredAssets':runtime_triangle_instances,'identical':source_triangle_instances==runtime_triangle_instances},
      'sharedGeometry':{k:{a:b for a,b in v.items() if a not in ['butt','feet']} for k,v in geometry.items()},
      'patrols':patrol_checks,'failureCount':len(failures),'failures':failures[:100],'images':images,
      'actualSourcePatrolPoseSamples':patrol_pose_samples,
      'contactToleranceMeters':{'foot':.025,'seatedBody':.04},'supportChecksUseActualSourceMeshRaycasts':True}
    (ROOT/'characters/population-source-qc.json').write_text(json.dumps(report,indent=2))
    assert unchanged,'Read-only source verification unexpectedly changed source file bytes'
    print('POPULATION_SOURCE_QC',json.dumps(report),flush=True)
    if failures:raise RuntimeError(f'Population QC found {len(failures)} issue(s); inspect report before acceptance')
if __name__=='__main__':main()
