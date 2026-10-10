"""Add portable wares to exact animated GLB, preserving its original binary payload.

Run with Blender background --python. This uses Blender's math only and never
opens/saves the canonical character or arena source. Added rigid meshes are
bone children with explicit straps; all body/skin/animation accessors are kept.
"""
from pathlib import Path
import json,struct,hashlib,math,copy
from mathutils import Matrix,Vector,Quaternion
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'characters/runtime'
def sha(data):return hashlib.sha256(data).hexdigest()
raw=(OUT/'animated-citizen.glb').read_bytes();n=struct.unpack_from('<I',raw,12)[0]
base=json.loads(raw[20:20+n]);binary=raw[28+n:]
def world_matrices(g):
    result={}
    def walk(i,parent):
        node=g['nodes'][i]
        if 'matrix' in node:local=Matrix([node['matrix'][j:j+4] for j in range(0,16,4)]).transposed()
        else:
            r=node.get('rotation',[0,0,0,1]);local=Matrix.LocRotScale(Vector(node.get('translation',[0,0,0])),Quaternion((r[3],*r[:3])),Vector(node.get('scale',[1,1,1])))
        result[i]=parent@local
        for child in node.get('children',[]):walk(child,result[i])
    for i in g['scenes'][g.get('scene',0)]['nodes']:walk(i,Matrix.Identity(4))
    return result
