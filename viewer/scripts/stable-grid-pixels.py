from pathlib import Path
import json,hashlib
import numpy as np
from PIL import Image
folder=Path('performance/grid-images');results=[]
for a in sorted(folder.glob('*_original.png')):
 b=a.with_name(a.name.replace('_original.png','_stable.png'));x=np.asarray(Image.open(a).convert('RGB'),dtype=np.int16);y=np.asarray(Image.open(b).convert('RGB'),dtype=np.int16);d=np.abs(x-y);peak=d.max(axis=2)
 results.append({'id':a.stem.removesuffix('_original'),'status':'passed' if d.mean()<.001 and (peak>1).mean()<.00001 else 'failed','meanRGBError':float(d.mean()),'maxChannelError':int(d.max()),'pixelsOver1':int((peak>1).sum()),'originalSHA256':hashlib.sha256(a.read_bytes()).hexdigest(),'stableSHA256':hashlib.sha256(b.read_bytes()).hexdigest()})
report={'status':'passed' if results and all(x['status']=='passed' for x in results) else 'failed','sourceSHA256':json.loads(Path('public/assets/environment.json').read_text())['sourceHash'],'moduleSHA256':hashlib.sha256(Path('src/stable-clustered-lighting.js').read_bytes()).hexdigest(),'pixelUnits':'8-bit RGB','scope':'17 paired original/stable native-resolution WebGPU captures with all53lights,4MSAA,4096PCFshadows and actual day/night/camera/resize through4K.','results':results}
Path('stable_grid_pixel_validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'status':report['status'],'cases':len(results),'worstMean':max(x['meanRGBError'] for x in results),'worstMax':max(x['maxChannelError'] for x in results),'failed':[x['id'] for x in results if x['status']=='failed']}))
