"""Lossless float32 evaluated scene transfer, shared mesh arrays and instance transforms."""
import bpy,sys,json,struct,hashlib,math,shutil,os
from pathlib import Path
from mathutils import Matrix,Vector
R=Path(__file__).resolve().parents[1]
path=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else R/'Aurelia_Arena.blend'
bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.view_layer.update()
OUT=R/'viewer/public/assets';OUT.mkdir(parents=True,exist_ok=True)
C=Matrix(((1,0,0,0),(0,0,1,0),(0,-1,0,0),(0,0,0,1)));Ci=C.inverted()
blob=bytearray();meshes=[];instances=[];materials=[];matids={};meshcache={};dg=bpy.context.evaluated_depsgraph_get()
def chunk(values,fmt):
    while len(blob)%4:blob.append(0)
    off=len(blob);blob.extend(struct.pack('<'+str(len(values))+fmt,*values));return {'offset':off,'count':len(values)}
def matid(m):
    name=m.name if m else 'Default'
    if name in matids:return matids[name]
    i=len(materials);matids[name]=i;d={'id':i,'name':name,'color':[.55,.45,.3],'roughness':.8,'metalness':0}
    if m:
        d['color']=list(m.diffuse_color[:3]);p=m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
        if p:
            d['color']=list(p.inputs['Base Color'].default_value[:3]);d['roughness']=p.inputs['Roughness'].default_value;d['metalness']=p.inputs['Metallic'].default_value;d['opacity']=p.inputs['Alpha'].default_value
            if p.inputs['Emission Strength'].default_value>0:d['emissive']=[v*p.inputs['Emission Strength'].default_value for v in p.inputs['Emission Color'].default_value[:3]]
        for field in ['map','normalMap','roughnessMap','bumpMap']:
            if m.get(field):
                fn=m[field];shutil.copy2(R/'textures'/fn,OUT/fn);d[field]=fn
                if field=='map':d['color']=[1,1,1]
        if m.get('bumpScale'):d['bumpScale']=m['bumpScale']
    materials.append(d);return i
