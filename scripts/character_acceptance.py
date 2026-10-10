from pathlib import Path
import json,hashlib
ROOT=Path('E:/Dev/underwater-colony/artifacts/roman-arena/characters')
names=['garment-validation.json','CharacterBase_animation_validation.json','CharacterBase_animation_workflow.json','CharacterBase_animation_qc.json','reports/CharacterBase_export_workflow.json','runtime-validation.json']
checks={n:json.loads((ROOT/n).read_text())['passed'] for n in names}
qc=json.loads((ROOT/'garment-qc.json').read_text())
checks['garment-qc.json']=qc['status']=='ok' and all((ROOT/'garment-qc'/('roman_wardrobe_isolated_'+name+'.png')).exists() for name in ['bronze_armor','gladiator_sword','guard_shield','guard_spear','hair_cap','leather_belt','roman_helmet','roman_sandals','roman_tunic'])
assert all(checks.values())
canonical=ROOT/'CharacterBase.blend';source_sha=hashlib.sha256(canonical.read_bytes()).hexdigest()
assert qc['input_blend_sha256'].lower()==source_sha
assert len(list(ROOT.rglob('*.blend')))==1
report={'passed':True,'checks':checks,'canonical_blend':str(canonical),'canonical_sha256':source_sha,
 'base_source':'blender-lowpoly-character exact bundled CharacterBase; created once',
 'base_contract':{'vertices':1596,'triangles':3134,'bones':49,'constraints':7},
 'roles':['citizen','merchant','worker','noble','seated-spectator','guard','gladiator'],
 'animations':['Idle','Walk','Run','Jump'],
 'visual_qc':['roman-roles-qc.png','seated-spectator-qc.png','guard-qc.png'],
 'assumptions':['The aerial reference cannot resolve seams or facial details. Plain earth-color tunics and explicitly requested Roman role accessories are used.',
 'Crowd clothing color variation is applied to runtime derived assets while the base signatures are preserved.'],
 'source_unchanged_by_runtime_exports':True}
(ROOT/'acceptance.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
