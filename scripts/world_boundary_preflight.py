"""Build the physical city edge in memory without changing saved source."""
from pathlib import Path
import bpy,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
import world_boundary_geometry as W
bpy.ops.wm.open_mainfile(filepath=str(R/'Aurelia_Arena.blend'))
B.mats()
W.apply(B)
print('WORLD_BOUNDARY_PREFLIGHT_PASSED',flush=True)
