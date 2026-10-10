from pathlib import Path
import json, hashlib
from PIL import Image
import numpy as np
root=Path('performance/primitive-images');results=[]
for original in sorted(root.glob('*_original.png')):
 merged=original.with_name(original.name.replace('_original.png','_merged.png'))
 if not merged.exists():raise RuntimeError(f'Missing paired image {merged}')
 a=np.asarray(Image.open(original).convert('RGB'),dtype=np.int16);b=np.asarray(Image.open(merged).convert('RGB'),dtype=np.int16)
 delta=np.abs(a-b);peak=delta.max(axis=2)
 result={'image':original.name.removesuffix('_original.png'),'meanRGBError':float(delta.mean()),'maximumChannelError':int(delta.max()),'pixelsOver2':int((peak>2).sum()),'fractionPixelsOver2':float((peak>2).mean()),'originalSHA256':hashlib.sha256(original.read_bytes()).hexdigest(),'mergedSHA256':hashlib.sha256(merged.read_bytes()).hexdigest()}
 result['status']='passed' if result['meanRGBError']<.025 and result['fractionPixelsOver2']<.001 else 'failed';results.append(result)
report={'status':'passed' if results and all(r['status']=='passed' for r in results) else 'failed','scope':'Paired original and merged full character geometry in the actual production WebGPU renderer at native DPR, 4x MSAA, original 4096 PCF shadows; all static roles, palette variants, all four clips of all animated prototypes, and stone override.','threshold':{'meanRGBErrorMax':.025,'fractionPixelsOver2Max':.001,'pixelUnits':'8-bit RGB'},'results':results}
Path('primitive_visual_validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({'status':report['status'],'cases':len(results),'failures':[r for r in results if r['status']=='failed'],'worstMean':max((r['meanRGBError'] for r in results),default=None)}))