total=0;normals_bad=0
for obj in sorted(bpy.context.scene.objects,key=lambda o:o.name):
    if obj.type!='MESH' or obj.hide_render or obj.get('runtime_skip',False):continue
    matrix=C@obj.matrix_world@Ci
    key=(obj.data.as_pointer(),tuple(m.name if m else '' for m in obj.data.materials),str([m.type for m in obj.modifiers]))
    if key not in meshcache:
        ev=obj.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();uv=me.uv_layers.active;parts=[]
        # Retain corner normals, UV seams and all source triangles without quantization.
        for slot in sorted(set(t.material_index for t in me.loop_triangles)):
            ps=[];ns=[];uvs=[];indices=[];dedup={}
            for tri in me.loop_triangles:
                if tri.material_index!=slot:continue
                for li in tri.loops:
                    vi=me.loops[li].vertex_index;v=me.vertices[vi].co;n=me.corner_normals[li].vector
                    if n.length<.5 or not all(math.isfinite(t) for t in n):normals_bad+=1;n=tri.normal
                    tx=tuple(uv.data[li].uv) if uv else (0.,0.)
                    vk=(vi,tuple(n),tx)
                    if vk not in dedup:
                        dedup[vk]=len(ps)//3;ps.extend([v.x,v.z,-v.y]);ns.extend([n.x,n.z,-n.y]);uvs.extend(tx)
                    indices.append(dedup[vk])
            if not indices:continue
            mi=matid(me.materials[slot] if slot<len(me.materials) else None);ident=len(meshes)
            meshes.append({'id':ident,'name':me.name,'positions':chunk(ps,'f'),'normals':chunk(ns,'f'),'uvs':chunk(uvs,'f'),'indices':chunk(indices,'I'),'material':mi})
            parts.append((ident,len(indices)//3))
        ev.to_mesh_clear();meshcache[key]=parts
    for ident,tris in meshcache[key]:
        instances.append({'id':obj.name,'mesh':ident,'matrix':[matrix[row][col] for col in range(4) for row in range(4)],'semantic':obj.get('semantic',obj.name),'collision':obj.get('collision','none')})
        total+=tris
def pos(p):return [p[0],p[2],-p[1]]
spec=json.loads((R/'scene_spec.json').read_text());cameras={}
for ob in bpy.context.scene.objects:
    if ob.type=='CAMERA':
        target=ob.location+ob.rotation_euler.to_matrix()@Vector((0,0,-1))*30
        cameras[ob.name.replace('CAM_','')]={'position':pos(ob.location),'target':pos(target),'fov':math.degrees(ob.data.angle_y),'lens':ob.data.lens,'sensorWidth':ob.data.sensor_width,'sensorFit':ob.data.sensor_fit}
nav={'spawn':pos((0,-119,1.72)),'eyeHeight':1.72,'radius':.32,'stepHeight':.38,'destinations':[
 {'id':'plaza','label':'Festival plaza','position':pos((0,-119,1.72)),'lookAt':pos((0,-80,16))},
 {'id':'sands','label':'The sands','position':pos((15,-22,2.12)),'lookAt':pos((0,55,16))},
 {'id':'cavea','label':'Upper terraces','position':pos((72.2,55.9,33.024)),'lookAt':pos((0,0,8))},
 {'id':'hypogeum','label':'The hypogeum','position':pos((34,0,-3.88)),'lookAt':pos((0,0,-3.8))},
 {'id':'imperial','label':'Imperial loggia','position':pos((0,58,20.44)),'lookAt':pos((0,0,5))},
 {'id':'river','label':'River bridge','position':pos((-177,105,7.77)),'lookAt':pos((-198,105,8))},
 {'id':'temple','label':'Temple approach','position':pos((10,106,1.72)),'lookAt':pos((10,142,20))}
], 'routes':[],'lights':[]}
nav['bounds']={'min':[-315,-435],'max':[355,235]}
street_layout=R/'street_life_layout.json'
if street_layout.exists():
    street=json.loads(street_layout.read_text())
    for destination in street.get('destinations',[]):
        nav['destinations'].append({'id':destination['id'],'label':destination['label'],
            'position':pos(destination['position']),'lookAt':pos(destination['lookAt'])})
    nav['routes']=[dict(route,points=[pos(p) for p in route['points']]) for route in street.get('routes',[])]
    nav['streetLifeLayout']='street_life_layout.json'
    nav['streetLifeLayoutSHA256']=hashlib.sha256(street_layout.read_bytes()).hexdigest()
    shutil.copy2(street_layout,OUT/'street_life_layout.json')
district_layout=R/'district_life_layout.json'
if district_layout.exists():
    district=json.loads(district_layout.read_text())
    for destination in district.get('destinations',[]):
        nav['destinations'].append({'id':destination['id'],'label':destination['label'],
            'position':pos(destination['position']),'lookAt':pos(destination['lookAt'])})
    nav['routes'].extend(dict(route,points=[pos(p) for p in route['points']]) for route in district.get('routes',[]))
    nav['districtLifeLayout']='district_life_layout.json'
    nav['districtLifeLayoutSHA256']=hashlib.sha256(district_layout.read_bytes()).hexdigest()
    shutil.copy2(district_layout,OUT/'district_life_layout.json')
interior_layout=R/'arena_interior_life_layout.json'
if interior_layout.exists():
    interior=json.loads(interior_layout.read_text())
    for view in interior.get('cameraCandidates',[]):
        nav['destinations'].append({'id':view['id'],
            'label':'Arena gallery' if 'gallery' in view['id'] else 'Backstage passage',
            'position':pos(view['position']),'lookAt':pos(view['target'])})
    nav['arenaInteriorLifeLayout']='arena_interior_life_layout.json'
    nav['arenaInteriorLifeLayoutSHA256']=hashlib.sha256(interior_layout.read_bytes()).hexdigest()
    shutil.copy2(interior_layout,OUT/'arena_interior_life_layout.json')
civic_layout=R/'civic_court_layout.json'
if civic_layout.exists() and bpy.context.scene.get('civic_court_revision'):
    civic=json.loads(civic_layout.read_text())
    assert civic['revision']==bpy.context.scene['civic_court_revision'],'Civic court layout differs from applied source'
    nav['civicCourtLayout']=civic_layout.name
    nav['civicCourtLayoutSHA256']=hashlib.sha256(civic_layout.read_bytes()).hexdigest()
    shutil.copy2(civic_layout,OUT/civic_layout.name)
    for destination in civic.get('destinations',[]):
        nav['destinations'].append({'id':destination['id'],'label':destination['label'],
            'position':pos(destination['position']),'lookAt':pos(destination['lookAt'])})
    nav['routes'].extend(dict(route,points=[pos(p) for p in route['points']]) for route in civic.get('routes',[]))
if bpy.context.scene.get('master_city_reflow'):
    master_layout=R/'master_world_layout.json'
    master_audit=json.loads((R/'comparisons/master_world_geometry_audit.json').read_text())
    master_hash=hashlib.sha256(master_layout.read_bytes()).hexdigest()
    assert master_audit['layout_sha256']==master_hash,'Applied city layout differs from its source audit'
    nav['masterWorldLayout']=master_layout.name
    nav['masterWorldLayoutSHA256']=master_hash
    shutil.copy2(master_layout,OUT/master_layout.name)
if bpy.context.scene.get('master_world_boundary'):
    boundary_path=R/'master_world_boundary.json'
    boundary_bytes=boundary_path.read_bytes();boundary=json.loads(boundary_bytes)
    geometry_path=R/'comparisons/world_boundary_geometry.json'
    geometry_bytes=geometry_path.read_bytes();boundary_geometry=json.loads(geometry_bytes)
    boundary_hash=hashlib.sha256(boundary_bytes).hexdigest()
    assert boundary_geometry['passed'] and boundary_geometry['boundarySHA256']==boundary_hash,'Boundary frames do not match the applied source enclosure'
    for field,file,data in [('masterWorldBoundary',boundary_path,boundary_bytes),('worldBoundaryGeometry',geometry_path,geometry_bytes)]:
        nav[field]=file.name;nav[field+'SHA256']=hashlib.sha256(data).hexdigest()
        shutil.copy2(file,OUT/file.name)
    nav['boundaryChecks']=[]
    def outward(center,rotation):
        n=(-math.sin(rotation),math.cos(rotation))
        return n if n[0]*center[0]+n[1]*(center[1]-90)>0 else (-n[0],-n[1])
    def boundary_check(ident,center,rotation,prefix):
        n=outward(center,rotation)
        start=(center[0]-n[0]*5.5,center[1]-n[1]*5.5,1.685)
        target=(center[0]+n[0]*5.5,center[1]+n[1]*5.5,1.685)
        nav['boundaryChecks'].append({'id':ident,'start':pos(start),'towards':pos(target),'expectedBarrierContains':prefix})
    for gate in boundary['gates']:
        if not gate.get('closed'):continue
        frame=boundary_geometry['closedGates'][gate['id']]
        boundary_check(gate['id'],frame['center'],frame['rotation'],'CITYGATE/'+gate['id']+'/Closed oak leaf')
    points=boundary['wall']['centerline']
    for index in [1,10,18,22,29,35]:
        a,b=points[index],points[(index+1)%len(points)]
        center=((a[0]+b[0])/2,(a[1]+b[1])/2)
        boundary_check('CityWall_'+str(index),center,math.atan2(b[1]-a[1],b[0]-a[0]),f'CITYWALL/Span{index:02}_')
bank_report=None
if bpy.context.scene.get('watergate_boundary_revision'):
    bank_path=R/'watergate_boundary_revision.json';bank_bytes=bank_path.read_bytes()
    bank_hash=hashlib.sha256(bank_bytes).hexdigest()
    bank_report=json.loads((R/'comparisons/watergate_boundary_integration.json').read_text())
    assert bank_report['passed'] and not bank_report['changedExistingComponents']
    assert bank_report['cameraUnchanged'] and bank_report['populationUnchanged']
    assert bank_report['sourceSHA256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert bank_report['authoritySHA256']==bank_hash==bpy.context.scene.get('watergate_boundary_authority_sha256')
    nav['watergateBoundaryRevision']=bank_path.name
    nav['watergateBoundaryRevisionSHA256']=bank_hash
    shutil.copy2(bank_path,OUT/bank_path.name)
    for gate in json.loads(bank_bytes)['gates']:
        check=gate['testPath']
        nav.setdefault('boundaryChecks',[]).append({'id':check['id'],'start':pos(check['start']),
            'towards':pos(check['towards']),'expectedBarrierContains':check['expectedBarrierContains']})
review_report_path=R/'comparisons/district_review_camera_integration.json'
if review_report_path.exists():
    review_report=json.loads(review_report_path.read_text())
    reviewed_source=review_report.get('sourceSHA256')
    if reviewed_source==hashlib.sha256(path.read_bytes()).hexdigest() or (bank_report and bank_report['beforeSourceSHA256']==reviewed_source):
        review_path=R/'district_review_views.json';review_bytes=review_path.read_bytes()
        assert review_report['passed'] and review_report['cameraAuthoritySHA256']==hashlib.sha256(review_bytes).hexdigest(),'Reviewed camera authority differs from saved source'
        review=json.loads(review_bytes)
        destinations={destination['id']:destination for destination in nav['destinations']}
        nav['reviewedDestinations']=[]
        for ident,view in review['cameras'].items():
            if ident not in destinations:continue
            assert not view.get('actualSupportPending',True) and not view['headroom']['hits'],'Reviewed arrival lacks source clearance'
            destinations[ident]['position']=pos(view['position']);destinations[ident]['lookAt']=pos(view['target'])
            nav['reviewedDestinations'].append(ident)
        nav['reviewViewAuthority']=review_path.name
        nav['reviewViewAuthoritySHA256']=hashlib.sha256(review_bytes).hexdigest()
        shutil.copy2(review_path,OUT/review_path.name)
for o in bpy.context.scene.objects:
    if o.type=='LIGHT' and o.data.type=='POINT':nav['lights'].append({'position':pos(o.location),'color':list(o.data.color),'intensity':o.data.energy*.12,'distance':o.get('distance',22)})
doc={'version':1,'binary':'environment.bin','source':path.name,'sourceHash':hashlib.sha256(path.read_bytes()).hexdigest(),'units':'meters','sourceAxes':'Blender Z up transformed to Three Y up','meshes':meshes,'materials':materials,'instances':instances,'cameras':cameras,'navigation':nav,'inventory':{'objects':len(instances),'uniqueMeshes':len(meshes),'sourceVisibleTriangles':total,'invalidNormals':normals_bad}}
crowd=R/'characters/runtime/crowd_manifest.json'
if crowd.exists() and bpy.context.scene.get('population_instances',0):
    crowd_doc=json.loads(crowd.read_text())
    for record in crowd_doc.get('districtLife',{}).get('layouts',[]):
        layout_path=R/record['path']
        layout_hash=hashlib.sha256(layout_path.read_bytes()).hexdigest()
        assert layout_hash==record['sha256'],'Population layout provenance differs: '+record['path']
        if record['path']=='master_spine_life_layout.json':
            nav['masterSpineLifeLayout']=layout_path.name
            nav['masterSpineLifeLayoutSHA256']=layout_hash
            shutil.copy2(layout_path,OUT/layout_path.name)
    nav['crowdManifest']='characters/crowd_manifest.json';(OUT/'characters').mkdir(exist_ok=True)
    for f in (R/'characters/runtime').glob('*.glb'):shutil.copy2(f,OUT/'characters'/f.name)
    shutil.copy2(crowd,OUT/'characters/crowd_manifest.json')
    doc['inventory']['characterInstances']=bpy.context.scene['population_instances'];doc['inventory']['sourceCharacterTriangles']=bpy.context.scene['population_triangle_instances']
(OUT/'environment.bin').write_bytes(blob);(OUT/'environment.json').write_text(json.dumps(doc,separators=(',',':')),encoding='utf8')
(R/'source_transfer_validation.json').write_text(json.dumps({'source':doc['source'],'sourceHash':doc['sourceHash'],'meshInstances':len(instances),'uniqueMaterialMeshes':len(meshes),'visibleTriangles':total,'invalidNormalsRepaired':normals_bad,'binaryBytes':len(blob),'preservation':'Full evaluated positions, corner normals, UVs, triangles, transforms and portable material assignments; no compression, LOD or decimation.','binarySHA256':hashlib.sha256(blob).hexdigest()},indent=2))
print('EXPORTED',len(instances),'instances',len(meshes),'unique meshes',total,'triangles',len(blob),'bytes',flush=True)