world=world_matrices(base)
parent=next(i for i,n in enumerate(base['nodes']) if n['name']=='spine1')
inverse=world[parent].inverted();normal_matrix=inverse.to_3x3().inverted().transposed()
reports=[]
for role in ['merchant','porter']:
    g=copy.deepcopy(base);blob=bytearray(binary);parts={}
    def tri(material,a,b,c):
        a,b,c=Vector(a),Vector(b),Vector(c);normal=(b-a).cross(c-a).normalized()
        part=parts.setdefault(material,{'positions':[],'normals':[]})
        for p in [a,b,c]:
            part['positions'].append(tuple(inverse@p));part['normals'].append(tuple((normal_matrix@normal).normalized()))
    def quad(material,a,b,c,d):tri(material,a,b,c);tri(material,a,c,d)
    def box(material,center,size):
        x,y,z=center;dx,dy,dz=[v/2 for v in size]
        p=[(x+sx*dx,y+sy*dy,z+sz*dz) for sx,sy,sz in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
        for a,b,c,d in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]:quad(material,p[a],p[b],p[c],p[d])
    def beam(material,a,b,width,depth):
        a,b=Vector(a),Vector(b);direction=(b-a).normalized();side=direction.cross(Vector((0,0,1)))
        if side.length<.1:side=direction.cross(Vector((0,1,0)))
        side.normalize();other=direction.cross(side).normalized();p=[]
        for end in [a,b]:
            p.extend([end+side*s*width/2+other*t*depth/2 for s,t in [(-1,-1),(1,-1),(1,1),(-1,1)]])
        for i,j,k,l in [(0,3,2,1),(4,5,6,7),(0,1,5,4),(3,7,6,2),(0,4,7,3),(1,2,6,5)]:quad(material,p[i],p[j],p[k],p[l])
    def vessel(material,center,profile,segments=10):
        x,y,z=center
        rings=[[(x+r*math.cos(i*math.tau/segments),y+h,z+r*math.sin(i*math.tau/segments)) for i in range(segments)] for h,r in profile]
        for bottom,top in zip(rings,rings[1:]):
            for i in range(segments):quad(material,bottom[i],bottom[(i+1)%segments],top[(i+1)%segments],top[i])
        for i in range(1,segments-1):tri(material,rings[0][0],rings[0][i+1],rings[0][i]);tri(material,rings[-1][0],rings[-1][i],rings[-1][i+1])
    if role=='merchant':
        # A light shoulder-slung tray; hands remain free for the authored Walk clip.
        box('reed',(0,.94,.285),(.49,.025,.32))
        for y in [.965,1.005,1.045,1.085]:
            box('reed',(0,y,.125),(.51,.018,.017));box('reed',(0,y,.445),(.51,.018,.017))
            for x in [-.245,.245]:box('reed',(x,y,.285),(.018,.018,.32))
        for x in [-.245,-.17,-.085,0,.085,.17,.245]:
            for z in [.125,.445]:box('reed',(x,1.02,z),(.013,.17,.014))
        for x in [-.16,.16]:
            beam('leather',(x,1.095,.135),(x,1.49,.07),.022,.009)
            beam('leather',(x,1.49,.07),(x,1.46,-.09),.022,.009)
            beam('leather',(x,1.46,-.09),(x,1.05,-.105),.022,.009)
        for i,(x,z) in enumerate([(-.135,.28),(.025,.28),(.145,.26),(-.075,.38),(.11,.38)]):
            vessel('bread' if i<3 else 'fruit',(x,.972,z),[(0,.043),(.035,.068),(.07,.034)],8)
        vessel('pottery',(-.14,.972,.18),[(0,.032),(.06,.045),(.12,.022),(.13,.027)],10)
    else:
        # A tapered reed pack with two actual shoulder straps and rolled goods.
        for h in range(9):
            y=.94+h*.064;r=.18+.05*h/8
            segments=12
            for i in range(segments):
                a=i*math.tau/segments;b=(i+1)*math.tau/segments
                beam('reed',(r*math.cos(a),y,-.29+r*.70*math.sin(a)),(r*math.cos(b),y,-.29+r*.70*math.sin(b)),.016,.02)
        for i in range(12):
            a=i*math.tau/12
            beam('reed',(.18*math.cos(a),.93,-.29+.126*math.sin(a)),(.23*math.cos(a),1.49,-.29+.161*math.sin(a)),.018,.018)
        box('reed',(0,.94,-.29),(.32,.025,.24))
        for x in [-.14,.14]:
            beam('leather',(x,1.48,-.26),(x,1.52,-.07),.038,.015)
            beam('leather',(x,1.52,-.07),(x,1.40,.105),.038,.015)
            beam('leather',(x,1.40,.105),(x,1.02,.09),.038,.015)
            beam('leather',(x,1.02,.09),(x,.95,-.24),.038,.015)
        vessel('canvas',(-.085,1.1,-.285),[(0,.065),(.45,.065),(.52,.055)],10)
        vessel('pottery',(.095,1.1,-.28),[(0,.06),(.25,.073),(.4,.036),(.44,.043)],10)
    def accessor(values,kind):
        while len(blob)%4:blob.append(0)
        offset=len(blob);flat=[v for row in values for v in row];blob.extend(struct.pack('<'+'f'*len(flat),*flat))
        view=len(g['bufferViews']);g['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(flat)*4,'target':34962})
        acc={'bufferView':view,'componentType':5126,'count':len(values),'type':kind}
        if kind=='VEC3':acc.update(min=[min(v[k] for v in values) for k in range(3)],max=[max(v[k] for v in values) for k in range(3)])
        index=len(g['accessors']);g['accessors'].append(acc);return index
    colors={'reed':[.29,.15,.045,1],'leather':[.08,.031,.01,1],'bread':[.55,.27,.08,1],'fruit':[.28,.045,.025,1],'pottery':[.43,.17,.07,1],'canvas':[.31,.36,.27,1]}
    accessory_triangles=0
    for material,part in parts.items():
        mi=len(g['materials']);g['materials'].append({'name':'StreetWares_'+material,'doubleSided':False,'pbrMetallicRoughness':{'baseColorFactor':colors[material],'roughnessFactor':.87,'metallicFactor':0}})
        pi=accessor(part['positions'],'VEC3');ni=accessor(part['normals'],'VEC3')
        mesh=len(g['meshes']);g['meshes'].append({'name':role.title()+'_'+material,'primitives':[{'attributes':{'POSITION':pi,'NORMAL':ni},'material':mi,'mode':4}]})
        node=len(g['nodes']);g['nodes'].append({'name':'StreetWares_'+role+'_'+material,'mesh':mesh,'extras':{'source':'character_street_accessories.py','carrier':'spine1','canonicalBodyUnmodified':True}})
        g['nodes'][parent].setdefault('children',[]).append(node);accessory_triangles+=len(part['positions'])//3
    g['buffers'][0]['byteLength']=len(blob)
    while len(blob)%4:blob.append(0)
    js=json.dumps(g,separators=(',',':')).encode();js+=b' '*((-len(js))%4)
    output=struct.pack('<4sII',b'glTF',2,12+8+len(js)+8+len(blob))+struct.pack('<II',len(js),0x4E4F534A)+js+struct.pack('<II',len(blob),0x004E4942)+blob
    path=OUT/('animated-'+role+'.glb');path.write_bytes(output)
    assert bytes(blob[:len(binary)])==binary
    assert g['animations']==base['animations'] and g['skins']==base['skins']
    assert g['meshes'][:len(base['meshes'])]==base['meshes']
    reports.append({'asset':path.name,'sha256':sha(output),'bytes':len(output),'canonicalAsset':'animated-citizen.glb','canonicalAssetSHA256':sha(raw),
       'originalBinaryPayloadUnchanged':True,'bodyGarmentGeometryAndSkinAccessorsUnchanged':True,'animationsUnchanged':True,
       'originalVisibleTriangles':5002,'accessoryTriangles':accessory_triangles,'totalTriangles':5002+accessory_triangles,
       'attachmentBone':'spine1','attachment':'Torso straps support front basket' if role=='merchant' else 'Two shoulder straps support back basket',
       'compression':False,'clips':[a['name'] for a in g['animations']]})
(ROOT/'characters/street_accessory_assets.json').write_text(json.dumps({'passed':True,'assets':reports},indent=2))
print('STREET_ACCESSORIES',json.dumps(reports),flush=True)
