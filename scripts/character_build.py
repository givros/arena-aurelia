from pathlib import Path
import subprocess, sys, json
ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena')
OUT=ROOT/'characters'; SKILL=Path('C:/Users/limou/.codex/skills/blender-lowpoly-character')
for spec_path in sorted((OUT/'specs').glob('*.json')):
    spec=json.loads(spec_path.read_text()); gid=spec['garment_id']
    command=[sys.executable,str(SKILL/'scripts/core/run_scoped_blender_operation.py'),
      '--working-blend',str(OUT/'CharacterBase.blend'),'--script',str(ROOT/'scripts/character_garment_builder.py'),
      '--allow-scope','garment:'+gid,'--artifacts-dir',str(OUT/'reports'),'--blender','C:/Program Files/Blender Foundation/Blender 5.1/blender.exe',
      '--','--helper-dir',str(SKILL/'scripts'),'--action','update' if '--update' in sys.argv else 'create','--spec',str(spec_path),'--report',str(OUT/'reports'/(gid+'_build.json'))]
    print('Building',gid,flush=True)
    completed=subprocess.run(command,capture_output=True,text=True)
    (OUT/'reports'/(gid+'_build.log')).write_text(completed.stdout+completed.stderr)
    if completed.returncode:
        print((completed.stdout+completed.stderr)[-5000:]);sys.exit(completed.returncode)
    print('Guard passed',gid,flush=True)
