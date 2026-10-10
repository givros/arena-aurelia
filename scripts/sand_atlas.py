"""Original arena-wide sand atlas: physical wear follows the combat floor, not a tiled grid."""
from PIL import Image,ImageDraw,ImageFilter
from pathlib import Path
import numpy as np,math
R=Path(__file__).resolve().parents[1];N=4096;rng=np.random.default_rng(198)
def layer(size):
    a=(rng.random((size,size))*255).astype('uint8');return np.asarray(Image.fromarray(a).resize((N,N),Image.Resampling.BICUBIC),dtype=np.float32)/255-.5
v=1+layer(16)*.075+layer(74)*.08+layer(360)*.035+layer(4096)*.07
a=np.clip(np.array([186,159,115],dtype=np.float32)[None,None,:]*v[:,:,None],0,255).astype('uint8');im=Image.fromarray(a);del a,v
def xy(x,y):return (int((x/140+.5)*N),int((.5-y/94)*N))
wear=Image.new('RGBA',(N,N));d=ImageDraw.Draw(wear)
for _ in range(125):
    x=float(rng.uniform(-55,55));y=float(rng.uniform(-33,33));angle=float(rng.uniform(0,6.28));length=float(rng.uniform(.7,4.8))
    points=[xy(x+math.cos(angle+t*.05)*t,y+math.sin(angle+t*.05)*t) for t in np.linspace(0,length,12)]
    d.line(points,fill=(80,64,41,int(rng.integers(14,43))),width=int(rng.integers(2,8)))
for _ in range(18):
    x=float(rng.uniform(-46,46));y=float(rng.uniform(-29,29));r=float(rng.uniform(.28,1.05))
    points=[xy(x+math.cos(k*math.tau/32)*r*float(rng.uniform(.8,1.2))*1.6,y+math.sin(k*math.tau/32)*r*float(rng.uniform(.8,1.2))) for k in range(32)]
    d.polygon(points,fill=(87,38,24,int(rng.integers(60,110))))
wear=wear.filter(ImageFilter.GaussianBlur(8));im=Image.alpha_composite(im.convert('RGBA'),wear).convert('RGB');im.save(R/'textures/arena_sand_atlas.png')
print('Created 4096px original full-floor wear atlas')
