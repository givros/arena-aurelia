from pathlib import Path
import shutil, hashlib, json

ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena')
OUT=ROOT/'characters'
SKILL=Path('C:/Users/limou/.codex/skills/blender-lowpoly-character')
OUT.mkdir(parents=True,exist_ok=True)
(OUT/'specs').mkdir(exist_ok=True)
(OUT/'references').mkdir(exist_ok=True)
src=Path('C:/Users/limou/AppData/Local/Temp/codex-clipboard-618db799-bf8a-4459-92d1-01ea1dde98ce.png')
ref=OUT/'references'/'arena-primary.png'
shutil.copyfile(src,ref)
asset={'original_path':str(src),'copied_path':str(ref),'sha256':hashlib.sha256(ref.read_bytes()).hexdigest().upper()}
parts=[
 ('RomanTunic','roman_tunic','#C8B88D','cross_section','Loose short sleeved Roman tunic with a knee-length flared hem'),
 ('LeatherBelt','leather_belt','#533620','cross_section','Plain leather waist belt'),
 ('BronzeArmor','bronze_armor','#9D783E','cross_section','Bronze torso cuirass for explicitly requested guards and gladiators'),
 ('RomanHelmet','roman_helmet','#A28A52','cross_section','Open-faced bronze helmet'),
 ('HairCap','hair_cap','#362A20','cross_section','Simple close cropped dark hair'),
 ('RomanSandals','roman_sandals','#56402A','cross_section','Simple leather foot covering'),
 ('GuardShield','guard_shield','#83302A','rigid_closed','Deep red rectangular curved scutum'),
 ('GuardSpear','guard_spear','#766044','rigid_closed','Long spear carried by a guard'),
 ('GladiatorSword','gladiator_sword','#A8A99D','rigid_closed','Short gladiator sword'),
]
for name,gid,color,strategy,description in parts:
    spec={
      'garment_id':gid,'object_name':name,'mesh_name':name+'Mesh','garment_type':description,
      'garment_slot':gid,'construction_strategy':strategy,'reference_images':[str(ref)],'reference_assets':[asset],
      'image_interpretation':{'primary_view':'elevated arena district','available_views':['aerial oblique'],
        'body_coverage':[description],'start_landmarks':['body fitted local anatomical coordinates'],
        'end_landmarks':['role appropriate silhouette'],'fit':'rigid' if strategy=='rigid_closed' else 'loose',
        'silhouette_by_view':{'front':description,'back':'Plain symmetric continuation'},
        'openings':['neck, sleeve and hem openings'] if strategy!='rigid_closed' else [],
        'visible_details':['Earth coloured clothing, bronze/red guard group, crowd diversity'],
        'symmetry':'symmetric','colors':[color],'material_appearance':'Matte stylized low polygon materials',
        'direct_under':'CharacterBase','direct_above':'None',
        'visible_evidence':['Reference shows dense spectators, red and bronze guards and warm neutral citizens; user explicitly requests role clothing and accessories'],
        'assumptions':['Character-scale seam and fastening details cannot be resolved in the aerial reference; use plain garments and explicitly requested role accessories.'],
        'confidence':'medium'},
      'material':{'name':name+'Material','color':color,'roughness':0.83 if strategy!='rigid_closed' else 0.56,'metallic':0.6 if name in ['BronzeArmor','RomanHelmet','GladiatorSword'] else 0},
      'visibility_property':'show_'+gid,'layering':'CharacterBase < tunic < belt and armor; hair < helmet; held accessories outside body',
      'max_influences':4,'open_surface':strategy!='rigid_closed','thickness':0.002 if strategy!='rigid_closed' else 0,
      'builder_script':str(ROOT/'scripts'/'character_garment_builder.py'),
      'geometry_method':'Deterministic body-derived surface shell and measured cross-section or rigid accessory geometry',
    }
    (OUT/'specs'/(gid+'.json')).write_text(json.dumps(spec,indent=2),encoding='utf8')
(OUT/'reference_record.json').write_text(json.dumps(asset,indent=2))

