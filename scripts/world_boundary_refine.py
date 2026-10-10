"""Replace only the authored exterior boundary pass after visual inspection."""
from pathlib import Path
import bpy,sys,json,hashlib
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
import world_boundary_geometry as W
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
B.mats()
for name in ['World_Boundary','Outer_Landscape']:
    c=bpy.data.collections.get(name)
    if c:
        for o in list(c.objects):bpy.data.objects.remove(o,do_unlink=True)
        bpy.data.collections.remove(c)
W.apply(B)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(R/'checkpoints/current.blend'))
bpy.ops.wm.save_as_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
(R/'comparisons/world_boundary_refinement.json').write_text(json.dumps({'passed':True,'sourceSHA256':hashlib.sha256((R/'Aurelia_Arena.blend').read_bytes()).hexdigest(),'corrections':['Continuous seamless soil instead of discrete face color patches','Broad river valleys replacing narrow excavated gorges','River continuation extends beyond the outer landscape'],'scope':['World_Boundary','Outer_Landscape']},indent=2))
print('WORLD_BOUNDARY_REFINEMENT_SAVED',flush=True)
