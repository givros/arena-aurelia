"""Read-only final Blender audit for city structure, shared geometry and support.

Run only after the source is final:
blender --background --python city_final_audit.py -- --source <final.blend>
This script never saves or modifies the supplied .blend. It writes evidence JSON.
"""
import argparse
import bpy
import collections
import hashlib
import json
import math
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree


ROOT=Path(__file__).resolve().parents[1]


def _arguments():
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True,type=Path)
    parser.add_argument('--output',type=Path,default=ROOT/'comparisons'/'city'/'city_final_audit.json')
    return parser.parse_args(args)


def _support_objects():
    records=[]
    cache={}
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        owners=[c.name for c in obj.users_collection]
        if not (any(n.startswith('City_') or n=='Ground' for n in owners) or
                obj.name.upper().startswith('TEMPLE/')):continue
        if obj.get('collision','solid') in ['none',False]:continue
        mesh=obj.data
        key=mesh.as_pointer()
        if key not in cache:
            cache[key]=BVHTree.FromPolygons([v.co.copy() for v in mesh.vertices],
                                          [tuple(p.vertices) for p in mesh.polygons],all_triangles=False)
        matrix=obj.matrix_world.copy()
        inverse=matrix.inverted_safe()
        bounds=[matrix@Vector(v) for v in obj.bound_box]
        lo=[min(v[i] for v in bounds) for i in range(3)]
        hi=[max(v[i] for v in bounds) for i in range(3)]
        records.append({'name':obj.name,'tree':cache[key],'matrix':matrix,'inverse':inverse,
                        'lo':lo,'hi':hi,'semantic':obj.get('semantic','')})
    return records,len(cache)


def _support(records,x,y,expected_z):
    origin=Vector((x,y,expected_z+.65))
    direction=Vector((0,0,-1))
    hits=[]
    for entry in records:
        lo,hi=entry['lo'],entry['hi']
        if x<lo[0]-.01 or x>hi[0]+.01 or y<lo[1]-.01 or y>hi[1]+.01:continue
        if hi[2]<expected_z-5 or lo[2]>origin.z:continue
        inv=entry['inverse']
        local_origin=inv@origin
        local_direction=inv.to_3x3()@direction
        scale=local_direction.length
        if scale<1e-8:continue
        position,normal,face,distance=entry['tree'].ray_cast(local_origin,local_direction/scale,5.7*scale)
        if position is None:continue
        world=entry['matrix']@position
        if world.z<=origin.z+.001:
            hits.append((world.z,entry['name'],entry['semantic']))
    if not hits:return {'height':None,'error':None,'object':None}
    z,name,semantic=max(hits,key=lambda h:h[0])
    return {'height':round(z,5),'error':round(z-expected_z,5),'object':name,'semantic':semantic}


def _route(records,name,points):
    samples=[]
    for x,y,z in points:
        hit=_support(records,x,y,z)
        sample={'point':[round(x,5),round(y,5),round(z,5)],**hit}
        sample['within_tolerance']=hit['height'] is not None and abs(hit['error'])<=.085
        samples.append(sample)
    missing=[i for i,s in enumerate(samples) if s['height'] is None]
    wrong=[i for i,s in enumerate(samples) if not s['within_tolerance']]
    return {'name':name,'sample_count':len(samples),'passed':not wrong,
            'missing_support_indices':missing,'failed_indices':wrong,'samples':samples}


def _bridge_height(x):
    if x<-232.5 or x>-127.5:return 0
    if x<-212.5:return (x+232.5)*6.05/20
    if x<=-147.5:return 6.05
    return (-127.5-x)*6.05/20


def _temple_height(y):
    if y<112.2:return 0
    if y<133.0:return min(8.0,(math.floor((y-112.2+1e-7)/.65)+1)*.25)
    if y<145.8:return min(12.0,8+(math.floor((y-133.0+1e-7)/.8)+1)*.25)
    if y<147.0:return 12.0
    if y<156.1:return 12.26
    if y<156.7:return 12.46
    return 12.66


