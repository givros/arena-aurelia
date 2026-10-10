"""Put immutable human scale above all animated nodes without changing clip/mesh data."""
from pathlib import Path
import json,struct,hashlib
ROOT=Path(__file__).resolve().parents[1]/'characters';SCALE=1.8/1.0514808893203735
def normalize_animated_glb(path):
    path=Path(path);data=path.read_bytes();size,kind=struct.unpack_from('<II',data,12)
    scene=json.loads(data[20:20+size]);tail=data[20+size:]
    if any(n.get('name')=='CanonicalHumanScale' for n in scene['nodes']):return
    original=[n for n in scene['nodes'] if n.get('name')=='CharacterRig']
    assert len(original)==1
    node=original[0];node['scale']=[1,1,1]
    node['translation']=[v/SCALE for v in node.get('translation',[0,0,0])]
    for display in scene['scenes']:
        roots=list(display.get('nodes',[]));index=len(scene['nodes'])
        scene['nodes'].append({'name':'CanonicalHumanScale','scale':[SCALE]*3,'children':roots,
          'extras':{'purpose':'Uniform runtime human-height normalization outside animation tracks','canonicalBasePreserved':True}})
        display['nodes']=[index]
    encoded=json.dumps(scene,separators=(',',':')).encode();encoded+=b' '*((-len(encoded))%4)
    result=struct.pack('<III',0x46546c67,2,20+len(encoded)+len(tail))+struct.pack('<II',len(encoded),kind)+encoded+tail
    path.write_bytes(result)
    assert path.read_bytes()[20+len(encoded):]==tail
    report={'passed':True,'asset':str(path),'sha256':hashlib.sha256(result).hexdigest(),'normalizationParent':'CanonicalHumanScale',
      'scale':SCALE,'binaryMeshSkinAnimationPayloadUnchanged':True,'binaryChunkSHA256':hashlib.sha256(tail).hexdigest(),
      'animationChannelDataUnchanged':True,'reason':'Rig-root scale tracks override object scale; the unanimated parent keeps all clips at human scale'}
    (ROOT/'runtime/animation-normalization.json').write_text(json.dumps(report,indent=2))
    print('ANIMATION_NORMALIZED',json.dumps(report))
if __name__=='__main__':normalize_animated_glb(ROOT/'runtime/animated-citizen.glb')
