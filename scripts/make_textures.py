from PIL import Image,ImageFilter,ImageDraw
import numpy as np
from pathlib import Path
R=Path(__file__).resolve().parents[1];rng=np.random.default_rng(17);N=1024
def noise(scale):
    s=max(2,N//scale);a=(rng.random((s,s))*255).astype('uint8');return np.asarray(Image.fromarray(a).resize((N,N),Image.Resampling.BICUBIC),dtype=float)/255-.5
fine=noise(1);medium=noise(12);broad=noise(100)
for name,color in [('travertine',(173,156,127)),('sand',(184,146,94)),('paving',(144,136,116))]:
    value=1+fine*.12+medium*.14+broad*.18
    a=np.clip(np.array(color)[None,None,:]*value[:,:,None],0,255).astype('uint8');im=Image.fromarray(a)
    if name=='travertine':
        d=ImageDraw.Draw(im,'RGBA')
        for y in [0,256,512,768]:
            d.line([(0,y),(1024,y)],fill=(59,50,39,140),width=4)
            for x in range((y//256%2)*256,1024,512):d.line([(x,y),(x,y+256)],fill=(63,55,43,120),width=3)
        for _ in range(1100):
            x,y=rng.integers(0,N,2);d.ellipse((x,y,x+int(rng.integers(1,7)),y+int(rng.integers(1,3))),fill=(59,48,34,35))
    elif name=='paving':
        d=ImageDraw.Draw(im,'RGBA')
        for y in range(0,N,256):
            d.line([(0,y),(N,y)],fill=(57,52,40,150),width=7)
            for x in range((y//256%2)*128,N,256):d.line([(x,y),(x,y+256)],fill=(57,52,40,145),width=6)
    im.save(R/'textures'/f'{name}.png')
print('Generated original 1024px surface textures')
