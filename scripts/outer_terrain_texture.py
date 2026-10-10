"""Original seamless fine soil and herb variation for the surrounding hills."""
from pathlib import Path
import numpy as np
from PIL import Image
R=Path(__file__).resolve().parents[1]
N=2048;rng=np.random.default_rng(8291)
field=np.zeros((N,N))
for size,amplitude in [(3,.065),(7,.055),(17,.04),(41,.03),(97,.023),(211,.015)]:
    grid=(rng.random((size,size))*255).astype('uint8')
    tiled=Image.fromarray(np.tile(grid,(3,3))).resize((3*N,3*N),Image.Resampling.BICUBIC)
    layer=np.asarray(tiled.crop((N,N,2*N,2*N)),dtype=float)/255-.5
    field+=amplitude*layer
value=1+field+rng.normal(0,.013,(N,N))
rgb=np.clip(np.array([128,124,97])[None,None,:]*value[:,:,None],0,255).astype('uint8')
Image.fromarray(rgb).save(R/'textures/mediterranean_earth.png')
print('ORIGINAL_OUTER_TERRAIN_TEXTURE_SAVED')
