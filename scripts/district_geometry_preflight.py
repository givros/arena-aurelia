"""Check complete kit projections in an isolated, unsaved Blender scene."""
from pathlib import Path
import bpy,sys
R=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(R/'scripts'))
import build_arena as B
import district_life_geometry as D
bpy.ops.wm.read_factory_settings(use_empty=True)
B.mats()
D.apply(B)
print('DISTRICT_KIT_PREFLIGHT_PASSED',flush=True)
