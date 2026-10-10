"""Read-only population preflight, interior by default or all layouts with --all."""
from pathlib import Path
from collections import Counter
import sys,json,hashlib,argparse,bpy
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'scripts'))
import district_life_population as P
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
parser=argparse.ArgumentParser();parser.add_argument('--all',action='store_true');parser.add_argument('--layout',action='append')
options=parser.parse_args(args)
source=R/'Aurelia_Arena.blend';before=P.sha(source)
bpy.ops.wm.open_mainfile(filepath=str(source))
paths=[R/p for p in options.layout] if options.layout else (None if options.all else [R/'arena_interior_life_layout.json'])
result=P.apply_population(R,validate_only=True,layout_paths=paths)
result['sourceSHA256']=before;result['sourceUnchanged']=P.sha(source)==before
result['layouts']=[{'path':p.name,'sha256':P.sha(p)} for p,_ in (P.read_layouts(R) if paths is None else [(p,None) for p in paths])]
result['zoneCounts']=dict(Counter(e['zone'] for e in result['accepted']+result['npcs']))
result['rejectionReasons']=dict(Counter(e['reason'].split(':')[0] for e in result['rejectedAnchors']))
if options.all:
    # Prove the city broad phase preserves the original full-scene ray results.
    support=P.GeometrySupport();points=[e['sourcePosition'] for e in result['accepted']]
    points += [q for e in result['npcs'] if e.get('path') for q in P.source(e['path'])]
    probes=[points[min(len(points)-1,round(i*(len(points)-1)/127))] for i in range(128)] if points else []
    differences=[]
    for p in probes:
        if support.ground(p)!=P.SourceGeometrySupport.ground(support,p) or support.blocked(p,.53)!=P.SourceGeometrySupport.blocked(support,p,.53):differences.append(p)
    result['supportBroadPhaseEquivalence']={'probes':len(probes),'differences':differences,'passed':not differences}
    result['passed']=result['passed'] and not differences
report='district_life_preflight.json' if options.all or options.layout else 'interior_life_preflight.json'
(R/'characters'/report).write_text(json.dumps(result,indent=2))
print('DISTRICT_PREFLIGHT' if options.all else 'INTERIOR_PREFLIGHT',json.dumps({k:v if not isinstance(v,list) else len(v) for k,v in result.items()}),flush=True)
assert result['passed'] and result['sourceUnchanged']
