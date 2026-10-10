"""Reference-aligned and eye-height evidence from the saved street revision."""
from pathlib import Path
import bpy, sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['review','reference']
tag=args[0]
names=args[1:] or ['reference','market','approach']
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
s=bpy.context.scene
s.frame_set(1)
s.cycles.samples=24 if tag=='layout' else 32
s.render.resolution_percentage=100
for name in names:
    B.render(name,f'street_life_{tag}_{name}.png',100)
    print('STREET_VIEW_DONE',tag,name,flush=True)
