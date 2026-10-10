"""Validated relocation of complete workshops and shared foreground architecture."""
import bpy
import json
import math
from pathlib import Path
from mathutils import Vector
from market_refinement import _constraints,_rectangle,_overlap,_clear

ROOT=Path(__file__).resolve().parents[1]


def _group_bounds(objects):
    points=[obj.matrix_world@Vector(p) for obj in objects for p in obj.bound_box]
    return [min(p[i] for p in points) for i in range(3)],[max(p[i] for p in points) for i in range(3)]


def _building_groups():
    groups={}
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        semantic=str(obj.get('semantic',''))
        if semantic.startswith('city/building/'):
            groups.setdefault(semantic.rsplit('/',1)[-1],[]).append(obj)
    return groups


def plan_layout():
    registry,occupied,humans=_constraints()
    refinements=json.loads((ROOT/'market_refinement_registry.json').read_text())
    for p in refinements['goods_racks']:
        occupied.append(('Rack_'+p['parent'],_rectangle(*p['center'],3.3,2,p['rotation'],.2)))
    for i,p in enumerate(refinements['foreground_cypresses']):
        occupied.append((f'ForegroundCypress_{i}',_rectangle(*p[:2],3.6,3.6,0,.2)))
    groups=_building_groups()
    for name,objects in groups.items():
        lo,hi=_group_bounds(objects)
        occupied.append((name,_rectangle((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,hi[0]-lo[0],hi[1]-lo[1],0,.25)))
    workshop_plans=[]
    for i,x in enumerate([-62,62]):
        poly=_rectangle(x,-117,18.6,9.8,math.pi,.25)
        conflicts=_clear(poly,occupied,humans)
        if conflicts:raise RuntimeError(f'Workshop_{i} candidate blocked: {conflicts}')
        occupied.append((f'Workshop_{i}',poly))
        workshop_plans.append({'id':f'Workshop_{i}','center':[x,-117],'full_projection':[18.6,9.8]})
    houses=[]
    candidates=[('SouthEast_01',-114,-147),('SouthEast_02',116,-145),
                ('North_00_04',-116,-174),('North_00_01',141,-181)]
    for i,(template,x,y) in enumerate(candidates):
        objects=groups[template]
        lo,hi=_group_bounds(objects)
        anchor=objects[0].location.copy()
        dx,dy=x-anchor.x,y-anchor.y
        poly=_rectangle((lo[0]+hi[0])/2+dx,(lo[1]+hi[1])/2+dy,hi[0]-lo[0],hi[1]-lo[1],0,.30)
        conflicts=_clear(poly,occupied,humans)
        if conflicts:raise RuntimeError(f'ForegroundHouse_{i} candidate blocked: {conflicts}')
        # All selected parcels are beyond the protected inner ellipse, east of the
        # river and within the continuous city ground plane's modeled rectangle.
        if min((px/128)**2+(py/105)**2 for px,py in poly)<=1:raise RuntimeError('House intrudes central ground reservation')
        if not all(-158<px<360 and -240<py<440 for px,py in poly):raise RuntimeError('House lacks city ground')
        occupied.append((f'ForegroundHouse_{i}',poly))
        houses.append({'id':f'ForegroundHouse_{i}','template':template,'center':[x,y],
                       'ground_support_z':-.035,'source_min_z':lo[2],
                       'full_projection':[hi[0]-lo[0],hi[1]-lo[1]],
                       'source_component_count':len(objects)})
    return {'workshops':workshop_plans,'houses':houses,'ground_human_anchors_checked':len(humans),
            'clearance_conflicts':[],'projection_method':'Full evaluated object bounding corners with0.25–0.30m clearance margins; SAT against occupied rectangles.'}


def relocate_foreground(api=None,spec=None):
    plan=plan_layout()
    groups=_building_groups()
    for item in plan['workshops']:
        objects=[o for o in bpy.context.scene.objects if str(o.get('semantic',''))=='market/'+item['id']]
        if not objects:raise RuntimeError('Missing complete workshop '+item['id'])
        old=objects[0].location.copy()
        delta=Vector((item['center'][0]-old.x,item['center'][1]-old.y,0))
        for obj in objects:obj.location+=delta
    collection=bpy.data.collections.get('City_Architecture')
    for item in plan['houses']:
        source=groups[item['template']]
        anchor=source[0].location.copy()
        delta=Vector((item['center'][0]-anchor.x,item['center'][1]-anchor.y,
                      item['ground_support_z']-item['source_min_z']))
        for original in source:
            obj=original.copy()
            obj.data=original.data
            obj.name=item['id']+'/'+original.data.materials[0].name
            collection.objects.link(obj)
            obj.location=original.location+delta
            obj['semantic']='city/building/'+item['id']
            obj['prototype']=item['template']
            obj['collision']='solid'
            obj['ground_support_z']=item['ground_support_z']
    return plan
