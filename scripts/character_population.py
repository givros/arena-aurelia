"""Stage 11 population: exact CharacterBase assets, shared source collections, identical runtime placements.

Import this module and call build_population(api, spec) only after the architecture
and district reference checkpoints have been accepted. Importing has no side effects.
"""
from pathlib import Path
import json, math, random, hashlib
from collections import Counter

TAU=math.tau
PALETTE=['#C8B88D','#9F4939','#B28B56','#798477','#9A8A73','#BAAB91','#6D3158','#C39B79']
ROLES=['citizen','merchant','worker','noble','seated-spectator','guard','gladiator']

def _runtime(p):
    return [round(p[0],5),round(p[2],5),round(-p[1],5)]

def _facing(x,y,target=(0,0)):
    return math.atan2(target[1]-y,target[0]-x)+math.pi/2

def plan_population(root,spec,market_registry=None):
    """Pure deterministic placement plan; does not access or mutate Blender."""
    root=Path(root);rng=random.Random(int(spec.get('seed',71664))+1103)
    instances=[];npcs=[];candidates=[]
    spectator_count=int(spec.get('spectator_count',12000))
    spectator_spacing=float(spec.get('spectator_spacing',.72))
    def entry(ident,role,p,rotation,zone,color=0,scale=1.0,**extra):
        return dict(id=ident,role=role,position=_runtime(p),rotationY=round(rotation,7),scale=scale,
                    colorIndex=color,zone=zone,sourcePosition=[round(v,5) for v in p],**extra)
    # One true seated character per slot. Layered occupancy reserves every aisle
    # and the imperial axis while producing distinct dense upper / calmer lower tiers.
    for row in range(24):
        radius=73.3+row*.86+(1.8 if row>=8 else 0)+(1.8 if row>=16 else 0)
        rx=radius+.68;ry=radius-23+.68;z=(5.15+row*.74)*1.3-.01
        tier='lower' if row<8 else ('middle' if row<16 else 'upper')
        for sector in range(16):
            a0=TAU*sector/16+.032;a1=TAU*(sector+1)/16-.032
            mid=(a0+a1)/2
            length=(a1-a0)*math.hypot(rx*math.sin(mid),ry*math.cos(mid))
            slots=max(1,int(length/spectator_spacing))
            for slot in range(slots):
                a=a0+(a1-a0)*(slot+.5)/slots
                x=rx*math.cos(a);y=ry*math.sin(a)
                if abs(x)<12.8 and 48<y<73.5:continue
                # Weighted sampling is stable and adds family-sized occupied zones
                # without a repeated checkerboard pattern in the reference view.
                weight=(.82 if row<8 else (1.03 if row<16 else 1.20))*(1+.12*math.cos(sector*.85))
                key=rng.random()**(1/weight)
                color=rng.choices(range(8),weights=[27,12,13,12,12,14,3,7])[0]
                if row<5 and rng.random()<.09:color=6
                candidates.append((key,entry(f'crowd_r{row:02}_s{sector:02}_{slot:02}','seated-spectator',(x,y,z),_facing(x,y),'seating_'+tier,color,row=row,sector=sector,slot=slot)))
    if len(candidates)<spectator_count:raise RuntimeError(f'Only {len(candidates)} collision-safe spectator slots; requested {spectator_count}')
    candidates.sort(key=lambda pair:pair[0],reverse=True)
    instances.extend(e for _,e in candidates[:spectator_count])

    registry_path=root/'market_registry.json'
    if market_registry is None:
        if not registry_path.exists():raise FileNotFoundError('Stage 8 market_registry.json is required before population')
        market=json.loads(registry_path.read_text())
    else:market=market_registry
    stalls=market.get('stalls',market.get('vendors',[])) if isinstance(market,dict) else market
    vendor_lookup={v.get('id'):v for v in market.get('vendor_spawns',[])} if isinstance(market,dict) else {}
    merchant_positions=[]
    for i,stall in enumerate(stalls):
        center=stall.get('position',stall.get('center',stall.get('location')))
        recorded_vendor=vendor_lookup.get(stall.get('id'),{})
        vendor=recorded_vendor.get('position',stall.get('vendor_position',stall.get('vendorPosition',stall.get('vendor'))))
        if isinstance(vendor,dict):vendor=vendor.get('position')
        angle=recorded_vendor.get('facing',stall.get('rotation',stall.get('rotation_z',stall.get('rotationZ',0))))
        if isinstance(angle,(list,tuple)):angle=angle[-1]
        if vendor is None:
            if center is None:continue
            # Vendor remains behind the table, inside the stall footprint.
            vendor=[center[0]-math.sin(angle)*.5,center[1]+math.cos(angle)*.5,center[2] if len(center)>2 else 0]
        vendor=list(vendor)+[0]*(3-len(vendor))
        merchant_positions.append(vendor)
        instances.append(entry(f'merchant_{i:03}','merchant',vendor,float(angle),'market_vendor',(2+i%3)%8,stallId=stall.get('id',str(i))))

    # Two hundred citizens gather in small conversational groups along the clear
    # perimeter route, with the central ceremonial axis left unobstructed.
    accepted=[];attempts=0
    while len(accepted)<200 and attempts<30000:
        attempts+=1;angle=rng.uniform(0,TAU)
        rx=111.8+rng.uniform(0,4.6);ry=rx-23
        x=rx*math.cos(angle);y=ry*math.sin(angle)
        if abs(x)<4.6 and y<-79:continue
        if any((x-p[0])**2+(y-p[1])**2<1.8**2 for p in merchant_positions):continue
        if any((x-p[0])**2+(y-p[1])**2<.90**2 for p in accepted):continue
        accepted.append((x,y,0))
        instances.append(entry(f'plaza_citizen_{len(accepted):03}','citizen',(x,y,.015),rng.uniform(-math.pi,math.pi),'plaza_crowd',rng.randrange(8)))
    if len(accepted)!=200:raise RuntimeError('Unable to place the requested plaza gathering without overlaps')

    # Gate guards stand beside the main access axes, never in an entrance center.
    for axis in range(4):
        a=axis*math.pi/2
        for rank in range(3):
            for side in [-1,1]:
                da=side*(.040+rank*.010);rx=109.2+rank*1.05;ry=rx-23
                x=rx*math.cos(a+da);y=ry*math.sin(a+da)
                instances.append(entry(f'guard_gate{axis}_{rank}_{side}','guard',(x,y,.02),_facing(x,y,(x+math.cos(a)*10,y+math.sin(a)*10)),'gate_guard',1))

    fighter_positions=[(-18,-13,.4),(-13,-12,.4),(-16,-18,.4),(24,14,.4),(29,12,.4),(27,18,.4),
                       (5,26,-5.6),(10,26,-5.6),(18,26,-5.6),(23,26,-5.6),(31,26,-5.6),(36,26,-5.6)]
    for i,p in enumerate(fighter_positions):
        target=fighter_positions[(i//3)*3+(i+1)%3]
        instances.append(entry(f'gladiator_{i:02}','gladiator',p,_facing(p[0],p[1],target[:2]),'arena_training' if i<6 else 'gladiator_preparation',1))
    # Workers are close to supply bays and equipment; the cross-vault centerline
    # and all portal centerlines remain empty.
    worker_positions=[(-34,-27,-5.6),(-29,-27,-5.6),(-21,-27,-5.6),(-16,-27,-5.6),(-8,-26,-5.6),(-3,-26,-5.6),
      (6,-27,-5.6),(11,-27,-5.6),(19,-27,-5.6),(24,-27,-5.6),(32,-26,-5.6),(37,-26,-5.6),
      (-27,12,-5.6),(-23,12,-5.6),(23,12,-5.6),(27,12,-5.6)]
    for i,p in enumerate(worker_positions):instances.append(entry(f'worker_{i:02}','worker',p,rng.uniform(-math.pi,math.pi),'hypogeum_work',3 if i%2 else 4))
    for i,(x,y) in enumerate([(-5,55.2),(-2,55.4),(2,55.4),(5,55.2),(-5,59),(-2,61),(2,61),(5,59)]):
        instances.append(entry(f'noble_vip_{i:02}','noble',(x,y,18.72),_facing(x,y),'imperial_loggia',6 if i%3 else 0))

    # Façade sculpture uses the very same validated full character geometry, with
    # a stone material override. No visible human-shaped proxy meshes are used.
    for bay in range(64):
        if bay%8 not in [1,3,5]:continue
        a=TAU*bay/64;x=104.5*math.cos(a);y=81.5*math.sin(a)
        instances.append(entry(f'statue_arcade_{bay:02}','gladiator',(x,y,15.21+.55),_facing(x,y,(x*2,y*2)),'facade_statue',0,3/1.8652865887,materialOverride='stone',pedestal=True,bay=bay))
    for side in [-1,1]:
        instances.append(entry(f'statue_hero_{side}','gladiator',(side*13,-90,5.348205),0,'ceremonial_statue',0,4.0/1.8652865887,materialOverride='stone'))

    # The source shows the actual bundled Walk pose. Runtime follows the same
    # plaza ring on foot using that clip; no route crosses arena walls or stalls.
    for i in range(8):
        start=TAU*i/8
        points=[(113.4*math.cos(start+TAU*j/32),90.4*math.sin(start+TAU*j/32),.015) for j in range(33)]
        item=entry(f'patrol_{i:02}','citizen',points[0],_facing(points[0][0],points[0][1],points[1][:2]),'plaza_patrol',0)
        item.update(asset='characters/animated-citizen.glb',clip='Walk',path=[_runtime(p) for p in points],speed=.85+(i%3)*.12,loop=True,sourcePrototype='animated-citizen',animationPhase=0,patrolPathPhase=i/8)
        npcs.append(item)
    instances.sort(key=lambda e:e['id'])
    counts=Counter(e['zone'] for e in instances)
    return {'version':1,'coordinate_system':'three_y_up','source_coordinate_system':'Blender Z up; runtime x,z,-y',
       'prototypes':{r:'characters/'+r+'.glb' for r in ROLES},'palette':PALETTE,
       'materialOverrides':{'stone':{'colorLinear':[.76,.66,.48],'roughness':.8,'metalness':0}},
       'instances':instances,'npcs':npcs,'counts':dict(counts),'spectators':spectator_count,
       'spectatorSpacingMeters':spectator_spacing,'availableSpectatorSlots':len(candidates),
       'character_source':'Exact bundled blender-lowpoly-character CharacterBase; complete original body retained in every role',
       'crowd_strategy':'Full character geometry shared across instances; explicit rows, aisle gaps and imperial axis exclusions; no billboard or simplified body proxies',
       'placement_contract':{'seated_pelvis_radius_offset':.68,'bench_radius_offset':.64,'bench_top_above_tread':.43,'seated_butt_above_origin':.43974,'seating_height_scale':1.3,'feet_z_relative_tread':-.01,'spectator_spacing':spectator_spacing,'seated_pose':'Compact arms held alongside the torso; forearms toward lap'},
       'source_runtime_relationship':'Runtime instances replace source collection instances exactly; source objects carry runtime_skip=true.'}

def build_population(api,spec):
    """Create stage-11 source population and write the identical runtime manifest."""
    import bpy
    from mathutils import Matrix
    root=Path(api.ROOT);runtime=root/'characters'/'runtime'
    if bpy.data.collections.get('Population'):
        raise RuntimeError('Population already exists; refusing duplicate humans. Remove the managed Population collection explicitly before regeneration.')
    manifest=plan_population(root,spec)
    source_report=json.loads((root/'characters'/'acceptance.json').read_text())
    if not source_report['passed']:raise RuntimeError('Canonical character acceptance has not passed')
    population=bpy.data.collections.new('Population');bpy.context.scene.collection.children.link(population)
    libraries={};prototypes={};cloth_materials={};asset_hashes={}
    stone=api.M['light']
    def action_curves(action):
        if hasattr(action,'fcurves'):yield from action.fcurves
        else:
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:yield from bag.fcurves
    def cyclic_action(action,linear=False):
        for curve in action_curves(action):
            if not any(m.type=='CYCLES' for m in curve.modifiers):curve.modifiers.new('CYCLES')
            if linear:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
    def cloth(index):
        if index in cloth_materials:return cloth_materials[index]
        hx=PALETTE[index];rgb=[int(hx[k:k+2],16)/255 for k in [1,3,5]]
        linear=[v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
        mat=api.material('Population cloth '+str(index),linear,.88)
        cloth_materials[index]=mat;return mat
    def load_asset(role):
        if role in libraries:return libraries[role]
        path=runtime/(role+'.glb')
        asset_hashes[role]=hashlib.sha256(path.read_bytes()).hexdigest()
        existing=set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        imported=list(set(bpy.data.objects)-existing)
        # Blender creates bone display Icospheres that are not glTF asset nodes.
        # Keep those editor helpers out of instanced and rendered character geometry.
        display_helpers={p.custom_shape for obj in imported if obj.type=='ARMATURE' for p in obj.pose.bones if p.custom_shape}
        for obj in imported:
            if obj.type=='ARMATURE':
                for p in obj.pose.bones:
                    if p.custom_shape in display_helpers:p.custom_shape=None
        for helper in display_helpers:
            if helper in imported:
                imported.remove(helper);bpy.data.objects.remove(helper,do_unlink=True)
        matrices={obj:obj.matrix_world.copy() for obj in imported}
        collection=bpy.data.collections.new('CharacterLibrary/'+role)
        # Unlinked source collections are visible only through explicit instances.
        for obj in imported:
            if role!='animated-citizen':
                obj.parent=None;obj.matrix_world=matrices[obj]
            for previous in list(obj.users_collection):previous.objects.unlink(obj)
            collection.objects.link(obj)
            obj['source_role']=role;obj['runtime_skip']=True;obj['collision']='none'
            obj['canonical_character_sha256']=source_report['canonical_sha256']
        if role=='animated-citizen':
            for obj in imported:
                if obj.type=='ARMATURE':
                    actions=[a for a in bpy.data.actions if 'walk' in a.name.lower()]
                    if actions:
                        obj.animation_data_create();obj.animation_data.action=actions[0]
                        if hasattr(actions[0],'slots') and len(actions[0].slots):
                            obj.animation_data.action_slot=actions[0].slots[0]
                        cyclic_action(actions[0])
        libraries[role]=collection
        return collection
    def prototype(role,color_index=0,stone_override=False):
        key=(role,color_index,stone_override)
        if key in prototypes:return prototypes[key]
        library=load_asset(role)
        if role=='animated-citizen':
            prototypes[key]=library;return library
        collection=bpy.data.collections.new(f'CharacterVariants/{role}/{"stone" if stone_override else color_index}')
        for original in library.objects:
            obj=original.copy();obj.data=original.data
            collection.objects.link(obj)
            if obj.type=='MESH':
                for slot in obj.material_slots:
                    name=slot.material.name if slot.material else ''
                    if stone_override or 'cloth' in name.lower() or 'romantunic' in name.lower():
                        slot.link='OBJECT';slot.material=stone if stone_override else cloth(color_index)
            obj['runtime_skip']=True;obj['collision']='none'
        prototypes[key]=collection
        return collection
    source_counts=Counter();triangle_count=0
    def instantiate(item,is_npc=False):
        nonlocal triangle_count
        role='animated-citizen' if is_npc else item['role'];is_stone=item.get('materialOverride')=='stone'
        collection=prototype(role,item.get('colorIndex',0),is_stone)
        obj=bpy.data.objects.new('NPC/'+item['id'] if is_npc else 'CROWD/'+item['id'],None)
        population.objects.link(obj);obj.instance_type='COLLECTION';obj.instance_collection=collection
        obj.location=item['sourcePosition'];obj.rotation_euler.z=item['rotationY'];obj.scale=(item['scale'],)*3
        obj.empty_display_type='PLAIN_AXES';obj.empty_display_size=.15
        obj['runtime_skip']=True;obj['collision']='none';obj['semantic']=item['zone'];obj['role']=item['role'];obj['runtime_id']=item['id']
        obj['canonical_character_sha256']=source_report['canonical_sha256'];obj['source_asset_sha256']=asset_hashes[role]
        if is_npc:
            obj['clip']='Walk';obj['patrol_route']=json.dumps(item['path']);obj['speed']=item['speed']
            fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
            points=[(p[0],-p[2],p[1]) for p in item['path']]
            frame=1.0;previous_angle=None
            for i,p in enumerate(points):
                next_point=points[(i+1)%(len(points)-1)]
                angle=_facing(p[0],p[1],next_point[:2])
                if previous_angle is not None:
                    while angle-previous_angle>math.pi:angle-=TAU
                    while angle-previous_angle<-math.pi:angle+=TAU
                previous_angle=angle
                obj.location=p;obj.rotation_euler.z=angle
                obj.keyframe_insert(data_path='location',frame=frame)
                obj.keyframe_insert(data_path='rotation_euler',index=2,frame=frame)
                if i<len(points)-1:
                    frame+=math.dist(p,points[i+1])/item['speed']*fps
            cyclic_action(obj.animation_data.action,linear=True)
            obj['patrol_loop_frames']=frame-1
            obj['patrol_path_phase']=item.get('patrolPathPhase',0)
            bpy.context.scene.frame_end=max(bpy.context.scene.frame_end,math.ceil(frame))
        for mesh in collection.objects:
            if mesh.type=='MESH':
                mesh.data.calc_loop_triangles();triangle_count+=len(mesh.data.loop_triangles)
        source_counts[item['zone']]+=1
        if item.get('pedestal'):
            x,y,z=item['sourcePosition']
            pedestal_name='STATUARY/Pedestal_'+item['id']
            if bpy.data.objects.get(pedestal_name) is None:
                api.box(pedestal_name,(x,y,z-.275),(1.7,1.4,.55),'light',rot=item['rotationY'],collection='FacadeStatues',collision='none')
        return obj
    for item in manifest['instances']:instantiate(item)
    for item in manifest['npcs']:instantiate(item,True)
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    manifest['assetHashes']=asset_hashes
    manifest['materialOverrides']['stone']['colorLinear']=list(stone.diffuse_color[:3])
    manifest['canonicalCharacterSHA256']=source_report['canonical_sha256']
    manifest['sourcePopulation']={'instanceCount':len(manifest['instances'])+len(manifest['npcs']),
      'sharedVariantCollections':len(prototypes),'importedAssetCollections':len(libraries),
      'evaluatedTriangleInstances':triangle_count,'sourceCollection':'Population','allCharactersFullBase':True,
      'sourcePatrolTransformKeyframes':True,'sourceWalkClipCyclic':True,
      'sourceInstancesExcludedFromEnvironmentTransfer':True,'runtimeManifestRequired':True}
    target=runtime/'crowd_manifest.json';target.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    result={'passed':True,'manifest':str(target),'counts':dict(source_counts),'sourcePopulation':manifest['sourcePopulation'],
      'source_runtime_positions_identical':True,'canonicalCharacterSHA256':source_report['canonical_sha256'],
      'assetHashes':asset_hashes,'placement_contract':manifest['placement_contract']}
    (root/'characters'/'population-validation.json').write_text(json.dumps(result,indent=2))
    bpy.context.scene['population_manifest']='characters/crowd_manifest.json'
    bpy.context.scene['population_instances']=manifest['sourcePopulation']['instanceCount']
    bpy.context.scene['population_triangle_instances']=triangle_count
    print('ROMAN_POPULATION_BUILT',json.dumps(result),flush=True)
    return result
