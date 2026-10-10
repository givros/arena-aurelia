"""Add whole-district life to the open scene; only the parent saves Blender.

Every current population object, shared character mesh, placement and animation
is retained. New people reuse the complete validated canonical role assets.
"""
from pathlib import Path
from collections import Counter,defaultdict
import copy,json,math,hashlib
from street_life_population import GeometrySupport as SourceGeometrySupport,sha,runtime,facing,phase_route,close,curves,cycle,distance_segment,segment_distance,PALETTE

ROOT=Path(__file__).resolve().parents[1]

class GeometrySupport(SourceGeometrySupport):
    """Same source triangle tests, with a broad phase for city-sized route audits."""
    def __init__(self):
        super().__init__();self.spatial=defaultdict(list);self.large=[];self.cell_size=8.
        for i,(_,lo,hi) in enumerate(self.records):
            x0,x1=[math.floor(x/self.cell_size) for x in [lo[0],hi[0]]]
            y0,y1=[math.floor(y/self.cell_size) for y in [lo[1],hi[1]]]
            if (x1-x0+1)*(y1-y0+1)>256:self.large.append(i);continue
            for x in range(x0,x1+1):
                for y in range(y0,y1+1):self.spatial[(x,y)].append(i)
    def near(self,p,radius=.002):
        indices=set(self.large)
        for x in range(math.floor((p[0]-radius)/self.cell_size),math.floor((p[0]+radius)/self.cell_size)+1):
            for y in range(math.floor((p[1]-radius)/self.cell_size),math.floor((p[1]+radius)/self.cell_size)+1):indices.update(self.spatial.get((x,y),[]))
        return (self.records[i] for i in sorted(indices))
    def ground(self,p):
        hits=[];V=self.Vector
        for o,lo,hi in self.near(p):
            if not(lo[0]-.001<=p[0]<=hi[0]+.001 and lo[1]-.001<=p[1]<=hi[1]+.001 and lo[2]<=p[2]+.35 and hi[2]>=p[2]-.45):continue
            hit,normal,_,_=self.bvh(o).ray_cast(V((p[0],p[1],p[2]+.35)),V((0,0,-1)),.8)
            if hit is not None and normal.z>.55:hits.append((abs(hit.z-p[2]),hit.z,o.name))
        return max(hits,key=lambda h:h[1]) if hits else None
    def blocked(self,p,radius=.35):
        V=self.Vector
        for o,lo,hi in self.near(p,radius):
            if o.get('collision')!='solid' or hi[2]<p[2]+.3 or lo[2]>p[2]+1.7:continue
            if p[0]+radius<lo[0] or p[0]-radius>hi[0] or p[1]+radius<lo[1] or p[1]-radius>hi[1]:continue
            for z in [.45,1.05,1.6]:
                for axis in [(1,0,0),(0,1,0),(.707,.707,0),(.707,-.707,0)]:
                    direction=V(axis);origin=V((p[0],p[1],p[2]+z))-direction*radius
                    hit,_,_,_=self.bvh(o).ray_cast(origin,direction,radius*2)
                    if hit is not None:return o.name
        return None

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def source(points):return [[p[0],-p[2],p[1]] for p in points]
def role_of(entry):return entry.get('sourcePrototype',entry['role'])

def region_coverage(static,npcs):
    """Count authored living uses separately from static representation."""
    result={}
    for e in static+npcs:
        row=result.setdefault(e['zone'],{'static':0,'walking':0,'fixedIdle':0,'seated':0,'activities':Counter()})
        row['walking' if e.get('path') else ('fixedIdle' if e.get('animated') else 'static')]+=1
        row['seated']+=int(e['role']=='seated-citizen');row['activities'][e.get('activity','resident')]+=1
    return {zone:{**value,'activities':dict(value['activities'])} for zone,value in sorted(result.items())}

def read_layouts(root):
    paths=[root/'district_life_layout.json',root/'arena_interior_life_layout.json',root/'master_spine_life_layout.json',root/'civic_court_layout.json']
    return [(p,json.loads(p.read_text())) for p in paths if p.exists()]

