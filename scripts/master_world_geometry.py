"""Rigidly recompose complete city assemblies; the caller owns source saving."""
import bpy,json,math,hashlib
from pathlib import Path
from collections import defaultdict
from mathutils import Matrix,Vector
from city import CityGeometry,_collection

R=Path(__file__).resolve().parents[1]

def eligible_object_names(B=None):
    plan=json.loads((R/'master_world_layout.json').read_text());ids={h['id'] for h in plan['housePlacements']}
    return sorted(o.name for o in bpy.context.scene.objects if o.type=='MESH' and
        (o.name.split('/')[0] in ids or o.name.startswith('Tree_') or o.name.startswith('Block_courtyard_boundaries/') or o.name.startswith('District_routes/')))

def _components(mesh):
    parent=list(range(len(mesh.vertices)))
    def find(a):
        while parent[a]!=a:parent[a]=parent[parent[a]];a=parent[a]
        return a
    for edge in mesh.edges:
        a,b=(find(i) for i in edge.vertices);parent[a]=b
    groups=defaultdict(list)
    for i in range(len(parent)):groups[find(i)].append(i)
    return list(groups.values())

def _keep_original_approaches(obj,mats,collection):
    g=CityGeometry();kept=0
    for indices in _components(obj.data):
        center=sum((obj.matrix_world@obj.data.vertices[i].co for i in indices),Vector())/len(indices)
        if min(math.dist(center[:2],p) for p in [(0,-180),(10,105)])>.2:continue
        remap={k:i for i,k in enumerate(indices)};faces=[tuple(remap[i] for i in p.vertices) for p in obj.data.polygons if all(i in remap for i in p.vertices)]
        g.mesh('road',[tuple(obj.matrix_world@obj.data.vertices[i].co) for i in indices],faces);kept+=1
    out=g.objects('Preserved_ceremonial_approaches',collection,mats,'walkable','city/routes/preserved-approaches')
    return [o.name for o in out],kept

