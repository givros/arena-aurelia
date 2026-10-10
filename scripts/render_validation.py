import bpy,sys,json
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'));import build_arena as B
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else ['1'];p=args[0]
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
bpy.context.scene.cycles.samples=32;bpy.context.scene.render.resolution_percentage=100
names=['reference','top','approach','facade','seating','floor','vip','hypogeum','market','reverse']
if len(args)>1:names=args[1:]
for n in names:B.render(n,f'pass{p}_{n}.png',100);print('VIEW_DONE',p,n,flush=True)
