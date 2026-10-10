import json, hashlib
from pathlib import Path
from PIL import Image
import numpy as np

root=Path(__file__).resolve().parents[1]
run=json.loads((root/'performance/bundle_validation.json').read_text())
checks=[]
def compare(name,base,left,right):
    a=np.asarray(Image.open(root/(base+left+'.png')).convert('RGB')).astype(np.int16)
    b=np.asarray(Image.open(root/(base+right+'.png')).convert('RGB')).astype(np.int16)
    delta=np.abs(a-b); bad=np.any(delta>2,axis=2)
    item={'name':name,'left':base+left+'.png','right':base+right+'.png','maximumChannelDelta':int(delta.max()),'meanChannelDelta':float(delta.mean()),'pixelsOverTwoLevels':int(bad.sum()),'pixelFractionOverTwoLevels':float(bad.mean()),'identical':bool(not delta.any())}
    item['status']='passed' if item['meanChannelDelta']<0.025 and item['pixelFractionOverTwoLevels']<0.001 else 'failed'
    checks.append(item)
for case in run['results']:
    compare(case['view']+' initial '+str(case['hour']),case['base'],'_normal','_bundle')
    compare(case['view']+' reuse '+str(case['hour']),case['base'],'_normal','_reuse')
for case in run['temporal']:
    compare('Cached '+case['change']+' uniform update',case['base'],'_normal','_cached')
result={'status':'passed' if all(c['status']=='passed' for c in checks) and not run['errors'] else 'failed','sourceSHA256':run['sourceHash'],'checks':checks,'temporalMembership':run['temporal'],'errors':run['errors'],'threshold':'Mean absolute 8-bit RGB error <0.025 and <0.1% pixels exceeding 2 channel levels; exact counts retained.','build':{p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in (root/'dist/assets').glob('*.js')}}
(root/'bundle_visual_validation.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