template=(SKILL/'templates'/'custom_garment_builder.py').read_text()
geometry='''def build_geometry(source, spec):
    from mathutils import Vector
    name=spec['object_name']; vertices=[]; faces=[]
    def shell(predicate, offset):
        selected=[p for p in source.data.polygons if all(predicate(source.data.vertices[i].co) for i in p.vertices)]
        ids=sorted({i for p in selected for i in p.vertices})
        mapping={old:len(vertices)+i for i,old in enumerate(ids)}
        for i in ids:
            v=source.data.vertices[i]; vertices.append(tuple(v.co+v.normal*offset))
        faces.extend([[mapping[i] for i in p.vertices] for p in selected])
        return selected,mapping
    def box(center, size):
        offset=len(vertices); cx,cy,cz=center; sx,sy,sz=[v/2 for v in size]
        vertices.extend([(cx+x*sx,cy+y*sy,cz+z*sz) for x,y,z in [(-1,-1,-1),(-1,-1,1),(-1,1,1),(-1,1,-1),(1,-1,-1),(1,-1,1),(1,1,1),(1,1,-1)]])
        faces.extend([[offset+i for i in p] for p in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]])
    def cylinder_x(x0,x1,y,z,r0,r1,n=10):
        rings=[]
        for x,r in [(x0,r0),(x1,r1)]:
            ring=[]
            for i in range(n):
                angle=2*math.pi*i/n; ring.append(len(vertices)); vertices.append((x,y+math.cos(angle)*r,z+math.sin(angle)*r))
            rings.append(ring)
        bridge_loops(faces,*rings); faces.append(rings[0][::-1]); faces.append(rings[1])
    if name=='RomanTunic':
        selected,mapping=shell(lambda c:0.59<=c.z<=0.89 and abs(c.x)<=0.24,0.010)
        from collections import Counter
        counts=Counter(tuple(sorted((p.vertices[i],p.vertices[(i+1)%len(p.vertices)]))) for p in selected for i in range(len(p.vertices)))
        bottom=sorted({i for edge,n in counts.items() if n==1 for i in edge if source.data.vertices[i].co.z<0.62},key=lambda i:math.atan2(source.data.vertices[i].co.y,source.data.vertices[i].co.x))
        last=[mapping[i] for i in bottom]
        for z,rx,ry in [(0.51,0.132,0.098),(0.395,0.157,0.100)]:
            ring=[]
            for i in bottom:
                c=source.data.vertices[i].co; angle=math.atan2(c.y,c.x)
                ring.append(len(vertices)); vertices.append((math.cos(angle)*rx,math.sin(angle)*ry,z))
            bridge_loops(faces,last,ring); last=ring
    elif name=='LeatherBelt':
        a=ellipse_ring(vertices,(0,0.003),0.107,0.086,0.602,20)
        b=ellipse_ring(vertices,(0,0.003),0.104,0.083,0.630,20); bridge_loops(faces,a,b)
    elif name=='BronzeArmor':
        shell(lambda c:0.648<=c.z<=0.87 and abs(c.x)<=0.168,0.024)
    elif name=='RomanHelmet':
        shell(lambda c:c.z>=0.990,0.018)
    elif name=='HairCap':
        shell(lambda c:c.z>=0.997,0.006)
    elif name=='RomanSandals':
        shell(lambda c:c.z<0.036,0.005)
    elif name=='GuardShield':
        # Length along the T-pose arm becomes vertical after the arm lowers.
        box((0.46,-0.081,0.830),(0.38,0.026,0.235))
        box((0.46,-0.100,0.830),(0.048,0.024,0.048))
    elif name=='GuardSpear':
        cylinder_x(-1.17,0.22,-0.010,0.833,0.007,0.007)
        cylinder_x(-1.31,-1.17,-0.010,0.833,0.0006,0.025)
    elif name=='GladiatorSword':
        box((-0.63,-0.010,0.833),(0.29,0.015,0.035))
        box((-0.48,-0.010,0.833),(0.035,0.020,0.106))
        cylinder_x(-0.470,-0.413,-0.010,0.833,0.013,0.013)
    else: raise ValueError(name)
    return vertices, faces
'''
start=template.index('def build_geometry('); end=template.index('\ndef file_sha256',start)
template=template[:start]+geometry+template[end:]
insertion='''    rigid_bone={'RomanHelmet':'head','HairCap':'head','GuardShield':'hand.L','GuardSpear':'hand.R','GladiatorSword':'hand.R'}.get(name)
    if rigid_bone:
        garment.vertex_groups.clear()
        garment.vertex_groups.new(name=rigid_bone).add(list(range(len(mesh.vertices))),1.0,'REPLACE')

'''
template=template.replace('    if spec["open_surface"]:\n        solidify',insertion+'    if spec["open_surface"]:\n        solidify')
builder_path=ROOT/'scripts'/'character_garment_builder.py'
if not builder_path.exists():
    builder_path.write_text(template,encoding='utf8')
else:
    print('Preserving revised, validated custom builder:',builder_path)
print('Prepared',len(parts),'Roman components')
