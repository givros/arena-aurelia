"""Read-only actual court support check after an anchor-only paving adjustment."""
from pathlib import Path
import sys,json,bpy
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import district_life_population as P
source=R/'Aurelia_Arena.blend';before=P.sha(source);bpy.ops.wm.open_mainfile(filepath=str(source))
result=P.apply_population(R,validate_only=True,layout_paths=[R/'civic_court_layout.json'])
result.update(sourceSHA256=before,sourceUnchanged=P.sha(source)==before,layoutSHA256=P.sha(R/'civic_court_layout.json'))
(R/'characters/civic_life_preflight.json').write_text(json.dumps(result,indent=2))
print('CIVIC_LIFE_PREFLIGHT',json.dumps({k:v if not isinstance(v,list) else len(v) for k,v in result.items()}),flush=True)
assert result['passed'] and result['sourceUnchanged'] and not result['rejectedAnchors']