def apply(B=None):
    plan=json.loads((R/'master_world_layout.json').read_text());revision=plan['revision']
    if bpy.context.scene.get('master_city_reflow')==revision:raise RuntimeError('Master city reflow has already been applied; source mutation is intentionally single-pass.')
    if plan['unplacedHouseIds']:raise RuntimeError('Cannot integrate an incomplete house allocation')
    allowed=eligible_object_names();before={o.name:o.data.as_pointer() for o in bpy.context.scene.objects if o.name in allowed}
    groups=defaultdict(list)
    for o in bpy.context.scene.objects:
        if o.type=='MESH':groups[o.name.split('/')[0]].append(o)
    records=[]
    for h in plan['housePlacements']:
        objects=groups.get(h['id'],[])
        if not objects:raise RuntimeError('Missing house assembly '+h['id'])
        old=Vector((*h['sourceCenter'],0));new=Vector((*h['center'],0));delta=Matrix.Translation(new)@Matrix.Rotation(h['rotationDelta'],4,'Z')@Matrix.Translation(-old)
        for o in objects:
            o.matrix_world=delta@o.matrix_world;o['master_city_quarter']=h['quarter'];o['master_city_revision']=revision
        records.append({'id':h['id'],'components':len(objects),'sourceCenter':h['sourceCenter'],'center':h['center'],'rotationDelta':h['rotationDelta']})
    tree_groups=sorted((k,v) for k,v in groups.items() if k.startswith('Tree_'))
    if len(plan['treePlantings'])<len(tree_groups):raise RuntimeError('Insufficient intentional grove positions')
    for (_,objects),p in zip(tree_groups,plan['treePlantings']):
        anchor=objects[0].location.copy();target=Vector(p['position']);delta=target-anchor
        for o in objects:
            o.location+=delta;o['master_city_grove']=p['grove'];o['master_city_revision']=revision
            if '/bark' in o.name:o['collision']='solid'
    bpy.context.view_layer.update()
    # Exact complete mesh corners must remain inside the solver's conservative
    # local envelope. This includes roofs, beams, stoops and front threshold steps.
    projection_errors=[]
    for h in plan['housePlacements']:
        ca,sa=math.cos(h['rotation']),math.sin(h['rotation']);w,d=h['projection_envelope'];cx,cy=h['center']
        for o in groups[h['id']]:
            for p in o.bound_box:
                v=o.matrix_world@Vector(p);x=(v.x-cx)*ca+(v.y-cy)*sa;y=-(v.x-cx)*sa+(v.y-cy)*ca
                if abs(x)>w/2+.025 or abs(y)>d/2+.025:projection_errors.append({'house':h['id'],'object':o.name,'localCorner':[x,y]})
    if projection_errors:raise RuntimeError('Moved assembly exceeded conservative envelope: '+str(projection_errors[:3]))
    collection=_collection('City_Organic_Quarters');mats={k:bpy.data.materials['City/'+k] for k in ['stone','bank','ground','road','wood']}
    created=[];retired=[];preserved_approach_components=0
    for o in list(bpy.context.scene.objects):
        if o.name.startswith('District_routes/'):
            names,count=_keep_original_approaches(o,mats,collection);created.extend(names);preserved_approach_components+=count
            retired.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
        elif o.name.startswith('Block_courtyard_boundaries/'):
            retired.append(o.name);bpy.data.objects.remove(o,do_unlink=True)
    for yard in plan['courtyards']:
        g=CityGeometry();x,y=yard['center'];a=yard['rotation'];w,d=yard['width'],yard['depth'];ca,sa=math.cos(a),math.sin(a)
        def box(mat,u,v,z,size):g.box(mat,(x+u*ca-v*sa,y+u*sa+v*ca,z),size,a)
        # Two short rear wall wings leave a real2m opening; side walls end before
        # the house corners so that the front street and side passage stay legible.
        wall_h=1.10+(len(created)%3)*.12
        for side in [-1,1]:
            box('bank',side*(w/4+.5),d/2-.16,wall_h/2,((w-2)/2,.32,wall_h))
            box('stone',side*(w/2-.16),0,.60,(.32,d-.32,1.20))
        box('ground',0,0,-.023,(w-.4,d-.4,.025))
        names=g.objects(yard['id'],collection,mats,'solid','city/organic-courtyard/'+yard['houseId']);created.extend(o.name for o in names)
    roads=CityGeometry()
    for s in plan['quarterSpines']:
        pts=s['points'];w=s['width']
        for a,b in zip(pts,pts[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
            if length<1e-6:continue
            nx,ny=-dy/length*w/2,dx/length*w/2
            roads.mesh('road',[(a[0]+nx,a[1]+ny,-.012),(a[0]-nx,a[1]-ny,-.012),(b[0]-nx,b[1]-ny,-.012),(b[0]+nx,b[1]+ny,-.012)],[(0,1,2,3)])
    created.extend(o.name for o in roads.objects('Organic_city_streets',collection,mats,'walkable','city/organic-streets'))
    # Mesh datablocks are never regenerated for the159 reused buildings or trees.
    changed=[n for n in allowed if n not in retired]
    assert all(bpy.data.objects[n].data.as_pointer()==before[n] for n in changed)
    registry=json.loads((R/'city_registry.json').read_text());byid={h['id']:h for h in plan['housePlacements']}
    for h in registry['parcels']:
        p=byid[h['id']];h['original_grid_center']=h['center'];h['original_grid_rotation']=h['rotation'];h['center']=p['center'];h['rotation']=p['rotation'];h['projection_envelope']=p['projection_envelope'];h['quarter']=p['quarter'];h['frontage']='organic-street';h['master_reflow']=revision
    registry['master_world_layout']='master_world_layout.json';registry['courtyard_count']=len(plan['courtyards']);registry['city_grid_retired']=True
    (R/'city_registry.json').write_text(json.dumps(registry,indent=2))
    bpy.context.scene['master_city_reflow']=revision
    result={'revision':revision,'changed_existing_objects':changed,'retired_objects':retired,'new_objects':created,
        'house_count':len(records),'tree_count':len(tree_groups),'courtyard_count':len(plan['courtyards']),
        'preserved_original_approach_components':preserved_approach_components,'projection_errors':projection_errors,
        'house_shared_meshes_preserved':True,'houses':records,'layout_sha256':hashlib.sha256((R/'master_world_layout.json').read_bytes()).hexdigest()}
    (R/'comparisons/master_world_geometry_audit.json').write_text(json.dumps(result,indent=2))
    return result
