"""Replace only district population from explicit street-life layout anchors.

Root integration: apply_population(root=ROOT, layout_path=None). The arena scene
must already be open and the city geometry revision applied. This module never
opens or saves a .blend. It retains exact canonical character mesh data, every
spectator and all protected arena/backstage/statue instances.
"""
from pathlib import Path
from collections import Counter
import hashlib,json,math,copy

ROOT=Path(__file__).resolve().parents[1]
REPLACE_ZONES={'plaza_crowd','market_vendor','plaza_patrol'}
PALETTE=['#C8B88D','#9F4939','#B28B56','#798477','#9A8A73','#BAAB91','#6D3158','#C39B79']
TAU=math.tau

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def runtime(p):return [round(p[0],5),round(p[2],5),round(-p[1],5)]
def facing(a,b):return math.atan2(b[1]-a[1],b[0]-a[0])+math.pi/2
def distance_segment(p,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    t=0 if not den else max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den))
    return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def segment_distance(a,b,c,d):
    def side(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
    if side(a,b,c)*side(a,b,d)<0 and side(c,d,a)*side(c,d,b)<0:return 0
    return min(distance_segment(a,c,d),distance_segment(b,c,d),distance_segment(c,a,b),distance_segment(d,a,b))
def independent_routes(routes,clearance=1.4):
    """Avoid opposing traffic on near-coincident edges of adjacent stall loops."""
    conflicts={i:set() for i in range(len(routes))}
    for i,r in enumerate(routes):
        for j in range(i):
            other=routes[j]
            gap=min(segment_distance(a,b,c,d) for a,b in zip(r['points'],r['points'][1:]) for c,d in zip(other['points'],other['points'][1:]))
            if gap<clearance:conflicts[i].add(j);conflicts[j].add(i)
    remaining=set(conflicts);selected=[]
    while remaining:
        best=min(remaining,key=lambda i:(len(conflicts[i]&remaining),i));selected.append(best)
        remaining-=conflicts[best]|{best}
    return [routes[i] for i in sorted(selected)]
def curves(action):
    if hasattr(action,'fcurves'):yield from action.fcurves
    else:
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:yield from bag.fcurves
def cycle(action,linear=False):
    for curve in curves(action):
        if not any(m.type=='CYCLES' for m in curve.modifiers):curve.modifiers.new('CYCLES')
        if linear:
            for key in curve.keyframe_points:key.interpolation='LINEAR'
def close(points):
    result=[list(p) for p in points]
    if len(result)<3:raise ValueError('Walking routes require at least three points')
    if math.dist(result[0],result[-1])>1e-6:result.append(result[0][:])
    return result
def phase_route(points,phase):
    """Shift a closed path by arc length without inventing a shortcut segment."""
    points=close(points);lengths=[math.dist(a,b) for a,b in zip(points,points[1:])]
    distance=sum(lengths)*(phase%1)
    for i,length in enumerate(lengths):
        if distance<=length:
            t=distance/length if length else 0
            p=[a+(b-a)*t for a,b in zip(points[i],points[i+1])]
            raw=[p]+copy.deepcopy(points[i+1:-1])+copy.deepcopy(points[:i+1])+[p[:]]
            result=[raw[0]]
            for q in raw[1:]:
                if math.dist(result[-1],q)>1e-7:result.append(q)
            return close(result)
        distance-=length
    return points
def _entry(ident,role,p,heading,zone,color=0,**extra):
    return dict(id=ident,role=role,position=runtime(p),sourcePosition=[round(v,5) for v in p],
        rotationY=round(heading,7),scale=1.0,colorIndex=color,zone=zone,streetLife=True,**extra)

def plan_population(root=ROOT,layout=None,layout_path=None):
    """Pure plan from city-owned safe anchors; no Blender or file writes."""
    root=Path(root);layout_path=Path(layout_path or root/'street_life_layout.json')
    layout=layout or json.loads(layout_path.read_text())
    manifest=json.loads((root/'characters/runtime/crowd_manifest.json').read_text())
    protected=[e for e in manifest['instances'] if e['zone'] not in REPLACE_ZONES and not e.get('streetLife')]
    protected_npcs=[e for e in manifest['npcs'] if e['zone'] not in REPLACE_ZONES and not e.get('streetLife')]
    if sum(e['role']=='seated-spectator' for e in protected)!=12000:raise ValueError('The twelve thousand seated spectators must be preserved')
    routes=layout.get('routes',[])
    if not routes:raise ValueError('Street layout must provide explicit closed walking routes')
    routes=[dict(r,points=close(r.get('points',r.get('path',[])))) for r in routes]
    walking_routes=independent_routes(routes)
    if len(walking_routes)<8:raise ValueError('Layout must provide at least eight mutually clear loops for active merchants')
    placed=[];rejected=[];accepted=[]
    # Existing protected actors are hard reservations; no city update may move them.
    reservations=[e['sourcePosition'] for e in protected if e['sourcePosition'][2]<3 and e['sourcePosition'][2]>-1]
    def add(anchor,vendor=False):
        p=anchor.get('position',anchor.get('sourcePosition'));p=list(p)+[0]*(3-len(p))
        ident=anchor['id'];heading=float(anchor.get('facing',anchor.get('heading',0)))
        role=anchor.get('role','merchant' if vendor else 'citizen')
        if role not in ['citizen','merchant','worker','noble']:role='citizen'
        reason=None
        if any(math.dist(p,q)<.77 for q in reservations+accepted):reason='neighbor_clearance'
        clearance=float(anchor.get('routeClearance',.80))
        if not vendor and any(distance_segment(p,a,b)<clearance for r in routes for a,b in zip(r['points'],r['points'][1:])):reason='walking_corridor'
        if reason:
            rejected.append({'id':ident,'reason':reason,'position':p});return
        accepted.append(p)
        activity=anchor.get('activity','vendor' if vendor else 'customer')
        zone='street_vendor' if vendor else 'street_'+activity
        color=int(anchor.get('colorIndex',(len(placed)*5+len(ident))%8))%8
        extras={k:anchor[k] for k in ['stallId','groupId','courtId','purpose'] if k in anchor}
        placed.append(_entry('street_'+ident,role,p,heading,zone,color,activity=activity,**extras))
    for a in layout.get('vendors',layout.get('vendor_spawns',[])):add(a,True)
    for a in layout.get('anchors',layout.get('crowd_anchors',[])):add(a)
    target=int(layout.get('animatedActorCount',32));npcs=[]
    if target<24 or target>40:raise ValueError('Revision target is 24–40 full skeletal street actors')
    for i in range(target):
        route=walking_routes[i%len(walking_routes)];occupancy=math.ceil((target-i%len(walking_routes))/len(walking_routes))
        phase=(i//len(walking_routes))/occupancy
        points=phase_route(route['points'],phase)
        role=['merchant','citizen','worker','citizen'][i%4]
        activity={'merchant':'itinerant_merchant','worker':'porter','citizen':'passerby'}[role]
        color={'merchant':2,'worker':3,'citizen':(i*3)%8}[role]
        prototype={'merchant':'animated-merchant','worker':'animated-porter','citizen':'animated-citizen'}[role]
        item=_entry(f'street_walker_{i:03}',role,points[0],facing(points[0],points[1]),'street_'+activity,color,
            activity=activity,routeId=route['id'],courtId=route.get('courtId',route.get('zone','market')),
            asset='characters/'+prototype+'.glb',clip='Walk',path=[runtime(p) for p in points],
            speed=float(route.get('speed',.78+(i%len(walking_routes)%4)*.065)),loop=True,sourcePrototype=prototype,
            animationPhase=round((i*.173)%(.8),5),patrolPathPhase=phase)
        npcs.append(item)
    # A few fixed front-line vendors breathe and gesture with the actual Idle
    # clip. Their goods remain on counters; wearable baskets belong to hawkers.
    vendor_choices=[e for e in placed if e['zone']=='street_vendor']
    if len(vendor_choices)>=8:
        selection=[vendor_choices[round(i*(len(vendor_choices)-1)/7)] for i in range(8)]
        for i,vendor in enumerate(selection):
            placed.remove(vendor);item=copy.deepcopy(vendor)
            item.update(id=vendor['id']+'_idle',animated=True,asset='characters/animated-citizen.glb',
                sourcePrototype='animated-citizen',clip='Idle',animationPhase=round(i*.417,5),
                activity='active_vendor',zone='street_active_vendor',speed=0,loop=True)
            npcs.append(item)
    manifest['instances']=sorted(protected+placed,key=lambda e:e['id'])
    manifest['npcs']=protected_npcs+npcs
    manifest['counts']=dict(Counter(e['zone'] for e in manifest['instances']+manifest['npcs']))
    manifest['streetLife']={'layout':str(layout_path),'layoutSHA256':sha(layout_path) if layout_path.exists() else None,
       'staticAdded':len(placed),'animatedAdded':len(npcs),'rejectedAnchors':rejected,
       'selectedWalkingRoutes':[r['id'] for r in walking_routes],'minimumIndependentRouteGap':1.4,
       'protectedStaticCount':len(protected),'fullCharacterGeometry':True,
       'activityCounts':dict(Counter(e.get('activity') for e in placed+npcs)),
       'staticGeometryUnchanged':True,'canonicalAssetsUnchanged':True,
       'behavior':'Purposeful static market groups plus independently phased real bundled Walk actors on clear closed loops'}
    return manifest

class GeometrySupport:
    """Use actual authored mesh support and obstruction surfaces, never floor guesses."""
    def __init__(self):
        import bpy
        from mathutils import Vector
        self.Vector=Vector;self.records=[];self.cache={}
        for o in bpy.context.scene.objects:
            if o.type!='MESH' or o.get('runtime_skip') or o.hide_render:continue
            if o.get('collision') not in ['solid','walkable']:continue
            points=[o.matrix_world@Vector(p) for p in o.bound_box]
            lo=[min(p[k] for p in points) for k in range(3)];hi=[max(p[k] for p in points) for k in range(3)]
            self.records.append((o,lo,hi))
    def bvh(self,o):
        from mathutils.bvhtree import BVHTree
        if o.name not in self.cache:
            self.cache[o.name]=BVHTree.FromPolygons([o.matrix_world@v.co for v in o.data.vertices],[list(p.vertices) for p in o.data.polygons])
        return self.cache[o.name]
    def ground(self,p):
        hits=[];V=self.Vector
        for o,lo,hi in self.records:
            if not(lo[0]-.001<=p[0]<=hi[0]+.001 and lo[1]-.001<=p[1]<=hi[1]+.001 and lo[2]<=p[2]+.35 and hi[2]>=p[2]-.45):continue
            hit,normal,_,_=self.bvh(o).ray_cast(V((p[0],p[1],p[2]+.35)),V((0,0,-1)),.8)
            if hit is not None and normal.z>.55:hits.append((abs(hit.z-p[2]),hit.z,o.name))
        # Highest reachable top surface wins over a buried plaza/terrain layer.
        # The short +0.35m ray window deliberately excludes roofs and tables.
        return max(hits,key=lambda h:h[1]) if hits else None
    def blocked(self,p,radius=.35):
        V=self.Vector
        for o,lo,hi in self.records:
            if o.get('collision')!='solid' or hi[2]<p[2]+.3 or lo[2]>p[2]+1.7:continue
            if p[0]+radius<lo[0] or p[0]-radius>hi[0] or p[1]+radius<lo[1] or p[1]-radius>hi[1]:continue
            for z in [.45,1.05,1.6]:
                for axis in [(1,0,0),(0,1,0),(.707,.707,0),(.707,-.707,0)]:
                    direction=V(axis);origin=V((p[0],p[1],p[2]+z))-direction*radius
                    hit,_,_,_=self.bvh(o).ray_cast(origin,direction,radius*2)
                    if hit is not None:return o.name
        return None

def apply_population(root=ROOT,layout_path=None):
    """Apply to the currently open city-revised scene; caller alone saves source."""
    import bpy
    from mathutils import Vector
    root=Path(root);manifest=plan_population(root,layout_path=layout_path)
    canonical=root/'characters/CharacterBase.blend';canonical_before=sha(canonical)
    asset_hashes={p.name:sha(p) for p in (root/'characters/runtime').glob('*.glb')}
    population=bpy.data.collections['Population']
    protected_objects={o.get('runtime_id'):o for o in population.objects if o.get('runtime_id') and o.get('semantic') not in REPLACE_ZONES and not o.get('streetLife')}
    signatures={i:(tuple(o.matrix_world),o.instance_collection) for i,o in protected_objects.items()}
    def retained_role_collection(role):
        """A saved file keeps used variants, while unused base libraries may vanish."""
        def complete(c):return any(o.type=='MESH' and 'characterbase' in o.name.lower() for o in c.objects)
        library=bpy.data.collections.get('CharacterLibrary/'+role)
        if library is not None and complete(library):return library
        variants=sorted((c for c in bpy.data.collections if c.name.startswith('CharacterVariants/'+role+'/') and complete(c)),key=lambda c:c.name)
        if variants:return variants[0]
        raise RuntimeError('No retained full character collection for role '+role)
    support=GeometrySupport();rejected=manifest['streetLife']['rejectedAnchors'];contact=[];feet_cache={}
    def foot_points(role):
        if role not in feet_cache:
            lib=retained_role_collection(role)
            shoe=next(o for o in lib.objects if o.type=='MESH' and 'romansandals' in o.name.lower())
            points=[shoe.matrix_world@v.co for v in shoe.data.vertices];feet=[]
            for sign in [-1,1]:
                side=[p for p in points if p.x*sign>0];low=min(p.z for p in side);bottom=[p for p in side if p.z<low+.002]
                feet.append(sum(bottom,Vector())/len(bottom))
            feet_cache[role]=feet
        return feet_cache[role]
    # Place feet on actual support before touching source objects.
    static=[]
    for e in manifest['instances']:
        if not e.get('streetLife'):static.append(e);continue
        p=e['sourcePosition'];ground=support.ground(p)
        if ground is None:
            rejected.append({'id':e['id'],'reason':'missing_mesh_support'});continue
        p[2]=round(ground[1],5)
        angle=e['rotationY'];foot_hits=[]
        for foot in foot_points(e['role']):
            q=(p[0]+foot.x*math.cos(angle)-foot.y*math.sin(angle),p[1]+foot.x*math.sin(angle)+foot.y*math.cos(angle),p[2]+foot.z)
            hit=support.ground(q)
            if hit:foot_hits.append((q[2]-hit[1],hit[2],hit[1]))
        if len(foot_hits)!=2 or abs(foot_hits[0][0]-foot_hits[1][0])>.025:
            rejected.append({'id':e['id'],'reason':'uneven_or_absent_two_foot_support'});continue
        p[2]=round(p[2]-sum(h[0] for h in foot_hits)/2,5)
        blocker=support.blocked(p)
        if blocker:
            rejected.append({'id':e['id'],'reason':'body_intersects_geometry','object':blocker});continue
        e['position']=runtime(p);static.append(e);contact.append({'id':e['id'],'support':ground[2],'groundZ':p[2],
            'footSupport':[h[1] for h in foot_hits],'maximumFootGap':abs(foot_hits[0][0]-foot_hits[1][0])/2})
    manifest['instances']=static
    route_records=[]
    for e in manifest['npcs']:
        if not e.get('streetLife'):continue
        if not e.get('path'):
            hit=support.ground(e['sourcePosition'])
            if hit is None:raise RuntimeError(f"Animated vendor {e['id']} has no mesh support")
            e['sourcePosition'][2]=round(hit[1]+.015,5);e['position']=runtime(e['sourcePosition'])
            blocker=support.blocked(e['sourcePosition'])
            if blocker:raise RuntimeError(f"Animated vendor {e['id']} intersects {blocker}")
            continue
        planned=[[p[0],-p[2],p[1]] for p in e['path']]
        checked=0;points=[]
        for a,b in zip(planned,planned[1:]):
            steps=max(1,math.ceil(math.dist(a,b)/.65))
            for j in range(steps):
                p=[v+(w-v)*j/steps for v,w in zip(a,b)]
                ground=support.ground(p)
                if ground is None:raise RuntimeError(f"Street route {e['routeId']} loses ground support at {p}")
                p[2]=round(ground[1]+.015,5)
                if points and abs(points[-1][2]-p[2])>.28:raise RuntimeError(f"Street route {e['routeId']} has an impassable ground step")
                radius=.53 if e['sourcePrototype'] in ['animated-merchant','animated-porter'] else .35
                blocker=support.blocked(p,radius)
                if blocker:raise RuntimeError(f"Street route {e['routeId']} intersects {blocker} at {p}")
                checked+=1;points.append(p)
        points.append(points[0][:])
        e['sourcePosition']=points[0][:];e['position']=runtime(points[0]);e['path']=[runtime(p) for p in points]
        route_records.append({'id':e['id'],'routeId':e['routeId'],'meshObstacleSamples':checked,'passed':True})
    added=[e for e in static if e.get('streetLife')]
    if len(added)<350:raise RuntimeError(f'Only {len(added)} accepted market actors; layout must support purposeful density before integration')
    for o in list(population.objects):
        if o.get('semantic') in REPLACE_ZONES or o.get('streetLife'):bpy.data.objects.remove(o,do_unlink=True)
    # Old revision-only animation prototypes have no scene consumers after removal.
    for c in list(bpy.data.collections):
        if c.name.startswith('StreetLifeAnimated/'):
            for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
            bpy.data.collections.remove(c)
    mats={};variants={}
    def cloth(index):
        if index in mats:return mats[index]
        m=bpy.data.materials.get('Population cloth '+str(index))
        if m is None:
            m=bpy.data.materials.new('Population cloth '+str(index));m.use_nodes=True
            rgb=[int(PALETTE[index][k:k+2],16)/255 for k in [1,3,5]]
            linear=[v/12.92 if v<.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            m.diffuse_color=(*linear,1);bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*linear,1);bs.inputs['Roughness'].default_value=.88
        mats[index]=m;return m
    def tint(obj,index):
        if obj.type!='MESH':return
        for slot in obj.material_slots:
            if slot.material and ('cloth' in slot.material.name.lower() or 'romantunic' in (obj.name+' '+slot.material.name).lower()):
                slot.link='OBJECT';slot.material=cloth(index)
    def static_variant(role,index):
        key=(role,index)
        if key in variants:return variants[key]
        name=f'CharacterVariants/{role}/{index}';c=bpy.data.collections.get(name)
        if c is None or not len(c.objects):
            template=retained_role_collection(role)
            if c is None:c=bpy.data.collections.new(name)
            for original in template.objects:
                o=original.copy();o.data=original.data;c.objects.link(o);tint(o,index)
        variants[key]=c;return c
    def animated_variant(e):
        role=e['sourcePrototype'];library=bpy.data.collections.get('CharacterLibrary/'+role)
        if library is None:
            before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(root/'characters/runtime'/(role+'.glb')))
            imported=list(set(bpy.data.objects)-before)
            helpers={p.custom_shape for o in imported if o.type=='ARMATURE' for p in o.pose.bones if p.custom_shape}
            for o in imported:
                if o.type=='ARMATURE':
                    for bone in o.pose.bones:bone.custom_shape=None
            for o in helpers:
                if o in imported:imported.remove(o);bpy.data.objects.remove(o,do_unlink=True)
            library=bpy.data.collections.new('CharacterLibrary/'+role);library['human_scale_normalized']=True
            for o in imported:
                for previous in list(o.users_collection):previous.objects.unlink(o)
                library.objects.link(o);o['runtime_skip']=True;o['collision']='none';o['source_role']=role
        c=bpy.data.collections.new('StreetLifeAnimated/'+e['id']);c['human_scale_normalized']=True
        mapping={o:o.copy() for o in library.objects}
        for original,o in mapping.items():
            o.data=original.data;c.objects.link(o)
            if original.parent in mapping:o.parent=mapping[original.parent]
            for mod in o.modifiers:
                if mod.type=='ARMATURE' and mod.object in mapping:mod.object=mapping[mod.object]
            if o.type=='ARMATURE':
                desired=e['clip'].lower()
                candidates=[a for a in bpy.data.actions if a.name.lower().split('.')[0]==desired]
                if not candidates:raise RuntimeError('Required bundled action absent: '+e['clip'])
                action=candidates[0].copy();action.name='Street'+e['clip']+'/'+e['id']
                o.animation_data_create();o.animation_data.action=action
                if hasattr(action,'slots') and len(action.slots):o.animation_data.action_slot=action.slots[0]
                for track in o.animation_data.nla_tracks:track.mute=True
                offset=e['animationPhase']*(bpy.context.scene.render.fps/bpy.context.scene.render.fps_base)
                for curve in curves(action):
                    for key in curve.keyframe_points:
                        key.co.x-=offset;key.handle_left.x-=offset;key.handle_right.x-=offset
                cycle(action)
            tint(o,e['colorIndex'])
        return c
    fps=bpy.context.scene.render.fps/bpy.context.scene.render.fps_base
    def spawn(e,animated=False):
        c=animated_variant(e) if animated else static_variant(e['role'],e['colorIndex'])
        o=bpy.data.objects.new(('NPC/' if animated else 'CROWD/')+e['id'],None);population.objects.link(o)
        o.instance_type='COLLECTION';o.instance_collection=c;o.location=e['sourcePosition'];o.rotation_euler.z=e['rotationY']
        o['runtime_skip']=True;o['collision']='none';o['semantic']=e['zone'];o['role']=e['role'];o['runtime_id']=e['id'];o['streetLife']=True
        o['canonical_character_sha256']=canonical_before;o['source_asset_sha256']=asset_hashes[(e['sourcePrototype'] if animated else e['role'])+'.glb']
        if animated:
            o['clip']=e['clip'];o['speed']=e['speed'];o['patrol_route']=json.dumps(e.get('path',[]));o['animation_phase']=e['animationPhase']
            if not e.get('path'):return o
            points=[[p[0],-p[2],p[1]] for p in e['path']];frame=1.;previous=None
            for i,p in enumerate(points):
                nxt=points[(i+1)%(len(points)-1)];angle=facing(p,nxt)
                if previous is not None:
                    while angle-previous>math.pi:angle-=TAU
                    while angle-previous<-math.pi:angle+=TAU
                previous=angle;o.location=p;o.rotation_euler.z=angle
                o.keyframe_insert(data_path='location',frame=frame);o.keyframe_insert(data_path='rotation_euler',index=2,frame=frame)
                if i<len(points)-1:frame+=math.dist(p,points[i+1])/e['speed']*fps
            cycle(o.animation_data.action,True);o['patrol_loop_frames']=frame-1
            bpy.context.scene.frame_end=max(bpy.context.scene.frame_end,math.ceil(frame))
        return o
    for e in added:spawn(e)
    for e in manifest['npcs']:
        if e.get('streetLife'):spawn(e,True)
    bpy.context.scene.frame_set(1);bpy.context.view_layer.update()
    for ident,(matrix,collection) in signatures.items():
        o=protected_objects[ident]
        assert tuple(o.matrix_world)==matrix and o.instance_collection==collection,f'Protected character {ident} changed'
    assert sha(canonical)==canonical_before,'Canonical character changed during population-only update'
    assert all(sha(root/'characters/runtime'/name)==value for name,value in asset_hashes.items()),'Runtime character asset changed'
    triangles=0;cache={}
    for o in population.objects:
        c=o.instance_collection
        if c.name not in cache:
            count=0
            for mesh in c.objects:
                if mesh.type=='MESH':mesh.data.calc_loop_triangles();count+=len(mesh.data.loop_triangles)
            cache[c.name]=count
        triangles+=cache[c.name]
    manifest['counts']=dict(Counter(e['zone'] for e in manifest['instances']+manifest['npcs']))
    manifest['streetLife']['staticAdded']=len(added)
    manifest['streetLife']['activityCounts']=dict(Counter(e.get('activity') for e in added+manifest['npcs']))
    manifest['sourcePopulation'].update(instanceCount=len(population.objects),evaluatedTriangleInstances=triangles,
       animatedInstanceCount=len(manifest['npcs']),animatedIndependentPhases=True,sourcePatrolTransformKeyframes=True,
       sharedVariantCollections=len({o.instance_collection.name for o in population.objects if not o.name.startswith('NPC/')}),
       importedAssetCollections=sum(c.name.startswith('CharacterLibrary/') for c in bpy.data.collections))
    manifest['assetHashes'].update({name[:-4]:value for name,value in asset_hashes.items()})
    bpy.context.scene['population_instances']=len(population.objects);bpy.context.scene['population_triangle_instances']=triangles
    target=root/'characters/runtime/crowd_manifest.json';target.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    report={'passed':True,'sourceSaveResponsibility':'Caller','layoutSHA256':manifest['streetLife']['layoutSHA256'],
      'canonicalUnchanged':True,'runtimeCharacterAssetsUnchanged':True,'protectedInstancesUnchanged':len(protected_objects),
      'spectatorsPreserved':12000,'staticStreetInstances':len(added),'animatedStreetInstances':len(manifest['npcs']),
      'totalPopulation':len(population.objects),'characterTriangleInstances':triangles,'counts':manifest['counts'],
      'rejectedAnchors':rejected,'groundSupports':contact,'routes':route_records,'crowdManifestSHA256':sha(target)}
    (root/'characters/street_life_population_validation.json').write_text(json.dumps(report,indent=2))
    print('STREET_LIFE_POPULATION',json.dumps({k:v for k,v in report.items() if k not in ['groundSupports','routes','rejectedAnchors']}),flush=True)
    return report

apply=apply_population

def repair_empty_variants(root=ROOT):
    """Targeted recovery for the first saved street pass; no .blend save."""
    import bpy
    root=Path(root);target=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(target.read_text())
    canonical_before=sha(root/'characters/CharacterBase.blend')
    population=bpy.data.collections['Population'];counts=Counter(o.instance_collection.name for o in population.objects)
    repaired=[]
    for name,count in counts.items():
        c=bpy.data.collections[name]
        if len(c.objects):continue
        if not name.startswith('CharacterVariants/'):raise RuntimeError('Unexpected empty collection '+name)
        _,role,color=name.split('/');index=int(color)
        templates=[col for col in bpy.data.collections if col.name.startswith('CharacterVariants/'+role+'/')
            and any(o.type=='MESH' and 'characterbase' in o.name.lower() for o in col.objects)]
        if not templates:raise RuntimeError('No complete retained role geometry for '+role)
        template=sorted(templates,key=lambda col:col.name)[0]
        material=bpy.data.materials.get('Population cloth '+str(index))
        if material is None:raise RuntimeError('Missing validated palette material '+str(index))
        for original in list(template.objects):
            o=original.copy();o.data=original.data;c.objects.link(o)
            if o.type=='MESH':
                for slot in o.material_slots:
                    if slot.material and ('cloth' in slot.material.name.lower() or 'romantunic' in o.name.lower()):
                        slot.link='OBJECT';slot.material=material
        repaired.append({'collection':name,'sourceTemplate':template.name,'instanceCount':count,'meshCount':sum(o.type=='MESH' for o in c.objects)})
    cache={}
    for o in population.objects:
        c=o.instance_collection
        if c.name not in cache:
            n=0;body=0
            for mesh in c.objects:
                if mesh.type!='MESH':continue
                mesh.data.calc_loop_triangles();n+=len(mesh.data.loop_triangles)
                if 'characterbase' in mesh.name.lower():body+=len(mesh.data.loop_triangles)
            assert body==3134,f'{c.name} lacks complete canonical body'
            cache[c.name]=n
    actual=sum(cache[o.instance_collection.name] for o in population.objects)
    inventory=json.loads((root/'characters/runtime-validation.json').read_text())
    triangles={Path(r['asset']).stem:r['triangles'] for r in inventory['reimports']}
    expected=sum(triangles[e.get('sourcePrototype',e['role'])] for e in manifest['instances']+manifest['npcs'])
    assert actual==expected,f'Source {actual} differs from runtime {expected}'
    previous=manifest['sourcePopulation']['evaluatedTriangleInstances']
    manifest['sourcePopulation']['evaluatedTriangleInstances']=actual
    bpy.context.scene['population_triangle_instances']=actual
    target.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    report={'passed':True,'sourceSaveResponsibility':'Caller','repairedCollections':repaired,
        'repairedInstanceCount':sum(r['instanceCount'] for r in repaired),'previousSourceTriangleInstances':previous,
        'sourceTriangleInstances':actual,'runtimeTriangleInstances':expected,'allBodiesExact3134Triangles':True,
        'actorTransformsUnchanged':True,'canonicalUnchanged':sha(root/'characters/CharacterBase.blend')==canonical_before,
        'crowdManifestSHA256':sha(target)}
    (root/'characters/street_empty_variant_repair.json').write_text(json.dumps(report,indent=2))
    validation_path=root/'characters/street_life_population_validation.json'
    validation=json.loads(validation_path.read_text());validation['characterTriangleInstances']=actual
    validation['emptyVariantRepair']=report;validation['crowdManifestSHA256']=sha(target)
    validation_path.write_text(json.dumps(validation,indent=2))
    bpy.context.view_layer.update();print('STREET_EMPTY_VARIANT_REPAIR',json.dumps(report),flush=True)
    return report

def append_entry_gatherings(root=ROOT):
    """Add only city-owned EntryGathering anchors; keep every existing placement."""
    import bpy
    from mathutils import Vector
    root=Path(root);layout_path=root/'street_life_layout.json';layout=json.loads(layout_path.read_text())
    target=root/'characters/runtime/crowd_manifest.json';manifest=json.loads(target.read_text())
    anchors=[a for a in layout['anchors'] if a['id'].startswith('EntryGathering')]
    if not anchors:raise RuntimeError('Authoritative entry-gathering anchors are not published yet')
    population=bpy.data.collections['Population'];existing_ids={e['id'] for e in manifest['instances']+manifest['npcs']}
    reservations=[e['sourcePosition'] for e in manifest['instances'] if -.5<e['sourcePosition'][2]<.5]
    routes=[[[p[0],-p[2],p[1]] for p in e['path']] for e in manifest['npcs'] if e.get('path')]
    support=GeometrySupport();accepted=[];rejected=[]
    library=bpy.data.collections['CharacterVariants/citizen/0']
    shoe=next(o for o in library.objects if o.type=='MESH' and 'romansandals' in o.name.lower())
    vertices=[shoe.matrix_world@v.co for v in shoe.data.vertices];feet=[]
    for sign in [-1,1]:
        side=[p for p in vertices if p.x*sign>0];low=min(p.z for p in side);bottom=[p for p in side if p.z<low+.002]
        feet.append(sum(bottom,Vector())/len(bottom))
    for anchor in anchors:
        ident='street_'+anchor['id']
        if ident in existing_ids:continue
        p=list(anchor['position']);angle=float(anchor.get('facing',0));reason=None
        if abs(p[0])<3.65:reason='ceremonial_axis'
        if any(math.dist(p,q)<.999 for q in reservations):reason='actor_clearance'
        if any(distance_segment(p,a,b)<1.0 for points in routes for a,b in zip(points,points[1:])):reason='animated_route_clearance'
        ground=support.ground(p)
        if ground is None:reason='missing_actual_support'
        if reason:rejected.append({'id':ident,'reason':reason});continue
        p[2]=ground[1];gaps=[]
        for foot in feet:
            q=(p[0]+foot.x*math.cos(angle)-foot.y*math.sin(angle),p[1]+foot.x*math.sin(angle)+foot.y*math.cos(angle),p[2]+foot.z)
            hit=support.ground(q)
            if hit:gaps.append(q[2]-hit[1])
        if len(gaps)!=2 or abs(gaps[0]-gaps[1])>.025:
            rejected.append({'id':ident,'reason':'uneven_sandal_support'});continue
        p[2]=round(p[2]-sum(gaps)/2,5)
        blocked=support.blocked(p)
        if blocked:rejected.append({'id':ident,'reason':'body_obstacle','object':blocked});continue
        entry=_entry(ident,'citizen',p,angle,'street_entry_gathering',int(anchor.get('colorIndex',len(accepted)*3))%8,
            activity=anchor.get('activity','conversation'),groupId=anchor.get('groupId'),purpose='Waiting and conversation beside the ceremonial entrance')
        accepted.append(entry);reservations.append(p)
    already=sum(e['zone']=='street_entry_gathering' for e in manifest['instances'])
    if len(accepted)+already<100:raise RuntimeError(f'Only {len(accepted)+already} safe entry actors; review rejected anchors: {rejected}')
    canonical=sha(root/'characters/CharacterBase.blend');asset=sha(root/'characters/runtime/citizen.glb')
    for e in accepted:
        o=bpy.data.objects.new('CROWD/'+e['id'],None);population.objects.link(o)
        o.instance_type='COLLECTION';o.instance_collection=bpy.data.collections['CharacterVariants/citizen/'+str(e['colorIndex'])]
        o.location=e['sourcePosition'];o.rotation_euler.z=e['rotationY'];o['runtime_skip']=True;o['collision']='none'
        o['semantic']=e['zone'];o['role']='citizen';o['runtime_id']=e['id'];o['streetLife']=True
        o['canonical_character_sha256']=canonical;o['source_asset_sha256']=asset
    manifest['instances']=sorted(manifest['instances']+accepted,key=lambda e:e['id'])
    manifest['counts']=dict(Counter(e['zone'] for e in manifest['instances']+manifest['npcs']))
    manifest['sourcePopulation']['instanceCount']=len(population.objects)
    manifest['sourcePopulation']['evaluatedTriangleInstances']+=len(accepted)*5002
    manifest['streetLife']['staticAdded']+=len(accepted);manifest['streetLife']['layoutSHA256']=sha(layout_path)
    manifest['streetLife']['entryGatherings']=len(accepted)+already
    manifest['streetLife']['activityCounts']=dict(Counter(e.get('activity') for e in manifest['instances']+manifest['npcs'] if e.get('streetLife')))
    target.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8')
    bpy.context.scene['population_instances']=len(population.objects)
    bpy.context.scene['population_triangle_instances']=manifest['sourcePopulation']['evaluatedTriangleInstances']
    bpy.context.view_layer.update()
    report={'passed':True,'added':len(accepted),'alreadyPresent':already,'groups':len({e.get('groupId') for e in accepted}),
        'rejected':rejected,'centralAxisClearWidth':6,'minimumActorCenterSeparation':1.0,'sourceAndRuntimePositionsIdentical':True,
        'meshGroundAndTwoFootChecks':True,'sourceInstancesVisible':all(not bpy.data.objects['CROWD/'+e['id']].hide_render for e in accepted),
        'layoutSHA256':sha(layout_path),'crowdManifestSHA256':sha(target),'sourceSaveResponsibility':'Caller',
        'totalPopulation':len(population.objects),'characterTriangleInstances':manifest['sourcePopulation']['evaluatedTriangleInstances']}
    (root/'characters/street_entry_crowd_validation.json').write_text(json.dumps(report,indent=2))
    path=root/'characters/street_life_population_validation.json';data=json.loads(path.read_text())
    data.update(totalPopulation=len(population.objects),characterTriangleInstances=manifest['sourcePopulation']['evaluatedTriangleInstances'],
        staticStreetInstances=manifest['streetLife']['staticAdded'],counts=manifest['counts'],crowdManifestSHA256=sha(target),entryGatherings=report)
    path.write_text(json.dumps(data,indent=2));print('ENTRY_GATHERINGS',json.dumps(report),flush=True)
    return report