def entry(anchor,role=None):
    p=list(anchor['position']);role=role or anchor.get('role','citizen')
    default_color={'guard':1,'gladiator':1,'worker':3,'merchant':2,'noble':6}.get(role,sum(map(ord,anchor['id'])))
    result={'id':'district_'+anchor['id'],'role':role,'position':runtime(p),'sourcePosition':p,
        'rotationY':float(anchor.get('facing',0)),'scale':1.0,'colorIndex':int(anchor.get('colorIndex',default_color))%8,
        'zone':'district_'+anchor.get('zone','city'),'districtLife':True,'activity':anchor.get('activity','conversation')}
    for key in ['groupId','stallId','purpose','seatTop','feetZ','benchId','seatObject','interior','masterSpine','houseId','quarter']:
        if key in anchor:result[key]=anchor[key]
    if role=='seated-citizen':result['sourcePrototype']='seated-spectator'
    return result

def planned_additions(layouts):
    static=[];npcs=[];route_specs=[];seen=set()
    for path,layout in layouts:
        anchors=list(layout.get('vendors',[]))+list(layout.get('anchors',[]))+list(layout.get('seatedAnchors',[]))
        for anchor in anchors:
            if anchor['id'] in seen:continue
            seen.add(anchor['id']);static.append(entry(anchor,'merchant' if anchor in layout.get('vendors',[]) else None))
        routes=layout.get('routes',[])
        target=int(layout.get('animatedActorCount',48 if path.name=='district_life_layout.json' else len(routes)))
        explicit=any('actors' in r for r in routes)
        occupancy=[int(r.get('actors',1)) if explicit else target//max(1,len(routes))+(i<target%max(1,len(routes))) for i,r in enumerate(routes)]
        for route,count in zip(routes,occupancy):
            if not count:continue
            route_specs.append(route)
            for index in range(count):
                serial=len(npcs);roles=route.get('roles',['citizen','merchant','citizen','worker'])
                role=roles[serial%len(roles)];role={'porter':'worker','hawker':'merchant'}.get(role,role)
                prototype={'merchant':'animated-merchant','worker':'animated-porter'}.get(role,'animated-citizen')
                points=phase_route(route['points'],index/count)
                e=entry({'id':route['id']+'_'+str(index),'position':points[0],'facing':facing(points[0],points[1]),
                    'zone':route.get('zone','city'),'activity':{'merchant':'hawker','worker':'porter'}.get(role,'walking'),
                    'role':role,'colorIndex':{'merchant':2,'worker':3}.get(role,serial*3),'purpose':route.get('purpose','District circulation')})
                e.update(animated=True,asset='characters/'+prototype+'.glb',sourcePrototype=prototype,clip='Walk',path=[runtime(p) for p in points],
                    routeId=route['id'],speed=float(route.get('speed',.85)),loop=True,animationPhase=round((serial*.137)%1.01,5),
                    patrolPathPhase=index/count,personalSpace=.62,sourceCollection='DistrictLifeAnimated/'+e['id'])
                if route.get('masterSpine'):e['masterSpine']=route['masterSpine']
                npcs.append(e)
        animated_anchors=list(layout.get('animatedAnchors',[]))
        if path.name=='district_life_layout.json' and not animated_anchors:
            vendor_zones={}
            for anchor in layout.get('vendors',[]):vendor_zones.setdefault(anchor.get('zone','city'),anchor)
            for anchor in vendor_zones.values():
                selected=copy.deepcopy(anchor);selected['role']='merchant';selected['activity']='active_vendor'
                static=[e for e in static if e['id']!='district_'+anchor['id']]
                selected['id']+='_idle';animated_anchors.append(selected)
        for index,anchor in enumerate(animated_anchors):
            e=entry(anchor);e.update(animated=True,asset='characters/animated-citizen.glb',sourcePrototype='animated-citizen',
                clip='Idle',speed=0,loop=True,animationPhase=round(index*.373,5),personalSpace=.55,sourceCollection='DistrictLifeAnimated/'+e['id'])
            npcs.append(e)
    for e in static:
        if e['role'] in ['citizen','merchant','worker'] and e['zone']!='district_arena_upper_gallery':
            e['originalRole']=e['role'];e['role']='citizen-idle-'+str(sum(map(ord,e['id']))%4)
            e['sourcePrototype']=e['role'];e['pose']='Idle-derived relaxed or conversational pose'
    assert len({e['id'] for e in static+npcs})==len(static+npcs),'Duplicate district actor IDs'
    return static,npcs,route_specs

class Reservations:
    def __init__(self,entries):
        self.cells=defaultdict(list)
        for e in entries:self.add(e['sourcePosition'],e['id'])
    def add(self,p,ident):self.cells[(math.floor(p[0]),math.floor(p[1]))].append((p,ident))
    def conflict(self,p,distance=.88):
        x,y=math.floor(p[0]),math.floor(p[1]);radius=math.ceil(distance)
        for a in range(x-radius,x+radius+1):
            for b in range(y-radius,y+radius+1):
                for q,ident in self.cells.get((a,b),[]):
                    if abs(p[2]-q[2])<1.6 and math.hypot(p[0]-q[0],p[1]-q[1])<distance:return ident
        return None

class WalkingReservations:
    def __init__(self,paths):
        self.segments=[];self.cells=defaultdict(list);self.cell_size=4.
        for path in paths:
            for a,b in zip(path,path[1:]):
                i=len(self.segments);self.segments.append((a,b))
                for x in range(math.floor(min(a[0],b[0])/4),math.floor(max(a[0],b[0])/4)+1):
                    for y in range(math.floor(min(a[1],b[1])/4),math.floor(max(a[1],b[1])/4)+1):self.cells[(x,y)].append(i)
    def within(self,p,distance):
        indices=set()
        for x in range(math.floor((p[0]-distance)/4),math.floor((p[0]+distance)/4)+1):
            for y in range(math.floor((p[1]-distance)/4),math.floor((p[1]+distance)/4)+1):indices.update(self.cells.get((x,y),[]))
        return any(abs(p[2]-(a[2]+b[2])/2)<1.6 and distance_segment(p,a,b)<distance for a,b in (self.segments[i] for i in indices))

def apply_population(root=ROOT,validate_only=False,layout_paths=None):
    import bpy
    from mathutils import Vector
    root=Path(root);target=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(target.read_text())
    layouts=read_layouts(root) if layout_paths is None else [(Path(p),json.loads(Path(p).read_text())) for p in layout_paths]
    if not layouts or (not validate_only and layouts[0][0].name!='district_life_layout.json'):raise RuntimeError('City district layout must be published before population')
    static,npcs,routes=planned_additions(layouts)
    population=bpy.data.collections['Population'];bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    old_entries=copy.deepcopy(manifest['instances']+manifest['npcs']);old_ids={e['id'] for e in old_entries}
    if any(e['id'] in old_ids for e in static+npcs):raise RuntimeError('District IDs already exist; additive integration cannot replace them')
    signatures={o.name:(tuple(tuple(r) for r in o.matrix_world),o.instance_collection) for o in population.objects}
    canonical_hash=sha(root/'characters/CharacterBase.blend');asset_hashes={p.stem:sha(p) for p in (root/'characters/runtime').glob('*.glb')}
    validation=json.loads((root/'characters/runtime-validation.json').read_text());triangles={Path(r['asset']).stem:r['triangles'] for r in validation['reimports']}
    support=GeometrySupport();rejected=[];contacts=[];route_checks=[];feet_cache={}
    def retained(role):
        def full(c):return any(o.type=='MESH' and 'characterbase' in o.name.lower() for o in c.objects)
        exact=bpy.data.collections.get('CharacterLibrary/'+role)
        if exact and full(exact):return exact
        options=sorted((c for c in bpy.data.collections if c.name.startswith('CharacterVariants/'+role+'/') and full(c)),key=lambda c:c.name)
        if options:return options[0]
        if role.startswith('citizen-idle-') and (root/'characters/runtime'/(role+'.glb')).exists():
            before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(root/'characters/runtime'/(role+'.glb')))
            imported=list(set(bpy.data.objects)-before);library=bpy.data.collections.new('CharacterLibrary/'+role)
            for obj in imported:
                for c in list(obj.users_collection):c.objects.unlink(obj)
                library.objects.link(obj);obj['runtime_skip']=True;obj['collision']='none'
            assert full(library),'Pose import lost the full canonical body'
            return library
        raise RuntimeError('Missing full retained prototype '+role)
    def feet(role):
        if role not in feet_cache:
            c=retained(role);shoe=next(o for o in c.objects if o.type=='MESH' and 'romansandals' in o.name.lower())
            verts=[shoe.matrix_world@v.co for v in shoe.data.vertices];points=[]
            for sign in [-1,1]:
                side=[p for p in verts if p.x*sign>0];low=min(p.z for p in side);bottom=[p for p in side if p.z<low+.002]
                points.append(sum(bottom,Vector())/len(bottom))
            feet_cache[role]=points
        return feet_cache[role]
    def blocked(p,radius=.35,seated=False):
        if not seated:return support.blocked(p,radius)
        for o,lo,hi in support.near(p,radius):
            if o.get('collision')!='solid' or hi[2]<p[2]+.58 or lo[2]>p[2]+1.35:continue
            if p[0]+radius<lo[0] or p[0]-radius>hi[0] or p[1]+radius<lo[1] or p[1]-radius>hi[1]:continue
            for z in [.6,.95,1.3]:
                for axis in [(1,0,0),(0,1,0)]:
                    direction=Vector(axis);origin=Vector((p[0],p[1],p[2]+z))-direction*radius
                    hit,_,_,_=support.bvh(o).ray_cast(origin,direction,radius*2)
                    if hit is not None:return o.name
        return None
    def ceiling(p,height=1.85,start=.25):
        for o,lo,hi in support.near(p):
            if o.get('collision')!='solid' or not(lo[0]<=p[0]<=hi[0] and lo[1]<=p[1]<=hi[1] and hi[2]>=p[2]+.3 and lo[2]<=p[2]+height):continue
            hit,_,_,_=support.bvh(o).ray_cast(Vector((p[0],p[1],p[2]+start)),Vector((0,0,1)),height-start)
            if hit is not None:return o.name
        return None
    # Verify every authored route against actual support and complete structures.
    for route_index,e in enumerate(npcs):
        if not e.get('path'):continue
        if route_index%8==0:print('DISTRICT_ROUTE_CHECK',route_index,len(npcs),flush=True)
        points=[];sample_count=0;radius=.53 if role_of(e)!='animated-citizen' else .35
        for a,b in zip(source(e['path']),source(e['path'])[1:]):
            steps=max(1,math.ceil(math.dist(a,b)/.6))
            for j in range(steps):
                p=[x+(y-x)*j/steps for x,y in zip(a,b)];hit=support.ground(p)
                if hit is None:raise RuntimeError(f"District route {e['routeId']} lacks real support at {p}")
                p[2]=round(hit[1]+.015,5)
                if points and abs(points[-1][2]-p[2])>.28:raise RuntimeError(f"District route {e['routeId']} has an excessive step at {p}")
                obstacle=blocked(p,radius) or ceiling(p,2.05 if role_of(e)=='animated-porter' else 1.88)
                if obstacle:raise RuntimeError(f"District route {e['routeId']} intersects {obstacle} at {p}")
                points.append(p);sample_count+=1
        points.append(points[0][:]);e['path']=[runtime(p) for p in points];e['position']=runtime(points[0]);e['sourcePosition']=points[0]
        e['rotationY']=facing(points[0],points[1]);route_checks.append({'id':e['id'],'routeId':e['routeId'],'samples':sample_count,'passed':True})
    all_paths=[source(e['path']) for e in manifest['npcs']+npcs if e.get('path')]
    walking_reservations=WalkingReservations(all_paths)
    reservations=Reservations(manifest['instances'])
    accepted=[];accepted_npcs=[]
    for anchor_index,e in enumerate(static+[e for e in npcs if not e.get('path')]):
        if anchor_index%200==0:print('DISTRICT_ANCHOR_CHECK',anchor_index,len(static),len(accepted),len(rejected),flush=True)
        if e['role'].startswith('citizen-idle-') and e['role']!='citizen-idle-0':
            p=e['sourcePosition']
            near_path=walking_reservations.within(p,1.1)
            if blocked(p,.63) or reservations.conflict(p,1.2) or near_path:
                e['role']='citizen-idle-0';e['sourcePrototype']=e['role'];e['poseSpaceFallback']=True
        p=e['sourcePosition'][:];seated=e['role']=='seated-citizen';role=role_of(e) if not e.get('animated') else 'citizen';reason=None
        if seated:
            if 'seatTop' not in e:reason='seated_anchor_missing_seat_top'
            else:p[2]=float(e['seatTop'])-.43974
        else:
            hit=support.ground(p)
            if hit is None:reason='missing_mesh_support'
            else:p[2]=hit[1]
        if reason:rejected.append({'id':e['id'],'reason':reason});continue
        angle=e['rotationY'];gaps=[];supports=[]
        for foot in feet(role):
            q=(p[0]+foot.x*math.cos(angle)-foot.y*math.sin(angle),p[1]+foot.x*math.sin(angle)+foot.y*math.cos(angle),p[2]+foot.z)
            hit=support.ground(q)
            if hit:gaps.append(q[2]-hit[1]);supports.append(hit[2])
        if len(gaps)!=2 or max(gaps)-min(gaps)>.025 or (seated and max(abs(v) for v in gaps)>.04):reason='uneven_or_absent_sandal_support'
        elif not seated:p[2]-=sum(gaps)/2
        if e.get('animated'):p[2]+=.015
        body_radius=.63 if e['role'].startswith('citizen-idle-') and e['role']!='citizen-idle-0' else (.58 if e['role'] in ['guard','gladiator'] else .35)
        headroom=2.75 if e['role']=='guard' else 1.88
        obstacle=blocked(p,.29 if seated else body_radius,seated) or ceiling(p,1.45 if seated else headroom,.6 if seated else .25)
        if obstacle:reason='body_obstacle:'+obstacle
        other=reservations.conflict(p,.86 if seated else .9)
        if other:reason='actor_clearance:'+other
        if walking_reservations.within(p,.84):reason='walking_route_clearance'
        if seated:
            hit=support.ground([p[0],p[1],p[2]+.43974])
            if hit is None or abs(hit[1]-(p[2]+.43974))>.03:reason='missing_actual_seat_surface'
            else:e['seatObject']=hit[2]
        if reason:rejected.append({'id':e['id'],'reason':reason});continue
        p=[round(v,5) for v in p];e['sourcePosition']=p;e['position']=runtime(p);reservations.add(p,e['id'])
        (accepted_npcs if e.get('animated') else accepted).append(e)
        contacts.append({'id':e['id'],'supportObjects':supports,'maximumFootGap':max(abs(v-(0 if seated else sum(gaps)/2)) for v in gaps),
            'seated':seated,'seatObject':e.get('seatObject'),'seatTop':e.get('seatTop')})
    movers=[e for e in npcs if e.get('path')]
    # The old population is an immutable reservation too; walkers cannot pass through it.
    for e in movers:
        for p in source(e['path']):
            other=reservations.conflict(p,.73)
            if other:raise RuntimeError(f"District route {e['routeId']} intersects existing actor {other} at {p}")
    npcs=movers+accepted_npcs
    minimum=0 if validate_only else int(layouts[0][1].get('minimumAcceptedStatic',650))
    if len(accepted)<minimum:raise RuntimeError(f'Only {len(accepted)} safe district anchors, below {minimum}; review placement layout before source integration')
    if validate_only:
        return {'passed':True,'accepted':accepted,'npcs':npcs,'rejectedAnchors':rejected,'contacts':contacts,'routeChecks':route_checks,
            'regionCoverage':region_coverage(accepted,npcs),'sourceUnmodified':True}
    # All geometry tests complete before creating any source actor.
    materials={}
    def cloth(index):
        if index in materials:return materials[index]
        m=bpy.data.materials.get('Population cloth '+str(index))
        if m is None:
            m=bpy.data.materials.new('Population cloth '+str(index));m.use_nodes=True
            rgb=[int(PALETTE[index][k:k+2],16)/255 for k in [1,3,5]];linear=[v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            m.diffuse_color=(*linear,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*linear,1);bs.inputs['Roughness'].default_value=.88
        materials[index]=m;return m
    def tint(obj,index):
        if obj.type!='MESH':return
        for slot in obj.material_slots:
            if slot.material and ('cloth' in slot.material.name.lower() or 'romantunic' in (obj.name+' '+slot.material.name).lower()):
                slot.link='OBJECT';slot.material=cloth(index)
    def validate_collection(c,role):
        body=0;total=0
        for o in c.objects:
            if o.type!='MESH':continue
            o.data.calc_loop_triangles();count=len(o.data.loop_triangles);total+=count
            if 'characterbase' in o.name.lower():body+=count
        assert body==3134 and total==triangles[role],f'Incomplete exact character {c.name}: {body}/{total}'
    def static_collection(e):
        role=role_of(e);name=f"CharacterVariants/{role}/{e['colorIndex']}";c=bpy.data.collections.get(name)
        if c is None:
            template=retained(role);c=bpy.data.collections.new(name)
            for original in template.objects:
                obj=original.copy();obj.data=original.data;c.objects.link(obj);tint(obj,e['colorIndex'])
        validate_collection(c,role);return c
    def animated_collection(e):
        role=role_of(e);library=bpy.data.collections.get('CharacterLibrary/'+role)
        if library is None:
            before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(root/'characters/runtime'/(role+'.glb')))
            imported=list(set(bpy.data.objects)-before);helpers={p.custom_shape for o in imported if o.type=='ARMATURE' for p in o.pose.bones if p.custom_shape}
            for o in imported:
                if o.type=='ARMATURE':
                    for p in o.pose.bones:p.custom_shape=None
            for o in helpers:
                if o in imported:imported.remove(o);bpy.data.objects.remove(o,do_unlink=True)
            library=bpy.data.collections.new('CharacterLibrary/'+role);library['human_scale_normalized']=True
            for o in imported:
                for c in list(o.users_collection):c.objects.unlink(o)
                library.objects.link(o);o['runtime_skip']=True;o['collision']='none'
        c=bpy.data.collections.new(e['sourceCollection']);c['human_scale_normalized']=True
        mapping={o:o.copy() for o in library.objects}
        for original,obj in mapping.items():
            obj.data=original.data;c.objects.link(obj)
            if original.parent in mapping:obj.parent=mapping[original.parent]
            for mod in obj.modifiers:
                if mod.type=='ARMATURE' and mod.object in mapping:mod.object=mapping[mod.object]
            if obj.type=='ARMATURE':
                candidates=[a for a in bpy.data.actions if a.name.lower().split('.')[0]==e['clip'].lower()]
                if not candidates:raise RuntimeError('Bundled action missing '+e['clip'])
                action=candidates[0].copy();action.name='District'+e['clip']+'/'+e['id'];obj.animation_data_create();obj.animation_data.action=action
                if hasattr(action,'slots') and len(action.slots):obj.animation_data.action_slot=action.slots[0]
                for track in obj.animation_data.nla_tracks:track.mute=True
                offset=e['animationPhase']*bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
                for curve in curves(action):
                    for key in curve.keyframe_points:key.co.x-=offset;key.handle_left.x-=offset;key.handle_right.x-=offset
                cycle(action)
            tint(obj,e['colorIndex'])
        validate_collection(c,role);return c
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    for e in accepted+npcs:
        animated=e in npcs;c=animated_collection(e) if animated else static_collection(e)
        obj=bpy.data.objects.new(('NPC/' if animated else 'CROWD/')+e['id'],None);population.objects.link(obj)
        obj.instance_type='COLLECTION';obj.instance_collection=c;obj.location=e['sourcePosition'];obj.rotation_euler.z=e['rotationY']
        for k,v in {'runtime_skip':True,'collision':'none','semantic':e['zone'],'role':e['role'],'runtime_id':e['id'],'districtLife':True,
            'canonical_character_sha256':canonical_hash,'source_asset_sha256':asset_hashes[role_of(e)]}.items():obj[k]=v
        if not animated:continue
        obj['clip']=e['clip'];obj['speed']=e['speed'];obj['animation_phase']=e['animationPhase'];obj['patrol_route']=json.dumps(e.get('path',[]))
        if not e.get('path'):continue
        points=source(e['path']);frame=1.;previous=None
        for i,p in enumerate(points):
            nxt=points[(i+1)%(len(points)-1)];angle=facing(p,nxt)
            if previous is not None:
                while angle-previous>math.pi:angle-=math.tau
                while angle-previous<-math.pi:angle+=math.tau
            previous=angle;obj.location=p;obj.rotation_euler.z=angle
            obj.keyframe_insert(data_path='location',frame=frame);obj.keyframe_insert(data_path='rotation_euler',index=2,frame=frame)
            if i<len(points)-1:frame+=math.dist(p,points[i+1])/e['speed']*fps
        cycle(obj.animation_data.action,True);obj['patrol_loop_frames']=frame-1;bpy.context.scene.frame_end=max(bpy.context.scene.frame_end,math.ceil(frame))
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    for name,(matrix,collection) in signatures.items():
        obj=bpy.data.objects[name];assert tuple(tuple(r) for r in obj.matrix_world)==matrix and obj.instance_collection==collection,f'Existing actor changed: {name}'
    assert sha(root/'characters/CharacterBase.blend')==canonical_hash
    assert all(sha(root/'characters/runtime'/(role+'.glb'))==value for role,value in asset_hashes.items())
    manifest['instances']=sorted(manifest['instances']+accepted,key=lambda e:e['id']);manifest['npcs']+=npcs
    manifest['prototypes']['seated-citizen']='characters/seated-spectator.glb'
    for e in accepted:
        if e['role'].startswith('citizen-idle-'):manifest['prototypes'][e['role']]='characters/'+e['role']+'.glb'
    total=sum(triangles[role_of(e)] for e in manifest['instances']+manifest['npcs'])
    manifest['counts']=dict(Counter(e['zone'] for e in manifest['instances']+manifest['npcs']))
    manifest['districtLife']={'layouts':[{'path':p.name,'sha256':sha(p)} for p,_ in layouts],
        'staticAdded':len(accepted),'animatedAdded':len(npcs),'seatedAdded':sum(e['role']=='seated-citizen' for e in accepted),
        'walkingAdded':len(movers),'fixedIdleAdded':len(accepted_npcs),'protectedInstances':len(old_entries),
        'zoneCounts':dict(Counter(e['zone'] for e in accepted+npcs)),'activityCounts':dict(Counter(e['activity'] for e in accepted+npcs)),
        'regionCoverage':region_coverage(accepted,npcs),
        'previousPopulationFingerprint':digest(old_entries),'fullCanonicalGeometry':True,'oldPlacementsPreserved':True}
    manifest['sourcePopulation'].update(instanceCount=len(population.objects),evaluatedTriangleInstances=total,animatedInstanceCount=len(manifest['npcs']),
        sharedVariantCollections=len({o.instance_collection.name for o in population.objects if not o.name.startswith('NPC/')}),
        importedAssetCollections=sum(c.name.startswith('CharacterLibrary/') for c in bpy.data.collections))
    manifest['assetHashes'].update(asset_hashes)
    assert len(population.objects)==len(manifest['instances'])+len(manifest['npcs'])
    bpy.context.scene['population_instances']=len(population.objects);bpy.context.scene['population_triangle_instances']=total
    target.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    report={'passed':True,'sourceSaveResponsibility':'Caller','canonicalUnchanged':True,'runtimeAssetsUnchanged':True,
        'oldInstancesPreserved':len(old_entries),'districtLife':manifest['districtLife'],'totalPopulation':len(population.objects),
        'characterTriangleInstances':total,'rejectedAnchors':rejected,'groundContacts':contacts,'routeChecks':route_checks,'crowdManifestSHA256':sha(target)}
    (root/'characters/district_life_population_validation.json').write_text(json.dumps(report,indent=2))
    print('DISTRICT_POPULATION',json.dumps({k:v for k,v in report.items() if k not in ['rejectedAnchors','groundContacts','routeChecks']}),flush=True)
    return report

apply=apply_population