def _geometry_evidence():
    objects=[o for o in bpy.context.scene.objects if o.type=='MESH' and
             any(c.name.startswith('City_') for c in o.users_collection)]
    meshes={o.data.as_pointer():o.data for o in objects}
    usage=collections.Counter(o.data.as_pointer() for o in objects)
    rows=[]
    total_instance_triangles=0
    unique_triangles=0
    finite=True
    for key,mesh in meshes.items():
        triangles=sum(max(0,len(p.vertices)-2) for p in mesh.polygons)
        unique_triangles+=triangles
        total_instance_triangles+=triangles*usage[key]
        finite=finite and all(math.isfinite(float(c)) for v in mesh.vertices for c in v.co)
        rows.append({'mesh':mesh.name,'instances':usage[key],'vertices':len(mesh.vertices),
                     'polygons':len(mesh.polygons),'triangles':triangles,
                     'uv_layers':len(mesh.uv_layers),
                     'materials':[m.name for m in mesh.materials if m]})
    materials={m.name:m for o in objects for m in o.data.materials if m}
    maps=[]
    for name,m in materials.items():
        images=[n.image.filepath for n in m.node_tree.nodes if n.type=='TEX_IMAGE' and n.image] if m.use_nodes else []
        if images:maps.append({'material':name,'images':images,'repeat_meters':m.get('texture_repeat_meters')})
    return {'mesh_objects':len(objects),'unique_meshes':len(meshes),
            'shared_meshes':sum(1 for n in usage.values() if n>1),
            'unique_triangles':unique_triangles,'represented_instance_triangles':total_instance_triangles,
            'sharing_saves_duplicate_geometry':total_instance_triangles-unique_triangles,
            'all_vertices_finite':finite,'all_meshes_have_uvs':all(len(m.uv_layers)>0 for m in meshes.values()),
            'all_meshes_have_semantics':all('semantic' in o and 'collision' in o for o in objects),
            'surface_maps':maps,'meshes':rows}


def main():
    args=_arguments()
    source=args.source.resolve(strict=True)
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source))
    records,bvh_count=_support_objects()
    bridge=[(-233+i*.2,105,_bridge_height(-233+i*.2)) for i in range(536)]
    # Deliberately avoid landing exactly on shared tread edges, which are not a
    # stable numerical comparison point across Blender and exported float32 data.
    temple=[(10,110.037+i*.10,_temple_height(110.037+i*.10)) for i in range(561)]
    routes=[_route(records,'bridge_west_to_east',bridge),_route(records,'temple_main_stair_portico_cella',temple)]
    # Four explicit samples around each connection prevent broad sampling from hiding gaps.
    connections=[]
    for y in [132.90,133.05,145.75,145.90,146.50,147.05,150,154,156.05,156.30,156.65,156.85,158]:
        z=_temple_height(y)
        connections.append({'point':[10,y,z],**_support(records,10,y,z)})
    report={
        'source':str(source),'source_sha256':source_hash,
        'read_only':True,'source_saved':False,
        'evidence_scope':'Blender source structure and exact triangle support only; runtime traversal is independently verified by the viewer audit.',
        'coordinates':{'blender':'X east,Y north,Z up','runtime':'x=X,y=Z,z=-Y'},
        'geometry':_geometry_evidence(),'support_bvh_unique_meshes':bvh_count,
        'routes':routes,'temple_connection_samples':connections,
        'bridge_design':{'deck_top':6.05,'deck_width':13,'minimum_pier_clearance':10.7,
                         'approach_rise':6.05,'approach_run':20,'slope':.3025},
        'temple_design':{'lower_steps':32,'lower_rise':.25,'lower_run':.65,
                         'upper_steps':16,'upper_rise':.25,'upper_run':.8,
                         'landing_top':12.0,'portico_top':12.26,'threshold_top':12.46,'cella_top':12.66,
                         'required_last_stair_landing_y':[145.7,147.3],
                         'required_threshold_y':[156.1,156.8]},
        'route_support_passed':all(r['passed'] for r in routes),
        'reference_evidence':['references/primary_reference.png','renders/checkpoint_09_refined.png','renders/checkpoint_10_reference.png']}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2))
    print(json.dumps({'source':str(source),'output':str(args.output),'route_support_passed':report['route_support_passed'],
                      'routes':[{'name':r['name'],'failed_samples':len(r['failed_indices'])} for r in routes],
                      'city_mesh_objects':report['geometry']['mesh_objects'],'unique_meshes':report['geometry']['unique_meshes']}))


if __name__=='__main__':main()
