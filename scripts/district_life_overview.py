"""Read-only world coverage views, with identical cameras before and after."""
from pathlib import Path
import bpy,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
tag=sys.argv[sys.argv.index('--')+1] if '--' in sys.argv else 'baseline'
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
bpy.context.scene.frame_set(1)
bpy.context.scene.cycles.samples=24
for name,position,target,lens in [
 ('world',[310,-400,470],[0,115,4],38),
 ('reverse',[160,310,185],[0,45,5],42),
]:
    old=bpy.data.objects.get('CAM_'+name)
    if old:bpy.data.objects.remove(old,do_unlink=True)
    B.camera(name,position,target,lens)
    B.render(name,f'district_life_{tag}_{name}.png',100)
    print('DISTRICT_VIEW_DONE',tag,name,flush=True)
